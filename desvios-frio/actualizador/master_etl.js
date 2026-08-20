// ══════════════════════════════════════════════════════════════════
// Archivo Madre: envoltorio sobre computeDashboardData() (de selfservice_etl.js).
// El archivo trae UN solo dataset combinado (todas las divisiones de la compañía
// juntas, tal como viene el Base_de_desvios de cada semana) — se ve directo al
// abrir, sin pantalla de selección. Para actualizar, se sube el Base_de_desvios/
// Stock/Precio de la semana (con todas las divisiones adentro) y se descarga un
// archivo madre nuevo con los datos al día — ese es el que hay que compartir.
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

async function runMasterFlow() {
  const seedData = await msDecompressJson(window.__SEED_DATA_B64GZ__);

  const overlay = document.getElementById('uploadOverlay');
  const screenUpdate = document.getElementById('msScreenUpdate');
  const screenDone = document.getElementById('msScreenDone');
  const status = document.getElementById('ssStatus');
  const btn = document.getElementById('ssGenerateBtn');
  const fBase = document.getElementById('ssFileBase');
  const fStock = document.getElementById('ssFileStock');
  const fPrecio = document.getElementById('ssFilePrecio');
  const fPromo = document.getElementById('ssFilePromo');
  const fRolling = document.getElementById('ssFileRolling');

  function showScreen(el) {
    [screenUpdate, screenDone].forEach(s => { s.style.display = s === el ? 'block' : 'none'; });
    overlay.style.display = 'flex';
  }

  document.getElementById('msOpenUpdateBtn').addEventListener('click', () => {
    status.textContent = ''; status.className = 'ss-status';
    showScreen(screenUpdate);
  });
  document.getElementById('msCloseUpdateBtn').addEventListener('click', () => { overlay.style.display = 'none'; });
  document.getElementById('msBackFromDoneBtn').addEventListener('click', () => { overlay.style.display = 'none'; });

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
      const data = await computeDashboardData(fBase.files[0], fStock.files[0], fPrecio.files[0], fPromo.files[0] || null, fRolling.files[0] || null, msg => {
        status.textContent = msg;
      });
      if (data._promo_warning) alert(data._promo_warning);

      status.textContent = 'Armando el archivo madre actualizado…';
      // shellText es el molde (ver inject_frio_madre.py) con los dos placeholders
      // de datos todavía sin reemplazar — se rellenan de nuevo acá para producir
      // el próximo archivo madre descargable. Los tokens se arman concatenados
      // (no como texto literal contiguo) para que el propio build no los pise:
      // si aparecieran completos en el código fuente, el reemplazo de una sola
      // pasada en Python los corrompería a ellos también.
      const DATA_TOKEN = '__SEED_DATA' + '_VALUE__';
      const SELF_TOKEN = '__SELF_TEMPLATE' + '_VALUE__';
      const shellText = await msDecompressText(window.__SELF_TEMPLATE_B64GZ__);
      const dataB64gz = await msGzipBase64(JSON.stringify(data));
      const finalHtml = shellText
        .replace(DATA_TOKEN, dataB64gz)
        .replace(SELF_TOKEN, window.__SELF_TEMPLATE_B64GZ__);
      msDownloadFile('Archivo Madre - Desvío Semanal.html', finalHtml);

      btn.disabled = false;
      status.textContent = ''; status.className = 'ss-status';
      showScreen(screenDone);
    } catch (err) {
      console.error(err);
      status.textContent = 'Error procesando los archivos: ' + err.message + ' — revisa que sean los archivos correctos e intenta de nuevo.';
      status.className = 'ss-status ss-error';
      btn.disabled = false;
    }
  });

  overlay.style.display = 'none';
  return seedData;
}
