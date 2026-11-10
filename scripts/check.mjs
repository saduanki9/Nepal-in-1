// Quick health check for the Nepal in 1 site. Runs locally (`node scripts/check.mjs`) and in CI.
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
try { data = JSON.parse(readFileSync('site/data.json', 'utf8')); ok('data.json is valid JSON'); }
catch (e) { fail('data.json is not valid JSON: ' + e.message); }
if (data) {
  for (const key of ['feed', 'business', 'nepse', 'watch', 'invest', 'places', 'mentor']) {
    if (data[key] && typeof data[key] === 'object') ok('data.json has "' + key + '"');
    else fail('data.json is missing the "' + key + '" section');
  }
  // Mentor businesses: every figure the calculator multiplies must be a real number, and every source a real link.
  const ideas = data.mentor && Array.isArray(data.mentor.ideas) ? data.mentor.ideas : [];
  if (!ideas.length) fail('mentor has no businesses');
  for (const o of ideas) {
    const nums = [o.setup, o.first_cycle, o.cost_year, o.profit && o.profit.mid, o.scale && o.scale.min, o.scale && o.scale.max, o.scale && o.scale.step];
    const bad = nums.some((n) => typeof n !== 'number' || !isFinite(n) || n < 0) || !(o.first_cycle > 0) || !(o.cost_year > 0) || !(o.scale.step > 0) || o.scale.min > o.scale.max;
    const srcs = Array.isArray(o.sources) ? o.sources : [];
    if (!o.id || !o.name || bad) fail('mentor business "' + (o.id || o.name || '?') + '" has a missing or invalid number');
    else if (!srcs.length || srcs.some((s) => !/^https:\/\//.test(String(s.url || '')))) fail('mentor business "' + o.id + '" needs https source links');
    else ok('mentor business "' + o.id + '" is complete');
  }
  // Sector guides: every guide needs a name, summary and first steps, and every link must be https.
  const secs = data.mentor && data.mentor.sectors && Array.isArray(data.mentor.sectors.items) ? data.mentor.sectors.items : [];
  for (const s of secs) {
    const links = (s.sources || []).map((x) => x.url).concat((s.numbers || []).map((n) => n.source_url)).filter((u) => u);
    if (!s.id || !s.name || !s.summary || !Array.isArray(s.start) || !s.start.length) fail('sector guide "' + (s.id || '?') + '" is missing its name, summary or first steps');
    else if (links.some((u) => !/^https:\/\//.test(u))) fail('sector guide "' + s.id + '" has a link that is not https');
    else if ((s.numbers || []).some((n) => !n.label || !n.value || !n.source_url)) fail('sector guide "' + s.id + '" has a number without a label, value or source');
  }
  if (secs.length) ok(secs.length + ' sector guides are complete');
}

// 2. Page has a title and every tab has a matching section.
const html = readFileSync('site/index.html', 'utf8');
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

if (process.exitCode) console.error('\nSite check failed.'); else console.log('\nSite check passed.');
