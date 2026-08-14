const { chromium } = require('playwright-core');

(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
  const errors = [];
  page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
  page.on('pageerror', err => errors.push(err.message));

  await page.goto('file://' + __dirname + '/Desvío Semanal.html');
  await page.waitForTimeout(500);

  const overlayVisible = await page.$eval('#uploadOverlay', el => getComputedStyle(el).display !== 'none');
  console.log('overlay visible on load:', overlayVisible);

  await page.setInputFiles('#ssFileBase', '/root/.claude/uploads/c01cd6ab-9df3-55a4-8e79-362831a5a777/4afa8739-Base_de_desvios_.xlsx');
  await page.setInputFiles('#ssFileStock', '/root/.claude/uploads/c01cd6ab-9df3-55a4-8e79-362831a5a777/0c7a64bd-Informe_Stock_Pa_s_20260814.xlsx');
  await page.setInputFiles('#ssFilePrecio', '/root/.claude/uploads/c01cd6ab-9df3-55a4-8e79-362831a5a777/fc851ed1-PRECIO_PROMEDIO_SO.xlsx');

  await page.click('#ssGenerateBtn');
  // esperar a que el overlay se oculte (o que aparezca un error)
  await page.waitForFunction(() => {
    const overlay = document.getElementById('uploadOverlay');
    const status = document.getElementById('ssStatus');
    return overlay.style.display === 'none' || status.classList.contains('ss-error');
  }, undefined, { timeout: 120000 });

  const statusText = await page.$eval('#ssStatus', el => el.textContent);
  const overlayHidden = await page.$eval('#uploadOverlay', el => el.style.display === 'none');
  console.log('overlay hidden after processing:', overlayHidden, '| status:', statusText);

  if (!overlayHidden) {
    console.log('errors:', errors);
    await browser.close();
    return;
  }

  await page.waitForTimeout(500);

  const summary = await page.evaluate(() => window.DATA ? window.DATA.summary : null);
  console.log('summary:', JSON.stringify(summary, null, 1));

  const meta = await page.evaluate(() => {
    const d = window.DATA;
    return {
      wsc_rows: d.wsc_rows.length,
      skus_cadena: d.skus_cadena.length,
      liq_rows: d.liq_rows.length,
      interm_rows: d.interm_rows.length,
      price_rows: d.price_rows.length,
      promo_rows: d.promo_rows.length,
      promo_con_semana: d.promo_rows.filter(r => r.semIni !== null).length,
      sku_list_len: d.sku_list.length,
      cadena_list: d.cadena_list,
      semana_order_first: d.semana_order[0],
      semana_order_last: d.semana_order[d.semana_order.length - 1],
      semana_order_len: d.semana_order.length,
      mes_order_first: d.mes_order[0],
      mes_order_last: d.mes_order[d.mes_order.length - 1],
      stock_risk: d.stock_risk,
    };
  });
  console.log('meta:', JSON.stringify(meta, null, 1));

  const kpiRow = await page.$eval('#kpiRow', el => el.innerText.replace(/\n/g, ' | ')).catch(() => null);
  console.log('kpiRow (rendered UI):', kpiRow);
  const subtitle = await page.$eval('#subtitleText', el => el.textContent).catch(() => null);
  console.log('subtitle (rendered UI):', subtitle);

  console.log('errors:', errors);
  await browser.close();
})();
