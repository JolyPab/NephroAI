const puppeteer = require('puppeteer-core');
const path = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
(async() => {
  const browser = await puppeteer.launch({headless: 'new', executablePath: path});
  const page = (await browser.pages())[0];
  await page.goto('http://localhost:4300/auth', {waitUntil: 'networkidle0', timeout: 20000});
  await page.type('app-glass-input:nth-of-type(1) input', 'codex_test@example.com');
  await page.type('app-glass-input:nth-of-type(2) input', 'Test1234!');
  await page.click('button[type="submit"]');
  await new Promise(r => setTimeout(r, 1500));
  console.log('url', page.url());
  await browser.close();
})();
