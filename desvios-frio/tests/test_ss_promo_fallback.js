const { chromium } = require('playwright-core');

(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
  const errors = [];
  page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
  page.on('pageerror', err => errors.push(err.message));
  let alertMsg = null;
  page.on('dialog', async d => { alertMsg = d.message(); await d.accept(); });

  await page.goto('file://' + __dirname + '/dashboard_frio_autoservicio.html');
  await page.waitForTimeout(400);
  await page.setInputFiles('#ssFileBase', '/root/.claude/uploads/c01cd6ab-9df3-55a4-8e79-362831a5a777/24dcac4a-Base_de_desvios_.xlsx');
  await page.setInputFiles('#ssFileStock', '/root/.claude/uploads/c01cd6ab-9df3-55a4-8e79-362831a5a777/99c00878-Informe_Stock_Pa_s_20260812.xlsx');
  await page.setInputFiles('#ssFilePrecio', '/root/.claude/uploads/c01cd6ab-9df3-55a4-8e79-362831a5a777/88e3b974-PRECIO_PROMEDIO_SO.xlsx');
  // archivo equivocado en el campo de promo (el mismo de precio, sin las hojas esperadas)
  await page.setInputFiles('#ssFilePromo', '/root/.claude/uploads/c01cd6ab-9df3-55a4-8e79-362831a5a777/88e3b974-PRECIO_PROMEDIO_SO.xlsx');
  await page.click('#ssGenerateBtn');
  await page.waitForFunction(() => document.getElementById('uploadOverlay').style.display === 'none', undefined, { timeout: 90000 });

  console.log('alert mostrado:', alertMsg);
  const promoCount = await page.evaluate(() => window.DATA.promo_rows.length);
  console.log('promo_rows tras fallback (debe ser el respaldo, 3476):', promoCount);
  const kpiRow = await page.$eval('#kpiRow', el => el.innerText.replace(/\n/g, ' | '));
  console.log('kpiRow (el resto del dashboard debe seguir funcionando):', kpiRow);

  console.log('errors:', errors);
  await browser.close();
})();
