const { chromium } = require('playwright-core');
const path = require('path');
const fs = require('fs');

(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  const downloadDir = path.join(__dirname, 'madre_downloads');
  fs.rmSync(downloadDir, { recursive: true, force: true });
  fs.mkdirSync(downloadDir);
  const context = await browser.newContext({ acceptDownloads: true, viewport: { width: 1400, height: 1400 } });
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', err => errors.push(err.message));
  page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });

  await page.goto('file://' + __dirname + '/Archivo Madre - Desvío Semanal.html');
  await page.waitForTimeout(500);

  // --- 1. Pantalla de selección: debe listar "Frío" ---
  const catButtons = await page.$$eval('.ms-category-btn', els => els.map(e => e.textContent.trim()));
  console.log('categorías listadas al abrir:', catButtons);

  // --- 2. Elegir "Frío" -> debe renderizar el dashboard completo ---
  await page.click('[data-cat="Frío"]');
  await page.waitForTimeout(600);
  const kpiRow = await page.$eval('#kpiRow', el => el.innerText.replace(/\n/g, ' | '));
  console.log('kpiRow (categoría Frío):', kpiRow);
  const subtitle = await page.$eval('#subtitleText', el => el.textContent);
  console.log('subtitle:', subtitle);

  console.log('errors tras ver Frío:', errors);
  await context.close();

  // --- 3. Reabrir y actualizar/agregar una categoría nueva ---
  const context2 = await browser.newContext({ acceptDownloads: true, viewport: { width: 1400, height: 1400 } });
  const page2 = await context2.newPage();
  const errors2 = [];
  page2.on('pageerror', err => errors2.push(err.message));
  page2.on('console', msg => { if (msg.type() === 'error') errors2.push(msg.text()); });

  await page2.goto('file://' + __dirname + '/Archivo Madre - Desvío Semanal.html');
  await page2.waitForTimeout(500);
  await page2.click('#msGoUpdateBtn');
  await page2.waitForTimeout(200);
  await page2.selectOption('#msCategorySelect', '__new__');
  await page2.fill('#msCategoryNew', 'Categoria Test');
  await page2.setInputFiles('#ssFileBase', '/root/.claude/uploads/c01cd6ab-9df3-55a4-8e79-362831a5a777/509ebc3b-Base_de_desvios_.xlsx');
  await page2.setInputFiles('#ssFileStock', '/root/.claude/uploads/c01cd6ab-9df3-55a4-8e79-362831a5a777/d738601b-Informe_Stock_Pa_s_20260817.xlsx');
  await page2.setInputFiles('#ssFilePrecio', '/root/.claude/uploads/c01cd6ab-9df3-55a4-8e79-362831a5a777/41a3257b-PRECIO_PROMEDIO_SO.xlsx');

  const downloadPromise = page2.waitForEvent('download', { timeout: 90000 });
  await page2.click('#ssGenerateBtn');
  const download = await downloadPromise;
  const savedPath = path.join(downloadDir, 'archivo_madre_v2.html');
  await download.saveAs(savedPath);
  console.log('archivo descargado guardado en:', savedPath, '| tamaño:', fs.statSync(savedPath).size, 'bytes');

  await page2.waitForTimeout(500);
  const doneMsg = await page2.$eval('#msDoneMsg', el => el.textContent).catch(() => null);
  console.log('mensaje de confirmación:', doneMsg);

  await page2.click('#msViewNowBtn');
  await page2.waitForTimeout(600);
  const kpiRowTest = await page2.$eval('#kpiRow', el => el.innerText.replace(/\n/g, ' | '));
  console.log('kpiRow (categoría Categoria Test, recién generada):', kpiRowTest);

  console.log('errors tras actualizar categoría:', errors2);
  await context2.close();

  // --- 4. Reabrir el archivo DESCARGADO (v2) y confirmar que tiene AMBAS categorías ---
  const context3 = await browser.newContext({ viewport: { width: 1400, height: 1400 } });
  const page3 = await context3.newPage();
  const errors3 = [];
  page3.on('pageerror', err => errors3.push(err.message));
  await page3.goto('file://' + savedPath);
  await page3.waitForTimeout(500);
  const catButtons3 = await page3.$$eval('.ms-category-btn', els => els.map(e => e.textContent.trim()));
  console.log('categorías listadas en el archivo v2 (descargado):', catButtons3);

  await page3.click('[data-cat="Frío"]');
  await page3.waitForTimeout(600);
  const kpiRowFrioV2 = await page3.$eval('#kpiRow', el => el.innerText.replace(/\n/g, ' | '));
  console.log('kpiRow Frío en archivo v2 (debe seguir intacto):', kpiRowFrioV2);
  console.log('errors abriendo v2:', errors3);
  await context3.close();

  await browser.close();
})();
