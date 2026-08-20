// ══════════════════════════════════════════════════════════════════
// Archivo Madre: envoltorio multi-categoría sobre computeDashboardData()
// (de selfservice_etl.js). Cada categoría es un dashboard independiente
// completo (mismo formato de Base_de_desvios/Stock/Precio); el archivo
// madre guarda todas las categorías cargadas hasta ahora y permite
// verlas o actualizar una (lo que descarga un archivo madre nuevo con
// esa categoría al día y el resto tal como estaban).
// ══════════════════════════════════════════════════════════════════

async function msGzipBase64(str) {
  const bytes = new TextEncoder().encode(str);
  const stream = new Blob([bytes]).stream().pipeThrough(new CompressionStream('gzip'));
  const compressedBlob = await new Response(stream).blob();
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(',')[1]);
    reader.onerror = reject;
    reader.readAsDataURL(compressedBlob);
  });
}
async function msDecompressText(b64) {
  const binStr = atob(b64);
  const bytes = new Uint8Array(binStr.length);
  for (let i = 0; i < binStr.length; i++) bytes[i] = binStr.charCodeAt(i);
  const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'));
  return await new Response(stream).text();
}
async function msDecompressJson(b64) {
  const text = await msDecompressText(b64);
  return JSON.parse(text);
}

