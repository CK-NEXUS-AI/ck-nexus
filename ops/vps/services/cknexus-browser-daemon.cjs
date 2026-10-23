const puppeteer = require('/root/.npm/_npx/4b4c857f6efdfb61/node_modules/puppeteer');
let browser;
let stopping = false;
(async () => {
  browser = await puppeteer.launch({
    executablePath: '/opt/google/chrome/chrome',
    headless: true,
    userDataDir: '/var/lib/cknexus-browser/profile',
    timeout: 20000,
    args: [
      '--no-sandbox',
      '--disable-dev-shm-usage',
      '--disable-gpu',
      '--no-zygote',
      '--disable-background-networking',
      '--disable-extensions',
      '--remote-debugging-port=9222',
      '--remote-debugging-address=127.0.0.1'
    ]
  });
  console.log('CK-NEXUS_BROWSER_READY version=' + await browser.version() + ' endpoint=' + browser.wsEndpoint());
  await new Promise(resolve => {
    process.once('SIGTERM', resolve);
    process.once('SIGINT', resolve);
  });
})().catch(err => {
  console.error('CK-NEXUS_BROWSER_FATAL', err && err.stack || err);
  process.exitCode = 1;
}).finally(async () => {
  stopping = true;
  if (browser) await browser.close().catch(() => {});
});
