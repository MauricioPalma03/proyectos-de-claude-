const { chromium } = require('playwright-core');
const fs = require('fs');

(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
  const errors = [];
  page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
  page.on('pageerror', err => errors.push(err.message));

  await page.goto('file://' + __dirname + '/dashboard_frio.html');
  await page.waitForTimeout(1500);

  const targetSku = '30001871';
  await page.evaluate((sku) => {
    const sel = document.getElementById('skuSelect');
    const opt = Array.from(sel.options).find(o => o.value === sku);
    if (opt) { sel.value = sku; sel.dispatchEvent(new Event('change')); }
  }, targetSku);
  await page.waitForTimeout(400);

  // --- no cadena filter: bands/chips should only reflect status=Aceptado ---
  const chipTitlesNoCadena = await page.$$eval('#promoInlineSummary .promo-chip', els => els.map(e => e.getAttribute('title')));
  console.log('chip count (no cadena filter):', chipTitlesNoCadena.length);
  const anyNonAceptado = chipTitlesNoCadena.some(t => !t.includes('Aceptado'));
  console.log('any chip NOT Aceptado (should be false):', anyNonAceptado);

  const bandTitleNoCadena = await page.$eval('#lineChart rect[stroke-dasharray="2,2"] title', el => el.textContent).catch(() => null);
  console.log('band tooltip (no cadena filter) mentions only Aceptado:', bandTitleNoCadena && !bandTitleNoCadena.includes('Enviado') && !bandTitleNoCadena.includes('Planificado'));

  // --- apply cadena filter = Cencosud ---
  await page.selectOption('#cadenaSelect', 'Cencosud');
  await page.waitForTimeout(400);
  const chipTitlesCadena = await page.$$eval('#promoInlineSummary .promo-chip', els => els.map(e => e.getAttribute('title')));
  console.log('chip count (cadena=Cencosud):', chipTitlesCadena.length);
  const allCencosud = chipTitlesCadena.every(t => t.includes('Cencosud'));
  console.log('all chips are Cencosud:', allCencosud, chipTitlesCadena);

  const bandCountCadena = await page.$$eval('#lineChart rect[stroke-dasharray="2,2"]', els => els.length);
  console.log('band rect count (cadena=Cencosud):', bandCountCadena);

  console.log('errors:', errors);
  await browser.close();
})();
