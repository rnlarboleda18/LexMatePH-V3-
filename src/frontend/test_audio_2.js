const puppeteer = require('puppeteer');
(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  page.on('console', msg => console.log('PAGE LOG:', msg.text()));
  page.on('pageerror', err => console.log('PAGE ERROR:', err.message));
  page.on('requestfailed', request => console.log('REQ FAILED:', request.url(), request.failure().errorText));
  
  await page.goto('http://localhost:5173/codex/rpc', { waitUntil: 'networkidle2' });
  const playButtons = await page.c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\src\frontend('button:has(.lucide-headphones)');
  if (playButtons.length > 0) {
      await playButtons[0].click();
      await page.waitForTimeout(3000);
  }
  await browser.close();
})();
