// Headless browser smoke test of the built log-viewer.html (Playwright + Chromium).
// usage: NODE_PATH=<dir with playwright> node smoke.js <log-viewer.html> <shots-dir> <dbc> <rlog> [<rlog> ...]
'use strict';
const path = require('path');
const fs = require('fs');
const { chromium } = require('playwright');

const [html, shots, dbc, ...rlogs] = process.argv.slice(2);
fs.mkdirSync(shots, { recursive: true });
const checks = [];
const check = (name, ok, detail) => { checks.push({ name, ok: !!ok, detail }); console.log(`${ok ? 'PASS' : 'FAIL'} ${name}${detail !== undefined ? ' :: ' + detail : ''}`); };

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1500, height: 920 }, colorScheme: 'light' });
  const errors = [];
  page.on('pageerror', (e) => errors.push('pageerror: ' + e.message));
  page.on('console', (m) => { if (m.type() === 'error') errors.push('console: ' + m.text()); });
  await page.goto('file://' + path.resolve(html));
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  await page.screenshot({ path: path.join(shots, '01-empty.png') });
  check('page loads without errors', errors.length === 0, errors.join(' | '));

  // open two segments
  const t0 = Date.now();
  await page.setInputFiles('#file-input', rlogs);
  await page.waitForFunction(() => /events/.test(document.querySelector('#status').textContent), null, { timeout: 120000 });
  await page.waitForFunction(() => { const s = window.__logViewer.state; return s.route && !s.extracting.size && s.route.services.get('carState')?.extracted; }, null, { timeout: 120000 });
  check('files open', true, `${((Date.now() - t0) / 1000).toFixed(1)} s, status "${await page.textContent('#status')}"`);
  const info = await page.evaluate(() => {
    const s = window.__logViewer.state;
    const v = window.__logViewer.getSeries('/carState/vEgo');
    return { files: s.route.files.length, tMax: s.route.tMax, services: s.route.services.size, vEgo: v ? v.t.length : 0, lat: window.__logViewer.getSeries('/carControl/latActive')?.t.length || 0 };
  });
  check('two files, one timeline', info.files === rlogs.length && info.tMax > 100, JSON.stringify(info));
  check('carState/vEgo decoded (~100 Hz)', info.vEgo > 100 * 100, info.vEgo);

  // hover the first plot: cursor + legend values
  const box = await page.locator('.pane canvas').first().boundingBox();
  await page.mouse.move(box.x + box.width * 0.6, box.y + box.height * 0.5);
  await page.waitForTimeout(200);
  const legend = await page.locator('.pane .legend .v').first().textContent();
  check('legend shows value at cursor', /^-?\d/.test(legend), legend);
  // wheel zoom
  const before = await page.evaluate(() => ({ ...window.__logViewer.state.view }));
  await page.mouse.wheel(0, -600);
  await page.waitForTimeout(150);
  const after = await page.evaluate(() => ({ ...window.__logViewer.state.view }));
  check('wheel zooms the shared time axis', after.x1 - after.x0 < (before.x1 - before.x0) * 0.7, `${(before.x1 - before.x0).toFixed(1)} s -> ${(after.x1 - after.x0).toFixed(1)} s`);
  // pan by drag
  await page.mouse.move(box.x + box.width * 0.6, box.y + box.height * 0.5);
  await page.mouse.down(); await page.mouse.move(box.x + box.width * 0.3, box.y + box.height * 0.5, { steps: 5 }); await page.mouse.up();
  const panned = await page.evaluate(() => ({ ...window.__logViewer.state.view }));
  check('drag pans', panned.x0 > after.x0, `${after.x0.toFixed(2)} -> ${panned.x0.toFixed(2)}`);
  await page.screenshot({ path: path.join(shots, '02-starter-zoomed.png') });

  // tree: expand carControl, click a leaf into the empty third pane
  await page.locator('.pane').nth(2).click({ position: { x: 200, y: 60 } });
  await page.fill('#search', 'carcontrol actuators torque');
  await page.waitForTimeout(150);
  const rows = await page.locator('.row.leaf').allTextContents();
  check('filter finds /carControl/actuators/torque', rows.some((r) => r.includes('/carControl/actuators/torque')), rows.slice(0, 4).join(' | '));
  await page.locator('.row.leaf', { hasText: '/carControl/actuators/torque' }).first().click();
  await page.fill('#search', '');
  const curves3 = await page.evaluate(() => window.__logViewer.state.panes[2].model.curves.map((c) => c.name));
  check('click adds curve to the active pane', curves3.includes('/carControl/actuators/torque'), curves3.join(','));
  // expand a service in the tree
  await page.locator('.row.svc', { hasText: 'controlsState' }).first().click();
  await page.waitForFunction(() => window.__logViewer.state.route.services.get('controlsState').extracted && !window.__logViewer.state.extracting.size);
  await page.waitForTimeout(150);
  const treeRows = await page.locator('.row').count();
  check('expanding a service shows its fields', treeRows > 20, treeRows);
  await page.screenshot({ path: path.join(shots, '03-tree-three-panes.png') });

  // built-in layouts
  for (const name of ['longitudinal.json', 'torque-controller.json', 'tuning.json', 'CAN-bus-debug.json']) {
    await page.selectOption('#layout-select', name);
    await page.waitForFunction(() => !window.__logViewer.state.extracting.size, null, { timeout: 120000 });
    await page.waitForTimeout(300);
    const r = await page.evaluate(() => {
      const out = { curves: 0, ok: 0, errors: [] };
      for (const p of window.__logViewer.state.panes) for (const c of p.model.curves) {
        out.curves++;
        const d = window.__logViewer.curveData(c);
        if (d.t && d.t.length) out.ok++; else out.errors.push(`${c.name}: ${d.error || (d.pending ? 'pending' : 'empty')}`);
      }
      return out;
    });
    check(`layout ${name}`, r.curves > 0 && r.ok > 0, `${r.ok}/${r.curves} curves with data${r.errors.length ? '; ' + r.errors.slice(0, 6).join('; ') : ''}`);
    await page.screenshot({ path: path.join(shots, `04-layout-${name.replace('.json', '')}.png`) });
  }

  // logs + inspector panels
  await page.click('.tab-btn[data-panel="logs"]');
  await page.waitForTimeout(400);
  const logRows = await page.locator('.log-row').count();
  check('logs panel lists log messages', logRows > 5, logRows);
  await page.screenshot({ path: path.join(shots, '05-logs.png') });
  await page.click('.tab-btn[data-panel="inspector"]');
  await page.selectOption('#inspect-service', 'carState');
  await page.waitForTimeout(400);
  const insp = await page.textContent('#inspector');
  check('inspector shows the carState message', insp.includes('vEgo'), insp.slice(0, 80).replace(/\s+/g, ' '));
  await page.screenshot({ path: path.join(shots, '06-inspector.png') });

  // DBC + CAN signal
  await page.setInputFiles('#dbc-input', dbc);
  await page.waitForTimeout(300);
  const can = await page.evaluate(async () => {
    await window.__logViewer.ensureCan('can');
    const s = window.__logViewer.getSeries('/can/0/SAS11/SAS_Angle') || window.__logViewer.getSeries('/can/0/MDPS12/CR_Mdps_StrColTq');
    return s ? { n: s.t.length, first: s.v[0] } : null;
  });
  check('DBC signal decodes from can', can && can.n > 100, JSON.stringify(can));

  // custom python translation
  const cp = await page.evaluate(() => {
    const f = window.__logViewer.compileCustom;
    const jp = (body, params, n) => `def __jotpluggler_eval_sample(${params}):\n    return ${body}\n\n__jotpluggler_result = np.empty_like(value, dtype=np.float64)\nfor __jotpluggler_i in range(len(value)):\n    __jotpluggler_result[__jotpluggler_i] = __jotpluggler_eval_sample(${['time', 'value', ...Array.from({ length: n }, (_, i) => 'v' + (i + 1))].map((x) => x + '[__jotpluggler_i]').join(', ')})\nreturn __jotpluggler_result`;
    const ok = f({ function_code: jp('(value * v1 ** 2) - (v2 * 9.81)', 'time, value, v1, v2', 2), additional_sources: ['a', 'b'] });
    const bad = f({ function_code: 'return __import__("os").system("x")', additional_sources: [] });
    const bad2 = f({ function_code: 'return value.constructor', additional_sources: [] });
    const bad3 = f({ function_code: 'def __jotpluggler_eval_sample(time, value=globalThis.x):\n    return value\n\n__jotpluggler_result = np.empty_like(value)\n', additional_sources: [] });
    return { ok: ok.fn ? ok.fn(0, 2, 3, 1) : ok.error, bad: bad.error || 'compiled!', bad2: bad2.error || 'compiled!', bad3: bad3.error || 'compiled!' };
  });
  check('custom series: arithmetic translated, other code refused', cp.ok === 2 * 9 - 9.81 && !/compiled/.test(cp.bad + cp.bad2 + cp.bad3), JSON.stringify(cp));

  // layout titles, tab close, colors, custom-series semantics, filter during load-all
  await page.selectOption('#layout-select', 'torque-controller.json');
  await page.waitForFunction(() => !window.__logViewer.state.extracting.size, null, { timeout: 120000 });
  const titles = await page.locator('.pane-title:not(.hidden)').allTextContents();
  check('layout pane titles are shown', titles.length > 0, titles.slice(0, 2).join(' | '));
  const tabs = await page.locator('.tab').count();
  await page.locator('.tab').nth(tabs - 1).click();
  await page.locator('.tab').nth(tabs - 1).locator('.x').click();
  await page.waitForFunction(() => !window.__logViewer.state.extracting.size, null, { timeout: 120000 });
  await page.waitForTimeout(300);
  const afterClose = await page.evaluate(() => window.__logViewer.state.panes.flatMap((p) => p.model.curves.map((c) => window.__logViewer.curveData(c))).filter((d) => d.pending).length);
  check('closing the active tab loads the next tab\'s curves', afterClose === 0, `${afterClose} pending`);
  const color = await page.evaluate(() => {
    const l = window.__logViewer.normalizeLayout({ tabs: [{ root: { curves: [{ name: '/carState/vEgo', color: 'url(https://example.invalid/x)' }, { name: '/carState/aEgo', color: '#12ab9F' }] } }] });
    return l.tabs[0].root.curves.map((c) => c.color ?? null);
  });
  check('layout colors: only #rrggbb accepted', color[0] === null && color[1] === '#12ab9F', JSON.stringify(color));
  const sem = await page.evaluate(() => {
    const f = window.__logViewer.compileCustom;
    const jp = (body, params, n) => `def __jotpluggler_eval_sample(${params}):\n    return ${body}\n\n__jotpluggler_result = np.empty_like(value, dtype=np.float64)\nfor __jotpluggler_i in range(len(value)):\n    __jotpluggler_result[__jotpluggler_i] = __jotpluggler_eval_sample(${['time', 'value', ...Array.from({ length: n }, (_, i) => 'v' + (i + 1))].map((x) => x + '[__jotpluggler_i]').join(', ')})\nreturn __jotpluggler_result`;
    const run = (code, n, args) => { const r = f({ function_code: code, additional_sources: Array.from({ length: n }, (_, i) => 's' + i) }); return r.error ? 'ERR' : r.fn(...args); };
    const vec = (expr, n = 0) => run('return ' + expr, n, [0, 5, 7]);
    const smp = (expr, n = 0, args = [0, 5, 7]) => run(jp(expr, ['time', 'value', ...Array.from({ length: n }, (_, i) => 'v' + (i + 1))].join(', '), n), n, args);
    return {
      // refused: means something else in numpy or would fail in jotpluggler
      mod: vec('value % 3'), vecChained: vec('0 < value < 9'), tuple: vec('time, value'), vecmax: vec('value - np.max(value)'),
      vecAnd: vec('(value > 1) and (value < 9)'), bareSqrt: vec('sqrt(value)'), mathLog: vec('math.log(value)'), logBase: vec('np.log(value, 5)'),
      npMax2: smp('np.max(value, v1)', 1), decr: vec('value-->0'), constant: vec('0'),
      editedLoop: run(jp('value', 'time, value', 0).replace('return __jotpluggler_result', 'return __jotpluggler_result * 2 + 1'), 0, [0, 5]),
      // evaluated with Python's meaning, per sample
      sampleMax: smp('max(value, v1)', 1), negneg: vec('--value'), mulNeg: smp('value * --v1', 1), powNeg: vec('-value ** 2'),
      chained: smp('0 < value < 9'), nanOr: smp('value and 1 or 0', 0, [0, NaN]), maxNan: smp('max(value, v1)', 1, [0, NaN, 1]),
      maxNan2: smp('max(v1, value)', 1, [0, NaN, 1]), whereNp: smp('np.where(value > 4, 1, 0)'), npMax1: smp('np.max(value)'),
    };
  });
  const E = (k) => sem[k] === 'ERR';
  check('custom series: Python-only semantics refused, rest equal',
    ['mod', 'vecChained', 'tuple', 'vecmax', 'vecAnd', 'bareSqrt', 'mathLog', 'logBase', 'npMax2', 'decr', 'constant', 'editedLoop'].every(E) &&
    sem.sampleMax === 7 && sem.negneg === 5 && sem.mulNeg === 35 && sem.powNeg === -25 && sem.chained === true && sem.nanOr === 1 &&
    Number.isNaN(sem.maxNan) && sem.maxNan2 === 1 && sem.whereNp === 1 && sem.npMax1 === 5, JSON.stringify(sem));
  await page.fill('#search', 'steer');
  await page.click('#btn-loadall');
  await page.waitForFunction(() => document.querySelector('#progress').classList.contains('hidden') && !window.__logViewer.state.extracting.size, null, { timeout: 300000 });
  await page.fill('#search', '');
  check('filter + load all: no page errors', errors.length === 0, errors.slice(0, 3).join(' | '));

  // CAN event-level series and curve states; malformed layouts; a value range below float resolution
  const canState = await page.evaluate(async () => {
    const L = window.__logViewer;
    await L.ensureService('can');
    const t = L.getSeries('/can/t');
    const lay = L.normalizeLayout({ tabs: [{ root: { curves: [{ name: '/can/0/NOT_A_MSG/X' }, { name: '/can/0/0x2B0/byte0' }, { name: '/can/9/0x7FF/byte0' }] } }] });
    return { t: t ? t.t.length : 0, curves: lay.tabs[0].root.curves.map((c) => { const d = L.curveData(c); return d.error || (d.t ? d.t.length : 'pending'); }) };
  });
  check('/can/t exists; CAN curves resolve to data or an explicit error', canState.t > 100 && canState.curves.every((x) => x !== 'pending'), JSON.stringify(canState));
  const malformed = await page.evaluate(() => {
    const L = window.__logViewer;
    const lay = L.normalizeLayout({ tabs: [null, 5, { name: 'x', root: { curves: [
      { name: '/carState/vEgo', transform: 'scale', scale: null, offset: '3' },
      { name: 'c', custom_python: { linked_source: '/carState/vEgo', additional_sources: 5, globals_code: 5, function_code: 7 } },
      { name: '/carState/aEgo', _slot: 'x', color: 5 }] } }] });
    L.setLayout(lay, true);
    const curves = lay.tabs[0].root.curves;
    return { tabs: lay.tabs.length, panes: L.state.panes.length, scale: L.curveData(curves[0]).v[0] === L.getSeries('/carState/vEgo').v[0], custom: L.curveData(curves[1]).error || 'ok', slot: curves[2]._slot ?? null };
  });
  check('malformed layout parts are coerced like jotpluggler, nothing throws', malformed.tabs === 1 && malformed.panes === 1 && malformed.scale && malformed.slot === null && errors.length === 0, JSON.stringify(malformed));
  const tiny = await page.evaluate(() => {
    const L = window.__logViewer;
    L.setLayout(L.normalizeLayout({ tabs: [{ root: { y_limits: { min: 1e16, max: 1e16 + 2 }, curves: [{ name: '/carState/vEgo' }] } }] }), true);
    const t0 = performance.now(); L.state.panes.forEach((p) => { p.dirty = true; }); L.renderFrame(); return performance.now() - t0;
  });
  check('a value range below float resolution renders promptly', tiny < 1000, `${tiny.toFixed(0)} ms`);

  // dark theme
  await page.emulateMedia({ colorScheme: 'dark' });
  await page.selectOption('#layout-select', '__default');
  await page.waitForTimeout(400);
  await page.screenshot({ path: path.join(shots, '07-dark.png') });
  // narrow viewport
  await page.setViewportSize({ width: 390, height: 840 });
  await page.waitForTimeout(300);
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
  check('no horizontal page scroll at phone width', !overflow);
  await page.screenshot({ path: path.join(shots, '08-phone.png') });
  await page.selectOption('#layout-select', 'gps_vs_llk.json'); // has side-by-side panes
  await page.waitForTimeout(400);
  const overflow2 = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
  check('no horizontal page scroll at phone width with side-by-side panes', !overflow2);
  await page.locator('#btn-bottom-toggle').scrollIntoViewIfNeeded();
  await page.click('.tab-btn[data-panel="logs"]');
  await page.waitForTimeout(300);
  await page.locator('#log-list').scrollIntoViewIfNeeded();
  const logsVisible = await page.evaluate(() => {
    const r = document.querySelector('#log-list').getBoundingClientRect();
    return r.height > 100 && r.top < window.innerHeight && r.bottom > 0 && document.querySelectorAll('.log-row').length > 3;
  });
  check('phone width: the logs panel can be opened and scrolled into view', logsVisible);
  await page.screenshot({ path: path.join(shots, '11-phone-logs.png') });
  const fresh = await browser.newPage({ viewport: { width: 390, height: 840 } });
  await fresh.goto('file://' + path.resolve(html));
  const reach = await fresh.evaluate(() => [...document.querySelectorAll('.topbar button, .topbar select')].every((b) => {
    const r = b.getBoundingClientRect(), hit = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2);
    return hit && (hit === b || b.contains(hit));
  }));
  check('phone width, nothing open: every toolbar control is reachable', reach);
  await fresh.screenshot({ path: path.join(shots, '10-phone-empty.png') });
  await fresh.close();

  check('no page errors during the run', errors.length === 0, errors.slice(0, 5).join(' | '));
  await browser.close();
  const failed = checks.filter((c) => !c.ok).length;
  console.log(`${checks.length - failed}/${checks.length} checks passed`);
  process.exitCode = failed ? 1 : 0;
})().catch((e) => { console.error(e); process.exit(2); });
