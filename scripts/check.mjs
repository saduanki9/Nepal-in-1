// Quick health check for the dashboard. Runs locally (`node scripts/check.mjs`) and in CI.
// Catches the mistakes that would break the page: bad JSON, a JavaScript syntax error,
// or a missing section in the data snapshot.
import { readFileSync, writeFileSync, mkdtempSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const fail = (msg) => { console.error('FAIL: ' + msg); process.exitCode = 1; };
const ok = (msg) => console.log('ok   ' + msg);

// 1. Data snapshot is valid JSON and has every section the page reads.
let data;
try { data = JSON.parse(readFileSync('dashboard/public.json', 'utf8')); ok('public.json is valid JSON'); }
catch (e) { fail('public.json is not valid JSON: ' + e.message); }
if (data) {
  for (const key of ['feed', 'business', 'nepse', 'watch', 'invest', 'places']) {
    if (data[key] && typeof data[key] === 'object') ok('public.json has "' + key + '"');
    else fail('public.json is missing the "' + key + '" section');
  }
}

// 2. Page has a title and every tab has a matching section.
const html = readFileSync('dashboard/index.html', 'utf8');
if (/<title>[^<]+<\/title>/.test(html)) ok('index.html has a <title>'); else fail('index.html has no <title>');
const tabs = [...html.matchAll(/data-tab="([a-z]+)"/g)].map((m) => m[1]);
for (const t of tabs) {
  if (html.includes('id="v-' + t + '"')) ok('tab "' + t + '" has a section');
  else fail('tab "' + t + '" has no matching section id="v-' + t + '"');
}

// 3. Inline JavaScript parses.
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => m[1]);
const dir = mkdtempSync(join(tmpdir(), 'nd-check-'));
scripts.forEach((src, i) => {
  const f = join(dir, 'script-' + i + '.js');
  writeFileSync(f, src);
  try { execFileSync(process.execPath, ['--check', f], { stdio: 'pipe' }); ok('inline script ' + (i + 1) + ' parses'); }
  catch (e) { fail('inline script ' + (i + 1) + ' has a syntax error:\n' + e.stderr); }
});

if (process.exitCode) console.error('\nDashboard check failed.'); else console.log('\nDashboard check passed.');
