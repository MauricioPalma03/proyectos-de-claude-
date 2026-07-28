const { chromium } = require('playwright-core');

(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
  await page.goto('file://' + __dirname + '/dashboard_frio.html');
  await page.waitForTimeout(1200);

  const parseTiles = els => els.map(el => {
    const valText = el.querySelector('.mt-val').textContent.trim();
    const gap = parseFloat(valText.replace(' t', '').replace(/\./g, '').replace(',', '.'));
    return { name: el.querySelector('.mt-name').textContent, gap };
  });

  const subcatTiles = await page.$$eval('#desvioSubcatGrid .mini-tile', parseTiles);
  console.log('subcat tiles (name, gap tons) in displayed order:');
  subcatTiles.forEach(t => console.log(' ', t.name, t.gap));
  const isSorted = subcatTiles.every((v, i) => i === 0 || subcatTiles[i - 1].gap >= v.gap);
  console.log('sorted descending by signed gap (tons deviated):', isSorted);

  const marcaTiles = await page.$$eval('#desvioMarcaGrid .mini-tile', parseTiles);
  const marcaSorted = marcaTiles.every((v, i) => i === 0 || marcaTiles[i - 1].gap >= v.gap);
  console.log('marca tiles sorted descending by gap:', marcaSorted, marcaTiles.slice(0, 5));

  const cadenaTiles = await page.$$eval('#desvioCadenaGrid .mini-tile', parseTiles);
  const cadenaSorted = cadenaTiles.every((v, i) => i === 0 || cadenaTiles[i - 1].gap >= v.gap);
  console.log('cadena tiles sorted descending by gap:', cadenaSorted, cadenaTiles);

  await browser.close();
})();