function msDownloadFile(filename, text) {
  const blob = new Blob([text], { type: 'text/html' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 10000);
}

function msFmtDate(iso) {
  if (!iso) return '';
  const [y, m, d] = iso.split('-');
  return `${d}-${m}-${y}`;
}

const MS_MESES_ORDEN = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto',
  'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];

// ══════════════════════════════════════════════════════════════════
// Fusiona los DATA de varias categorías (cada una con su propio espacio de índices
// para SKU/semana/cadena/mes) en un único DATA combinado, para la vista "Ver todas
// juntas". Cada categoría es autocontenida (mismo formato que computeDashboardData()),
// así que fusionar es: unir los universos (SKU, cadena, semana, mes) y reindexar las
// filas compactas (wsc_rows/liq_rows/interm_rows/price_rows) contra los índices nuevos.
// promo_rows y skus/skus_cadena usan valores reales (SKU, nombres), no índices, así que
// solo se concatenan.
// ══════════════════════════════════════════════════════════════════
function msMergeCategoryData(categories, names) {
  const datas = names.map(n => categories[n].data);

  const semanaOrder = [...new Set(datas.flatMap(d => d.semana_order))].sort();
  const cadenaList = [...new Set(datas.flatMap(d => d.cadena_list))].sort();
  const skuList = [...new Set(datas.flatMap(d => d.sku_list))].sort((a, b) => a - b);
  const semIdx = new Map(semanaOrder.map((s, i) => [s, i]));
  const cadIdx = new Map(cadenaList.map((c, i) => [c, i]));
  const skuIdx = new Map(skuList.map((s, i) => [s, i]));

  // semana -> etiqueta de mes, recolectado de todas las categorías (para reconstruir
  // mes_order/meses_comparacion/sem_mes_idx combinados sin asumir que las categorías
  // cubren exactamente el mismo rango de semanas).
  const semToMes = new Map();
  datas.forEach(d => d.semana_order.forEach((s, i) => semToMes.set(s, d.mes_order[d.sem_mes_idx[i]])));
  const mesOrder = [];
  semanaOrder.forEach(s => { const m = semToMes.get(s); if (m && !mesOrder.includes(m)) mesOrder.push(m); });
  const mesIdxByLabel = new Map(mesOrder.map((m, i) => [m, i]));
  const semMesIdx = semanaOrder.map(s => mesIdxByLabel.get(semToMes.get(s)));
  const mesesComparacion = MS_MESES_ORDEN
    .map(mesNombre => ({ mes: mesNombre, semanas: semanaOrder.filter(s => (semToMes.get(s) || '').startsWith(mesNombre + ' ')) }))
    .filter(m => m.semanas.length);

  const remapWsc = (d) => d.wsc_rows.map(r => {
    const [si, sei, ci, ...rest] = r;
    return [skuIdx.get(d.sku_list[si]), semIdx.get(d.semana_order[sei]), cadIdx.get(d.cadena_list[ci]), ...rest];
  });
  const remapMesRows = (d, rows) => rows.map(r => {
    const [si, mi, ...rest] = r;
    return [skuIdx.get(d.sku_list[si]), mesIdxByLabel.get(d.mes_order[mi]), ...rest];
  });
  const remapPriceRows = (d) => d.price_rows.map(r => {
    const [si, mi, ci, ...rest] = r;
    return [skuIdx.get(d.sku_list[si]), mesIdxByLabel.get(d.mes_order[mi]), cadIdx.get(d.cadena_list[ci]), ...rest];
  });

  const sum = (key) => datas.reduce((a, d) => a + (d.summary[key] || 0), 0);
  const fcstTot = sum('fcst'), sellinTot = sum('sellin'), solicitadoTot = sum('solicitado');

  return {
    summary: {
      semanas_ini: semanaOrder[0], semanas_fin: semanaOrder[semanaOrder.length - 1],
      n_sku: skuList.length, n_excluidos: sum('n_excluidos'),
      fcst: Math.round(fcstTot * 10) / 10, solicitado: Math.round(solicitadoTot * 10) / 10,
      sellin: Math.round(sellinTot * 10) / 10, ventareal: Math.round(sum('ventareal') * 10) / 10,
      quebrados: Math.round(sum('quebrados') * 10) / 10,
      des_pct: fcstTot ? Math.round(sellinTot / fcstTot * 1000) / 10 : 0,
      gap_fs: Math.round((solicitadoTot - fcstTot) * 10) / 10,
      gap_ss: Math.round((solicitadoTot - sellinTot) * 10) / 10,
      gap_fc: Math.round((fcstTot - sellinTot) * 10) / 10,
      marcas: [...new Set(datas.flatMap(d => d.summary.marcas))].sort(),
      subcats: [...new Set(datas.flatMap(d => d.summary.subcats))].sort(),
      categorias: [...new Set(datas.flatMap(d => d.summary.categorias))].sort(),
      cadenas: cadenaList,
    },
    weekly: semanaOrder.map(s => {
      const rows = datas.map(d => {
        const i = d.semana_order.indexOf(s);
        return i === -1 ? null : d.weekly[i];
      }).filter(Boolean);
      return {
        semana: s, mes: semToMes.get(s),
        fcst: Math.round(rows.reduce((a, r) => a + r.fcst, 0) * 10) / 10,
        solicitado: Math.round(rows.reduce((a, r) => a + r.solicitado, 0) * 10) / 10,
        sellin: Math.round(rows.reduce((a, r) => a + r.sellin, 0) * 10) / 10,
        quebrados: Math.round(rows.reduce((a, r) => a + r.quebrados, 0) * 10) / 10,
      };
    }),
    skus: datas.flatMap(d => d.skus),
    skus_cadena: datas.flatMap(d => d.skus_cadena),
    wsc_rows: datas.flatMap(remapWsc),
    sku_list: skuList,
    cadena_list: cadenaList,
    semana_order: semanaOrder,
    mes_order: mesOrder,
    sem_mes_idx: semMesIdx,
    meses_comparacion: mesesComparacion,
    stock_risk: {
      rows: datas.flatMap(d => d.stock_risk.rows),
      ton_riesgo_total: Math.round(datas.reduce((a, d) => a + d.stock_risk.ton_riesgo_total, 0) * 10) / 10,
      ton_vliq_total: Math.round(datas.reduce((a, d) => a + d.stock_risk.ton_vliq_total, 0) * 10) / 10,
      n_sku: datas.reduce((a, d) => a + d.stock_risk.n_sku, 0),
      snapshot_fecha: datas[0].stock_risk.snapshot_fecha,
    },
    liq_rows: datas.flatMap(d => remapMesRows(d, d.liq_rows)),
    interm_rows: datas.flatMap(d => remapMesRows(d, d.interm_rows)),
    price_rows: datas.flatMap(remapPriceRows),
    promo_rows: datas.flatMap(d => d.promo_rows),
  };
}

async function runMasterFlow() {
  let categories = {}; // nombre -> { data: <DATA>, actualizado: 'YYYY-MM-DD' }
  try {
    categories = await msDecompressJson(window.__MASTER_CATEGORIES_B64GZ__);
  } catch (e) {
    console.error('No se pudo leer las categorías del archivo madre:', e);
    categories = {};
  }

  return new Promise((resolve) => {
    const screenPick = document.getElementById('msScreenPick');
    const screenUpdate = document.getElementById('msScreenUpdate');
    const screenDone = document.getElementById('msScreenDone');
    const categoryListEl = document.getElementById('msCategoryList');
    const categorySelect = document.getElementById('msCategorySelect');
    const categoryNewInput = document.getElementById('msCategoryNew');
    const status = document.getElementById('ssStatus');
    const btn = document.getElementById('ssGenerateBtn');
    const fBase = document.getElementById('ssFileBase');
    const fStock = document.getElementById('ssFileStock');
    const fPrecio = document.getElementById('ssFilePrecio');
    const fPromo = document.getElementById('ssFilePromo');

    function showScreen(el) {
      [screenPick, screenUpdate, screenDone].forEach(s => { s.style.display = s === el ? 'block' : 'none'; });
    }

    function renderCategoryList() {
      const names = Object.keys(categories).sort();
      if (!names.length) {
        categoryListEl.innerHTML = '<p class="ms-empty-note">Todavía no hay ninguna categoría cargada — empieza actualizando una.</p>';
        return;
      }
      const allBtn = names.length > 1
        ? `<button type="button" class="ms-category-btn ms-category-btn-all" data-cat="__all__">Ver todas juntas<span class="ms-cat-meta">${names.join(' + ')}</span></button>`
        : '';
      categoryListEl.innerHTML = allBtn + names.map(name => {
        const meta = categories[name].actualizado ? `Actualizado ${msFmtDate(categories[name].actualizado)}` : '';
        return `<button type="button" class="ms-category-btn" data-cat="${name}">${name}<span class="ms-cat-meta">${meta}</span></button>`;
      }).join('');
      categoryListEl.querySelectorAll('.ms-category-btn').forEach(elBtn => {
        elBtn.addEventListener('click', () => {
          const name = elBtn.dataset.cat;
          const data = name === '__all__' ? msMergeCategoryData(categories, names) : categories[name].data;
          window.DATA = data;
          document.getElementById('uploadOverlay').style.display = 'none';
          resolve(data);
        });
      });
    }

    function renderCategorySelect() {
      const names = Object.keys(categories).sort();
      categorySelect.innerHTML = names.map(n => `<option value="${n}">${n}</option>`).join('') +
        '<option value="__new__">+ Categoría nueva…</option>';
      categoryNewInput.style.display = names.length ? 'none' : 'block';
      if (!names.length) categorySelect.value = '__new__';
    }
    categorySelect.addEventListener('change', () => {
      categoryNewInput.style.display = categorySelect.value === '__new__' ? 'block' : 'none';
    });

    document.getElementById('msGoUpdateBtn').addEventListener('click', () => {
      renderCategorySelect();
      status.textContent = ''; status.className = 'ss-status';
      showScreen(screenUpdate);
    });
    document.getElementById('msBackFromUpdateBtn').addEventListener('click', () => showScreen(screenPick));
    document.getElementById('msBackFromDoneBtn').addEventListener('click', () => {
      renderCategoryList();
      showScreen(screenPick);
    });

    btn.addEventListener('click', async () => {
      let categoryName = categorySelect.value === '__new__' ? categoryNewInput.value.trim() : categorySelect.value;
      if (!categoryName) {
        status.textContent = 'Escribe el nombre de la categoría.';
        status.className = 'ss-status ss-error';
        return;
      }
      if (!fBase.files[0] || !fStock.files[0] || !fPrecio.files[0]) {
        status.textContent = 'Falta subir alguno de los 3 archivos obligatorios.';
        status.className = 'ss-status ss-error';
        return;
      }
      btn.disabled = true;
      status.textContent = 'Procesando…';
      status.className = 'ss-status';
      try {
        const data = await computeDashboardData(fBase.files[0], fStock.files[0], fPrecio.files[0], fPromo.files[0] || null, msg => {
          status.textContent = msg;
        });
        if (data._promo_warning) alert(data._promo_warning);

        const today = new Date().toISOString().slice(0, 10);
        categories[categoryName] = { data, actualizado: today };

        status.textContent = 'Armando el archivo madre actualizado…';
        // shellText es el molde (ver inject_frio_madre.py) con los dos placeholders
        // de datos todavía sin reemplazar — se rellenan de nuevo acá para producir
        // el próximo archivo madre descargable. Los tokens se arman concatenados
        // (no como texto literal contiguo) para que el propio build no los pise:
        // si aparecieran completos en el código fuente, el reemplazo de una sola
        // pasada en Python los corrompería a ellos también.
        const MASTER_TOKEN = '__MASTER_CATEGORIES' + '_VALUE__';
        const SELF_TOKEN = '__SELF_TEMPLATE' + '_VALUE__';
        const shellText = await msDecompressText(window.__SELF_TEMPLATE_B64GZ__);
        const categoriesB64gz = await msGzipBase64(JSON.stringify(categories));
        const finalHtml = shellText
          .replace(MASTER_TOKEN, categoriesB64gz)
          .replace(SELF_TOKEN, window.__SELF_TEMPLATE_B64GZ__);
        msDownloadFile('Archivo Madre - Desvío Semanal.html', finalHtml);

        document.getElementById('msDoneMsg').textContent =
          `"${categoryName}" quedó al día (${msFmtDate(today)}) y se descargó el archivo madre actualizado con las ${Object.keys(categories).length} categoría(s) cargadas.`;
        btn.disabled = false;
        status.textContent = ''; status.className = 'ss-status';
        showScreen(screenDone);

        document.getElementById('msViewNowBtn').onclick = () => {
          window.DATA = data;
          document.getElementById('uploadOverlay').style.display = 'none';
          resolve(data);
        };
      } catch (err) {
        console.error(err);
        status.textContent = 'Error procesando los archivos: ' + err.message + ' — revisa que sean los archivos correctos e intenta de nuevo.';
        status.className = 'ss-status ss-error';
        btn.disabled = false;
      }
    });

    renderCategoryList();
    showScreen(screenPick);
  });
}
