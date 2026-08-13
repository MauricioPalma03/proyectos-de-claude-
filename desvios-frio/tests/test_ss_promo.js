const { chromium } = require('playwright-core');

(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
  const errors = [];
  page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
  page.on('pageerror', err => errors.push(err.message));
  page.on('dialog', async d => { console.log('alert():', d.message()); await d.accept(); });

  await page.goto('file://' + __dirname + '/dashboard_frio_autoservicio.html');
  await page.waitForTimeout(400);
  await page.setInputFiles('#ssFileBase', '/root/.claude/uploads/c01cd6ab-9df3-55a4-8e79-362831a5a777/24dcac4a-Base_de_desvios_.xlsx');
  await page.setInputFiles('#ssFileStock', '/root/.claude/uploads/c01cd6ab-9df3-55a4-8e79-362831a5a777/99c00878-Informe_Stock_Pa_s_20260812.xlsx');
  await page.setInputFiles('#ssFilePrecio', '/root/.claude/uploads/c01cd6ab-9df3-55a4-8e79-362831a5a777/88e3b974-PRECIO_PROMEDIO_SO.xlsx');
  await page.setInputFiles('#ssFilePromo', __dirname + '/synthetic_grid_promocional.xlsx');
  await page.click('#ssGenerateBtn');
  await page.waitForFunction(() => document.getElementById('uploadOverlay').style.display === 'none', undefined, { timeout: 90000 });

  const promoRows = await page.evaluate(() => window.DATA.promo_rows.filter(r => r.sku === 30001871));
  console.log('promo rows para SKU 30001871:', JSON.stringify(promoRows, null, 1));
  console.log('total promo_rows:', await page.evaluate(() => window.DATA.promo_rows.length));

  console.log('errors:', errors);
  await browser.close();
})();
