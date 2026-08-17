const { chromium } = require('playwright-core');

(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });

  // --- 1. Error path: click Generar with no files ---
  let page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
  await page.goto('file://' + __dirname + '/Desvío Semanal.html');
  await page.waitForTimeout(400);
  await page.click('#ssGenerateBtn');
  await page.waitForTimeout(200);
  let statusText = await page.$eval('#ssStatus', el => el.textContent);
  let statusClass = await page.$eval('#ssStatus', el => el.className);
  console.log('no-files click -> status:', statusText, '| class:', statusClass);
  await page.close();

  // --- 2. Error path: wrong file for a slot (e.g. precio file used as base) ---
  page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
  await page.goto('file://' + __dirname + '/Desvío Semanal.html');
  await page.waitForTimeout(400);
  await page.setInputFiles('#ssFileBase', '/root/.claude/uploads/c01cd6ab-9df3-55a4-8e79-362831a5a777/aa179ee7-PRECIO_PROMEDIO_SO.xlsx');
  await page.setInputFiles('#ssFileStock', '/root/.claude/uploads/c01cd6ab-9df3-55a4-8e79-362831a5a777/df9e0146-Informe_Stock_Pa_s_20260817.xlsx');
  await page.setInputFiles('#ssFilePrecio', '/root/.claude/uploads/c01cd6ab-9df3-55a4-8e79-362831a5a777/aa179ee7-PRECIO_PROMEDIO_SO.xlsx');
  await page.click('#ssGenerateBtn');
  await page.waitForFunction(() => {
    const status = document.getElementById('ssStatus');
    return status.classList.contains('ss-error');
  }, undefined, { timeout: 30000 }).catch(() => {});
  statusText = await page.$eval('#ssStatus', el => el.textContent);
  const btnDisabled = await page.$eval('#ssGenerateBtn', el => el.disabled);
  console.log('wrong-file-in-base-slot -> status:', statusText, '| btn re-enabled:', !btnDisabled);
  await page.close();

  // --- 3. Happy path + screenshot of rendered dashboard ---
  page = await browser.newPage({ viewport: { width: 1400, height: 1400 } });
  await page.goto('file://' + __dirname + '/Desvío Semanal.html');
  await page.waitForTimeout(400);
  await page.setInputFiles('#ssFileBase', '/root/.claude/uploads/c01cd6ab-9df3-55a4-8e79-362831a5a777/20b150eb-Base_de_desvios_.xlsx');
  await page.setInputFiles('#ssFileStock', '/root/.claude/uploads/c01cd6ab-9df3-55a4-8e79-362831a5a777/df9e0146-Informe_Stock_Pa_s_20260817.xlsx');
  await page.setInputFiles('#ssFilePrecio', '/root/.claude/uploads/c01cd6ab-9df3-55a4-8e79-362831a5a777/aa179ee7-PRECIO_PROMEDIO_SO.xlsx');
  await page.click('#ssGenerateBtn');

  // muestrear el texto de status varias veces durante el procesamiento
  const seenMessages = new Set();
  for (let i = 0; i < 20; i++) {
    const t = await page.$eval('#ssStatus', el => el.textContent).catch(() => '');
    if (t) seenMessages.add(t);
    const hidden = await page.$eval('#uploadOverlay', el => el.style.display === 'none').catch(() => false);
    if (hidden) break;
    await page.waitForTimeout(2000);
  }
  console.log('progress messages seen:', [...seenMessages]);

  await page.waitForFunction(() => document.getElementById('uploadOverlay').style.display === 'none', undefined, { timeout: 90000 });
  await page.waitForTimeout(800);
  await page.screenshot({ path: 'ss_screenshot_top.png' });
  await page.$eval('#weeklyPanel', el => el.scrollIntoView({ block: 'start' })).catch(() => {});
  await page.waitForTimeout(300);
  await page.screenshot({ path: 'ss_screenshot_chart.png' });
  console.log('screenshots saved');
  await browser.close();
})();
