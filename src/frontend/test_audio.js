const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();

  page.on('console', msg => console.log('PAGE LOG:', msg.text()));
  page.on('requestfailed', request => {
    console.log(REQUEST FAILED:  - );
  });

  console.log('Navigating to http://localhost:5173/codex/rpc...');
  await page.goto('http://localhost:5173/codex/rpc', { waitUntil: 'networkidle2' });

  // Click the first play icon we can find
  console.log('Looking for play button...');
  try {
      await page.waitForTimeout(2000); // Give React time to render
      // Let's just click the first add to playlist button we find on the codals page
      const playButtons = await page.c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\src\frontend('button:has(.lucide-headphones)');
      if (playButtons.length > 0) {
          console.log('Clicking headphones...');
          await playButtons[0].click();
          await page.waitForTimeout(3000); // Wait for audio to try to play and fail
      } else {
          console.log('No headphones button found on the page.');
      }
  } catch (err) {
      console.log('Error interacting with page:', err.message);
  }

  await browser.close();
})();
