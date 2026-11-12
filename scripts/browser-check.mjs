// Opens the site in a real browser at phone, small-phone and desktop sizes and checks that
// every feature can be reached and shows content. Runs before every publish, so a change
// that hides a feature (or breaks the page) never goes live.
//
//   node scripts/browser-check.mjs
//
// Needs Playwright (`playwright` or `playwright-core`). On GitHub's runners it uses the
// Chrome that is already installed.
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { createRequire } from 'node:module';
import { extname, join, normalize, resolve } from 'node:path';

const require = createRequire(import.meta.url);
let chromium;
try { ({ chromium } = require('playwright')); } catch { ({ chromium } = require('playwright-core')); }

const ROOT = resolve('site');
const TYPES = { '.html': 'text/html; charset=utf-8', '.json': 'application/json', '.png': 'image/png', '.svg': 'image/svg+xml', '.js': 'text/javascript', '.css': 'text/css' };
const server = createServer(async (req, res) => {
  let path = normalize(decodeURIComponent(new URL(req.url, 'http://x').pathname));
  if (path.endsWith('/')) path += 'index.html';
  const file = join(ROOT, path);
  if (!file.startsWith(ROOT)) { res.writeHead(403).end(); return; }
  try { const body = await readFile(file); res.writeHead(200, { 'content-type': TYPES[extname(file)] || 'application/octet-stream' }).end(body); }
  catch { res.writeHead(404).end(); }
});
await new Promise((r) => server.listen(0, '127.0.0.1', r));
const base = 'http://127.0.0.1:' + server.address().port + '/';

async function launch() {
  const tries = [{}, { channel: 'chrome' }];
  for (const p of [process.env.CHROME_BIN, '/opt/pw-browsers/chromium']) if (p && existsSync(p)) tries.push({ executablePath: p });
  let last;
  for (const o of tries) { try { return await chromium.launch({ ...o, args: ['--no-sandbox'] }); } catch (e) { last = e; } }
  throw last;
}

const SIZES = [
  { name: 'small phone', width: 320, height: 640 },
  { name: 'phone', width: 390, height: 844 },
  { name: 'tablet', width: 820, height: 1100 },
  { name: 'desktop', width: 1280, height: 900 },
];
const failures = [];
const browser = await launch();

