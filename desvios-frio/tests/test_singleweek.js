const { chromium } = require('playwright-core');

(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
  const errors = [];
  page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
  page.on('pageerror', err => errors.push(err.message));

  await page.goto('file://' + __dirname + '/dashboard_frio.html');
  await page.waitForTimeout(1200);

  const opts = await page.$$eval('#weeksRangeSelect option, #weeksRangeSelect optgroup', els =>
    els.map(e => e.tagName === 'OPTGROUP' ? `[${e.label}]` : `${e.value}=${e.textContent}`));
  console.log('options:\n' + opts.join('\n'));

  for (const v of ['w1','w2','w3','w4','w8']) {
    await page.selectOption('#weeksRangeSelect', v);
    await page.waitForTimeout(300);
    const nPoints = await page.$eval('#lineChart path', el => {
      const d = el.getAttribute('d');
      return (d.match(/[ML]/g) || []).length;
    });
    const weekLabels = await page.$$eval('#lineChart text', els => els.map(e=>e.textContent).filter(t=>/^\d\d-S\d\d$/.test(t)));
    console.log(`v=${v} -> points=${nPoints}, weeks shown=${weekLabels.join(',')}`);
  }

  console.log('errors:', errors);
  await browser.close();
})();
