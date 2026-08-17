// ══════════════════════════════════════════════════════════════════
// Autoservicio: arma DATA a partir de los 3 Excel que sube el usuario,
// 100% en el navegador (sin servidor). Port 1:1 de build_data_frio.py.
// ══════════════════════════════════════════════════════════════════
const MESES_ES = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];
const MESES_ABR = ['', 'Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];

function ssNum(v) {
  if (v === null || v === undefined || v === '') return 0;
  const n = Number(v);
  return Number.isFinite(n) ? n : 0;
}
function ssStr(v, fallback) {
  if (v === null || v === undefined) return fallback;
  const s = String(v).trim();
  return s === '' ? fallback : s;
}
function ssSemLabel(s) {
  s = Math.trunc(s);
  const yy = Math.trunc(s / 100);
  const ww = s % 100;
  return `${String(yy).slice(-2)}-S${String(ww).padStart(2, '0')}`;
}
function ssParseMes(v) {
  if (v instanceof Date) return [v.getFullYear(), v.getMonth() + 1];
  if (typeof v === 'number') {
    const s = String(Math.trunc(v));
    return [parseInt(s.slice(0, 4), 10), parseInt(s.slice(4, 6), 10)];
  }
  if (typeof v === 'string') {
    return [parseInt(v.slice(0, 4), 10), parseInt(v.slice(4, 6), 10)];
  }
  return [NaN, NaN];
}
function ssRound(x, d) {
  const f = Math.pow(10, d);
  return Math.round(x * f) / f;
}
function ssIsoWeekInfo(date) {
  const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  const dayNum = (d.getUTCDay() + 6) % 7;
  d.setUTCDate(d.getUTCDate() - dayNum + 3);
  const firstThursday = new Date(Date.UTC(d.getUTCFullYear(), 0, 4));
  const firstDayNum = (firstThursday.getUTCDay() + 6) % 7;
  firstThursday.setUTCDate(firstThursday.getUTCDate() - firstDayNum + 3);
  const weekNum = 1 + Math.round((d - firstThursday) / (7 * 24 * 3600 * 1000));
  return [d.getUTCFullYear(), weekNum];
}
function ssFormatSnapshotFecha(filename) {
  const m = filename.match(/(\d{4})(\d{2})(\d{2})(?!\d)/);
  if (m) {
    const [, yyyy, mm, dd] = m;
    const mi = parseInt(mm, 10);
    if (mi >= 1 && mi <= 12) return `${dd}-${MESES_ABR[mi]}-${yyyy}`;
  }
  const now = new Date();
  return `${String(now.getDate()).padStart(2, '0')}-${MESES_ABR[now.getMonth() + 1]}-${now.getFullYear()}`;
}
async function ssReadWorkbook(file) {
  const buf = await file.arrayBuffer();
  return XLSX.read(buf, { cellDates: true });
}
function ssSheetRows(wb, sheetName) {
  const ws = wb.Sheets[sheetName || wb.SheetNames[0]];
  if (!ws) throw new Error(`No se encontró la hoja "${sheetName}" — hojas disponibles: ${wb.SheetNames.join(', ')}. ¿Subiste el archivo correcto en este campo?`);
  return XLSX.utils.sheet_to_json(ws, { defval: null, raw: true });
}
function ssRequireColumns(rows, requiredCols, fileLabel) {
  const present = new Set(Object.keys(rows[0] || {}));
  const missing = requiredCols.filter(c => !present.has(c));
  if (missing.length) {
    throw new Error(`El archivo de "${fileLabel}" no tiene las columnas esperadas (falta: ${missing.join(', ')}) — ¿lo subiste en el campo correcto?`);
  }
}
function ssNumOrNull(v) {
  if (v === null || v === undefined || v === '') return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}
function ssParseDateCell(v) {
  if (v instanceof Date) return Number.isFinite(v.getTime()) ? v : null;
  if (typeof v === 'number') {
    const d = XLSX.SSF.parse_date_code(v);
    return d ? new Date(Date.UTC(d.y, d.m - 1, d.d)) : null;
  }
  if (typeof v === 'string') {
    const s = v.trim();
    if (!s) return null;
    let m = s.match(/^(\d{4})-(\d{2})-(\d{2})/);
    if (m) return new Date(Date.UTC(+m[1], +m[2] - 1, +m[3]));
    m = s.match(/^(\d{1,2})[\/-](\d{1,2})[\/-](\d{4})/);
    if (m) return new Date(Date.UTC(+m[3], +m[2] - 1, +m[1]));
    const parsed = new Date(s);
    return Number.isFinite(parsed.getTime()) ? parsed : null;
  }
  return null;
}
function ssTitleCase(v) {
  return String(v).trim().toLowerCase().replace(/\b\w/g, c => c.toUpperCase());
}
const SS_CADENA_MAP = {
  CENCOSUD: 'Cencosud', UNIMARC: 'Unimarc', TOTTUS: 'Tottus', ALVI: 'Alvi',
  WALMART: 'Walmart', TRADICIONAL: 'Canal Tradicional', SUPERREGIONAL: 'Supermercados Region',
};
function ssMapCadenaPromo(v) {
  const key = String(v).trim().toUpperCase();
  return SS_CADENA_MAP[key] || ssTitleCase(v);
}
function ssIsoDateStr(d) {
  return d.toISOString().slice(0, 10);
}
function ssSemIdxForDateStr(dateStr, semanaOrder) {
  const [y, m, d] = dateStr.split('-').map(Number);
  const [isoY, isoW] = ssIsoWeekInfo(new Date(Date.UTC(y, m - 1, d)));
  const idx = semanaOrder.indexOf(ssSemLabel(isoY * 100 + isoW));
  return idx === -1 ? null : idx;
}

// Calendario de promociones (GRID_PROMOCIONAL) — 4 hojas con columnas casi
// idénticas (una difiere: YOGHURT), port 1:1 del bloque equivalente en
// build_data_frio.py. Es opcional: si no viene el archivo, se usa el último
// calendario ya guardado (promo_rows_backup.json, bundleado en la página).
function ssParsePromoGridRaw(wbPromo) {
  const sheetsComunes = ['UNTABLES, JUGOS CV, PASTAS (2)', 'UNTABLES, JUGOS CV, PASTAS', 'QUESOS'];
  const combined = [];
  for (const sheetName of sheetsComunes) {
    if (!wbPromo.Sheets[sheetName]) continue;
    const rows = XLSX.utils.sheet_to_json(wbPromo.Sheets[sheetName], { defval: null, raw: true });
    for (const r of rows) {
      combined.push({
        sap: r['SAP'], cadena: r['CADENA'], status: r['STATUS PROMO FINAL'],
        inicio: ssParseDateCell(r['INICIO']), termino: ssParseDateCell(r['TÉRMINO']),
        dcto: ssNumOrNull(r['DCTO TOTAL']),
      });
    }
  }
  if (wbPromo.Sheets['YOGHURT']) {
    const rows = XLSX.utils.sheet_to_json(wbPromo.Sheets['YOGHURT'], { defval: null, raw: true });
    for (const r of rows) {
      const pvpPromo = ssNumOrNull(r['PVP Promo']), pvpRegular = ssNumOrNull(r['PVP Regular']);
      const dcto = (pvpPromo !== null && pvpRegular) ? 1 - (pvpPromo / pvpRegular) : null;
      combined.push({
        sap: r['Código SAP'], cadena: r['Cadena'], status: r['Stattus'],
        inicio: ssParseDateCell(r['Fecha Inicio']), termino: ssParseDateCell(r['Fecha Término']),
        dcto,
      });
    }
  }
  return combined;
}
function ssBuildPromoRowsFromGrid(wbPromo, skuIdxMap, semanaOrder) {
  const raw = ssParsePromoGridRaw(wbPromo);
  const seen = new Set();
  const out = [];
  for (const r of raw) {
    if (!r.inicio || !r.termino) continue;
    const skuNum = Math.trunc(Number(r.sap));
    if (!Number.isFinite(skuNum) || !skuIdxMap.has(skuNum)) continue;
    const status = ssTitleCase(r.status == null || r.status === '' ? 'nan' : r.status);
    if (status === 'Rechazado' || status === 'Nan') continue;
    const inicioStr = ssIsoDateStr(r.inicio), terminoStr = ssIsoDateStr(r.termino);
    const cadena = ssMapCadenaPromo(r.cadena);
    const key = skuNum + '|' + cadena + '|' + inicioStr + '|' + terminoStr + '|' + status;
    if (seen.has(key)) continue;
    seen.add(key);
    out.push({
      sku: skuNum, cadena, status, inicio: inicioStr, termino: terminoStr,
      semIni: ssSemIdxForDateStr(inicioStr, semanaOrder), semFin: ssSemIdxForDateStr(terminoStr, semanaOrder),
      dcto: r.dcto === null ? null : ssRound(r.dcto * 100, 1),
    });
  }
  return out;
}
function ssBuildPromoRowsFromBackup(skuIdxMap, semanaOrder) {
  const out = [];
  for (const r of (window.__PROMO_ROWS_BACKUP__ || [])) {
    if (!skuIdxMap.has(r.sku)) continue;
    out.push({
      sku: r.sku, cadena: r.cadena, status: r.status, inicio: r.inicio, termino: r.termino,
      semIni: ssSemIdxForDateStr(r.inicio, semanaOrder), semFin: ssSemIdxForDateStr(r.termino, semanaOrder), dcto: r.dcto,
    });
  }
  return out;
}

async function computeDashboardData(baseFile, stockFile, precioFile, promoFile, onProgress) {
  const report = onProgress || (() => {});
  // ── 1. Leer y limpiar Base_de_desvios (primera hoja) ──
  report('Leyendo Base de desvíos… (archivo grande, puede tardar 15-20s)');
  const wbBase = await ssReadWorkbook(baseFile);
  const rawRows = ssSheetRows(wbBase);
  if (!rawRows.length) throw new Error('El archivo de Base de desvíos está vacío o no tiene el formato esperado.');
  ssRequireColumns(rawRows, ['SKU', 'Semana', 'CADENA', 'FCST', 'Solicitado', 'Venta Sell IN'], 'Base de desvíos');

  const SEMANAS_EXCLUIR = new Set([202634]); // semanas sin datos reales (recién cargadas en el sistema origen)

  let rows = rawRows.map(r => {
    let subcat = ssStr(r['SubCat DMD'], '-').toUpperCase();
    if (subcat === '0') subcat = '-';
    let categoria = ssStr(r['Categoria Producto'], '-');
    if (categoria === 'YOGHURT') categoria = 'YOGURT';
    return {
      SKU: Math.trunc(ssNum(r['SKU'])),
      NombreProducto: ssStr(r['Nombre Producto'], ''),
      Marca: ssStr(r['Marca'], '-'),
      SubCat: subcat,
      Categoria: categoria,
      CADENA: ssStr(r['CADENA'], '-'),
      Semana: Math.trunc(ssNum(r['Semana'])),
      Mes: r['Mes'],
      VentaSellIn: ssNum(r['Venta Sell IN']),
      FCST: ssNum(r['FCST']),
      Solicitado: ssNum(r['Solicitado']),
      VentaReal: ssNum(r['Venta Real']),
      Quebrados: ssNum(r['Quebrados']),
      Bloqueados: ssNum(r['Bloqueados']),
      VentaSellOut: ssNum(r['Venta Sell OUT']),
    };
  }).filter(r => !SEMANAS_EXCLUIR.has(r.Semana));

  if (!rows.length) throw new Error('No quedaron filas después de limpiar el archivo — revisa que sea el archivo correcto.');

  // Categoria/SubCat canónica por SKU = la de su semana más reciente (reclasificación del maestro).
  const latestBySku = new Map();
  for (const r of rows) {
    const cur = latestBySku.get(r.SKU);
    if (!cur || r.Semana >= cur.semana) latestBySku.set(r.SKU, { semana: r.Semana, categoria: r.Categoria, subcat: r.SubCat });
  }
  for (const r of rows) {
    const c = latestBySku.get(r.SKU);
    r.Categoria = c.categoria;
    r.SubCat = c.subcat;
  }

  // ── 2. Semanas / etiquetas (con el universo COMPLETO de SKU, antes de excluir) ──
  const semanas = [...new Set(rows.map(r => r.Semana))].sort((a, b) => a - b);
  const semLabels = new Map(semanas.map(s => [s, ssSemLabel(s)]));
  const semanaOrder = semanas.map(s => semLabels.get(s));

  const mesPorSemana = new Map();
  const seenSemana = new Set();
  for (const r of rows) {
    if (!seenSemana.has(r.Semana)) { seenSemana.add(r.Semana); mesPorSemana.set(r.Semana, ssParseMes(r.Mes)); }
  }
  const semMesLabel = new Map();
  for (const s of semanas) {
    const [y, m] = mesPorSemana.get(s);
    semMesLabel.set(s, `${MESES_ES[m]} ${y}`);
  }
  const mesOrder = [];
  for (const s of semanas) {
    const lbl = semMesLabel.get(s);
    if (!mesOrder.includes(lbl)) mesOrder.push(lbl);
  }
  const mesesComparacion = [];
  for (let mnum = 1; mnum <= 12; mnum++) {
    const sems = semanas.filter(s => mesPorSemana.get(s)[1] === mnum).map(s => semLabels.get(s));
    if (sems.length) mesesComparacion.push({ mes: MESES_ES[mnum], semanas: sems });
  }

  // ── 3. Exclusión: SKU con FCST=0 en más de 40% de sus semanas ──
  const fcstBySkuSem = new Map();
  for (const r of rows) {
    const k = r.SKU + '|' + r.Semana;
    fcstBySkuSem.set(k, (fcstBySkuSem.get(k) || 0) + r.FCST);
  }
  const skuWeekStats = new Map();
  for (const [k, fcstSum] of fcstBySkuSem) {
    const sku = parseInt(k.split('|')[0], 10);
    let st = skuWeekStats.get(sku);
    if (!st) { st = { n: 0, nz: 0 }; skuWeekStats.set(sku, st); }
    st.n += 1;
    if (fcstSum <= 0.001) st.nz += 1;
  }
  let skuExcluidos = new Set();
  for (const [sku, st] of skuWeekStats) if (st.nz / st.n > 0.4) skuExcluidos.add(sku);

  const ULTIMAS_N_SEMANAS_ADELANTE = 8;
  const semanasAdelante = new Set(semanas.slice(-ULTIMAS_N_SEMANAS_ADELANTE));
  const skusFcstReciente = new Set();
  for (const [k, fcstSum] of fcstBySkuSem) {
    const [skuStr, semStr] = k.split('|');
    if (semanasAdelante.has(parseInt(semStr, 10)) && fcstSum > 0.001) skusFcstReciente.add(parseInt(skuStr, 10));
  }
  const skuReincluidosFcstReciente = [...skuExcluidos].filter(s => skusFcstReciente.has(s)).sort((a, b) => a - b);
  skuExcluidos = new Set([...skuExcluidos].filter(s => !skusFcstReciente.has(s)));

  const SKU_FORZAR_INCLUSION = new Set([30002120]);
  skuExcluidos = new Set([...skuExcluidos].filter(s => !SKU_FORZAR_INCLUSION.has(s)));

  rows = rows.filter(r => !skuExcluidos.has(r.SKU));
  if (!rows.length) throw new Error('Todos los SKU quedaron excluidos — revisa el archivo de Base de desvíos.');

  // ── 4. Metadata por SKU (primera fila encontrada, ya con categoría/subcat canónicas) ──
  const skuDesc = new Map();
  for (const r of rows) if (!skuDesc.has(r.SKU)) skuDesc.set(r.SKU, { nombre: r.NombreProducto, marca: r.Marca, subcat: r.SubCat, categoria: r.Categoria });

  // ── 5. SKU x Cadena (agregado toda la historia) ──
  const gscMap = new Map();
  for (const r of rows) {
    const k = r.SKU + '|' + r.CADENA;
    let a = gscMap.get(k);
    if (!a) { a = { SKU: r.SKU, CADENA: r.CADENA, FCST: 0, Solicitado: 0, SellIn: 0, VentaReal: 0, Quebrados: 0 }; gscMap.set(k, a); }
    a.FCST += r.FCST; a.Solicitado += r.Solicitado; a.SellIn += r.VentaSellIn; a.VentaReal += r.VentaReal; a.Quebrados += r.Quebrados;
  }
  const skusCadenaJson = [];
  for (const a of gscMap.values()) {
    const meta = skuDesc.get(a.SKU);
    const desPct = a.FCST !== 0 ? (a.SellIn / a.FCST) * 100 : null;
    skusCadenaJson.push({
      SKU: a.SKU, CADENA: a.CADENA,
      FCST: ssRound(a.FCST, 3), Solicitado: ssRound(a.Solicitado, 3), SellIn: ssRound(a.SellIn, 3),
      VentaReal: ssRound(a.VentaReal, 3), Quebrados: ssRound(a.Quebrados, 3),
      'Nombre Producto': meta.nombre, Marca: meta.marca, SubCat: meta.subcat, Categoria: meta.categoria,
      gap_FS_t: ssRound(a.Solicitado - a.FCST, 3), gap_SS_t: ssRound(a.Solicitado - a.SellIn, 3),
      des_pct: desPct === null ? null : ssRound(desPct, 3),
      gap_FC_t: ssRound(a.FCST - a.SellIn, 3),
    });
  }

  // ── 6. SKU total (todas las cadenas) ──
  const gMap = new Map();
  for (const r of rows) {
    let a = gMap.get(r.SKU);
    if (!a) { a = { SKU: r.SKU, FCST: 0, Solicitado: 0, SellIn: 0, VentaReal: 0, Quebrados: 0 }; gMap.set(r.SKU, a); }
    a.FCST += r.FCST; a.Solicitado += r.Solicitado; a.SellIn += r.VentaSellIn; a.VentaReal += r.VentaReal; a.Quebrados += r.Quebrados;
  }
  const skusJson = [];
  const gExtra = new Map();
  for (const a of gMap.values()) {
    const meta = skuDesc.get(a.SKU);
    const desPct = a.FCST !== 0 ? (a.SellIn / a.FCST) * 100 : null;
    const gapFC = a.FCST - a.SellIn, gapSS = a.Solicitado - a.SellIn;
    skusJson.push({
      SKU: a.SKU, FCST: ssRound(a.FCST, 3), Solicitado: ssRound(a.Solicitado, 3), SellIn: ssRound(a.SellIn, 3),
      VentaReal: ssRound(a.VentaReal, 3), Quebrados: ssRound(a.Quebrados, 3),
      'Nombre Producto': meta.nombre, Marca: meta.marca, SubCat: meta.subcat, Categoria: meta.categoria,
      gap_FS_t: ssRound(a.Solicitado - a.FCST, 3), gap_SS_t: ssRound(gapSS, 3),
      des_pct: desPct === null ? null : ssRound(desPct, 3),
      gap_FC_t: ssRound(gapFC, 3),
    });
    gExtra.set(a.SKU, { Marca: meta.marca, Categoria: meta.categoria, FCST: a.FCST, SellIn: a.SellIn, des_pct: desPct, gap_FC_t: gapFC, gap_SS_t: gapSS });
  }

  // ── 7. Semanal total (sin filtro), reindexado a todas las semanas ──
  const wkMap = new Map();
  for (const r of rows) {
    let a = wkMap.get(r.Semana);
    if (!a) { a = { FCST: 0, Solicitado: 0, SellIn: 0, Quebrados: 0 }; wkMap.set(r.Semana, a); }
    a.FCST += r.FCST; a.Solicitado += r.Solicitado; a.SellIn += r.VentaSellIn; a.Quebrados += r.Quebrados;
  }
  const weeklyJson = semanas.map(s => {
    const a = wkMap.get(s) || { FCST: 0, Solicitado: 0, SellIn: 0, Quebrados: 0 };
    return { semana: semLabels.get(s), mes: semMesLabel.get(s), fcst: ssRound(a.FCST, 1), solicitado: ssRound(a.Solicitado, 1), sellin: ssRound(a.SellIn, 1), quebrados: ssRound(a.Quebrados, 1) };
  });

  // ── 8. SKU x Semana x Cadena (arrays compactos) ──
  const skuList = [...gMap.keys()].sort((a, b) => a - b);
  const skuIdxMap = new Map(skuList.map((s, i) => [s, i]));
  const semIdxMap = new Map(semanas.map((s, i) => [s, i]));
  const cadenaList = [...new Set(rows.map(r => r.CADENA))].sort();
  const cadenaIdxMap = new Map(cadenaList.map((c, i) => [c, i]));

  const wscMap = new Map();
  for (const r of rows) {
    const k = r.SKU + '|' + r.Semana + '|' + r.CADENA;
    let a = wscMap.get(k);
    if (!a) { a = { SKU: r.SKU, Semana: r.Semana, CADENA: r.CADENA, FCST: 0, Solicitado: 0, SellIn: 0, Quebrados: 0, Bloqueados: 0, SellOut: 0 }; wscMap.set(k, a); }
    a.FCST += r.FCST; a.Solicitado += r.Solicitado; a.SellIn += r.VentaSellIn; a.Quebrados += r.Quebrados; a.Bloqueados += r.Bloqueados; a.SellOut += r.VentaSellOut;
  }
  const wscRows = [];
  for (const a of wscMap.values()) {
    if (!skuIdxMap.has(a.SKU)) continue;
    wscRows.push([
      skuIdxMap.get(a.SKU), semIdxMap.get(a.Semana), cadenaIdxMap.get(a.CADENA),
      ssRound(a.FCST, 2), ssRound(a.Solicitado, 2), ssRound(a.SellIn, 2), ssRound(a.Quebrados, 2), ssRound(a.Bloqueados, 2), ssRound(a.SellOut, 2)
    ]);
  }

  // ── 9. Summary ──
  let totFCST = 0, totSolicitado = 0, totSellIn = 0, totVentaReal = 0, totQuebrados = 0;
  for (const a of gMap.values()) { totFCST += a.FCST; totSolicitado += a.Solicitado; totSellIn += a.SellIn; totVentaReal += a.VentaReal; totQuebrados += a.Quebrados; }
  const marcas = [...new Set(rows.map(r => r.Marca))].sort();
  const subcats = [...new Set(rows.map(r => r.SubCat))].sort();
  const categorias = [...new Set(rows.map(r => r.Categoria))].sort();

  const summary = {
    semanas_ini: semanaOrder[0], semanas_fin: semanaOrder[semanaOrder.length - 1],
    n_sku: gMap.size, n_excluidos: skuExcluidos.size,
    fcst: ssRound(totFCST, 1), solicitado: ssRound(totSolicitado, 1), sellin: ssRound(totSellIn, 1), ventareal: ssRound(totVentaReal, 1),
    quebrados: ssRound(totQuebrados, 1),
    des_pct: totFCST ? ssRound(totSellIn / totFCST * 100, 1) : 0,
    gap_fs: ssRound(totSolicitado - totFCST, 1), gap_ss: ssRound(totSolicitado - totSellIn, 1), gap_fc: ssRound(totFCST - totSellIn, 1),
    marcas, subcats, categorias, cadenas: cadenaList,
  };

  // ── 10. Stock en riesgo / liquidación (Informe_Stock_Pais, hoja "DETALLE WMS") ──
  report('Leyendo Informe de Stock País…');
  const wbStock = await ssReadWorkbook(stockFile);
  const stockRowsRaw = ssSheetRows(wbStock, 'DETALLE WMS');
  ssRequireColumns(stockRowsRaw, ['CODIGO_SAP', 'ESTADO', 'KILOS', 'PORCENTAJE', 'LOTE'], 'Informe de Stock País');
  const skuUniverse = new Set(gMap.keys());
  const riskGroupMap = new Map();
  for (const r of stockRowsRaw) {
    const estado = ssStr(r['ESTADO'], '');
    const esVliq = estado === 'VLIQ';
    if (!(esVliq || ssNum(r['PORCENTAJE']) > 26)) continue;
    const sku = Math.trunc(ssNum(r['CODIGO_SAP']));
    if (!skuUniverse.has(sku)) continue;
    const nombre = ssStr(r['Nombre Producto'], '');
    const k = sku + '|' + nombre;
    let a = riskGroupMap.get(k);
    if (!a) { a = { sku, nombre, kilos: 0, kilosVliq: 0, lotes: new Set() }; riskGroupMap.set(k, a); }
    const kilos = ssNum(r['KILOS']);
    a.kilos += kilos;
    if (esVliq) a.kilosVliq += kilos;
    a.lotes.add(r['LOTE']);
  }
  const cruceJson = [];
  let tonRiesgoTotal = 0, tonVliqTotal = 0;
  for (const a of riskGroupMap.values()) {
    const tonRiesgo = a.kilos / 1000, tonVliq = a.kilosVliq / 1000;
    tonRiesgoTotal += tonRiesgo; tonVliqTotal += tonVliq;
    const extra = gExtra.get(a.sku) || {};
    const r2 = v => (v === null || v === undefined) ? null : ssRound(v, 2);
    cruceJson.push({
      CODIGO_SAP: a.sku, 'Nombre Producto': a.nombre, SKU: a.sku,
      ton_riesgo: r2(tonRiesgo), ton_vliq: r2(tonVliq), n_lotes: a.lotes.size,
      Marca: extra.Marca ?? null, Categoria: extra.Categoria ?? null,
      FCST: r2(extra.FCST), SellIn: r2(extra.SellIn),
      des_pct: r2(extra.des_pct), gap_FC_t: r2(extra.gap_FC_t), gap_SS_t: r2(extra.gap_SS_t),
    });
  }
  const stockRisk = {
    rows: cruceJson,
    ton_riesgo_total: ssRound(tonRiesgoTotal, 1),
    ton_vliq_total: ssRound(tonVliqTotal, 1),
    n_sku: riskGroupMap.size,
    snapshot_fecha: ssFormatSnapshotFecha(stockFile.name),
  };

  // ── 11. Precio promedio / liquidación / intermedia (PRECIO_PROMEDIO_SO, primera hoja —
  // el nombre varía entre exports, ej. "Server_CH237-213" vs "Server_CH276-213") ──
  report('Leyendo Precio Promedio SO…');
  const wbPrecio = await ssReadWorkbook(precioFile);
  const precioRowsRaw = ssSheetRows(wbPrecio);
  ssRequireColumns(precioRowsRaw, ['SKU', 'Año', 'Mes', 'Tipo de Venta', 'Precio Promedio SO', 'Cadena Cliente'], 'Precio Promedio SO');
  const mesOrderSet = new Set(mesOrder);
  const soRowsAll = [];
  for (const r of precioRowsRaw) {
    const skuNum = Number(r['SKU']);
    if (!Number.isFinite(skuNum)) continue;
    const sku = Math.trunc(skuNum);
    if (!skuIdxMap.has(sku)) continue;
    const anio = r['Año'], mes = r['Mes'];
    if (anio === null || anio === undefined || mes === null || mes === undefined) continue;
    const anioNum = Math.trunc(Number(anio)), mesNum = Math.trunc(Number(mes));
    if (!Number.isFinite(anioNum) || !Number.isFinite(mesNum) || mesNum < 1 || mesNum > 12) continue;
    const mesLabel = `${MESES_ES[mesNum]} ${anioNum}`;
    if (!mesOrderSet.has(mesLabel)) continue;
    soRowsAll.push({
      sku, mesLabel, cadenaCliente: ssStr(r['Cadena Cliente'], '').toUpperCase(),
      tipoVenta: ssStr(r['Tipo de Venta'], '-'),
      ventaFisicaSellIn: ssNum(r['Venta Fisica SelI In (TON)']),
      precioPromedioSO: r['Precio Promedio SO'],
      ventaFisicaSellOut: ssNum(r['Venta Fisica Sell Out (TON)']),
    });
  }

  // Venta en Liquidación / Venta Intermedia casi nunca se registran contra las 6 cadenas
  // grandes — vienen de mayoristas/clientes chicos. Se calculan sobre TODAS las filas sin
  // distinguir cadena (no se pueden filtrar por cadena en el dashboard), si no quedan en cero.
  const liqMap = new Map();
  for (const r of soRowsAll) {
    if (r.tipoVenta !== 'VENTA LIQUIDACION') continue;
    const k = r.sku + '|' + r.mesLabel;
    liqMap.set(k, (liqMap.get(k) || 0) + r.ventaFisicaSellIn);
  }
  const liqRows = [...liqMap].map(([k, ton]) => {
    const [skuStr, mesLabel] = k.split('|');
    return [skuIdxMap.get(parseInt(skuStr, 10)), mesOrder.indexOf(mesLabel), ssRound(ton, 3)];
  });

  const intermMap = new Map();
  for (const r of soRowsAll) {
    if (r.tipoVenta !== 'VENTA INTERMEDIA') continue;
    const k = r.sku + '|' + r.mesLabel;
    intermMap.set(k, (intermMap.get(k) || 0) + r.ventaFisicaSellIn);
  }
  const intermRows = [...intermMap].map(([k, ton]) => {
    const [skuStr, mesLabel] = k.split('|');
    return [skuIdxMap.get(parseInt(skuStr, 10)), mesOrder.indexOf(mesLabel), ssRound(ton, 3)];
  });

  // Precio promedio SÍ queda filtrable por cadena. "Cadena Cliente" trae ~24 clientes (mucho
  // más fino que las 8 cadenas del resto del dashboard) — solo las 6 cadenas grandes tienen
  // mapeo directo y confiable; el resto (clientes chicos/institucionales) se excluye de este
  // reporte en vez de adivinar a qué cadena "bucket" pertenece cada uno.
  const CADENA_CLIENTE_MAP = {
    CENCOSUD: 'Cencosud', TOTTUS: 'Tottus', UNIMARC: 'Unimarc', WALMART: 'Walmart',
    'ALVI SUPERMERCADOS': 'Alvi', 'SUPERMERCADOS REGION': 'Supermercados Region',
  };
  const priceMap = new Map();
  for (const r of soRowsAll) {
    if (r.tipoVenta !== '-') continue;
    const cadenaNorm = CADENA_CLIENTE_MAP[r.cadenaCliente];
    if (!cadenaNorm || !cadenaIdxMap.has(cadenaNorm)) continue;
    const precio = Number(r.precioPromedioSO);
    if (!Number.isFinite(precio) || precio <= 0) continue;
    if (!(r.ventaFisicaSellOut > 0)) continue;
    const k = r.sku + '|' + r.mesLabel + '|' + cadenaIdxMap.get(cadenaNorm);
    let a = priceMap.get(k);
    if (!a) { a = { ton: 0, weighted: 0 }; priceMap.set(k, a); }
    a.ton += r.ventaFisicaSellOut;
    a.weighted += precio * r.ventaFisicaSellOut;
  }
  const priceRows = [...priceMap].map(([k, a]) => {
    const [skuStr, mesLabel, cadIdxStr] = k.split('|');
    return [skuIdxMap.get(parseInt(skuStr, 10)), mesOrder.indexOf(mesLabel), parseInt(cadIdxStr, 10), ssRound(a.weighted / a.ton, 2), ssRound(a.ton, 3)];
  });

  // ── 12. Calendario de promociones (GRID_PROMOCIONAL) — opcional. Si no se sube,
  // se usa el último calendario conocido (bundleado en la página) y se recalculan
  // semIni/semFin contra las semanas actuales. ──
  let promoRows, promoWarning = null;
  if (promoFile) {
    report('Leyendo Calendario de Promociones (GRID_PROMOCIONAL)…');
    try {
      const wbPromo = await ssReadWorkbook(promoFile);
      promoRows = ssBuildPromoRowsFromGrid(wbPromo, skuIdxMap, semanaOrder);
      if (!promoRows.length) throw new Error('no se encontraron promociones válidas (revisa los nombres de hoja del archivo)');
    } catch (err) {
      console.error('Error leyendo GRID_PROMOCIONAL, se usa el calendario guardado:', err);
      promoWarning = `No se pudo leer el archivo de promociones (${err.message}) — se usó el último calendario de promociones guardado.`;
      promoRows = ssBuildPromoRowsFromBackup(skuIdxMap, semanaOrder);
    }
  } else {
    promoRows = ssBuildPromoRowsFromBackup(skuIdxMap, semanaOrder);
  }

  report('Armando el dashboard…');
  console.log('SKUs finales:', gMap.size, '| excluidos:', skuExcluidos.size);
  console.log(`SKU reincluidos por tener FCST≠0 en las últimas ${ULTIMAS_N_SEMANAS_ADELANTE} semanas (${skuReincluidosFcstReciente.length}):`, skuReincluidosFcstReciente);

  return {
    summary, weekly: weeklyJson, skus: skusJson, skus_cadena: skusCadenaJson, wsc_rows: wscRows,
    sku_list: skuList, cadena_list: cadenaList, semana_order: semanaOrder, mes_order: mesOrder,
    sem_mes_idx: semanas.map(s => mesOrder.indexOf(semMesLabel.get(s))),
    meses_comparacion: mesesComparacion, stock_risk: stockRisk,
    liq_rows: liqRows, interm_rows: intermRows, price_rows: priceRows, promo_rows: promoRows,
    _sku_reincluidos: skuReincluidosFcstReciente.map(sku => ({ sku, ...(skuDesc.get(sku) || {}) })),
    _promo_warning: promoWarning,
  };
}

function runSelfServiceUpload() {
  return new Promise((resolve) => {
    const btn = document.getElementById('ssGenerateBtn');
    const status = document.getElementById('ssStatus');
    const fBase = document.getElementById('ssFileBase');
    const fStock = document.getElementById('ssFileStock');
    const fPrecio = document.getElementById('ssFilePrecio');
    const fPromo = document.getElementById('ssFilePromo');
    btn.addEventListener('click', async () => {
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
        if (data._sku_reincluidos && data._sku_reincluidos.length) {
          console.log('SKU incluidos automáticamente por tener FCST reciente:', data._sku_reincluidos);
        }
        if (data._promo_warning) alert(data._promo_warning);
        window.DATA = data; // útil para soporte/depuración desde la consola del navegador
        document.getElementById('uploadOverlay').style.display = 'none';
        resolve(data);
      } catch (err) {
        console.error(err);
        status.textContent = 'Error procesando los archivos: ' + err.message + ' — revisa que sean los archivos correctos e intenta de nuevo.';
        status.className = 'ss-status ss-error';
        btn.disabled = false;
      }
    });
  });
}
