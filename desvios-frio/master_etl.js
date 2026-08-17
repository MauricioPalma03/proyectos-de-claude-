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
      categoryListEl.innerHTML = names.map(name => {
        const meta = categories[name].actualizado ? `Actualizado ${msFmtDate(categories[name].actualizado)}` : '';
        return `<button type="button" class="ms-category-btn" data-cat="${name}">${name}<span class="ms-cat-meta">${meta}</span></button>`;
      }).join('');
      categoryListEl.querySelectorAll('.ms-category-btn').forEach(elBtn => {
        elBtn.addEventListener('click', () => {
          const name = elBtn.dataset.cat;
          window.DATA = categories[name].data;
          document.getElementById('uploadOverlay').style.display = 'none';
          resolve(categories[name].data);
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