for (const size of SIZES) {
  const fail = (msg) => failures.push(size.name + ' (' + size.width + 'px): ' + msg);
  const ctx = await browser.newContext({ viewport: { width: size.width, height: size.height }, hasTouch: size.width < 900 });
  const page = await ctx.newPage();
  // Only the site itself: no analytics or fonts, so the check never depends on the network.
  await page.route('**/*', (r) => r.request().url().startsWith(base) ? r.continue() : r.abort());
  page.on('pageerror', (e) => fail('page error: ' + e.message));

  const open = async (hash) => {
    await page.goto(base + (hash ? '#' + hash : ''));
    await page.waitForFunction(() => { const n = document.getElementById('n-nepse'); return n && n.textContent.trim() !== '–'; }, null, { timeout: 15000 }).catch(() => fail('data did not load'));
    await page.waitForTimeout(150);
  };
  const viewState = (tab) => page.evaluate((t) => {
    const v = document.getElementById('v-' + t);
    if (!v) return { missing: true };
    return { hidden: v.hidden, height: v.scrollHeight, text: v.innerText.trim().length, loading: /\bLoading\b/.test(v.innerText), sideways: document.documentElement.scrollWidth > innerWidth + 1 };
  }, tab);
  const checkView = async (tab, how) => {
    const s = await viewState(tab);
    if (s.missing) return fail('"' + tab + '" has no page');
    if (s.hidden) return fail('"' + tab + '" did not open ' + how);
    if (s.height < 150 || s.text < 80) fail('"' + tab + '" opens but looks empty');
    if (s.loading) fail('"' + tab + '" is stuck on Loading');
    if (s.sideways) fail('"' + tab + '" scrolls sideways');
  };

  await open('');
  const tabs = await page.evaluate(() => [...document.querySelectorAll('.tab[data-tab]')].map((t) => t.dataset.tab));
  if (tabs.length < 5) fail('only ' + tabs.length + ' tabs found');

  // 1. Every tab is either fully on screen, or the Menu button is.
  const offscreen = await page.evaluate(() => [...document.querySelectorAll('.tab[data-tab]')].filter((t) => { const r = t.getBoundingClientRect(); return r.left < -1 || r.right > innerWidth + 1; }).map((t) => t.dataset.tab));
  const menuOn = await page.evaluate(() => { const b = document.getElementById('menu-btn'); if (!b || !b.offsetParent) return false; const r = b.getBoundingClientRect(); return r.left >= 0 && r.right <= innerWidth + 1 && r.width > 30; });
  if (offscreen.length && !menuOn) fail('these tabs are off screen and there is no Menu button: ' + offscreen.join(', '));

  // 2. Each feature opens and shows content: through the Menu where it shows, and through its tab.
  if (menuOn) {
    await page.click('#menu-btn');
    const items = await page.evaluate(() => [...document.querySelectorAll('#menu-panel .menu-item')].map((b) => b.dataset.go));
    const missing = tabs.filter((t) => !items.includes(t));
    if (missing.length) fail('the Menu is missing: ' + missing.join(', '));
    const fits = await page.evaluate(() => { const m = document.getElementById('menu-panel').getBoundingClientRect(); return m.left >= -1 && m.right <= innerWidth + 1 && m.bottom <= innerHeight + 1; });
    if (!fits) fail('the Menu does not fit on the screen');
    await page.keyboard.press('Escape');
    for (const t of items) {
      await page.click('#menu-btn');
      await page.click('#menu-panel .menu-item[data-go="' + t + '"]');
      await page.waitForTimeout(250);
      await checkView(t, 'from the Menu');
      if (await page.evaluate(() => !document.getElementById('menu-panel').hidden)) fail('the Menu stayed open after choosing "' + t + '"');
    }
    // The Menu must still work far down a long page.
    await page.evaluate(() => window.scrollTo(0, 2500));
    await page.click('#menu-btn');
    if (!(await page.locator('#menu-panel .menu-item').first().isVisible())) fail('the Menu does not open when scrolled down');
    await page.keyboard.press('Escape');
  }
  for (const t of tabs) {
    await page.evaluate((id) => document.getElementById('tab-' + id).click(), t);
    await page.waitForTimeout(200);
    await checkView(t, 'from its tab');
    const shown = await page.evaluate((id) => { const r = document.getElementById('tab-' + id).getBoundingClientRect(), n = document.getElementById('tabs').getBoundingClientRect(); return r.left >= n.left - 2 && r.right <= n.right + 2; }, t);
    if (!shown) fail('the "' + t + '" tab is not scrolled into view when it is the open page');
  }

  // 3. A link straight to a feature (…/#mentor) opens it.
  for (const t of tabs) { await open(t); await checkView(t, 'from a direct link'); }

  // 4. The Start page links to every other feature.
  await open('start');
  const n = await page.locator('#start-links .qlink').count();
  const reached = new Set();
  for (let i = 0; i < n; i++) {
    await open('start');
    await page.locator('#start-links .qlink').nth(i).click();
    await page.waitForTimeout(200);
    reached.add(await page.evaluate(() => { const v = [...document.querySelectorAll('main > section.view')].find((x) => !x.hidden); return v ? v.id.slice(2) : ''; }));
  }
  const unlinked = tabs.filter((t) => t !== 'start' && !reached.has(t));
  if (unlinked.length) fail('the Start page has no link to: ' + unlinked.join(', '));

  await ctx.close();
  console.log((failures.some((f) => f.startsWith(size.name + ' (')) ? 'FAIL ' : 'ok   ') + size.name + ' (' + size.width + 'px): ' + tabs.length + ' features checked');
}

await browser.close();
server.close();
if (failures.length) { console.error('\nBrowser check failed:\n  ' + failures.join('\n  ')); process.exit(1); }
console.log('\nBrowser check passed.');
