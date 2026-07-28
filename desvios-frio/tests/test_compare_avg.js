const { chromium } = require('playwright-core');

(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
  const errors = [];
  page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
  page.on('pageerror', err => errors.push(err.message));

  await page.goto('file://' + __dirname + '/dashboard_frio.html');
  await page.waitForTimeout(1500);
  await page.$eval('#weeklyPanel', el => el.scrollIntoView({ block: 'center' }));
  await page.waitForTimeout(200);

  const getHitRectBox = async () => page.evaluate(() => {
    const svg = document.getElementById('lineChart');
    const rect = svg.querySelector('rect[fill="transparent"]');
    const b = rect.getBoundingClientRect();
    return { x: b.x, y: b.y, w: b.width, h: b.height };
  });

  await page.click('#compareModeBtn');
  await page.waitForTimeout(200);
  let hb = await getHitRectBox();
  await page.mouse.click(hb.x + hb.w * 0.15, hb.y + hb.h * 0.4);
  await page.waitForTimeout(200);
  await page.mouse.click(hb.x + hb.w * 0.75, hb.y + hb.h * 0.4);
  await page.waitForTimeout(300);

  const boxText = await page.$eval('#compareResultBox', el => el.innerText);
  console.log('--- compareResultBox full text ---');
  console.log(boxText);

  console.log('errors:', errors);
  await browser.close();
})();
