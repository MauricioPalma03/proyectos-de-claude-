const { chromium } = require('playwright-core');

(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
  await page.goto('file://' + __dirname + '/dashboard_frio.html');
  await page.waitForTimeout(1200);

  const subcatFcsts = await page.$$eval('#desvioSubcatGrid .mini-tile', els => els.map(el => {
    const title = el.getAttribute('title');
    const m = title.match(/FCST ([\d.,]+) t/);
    return { name: el.querySelector('.mt-name').textContent, fcst: m ? parseFloat(m[1].replace(/\./g, '').replace(',', '.')) : null };
  }));
  console.log('subcat tiles (name, fcst) in displayed order:');
  subcatFcsts.forEach(t => console.log(' ', t.name, t.fcst));
  const isSorted = subcatFcsts.every((v, i) => i === 0 || subcatFcsts[i - 1].fcst >= v.fcst);
  console.log('sorted descending by FCST:', isSorted);

  await browser.close();
})();
