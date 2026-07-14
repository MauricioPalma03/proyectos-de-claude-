const { chromium } = require('playwright-core');

(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
  const errors = [];
  page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
  page.on('pageerror', err => errors.push(err.message));

  await page.goto('file://' + __dirname + '/dashboard_frio.html');
  await page.waitForTimeout(1200);

  const listCount = await page.$$eval('#cadenaReviewList .review-item', els => els.length);
  console.log('cadena review list items (expect 8):', listCount);

  const first = await page.$eval('#cadenaReviewList .review-item:first-child', el => el.innerText.replace(/\n/g,' | '));
  console.log('top ranked:', first);

  const detailTitle = await page.$eval('#cadenaReviewDetail', el => el.querySelector('div')?.textContent);
  console.log('detail title:', detailTitle);

  const worstBox = await page.$eval('#cadenaReviewDetail', el => {
    const boxes = [...el.querySelectorAll('div')].filter(d => d.textContent.includes('Mayor desvío en'));
    return boxes.length ? boxes[0].textContent : null;
  });
  console.log('worst week callout:', worstBox);

  const pathCount = await page.$$eval('#cadenaReviewChart path', els => els.length);
  console.log('chart path count (expect 3):', pathCount);

  // check big-marker highlight circles exist (r=5)
  const bigCircles = await page.$$eval('#cadenaReviewChart circle[r="5"]', els => els.length);
  console.log('big highlight circles (expect 3, one per series):', bigCircles);

  // click 3rd cadena
  await page.click('#cadenaReviewList .review-item:nth-child(3)');
  await page.waitForTimeout(300);
  const navPos = await page.$eval('#cadenaReviewDetail', el => [...el.querySelectorAll('span')].map(s=>s.textContent).find(t=>t.includes('/')));
  console.log('nav position after click 3rd:', navPos);

  // test week range anchoring
  await page.selectOption('#weeksRangeSelect', '8');
  await page.waitForTimeout(400);
  const listCountAfter8w = await page.$$eval('#cadenaReviewList .review-item', els => els.length);
  console.log('cadena list count after últimas 8 semanas:', listCountAfter8w);

  await page.screenshot({ path: 'screenshot_cadenareview.png', clip: { x: 0, y: 250, width: 1400, height: 700 } });

  console.log('errors:', errors);
  await browser.close();
})();
