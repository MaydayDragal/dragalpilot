/* app.js: UI of the standalone log viewer (tree, plots, layouts, timeline, logs, inspector). */
(function () {
  'use strict';

  const LR = window.LogReader;
  LR.codecs.zstd = LR.fzstdCodec(window.fzstd);
  LR.codecs.bz2 = window.bunzip2;
  const readJson = (id) => JSON.parse(document.getElementById(id).textContent);
  const SCHEMA = LR.compileSchema(readJson('schema-json'));
  const BUILTIN_LAYOUTS = readJson('layouts-json');
  const BUILD = readJson('build-json');
  const { upperBound, lowerBound } = LR;

  // ---- small helpers ---------------------------------------------------------------------------
  const $ = (sel, el = document) => el.querySelector(sel);
  function h(tag, props, ...kids) {
    const el = document.createElement(tag);
    if (props) {
      for (const k of Object.keys(props)) {
        const v = props[k];
        if (v === undefined || v === null || v === false) continue;
        if (k === 'class') el.className = v;
        else if (k === 'style') el.style.cssText = v;
        else if (k.startsWith('on')) el.addEventListener(k.slice(2), v);
        else if (k === 'text') el.textContent = v;
        else el.setAttribute(k, v === true ? '' : v);
      }
    }
    for (const c of kids.flat()) if (c !== null && c !== undefined && c !== false) el.append(c.nodeType ? c : String(c));
    return el;
  }
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const nextFrame = () => new Promise((r) => requestAnimationFrame(() => setTimeout(r, 0)));
  const store = {
    get(k, d) { try { const v = localStorage.getItem('logviewer.' + k); return v === null ? d : JSON.parse(v); } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem('logviewer.' + k, JSON.stringify(v)); } catch (e) { /* storage unavailable */ } },
  };
  function download(name, text, type) {
    const a = h('a', { href: URL.createObjectURL(new Blob([text], { type })), download: name });
    document.body.append(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  }
  let toastTimer = 0;
  function toast(msg, isError) {
    const el = $('#toast');
    el.textContent = msg;
    el.classList.toggle('error', !!isError);
    el.classList.remove('hidden');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => el.classList.add('hidden'), isError ? 9000 : 4000);
  }
  function fmtCount(n) { return n.toLocaleString('en-US'); }
  function fmtValue(v, s) {
    if (v === undefined || v === null) return '';
    if (Number.isNaN(v)) return 'NaN';
    if (s && s.enumNames && s.enumNames[v] !== undefined && s.enumNames[v] !== '') return `${s.enumNames[v]} (${v})`;
    if (s && s.kind === 'bool') return v ? 'true' : 'false';
    if (Number.isInteger(v) && Math.abs(v) < 1e15) return String(v);
    const a = Math.abs(v);
    if (a !== 0 && (a < 1e-4 || a >= 1e9)) return v.toExponential(4);
    return String(+v.toPrecision(6));
  }
  function niceStep(range, target) {
    const raw = range / Math.max(1, target);
    const p = Math.pow(10, Math.floor(Math.log10(raw)));
    const m = raw / p;
    return (m < 1.5 ? 1 : m < 3.5 ? 2 : m < 7.5 ? 5 : 10) * p;
  }
  function tickLabel(v, step) {
    if (Math.abs(v) < step * 1e-6) v = 0;
    const a = Math.max(Math.abs(v), step);
    if (a >= 1e7 || a < 1e-4) return v.toExponential(Math.max(0, Math.min(6, -Math.floor(Math.log10(step)) + Math.floor(Math.log10(a || 1))))).replace('e+', 'e');
    const dec = Math.max(0, Math.min(8, -Math.floor(Math.log10(step) + 1e-9)));
    return v.toFixed(dec);
  }
  function sampleIndex(t, time) { return upperBound(t, time) - 1; }
  // Tick values k * step in [lo, hi], by index (adding step to a large value can stall when the
  // step is below its float resolution); at most 200, skipping values that round to the same float.
  function ticks(lo, hi, step) {
    const k0 = Math.ceil(lo / step), k1 = Math.floor(hi / step + 1e-9), out = [];
    if (!(k1 - k0 < 200) || !Number.isFinite(k0)) return out;
    for (let k = k0; k <= k1; k++) { const v = k * step; if (out[out.length - 1] !== v) out.push(v); }
    return out;
  }
  // A value range wide enough to draw: at least a few float steps at its magnitude.
  function minSpan(lo, hi) {
    const mid = (lo + hi) / 2, need = Math.max(Math.abs(mid) * 1e-9, 1e-12);
    return hi - lo >= need ? [lo, hi] : [mid - need / 2, mid + need / 2];
  }

  // ---- theme ---------------------------------------------------------------------------------------
  let themeVersion = 0, colors = null;
  function readColors() {
    const cs = getComputedStyle(document.documentElement);
    const g = (n) => cs.getPropertyValue(n).trim();
    colors = {
      surface: g('--surface'), grid: g('--grid'), axis: g('--axis'), text: g('--text-2'), muted: g('--muted'),
      cursor: g('--cursor'), select: g('--select'), lat: g('--lat'), long: g('--long'), shade: g('--shade'),
      series: [1, 2, 3, 4, 5, 6, 7, 8].map((i) => g('--s' + i)), mono: g('--mono'), sans: g('--sans'),
    };
    themeVersion++;
  }
  function applyTheme(mode) {
    if (mode === 'light' || mode === 'dark') document.documentElement.setAttribute('data-theme', mode);
    else document.documentElement.removeAttribute('data-theme');
    store.set('theme', mode);
    readColors();
    for (const p of state.panes) p.dirty = true;
    requestRender();
  }
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => { readColors(); for (const p of state.panes) p.dirty = true; requestRender(); });

  // ---- state -----------------------------------------------------------------------------------------
  const state = {
    route: null,
    view: { x0: 0, x1: 1 },
    cursor: null,
    layout: null,
    tabIndex: 0,
    activePane: null,     // pane model
    panes: [],            // PlotPane instances of the current tab
    dbcs: [],
    extracting: new Map(),
    canBuilding: new Map(),
    curveCache: new WeakMap(),
    engaged: null,
    shade: true,
  };

  // ---- layouts (jotpluggler JSON format) -----------------------------------------------------------
  function emptyPane() { return { title: '...', curves: [] }; }
  function defaultLayout() {
    return {
      current_tab_index: 0,
      tabs: [{
        name: 'main',
        root: {
          split: 'vertical', sizes: [0.34, 0.33, 0.33],
          children: [
            { title: '...', curves: [{ name: '/carState/vEgo', _slot: 0 }] },
            { title: '...', curves: [{ name: '/carState/steeringAngleDeg', _slot: 0 }] },
            emptyPane(),
          ],
        },
      }],
    };
  }
  function isPane(node) { return node && !node.split; }
  const HEX_COLOR = /^#[0-9a-fA-F]{6}$/;
  // As jotpluggler's parse_workspace_node: a node with a "curves" array is a pane, otherwise a split
  // whose orientation is vertical only when it says so; sizes are clamped at 0 and normalized.
  function normalizeNode(node) {
    if (!node || typeof node !== 'object') return emptyPane();
    if (!Array.isArray(node.curves)) {
      const kids = (Array.isArray(node.children) ? node.children : []).map(normalizeNode);
      if (!kids.length) return emptyPane();
      if (kids.length === 1) return kids[0];
      let sizes = Array.isArray(node.sizes) ? node.sizes.filter((s) => typeof s === 'number').map((s) => Math.max(s, 0)) : [];
      const sum = sizes.reduce((a, b) => a + b, 0);
      sizes = sizes.length === kids.length && sum > 0 ? sizes.map((s) => Math.max(s / sum, 0.02)) : kids.map(() => 1 / kids.length);
      return { split: node.split === 'vertical' ? 'vertical' : 'horizontal', sizes, children: kids };
    }
    const pane = { title: typeof node.title === 'string' ? node.title : '...', curves: [] };
    // Types as jotpluggler's parser reads them: a field of the wrong type is treated as absent.
    const num = (v) => (typeof v === 'number' && Number.isFinite(v) ? v : undefined);
    const str = (v) => (typeof v === 'string' ? v : '');
    if (typeof node.kind === 'string' && node.kind) pane.kind = node.kind;
    if (typeof node.camera_view === 'string') pane.camera_view = node.camera_view;
    if (node.y_limits && typeof node.y_limits === 'object') {
      const lim = { min: num(node.y_limits.min), max: num(node.y_limits.max) };
      if (lim.min !== undefined || lim.max !== undefined) pane.y_limits = lim;
    }
    if (node.range && typeof node.range === 'object') pane.range = node.range;
    for (const c of Array.isArray(node.curves) ? node.curves : []) {
      if (!c || typeof c !== 'object' || typeof c.name !== 'string') continue;
      const curve = { name: c.name };
      if (c.transform === 'derivative') { curve.transform = 'derivative'; if (num(c.derivative_dt) !== undefined) curve.derivative_dt = c.derivative_dt; }
      else if (c.transform === 'scale') { curve.transform = 'scale'; curve.scale = num(c.scale) ?? 1; curve.offset = num(c.offset) ?? 0; }
      if (c.custom_python && typeof c.custom_python === 'object') {
        const cp = c.custom_python;
        curve.custom_python = {
          linked_source: str(cp.linked_source),
          additional_sources: Array.isArray(cp.additional_sources) ? cp.additional_sources.filter((s) => typeof s === 'string') : [],
          globals_code: str(cp.globals_code), function_code: str(cp.function_code),
        };
      }
      if (Number.isInteger(c._slot) && c._slot >= 0 && c._slot < 64) curve._slot = c._slot;
      if (c._hidden === true) curve._hidden = true;
      if (typeof c.color === 'string' && HEX_COLOR.test(c.color)) curve.color = c.color; // nothing else reaches CSS
      pane.curves.push(curve);
    }
    return pane;
  }
  function normalizeLayout(obj) {
    if (!obj || typeof obj !== 'object' || !Array.isArray(obj.tabs)) throw new Error('not a jotpluggler layout (no tabs)');
    const tabs = obj.tabs.filter((t) => t && typeof t === 'object') // jotpluggler skips non-object tabs
      .map((t, i) => ({ name: typeof t.name === 'string' && t.name ? t.name : `tab${i + 1}`, root: normalizeNode(t.root) }));
    if (!tabs.length) throw new Error('layout has no tabs');
    const idx = typeof obj.current_tab_index === 'number' ? obj.current_tab_index : obj.currentTabIndex;
    return { current_tab_index: clamp(typeof idx === 'number' ? idx | 0 : 0, 0, tabs.length - 1), tabs };
  }
  function exportLayout() {
    const strip = (node) => {
      if (node.split) return { split: node.split, sizes: node.sizes, children: node.children.map(strip) };
      const out = { title: node.title || '...' };
      if (node.kind) out.kind = node.kind;
      if (node.camera_view) out.camera_view = node.camera_view;
      if (node.y_limits) out.y_limits = node.y_limits;
      const pp = state.panes.find((p) => p.model === node);
      if (pp && state.route && Number.isFinite(pp.y0)) out.range = { left: state.view.x0, right: state.view.x1, top: pp.y1, bottom: pp.y0 };
      else if (node.range) out.range = node.range;
      out.curves = node.curves.map((c) => {
        const o = { name: c.name, color: curveColor(c) };
        for (const k of ['transform', 'derivative_dt', 'scale', 'offset', 'custom_python']) if (c[k] !== undefined) o[k] = c[k];
        return o;
      });
      return out;
    };
    return { current_tab_index: state.tabIndex, tabs: state.layout.tabs.map((t) => ({ name: t.name, root: strip(t.root) })) };
  }
  function saveLayoutSoon() {
    clearTimeout(saveLayoutSoon.t);
    saveLayoutSoon.t = setTimeout(() => {
      const keep = (node) => node.split ? { ...node, children: node.children.map(keep) }
        : { ...node, curves: node.curves.map((c) => ({ ...c })) };
      store.set('layout', { current_tab_index: state.tabIndex, tabs: state.layout.tabs.map((t) => ({ name: t.name, root: keep(t.root) })) });
    }, 300);
  }
  function setLayout(layout, keepView) {
    state.layout = layout;
    state.tabIndex = layout.current_tab_index || 0;
    state.activePane = null;
    renderTabs();
    renderWorkspace();
    saveLayoutSoon();
    loadCurvesOfTab();
    if (!keepView) fitAll();
  }
  function currentTab() { return state.layout.tabs[state.tabIndex]; }
  function forEachPane(node, cb) { if (node.split) node.children.forEach((c) => forEachPane(c, cb)); else cb(node); }
  function findParent(node, target) {
    if (!node.split) return null;
    for (let i = 0; i < node.children.length; i++) {
      if (node.children[i] === target) return { parent: node, index: i };
      const r = findParent(node.children[i], target);
      if (r) return r;
    }
    return null;
  }
  function splitPane(pane, dir) {
    const tab = currentTab();
    const fresh = emptyPane();
    const loc = findParent(tab.root, pane);
    if (loc && loc.parent.split === dir) {
      const s = loc.parent.sizes[loc.index] / 2;
      loc.parent.sizes.splice(loc.index, 1, s, s);
      loc.parent.children.splice(loc.index + 1, 0, fresh);
    } else {
      const node = { split: dir, sizes: [0.5, 0.5], children: [pane, fresh] };
      if (loc) loc.parent.children[loc.index] = node; else tab.root = node;
    }
    state.activePane = fresh;
    layoutChanged();
  }
  function closePane(pane) {
    const tab = currentTab();
    const loc = findParent(tab.root, pane);
    if (!loc) { tab.root = emptyPane(); } else {
      const p = loc.parent;
      p.children.splice(loc.index, 1);
      const removed = p.sizes.splice(loc.index, 1)[0];
      const sum = p.sizes.reduce((a, b) => a + b, 0) || 1;
      p.sizes = p.sizes.map((s) => s / sum);
      if (p.children.length === 1) {
        const up = findParent(tab.root, p);
        if (up) up.parent.children[up.index] = p.children[0]; else tab.root = p.children[0];
      }
      void removed;
    }
    if (state.activePane === pane) state.activePane = null;
    layoutChanged();
  }
  function layoutChanged() { renderWorkspace(); saveLayoutSoon(); }

  function usedSlots(pane) { return new Set(pane.curves.map((c) => c._slot).filter((s) => s !== undefined)); }
  function curveColor(c) {
    if (c._slot !== undefined) return colors.series[c._slot % colors.series.length];
    return c.color && HEX_COLOR.test(c.color) ? c.color : colors.series[0];
  }
  function addCurve(pane, path) {
    if (!pane || pane.kind) return;
    if (pane.curves.some((c) => c.name === path && !c.custom_python && !c.transform)) { toast(`${path} is already in this plot`); return; }
    const used = usedSlots(pane);
    let slot = 0;
    while (used.has(slot) && slot < 64) slot++;
    // slots past the eight palette hues repeat colors: only once a plot has more than eight curves
    pane.curves.push({ name: path, _slot: slot });
    setActivePane(pane);
    ensureSeries([path]).then(() => { refreshPanes(); });
    refreshPanes(true);
    saveLayoutSoon();
  }

  // ---- series access ---------------------------------------------------------------------------------
  function serviceOf(path) { const m = /^\/([^/]+)/.exec(path); return m ? m[1] : null; }
  function getSeries(path) {
    const route = state.route;
    if (!route) return null;
    let s = route.series.get(path);
    if (s) return s;
    s = canSeries(path);
    if (s) route.series.set(path, s);
    return s;
  }
  async function ensureService(name) {
    const route = state.route;
    if (!route || !route.services.has(name)) return;
    const svc = route.services.get(name);
    if (svc.extracted && !state.extracting.has(name)) return;
    if (state.extracting.has(name)) return state.extracting.get(name);
    const extracting = state.extracting; // replaced when files are (re)opened
    const p = (async () => {
      const it = route.extractIter(name);
      const t0 = performance.now();
      let last = t0;
      for (;;) {
        const r = it.next();
        if (r.done) break;
        const now = performance.now();
        if (now - last > 40) { setStatus(`decoding ${name} ${Math.round(r.value * 100)}%`); await nextFrame(); last = performance.now(); }
      }
      if (route !== state.route) return;
      setStatus();
      if (svc.errors) toast(`${name}: ${svc.errors} message(s) could not be fully decoded (first: ${svc.firstError})`, true);
      state.curveCache = new WeakMap();
      if (name === 'carControl') state.engaged = null;
      treeChanged();
    })();
    extracting.set(name, p);
    try { await p; } finally { if (extracting.get(name) === p) extracting.delete(name); }
  }
  // CAN frame index of can / sendcan, built in steps like ensureService
  async function ensureCan(name) {
    const route = state.route;
    if (!route || !route.services.has(name)) return;
    const svc = route.services.get(name);
    if (svc.can) return;
    const building = state.canBuilding;
    if (building.has(name)) return building.get(name);
    const p = (async () => {
      const it = route.canIndexIter(name);
      let last = performance.now();
      for (;;) {
        const r = it.next();
        if (r.done) break;
        if (performance.now() - last > 40) { setStatus(`indexing ${name} frames ${Math.round(r.value * 100)}%`); await nextFrame(); last = performance.now(); }
      }
      if (route !== state.route) return;
      setStatus();
      if (svc.canErrors) toast(`${name}: ${svc.canErrors} message(s) with unreadable frames were skipped (first: ${svc.canFirstError})`, true);
      state.curveCache = new WeakMap();
      treeChanged();
      refreshPanes();
    })();
    building.set(name, p);
    try { await p; } finally { if (building.get(name) === p) building.delete(name); }
  }
  const CAN_BASE = /^\/(can|sendcan)\/(valid|logMonoTime|t)$/;
  async function ensureSeries(paths) {
    const names = new Set(), cans = new Set();
    for (const p of paths) {
      const s = serviceOf(p);
      if (!s) continue;
      if ((s === 'can' || s === 'sendcan') && !CAN_BASE.test(p)) cans.add(s); else names.add(s);
    }
    for (const n of names) await ensureService(n);
    for (const n of cans) await ensureCan(n);
  }
  function curvePaths(c) {
    if (c.custom_python) return [c.custom_python.linked_source, ...(c.custom_python.additional_sources || [])].filter(Boolean);
    return [c.name];
  }
  async function loadCurvesOfTab() {
    if (!state.route) return;
    const paths = [];
    forEachPane(currentTab().root, (p) => p.curves.forEach((c) => paths.push(...curvePaths(c))));
    await ensureSeries(paths);
    refreshPanes();
  }

  // Curve data after transforms: { t, v, step, s (base series) } or { error }
  function curveData(c) {
    const sig = `${c.name}|${c.transform}|${c.derivative_dt}|${c.scale}|${c.offset}|${c.custom_python ? JSON.stringify(c.custom_python) : ''}`;
    const cached = state.curveCache.get(c);
    if (cached && cached.sig === sig) return cached.data;
    let data;
    try { data = computeCurve(c); } catch (e) { data = { error: `cannot compute: ${e.message}` }; }
    if (!data.pending) state.curveCache.set(c, { sig, data });
    return data;
  }
  // Why a path has no series yet: { pending } while its service or CAN index is being built, else { error }
  function missingReason(path) {
    const route = state.route, svc = serviceOf(path);
    if (!svc || !route.services.has(svc)) return { error: svc ? `no ${svc} messages in these files` : 'not a series path' };
    const s = route.services.get(svc);
    if ((svc === 'can' || svc === 'sendcan') && !CAN_BASE.test(path)) {
      if (!s.can) { if (!state.canBuilding.has(svc)) setTimeout(() => ensureCan(svc), 0); return { pending: true }; }
      return { error: canMissing(path) };
    }
    if (!s.paths) { if (!state.extracting.has(svc)) setTimeout(() => ensureService(svc), 0); return { pending: true }; }
    return { error: 'not in this log' };
  }
  function computeCurve(c) {
    if (!state.route) return { error: 'no log loaded' };
    let base;
    if (c.custom_python) {
      base = customSeries(c.custom_python);
      if (base.error || base.pending) return base;
    } else {
      base = getSeries(c.name);
      if (!base) return missingReason(c.name);
    }
    let t = base.t, v = base.v;
    let step = !!base.integer;
    if (c.transform === 'derivative') {
      const dt = typeof c.derivative_dt === 'number' && c.derivative_dt > 0 ? c.derivative_dt : 0;
      const tt = [], vv = [];
      for (let i = 1; i < t.length; i++) {
        const d = dt || t[i] - t[i - 1];
        if (d <= 0) continue;
        tt.push(t[i]); vv.push((v[i] - v[i - 1]) / d);
      }
      t = Float64Array.from(tt); v = Float64Array.from(vv); step = false;
    }
    const fin = (x, d) => (typeof x === 'number' && Number.isFinite(x) ? x : d); // as jotpluggler: non-numbers mean the default
    const scale = c.transform === 'scale' ? fin(c.scale, 1) : 1;
    const offset = c.transform === 'scale' ? fin(c.offset, 0) : 0;
    // Float64Array.from: series keep their wire type (e.g. Uint8Array), which must not truncate the result
    if (scale !== 1 || offset !== 0) { v = Float64Array.from(v, (x) => x * scale + offset); step = step && Number.isInteger(scale) && Number.isInteger(offset); }
    const label = c.custom_python ? c.name : c.name + (c.transform === 'derivative' ? ' (d/dt)' : '') + (scale !== 1 || offset !== 0 ? ` (×${scale}${offset ? (offset > 0 ? '+' : '') + offset : ''})` : '');
    const plain = !c.transform && !c.custom_python;
    return { t, v, step, s: plain ? base : { kind: 'float64' }, label };
  }

  // jotpluggler custom Python series (tools/jotpluggler/math_eval.py). Two forms occur in layouts:
  //  - jotpluggler's generated wrapper: `def __jotpluggler_eval_sample(time, value, v1..):` with a
  //    one-line `return <expr>`, then its fixed loop over the samples (accepted only verbatim);
  //  - a single `return <expr>`, which numpy evaluates on whole arrays ("vectorized").
  // The expression is parsed (a small Python subset) and compiled to JS that means the same per
  // sample: Python truthiness for and/or/not (NaN is true), chained comparisons, `**` binding,
  // builtin min/max NaN behaviour, argument counts. Anything else is refused, never approximated.
  const PY_RT = Object.freeze({
    T: (x) => x !== 0 && x !== false,
    and: (a, b) => (PY_RT.T(a) ? b : a),
    or: (a, b) => (PY_RT.T(a) ? a : b),
    not: (a) => !PY_RT.T(a),
    // CPython's builtin max/min keep the first item unless a later one compares greater/less
    max: (...xs) => xs.reduce((m, x) => (x > m ? x : m)),
    min: (...xs) => xs.reduce((m, x) => (x < m ? x : m)),
    where: (c, a, b) => (PY_RT.T(c) ? a : b),
    clip: (a, lo, hi) => Math.min(Math.max(a, lo), hi),
    id: (x) => x,
    radians: (x) => x * Math.PI / 180, degrees: (x) => x * 180 / Math.PI, square: (x) => x * x,
    abs: Math.abs, sqrt: Math.sqrt, sin: Math.sin, cos: Math.cos, tan: Math.tan, asin: Math.asin, acos: Math.acos,
    atan: Math.atan, atan2: Math.atan2, exp: Math.exp, log: Math.log, log10: Math.log10, log2: Math.log2,
    floor: Math.floor, ceil: Math.ceil, sign: Math.sign, fmax2: Math.max, fmin2: Math.min, hypot: Math.hypot,
  });
  // numpy functions: [runtime name, argument count]; scalar semantics equal numpy's (NaN propagates)
  const NP_FUNCS = {
    abs: ['abs', 1], absolute: ['abs', 1], fabs: ['abs', 1], sqrt: ['sqrt', 1], square: ['square', 1],
    sin: ['sin', 1], cos: ['cos', 1], tan: ['tan', 1], arcsin: ['asin', 1], arccos: ['acos', 1], arctan: ['atan', 1],
    arctan2: ['atan2', 2], exp: ['exp', 1], log: ['log', 1], log10: ['log10', 1], log2: ['log2', 1],
    floor: ['floor', 1], ceil: ['ceil', 1], sign: ['sign', 1], maximum: ['fmax2', 2], minimum: ['fmin2', 2],
    hypot: ['hypot', 2], radians: ['radians', 1], degrees: ['degrees', 1], deg2rad: ['radians', 1], rad2deg: ['degrees', 1],
    clip: ['clip', 3], where: ['where', 3],
  };
  const PY_KEYWORDS = new Set(['and', 'or', 'not', 'if', 'else', 'lambda', 'in', 'is', 'None', 'True', 'False', 'for', 'def', 'return']);

  function compilePyExpr(expr, params, vectorized) {
    const toks = [];
    const TOK = /\s+|(\d+\.\d*(?:[eE][+-]?\d+)?|\.\d+(?:[eE][+-]?\d+)?|\d+(?:[eE][+-]?\d+)?)|([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)|(\*\*|<=|>=|==|!=|[-+*/(),<>])/y;
    for (let pos = 0; pos < expr.length;) {
      TOK.lastIndex = pos;
      const m = TOK.exec(expr);
      if (!m) throw new Error(`unsupported syntax at "${expr.slice(pos, pos + 12)}"`);
      pos = TOK.lastIndex;
      if (m[1]) toks.push({ k: 'num', v: m[1] }); else if (m[2]) toks.push({ k: 'name', v: m[2] }); else if (m[3]) toks.push({ k: 'op', v: m[3] });
    }
    let i = 0, usesSeries = false;
    const peek = () => toks[i], isOp = (v) => toks[i] && toks[i].k === 'op' && toks[i].v === v;
    const isWord = (v) => toks[i] && toks[i].k === 'name' && toks[i].v === v;
    const expect = (v) => { if (!isOp(v)) throw new Error(`expected "${v}"`); i++; };
    const refuse = (why) => { throw new Error(why); };
    const orExpr = () => {
      let a = andExpr();
      while (isWord('or')) { if (vectorized) refuse('"or" on whole arrays'); i++; a = `M.or(${a}, ${andExpr()})`; }
      return a;
    };
    const andExpr = () => {
      let a = notExpr();
      while (isWord('and')) { if (vectorized) refuse('"and" on whole arrays'); i++; a = `M.and(${a}, ${notExpr()})`; }
      return a;
    };
    const notExpr = () => {
      if (isWord('not')) { if (vectorized) refuse('"not" on whole arrays'); i++; return `M.not(${notExpr()})`; }
      return comparison();
    };
    const CMP = new Set(['<', '>', '<=', '>=', '==', '!=']);
    const comparison = () => {
      const terms = [arith()], ops = [];
      while (peek() && peek().k === 'op' && CMP.has(peek().v)) { ops.push(toks[i++].v); terms.push(arith()); }
      if (!ops.length) return terms[0];
      if (ops.length > 1 && vectorized) refuse('chained comparison on whole arrays');
      // a < b < c is (a < b) and (b < c); operands are pure, so repeating b is safe
      return '(' + ops.map((op, k) => `(${terms[k]} ${op} ${terms[k + 1]})`).join(' && ') + ')';
    };
    const arith = () => {
      let a = term();
      while (isOp('+') || isOp('-')) { const op = toks[i++].v; a = `(${a} ${op} ${term()})`; }
      return a;
    };
    const term = () => {
      let a = factor();
      while (isOp('*') || isOp('/')) { const op = toks[i++].v; a = `(${a} ${op} ${factor()})`; }
      return a;
    };
    const factor = () => {
      if (isOp('-') || isOp('+')) { const op = toks[i++].v; return `(${op}${factor()})`; }
      return power();
    };
    const power = () => {
      const a = atom();
      if (isOp('**')) { i++; return `(${a} ** ${factor()})`; } // right-associative, binds tighter than a unary minus on its left
      return a;
    };
    const args = () => {
      expect('(');
      const out = [];
      if (!isOp(')')) { out.push(orExpr()); while (isOp(',')) { i++; out.push(orExpr()); } }
      expect(')');
      return out;
    };
    const atom = () => {
      const t = peek();
      if (!t) refuse('unexpected end');
      if (t.k === 'num') { i++; return `(${t.v})`; }
      if (isOp('(')) { i++; const e = orExpr(); expect(')'); return e; }
      if (t.k !== 'name') refuse(`unexpected "${t.v}"`);
      i++;
      const name = t.v;
      if (params.includes(name)) { usesSeries = true; return `_${name}`; }
      if (name === 'True') return 'true';
      if (name === 'False') return 'false';
      const npm = /^(?:np|numpy)\.(\w+)$/.exec(name);
      if (npm && (npm[1] === 'pi' || npm[1] === 'e')) return npm[1] === 'pi' ? `(${Math.PI})` : `(${Math.E})`;
      if (!isOp('(')) refuse(`unsupported name "${name}"`);
      const a = args();
      const call = (fn, n) => { if (a.length !== n) refuse(`${name} takes ${n} argument(s) here`); return `M.${fn}(${a.join(', ')})`; };
      if (name === 'abs') return call('abs', 1);
      if (name === 'max' || name === 'min') {
        if (vectorized) refuse(`builtin ${name} on whole arrays`);
        if (a.length < 2) refuse(`${name} needs at least 2 arguments`);
        return `M.${name}(${a.join(', ')})`;
      }
      if (npm) {
        const f = npm[1];
        if (f === 'max' || f === 'min' || f === 'amax' || f === 'amin') {
          if (vectorized) refuse(`np.${f} is a reduction over the whole array`);
          return call('id', 1); // of a single sample: the sample itself
        }
        if (Object.prototype.hasOwnProperty.call(NP_FUNCS, f)) return call(NP_FUNCS[f][0], NP_FUNCS[f][1]);
      }
      return refuse(`unsupported function "${name}"`);
    };
    const js = orExpr();
    if (i !== toks.length) refuse(`unexpected "${toks[i].v}"`);
    if (vectorized && !usesSeries) refuse('constant result (jotpluggler needs an array)');
    return js;
  }

  function compileCustom(spec) {
    const fail = (why) => ({ error: `custom series not supported here: ${why}` });
    if (typeof spec.globals_code === 'string' && spec.globals_code.trim()) return fail('uses Python globals');
    const code = typeof spec.function_code === 'string' ? spec.function_code.replace(/\s+$/, '') : '';
    const nAdd = Array.isArray(spec.additional_sources) ? spec.additional_sources.length : 0;
    const envNames = ['time', 'value', ...Array.from({ length: nAdd }, (_, k) => 'v' + (k + 1))];
    let params = envNames, expr, vectorized = true;
    const m = /^def __jotpluggler_eval_sample\(([^)]*)\):\n {4}return ([^\n]+)(\n[\s\S]*)$/.exec(code);
    if (m) {
      params = m[1].split(',').map((s) => s.trim());
      const loop = `\n\n__jotpluggler_result = np.empty_like(value, dtype=np.float64)\nfor __jotpluggler_i in range(len(value)):\n` +
        `    __jotpluggler_result[__jotpluggler_i] = __jotpluggler_eval_sample(${envNames.map((p) => p + '[__jotpluggler_i]').join(', ')})\n` +
        'return __jotpluggler_result';
      if (m[3] !== loop) return fail('the code after the sample function is not jotpluggler\'s generated loop');
      expr = m[2]; vectorized = false;
    } else {
      const lines = code.trim().split('\n');
      if (lines.length !== 1 || !/^return\s/.test(lines[0].trim())) return fail('only a one-line return or jotpluggler\'s generated sample function');
      expr = lines[0].trim().replace(/^return\s+/, '');
    }
    if (params.length !== envNames.length) return fail('parameters do not match the sources');
    if (!params.every((p) => /^[A-Za-z_]\w*$/.test(p) && !PY_KEYWORDS.has(p)) || new Set(params).size !== params.length) return fail('parameter list');
    let js;
    try { js = compilePyExpr(expr, params, vectorized); } catch (e) { return fail(`${e.message} in "${expr}"`); }
    try {
      // eslint-disable-next-line no-new-func
      const raw = new Function('M', ...params.map((p) => '_' + p), `"use strict"; return (${js});`);
      return { fn: (...a) => raw(PY_RT, ...a), params, js }; // runtime bound here, not by callers
    } catch (e) { return fail(`cannot compile "${expr}"`); }
  }
  function customSeries(spec) {
    const compiled = compileCustom(spec);
    if (compiled.error) return compiled;
    const srcs = [spec.linked_source, ...spec.additional_sources];
    const series = srcs.map(getSeries);
    if (series.some((s) => !s)) {
      const reasons = srcs.map((p, i) => (series[i] ? null : missingReason(p))).filter(Boolean);
      if (reasons.some((r) => r.pending)) return { pending: true };
      return { error: `missing ${srcs.filter((p, i) => !series[i]).join(', ')}` };
    }
    const ref = series[0], n = ref.t.length;
    const extra = series.slice(1).map((s) => {
      // previous-sample hold onto the linked source's times, as jotpluggler's math_eval does
      const out = new Float64Array(n);
      for (let i = 0; i < n; i++) out[i] = s.v[clamp(upperBound(s.t, ref.t[i]) - 1, 0, s.v.length - 1)];
      return out;
    });
    const v = new Float64Array(n);
    const args = new Array(compiled.params.length);
    for (let i = 0; i < n; i++) {
      args[0] = ref.t[i]; args[1] = ref.v[i];
      for (let k = 0; k < extra.length; k++) args[k + 2] = extra[k][i];
      v[i] = Number(compiled.fn(...args));
    }
    return { t: ref.t, v, integer: false, kind: 'float64' };
  }

  // ---- CAN -------------------------------------------------------------------------------------------
  function dbcMessage(nameOrAddr) {
    for (const d of state.dbcs) {
      const m = typeof nameOrAddr === 'number' ? d.byId.get(nameOrAddr) : d.byName.get(nameOrAddr);
      if (m) return m;
    }
    return null;
  }
  // Frame groups of can / sendcan once indexed (ensureCan builds the index in steps), else []
  function canGroups(svc) {
    const s = state.route && state.route.services.get(svc);
    return (s && s.can) || [];
  }
  const hex = (a) => '0x' + a.toString(16).toUpperCase();
  const CAN_PATH = /^\/(can|sendcan)\/(\d+)\/([^/]+)\/([^/]+)$/;
  // Resolve a CAN path to { msg, sig, g, byte } or { error }
  function canLookup(path) {
    const m = CAN_PATH.exec(path);
    if (!m) return { error: 'not a CAN signal path (/can/<bus>/<Message or 0xADDR>/<Signal or byteN>)' };
    const [, svc, busStr, msgKey, sigKey] = m;
    const bus = Number(busStr);
    let address, msg = null;
    if (/^0x[0-9a-f]+$/i.test(msgKey)) address = parseInt(msgKey, 16);
    else {
      msg = dbcMessage(msgKey);
      if (!msg) return { error: state.dbcs.length ? `message ${msgKey} is not in a loaded DBC` : 'load a DBC to decode this signal' };
      address = msg.id;
    }
    const g = canGroups(svc).find((x) => x.bus === bus && x.address === address);
    if (!g) return { error: `no ${svc} frames on bus ${bus} with address ${hex(address)}` };
    const bm = /^byte(\d+)$/.exec(sigKey);
    if (!msg) return bm ? { g, byte: Number(bm[1]) } : { error: `use byte<N> for raw address ${msgKey}` };
    const sig = msg.signals.find((s) => s.name === sigKey);
    return sig ? { g, msg, sig } : { error: `signal ${sigKey} is not in DBC message ${msg.name}` };
  }
  function canMissing(path) { const r = canLookup(path); return r.error || 'no frame carries this signal (multiplexing or frame length)'; }
  function canSeries(path) {
    const r = canLookup(path);
    if (r.error) return null;
    const { g, msg, sig } = r;
    if (!msg) return { path, kind: 'uint8', integer: true, t: g.t, v: state.route.canBytes(g, r.byte) };
    const tt = [], vv = [];
    for (let i = 0; i < g.t.length; i++) {
      const val = DBC.signalValue(msg, sig, state.route.canFrame(g, i));
      if (Number.isNaN(val)) continue;
      tt.push(g.t[i]); vv.push(val);
    }
    if (!tt.length) return null;
    const integer = Number.isInteger(sig.factor) && Number.isInteger(sig.offset);
    // value tables are keyed by the raw value; the series holds physical values
    let names = null;
    if (sig.values) { names = {}; for (const k of Object.keys(sig.values)) names[Number(k) * sig.factor + sig.offset] = sig.values[k]; }
    return { path, kind: sig.size === 1 ? 'bool' : 'float64', integer, t: Float64Array.from(tt), v: Float64Array.from(vv), enumNames: names, unit: sig.unit };
  }

  // ---- engagement --------------------------------------------------------------------------------------
  function intervals(s) {
    const out = [];
    if (!s) return out;
    let start = null;
    for (let i = 0; i < s.t.length; i++) {
      const on = s.v[i] > 0.5;
      if (on && start === null) start = s.t[i];
      else if (!on && start !== null) { out.push([start, s.t[i]]); start = null; }
    }
    if (start !== null) out.push([start, s.t[s.t.length - 1]]);
    return out;
  }
  function engaged() {
    if (state.engaged) return state.engaged;
    const lat = getSeries('/carControl/latActive'), lon = getSeries('/carControl/longActive');
    if (!lat && !lon) return { lat: [], long: [] };
    state.engaged = { lat: intervals(lat), long: intervals(lon) };
    return state.engaged;
  }

  // ---- view ------------------------------------------------------------------------------------------
  function routeRange() {
    const r = state.route;
    return r ? [r.tMin, Math.max(r.tMax, r.tMin + 1e-3)] : [0, 1];
  }
  function setView(x0, x1) {
    const [lo, hi] = routeRange();
    const pad = (hi - lo) * 0.02;
    let span = clamp(x1 - x0, 1e-4, hi - lo + 2 * pad);
    x0 = clamp(x0, lo - pad, hi + pad - span);
    state.view.x0 = x0; state.view.x1 = x0 + span;
    requestRender();
  }
  function fitAll() {
    const r = state.route;
    // the bulk of the data: segments repeat a few route-start messages, which would otherwise widen the view
    if (r) setView(r.dataMin, r.dataMax); else setView(0, 1);
  }
  function zoomAround(t, factor) {
    const { x0, x1 } = state.view;
    setView(t - (t - x0) * factor, t + (x1 - t) * factor);
  }

  // ---- plot pane -------------------------------------------------------------------------------------
  const M = { l: 58, r: 10, t: 6, b: 20 };
  class PlotPane {
    constructor(model) {
      this.model = model;
      this.dirty = true;
      this.key = '';
      this.canvas = h('canvas');
      this.base = document.createElement('canvas');
      this.legend = h('div', { class: 'legend' });
      this.legendItems = [];
      this.yAuto = [0, 1];
      const tools = h('div', { class: 'pane-tools' },
        this.ylockBtn = h('button', { class: 'ylock hidden', title: 'Value axis is zoomed; click to auto-fit again (Esc)', onclick: (e) => { e.stopPropagation(); this.model._ylock = null; this.dirty = true; this.syncTools(); requestRender(); } }, 'auto Y'),
        h('button', { title: 'Split down', 'aria-label': 'Split down', onclick: (e) => { e.stopPropagation(); splitPane(model, 'vertical'); } }, svgIcon('down')),
        h('button', { title: 'Split right', 'aria-label': 'Split right', onclick: (e) => { e.stopPropagation(); splitPane(model, 'horizontal'); } }, svgIcon('right')),
        h('button', { title: 'Remove all curves', 'aria-label': 'Clear', onclick: (e) => { e.stopPropagation(); model.curves = []; refreshPanes(true); saveLayoutSoon(); } }, svgIcon('clear')),
        h('button', { title: 'Close pane', 'aria-label': 'Close pane', onclick: (e) => { e.stopPropagation(); closePane(model); } }, svgIcon('close')));
      this.body = h('div', { class: 'pane-body' }, this.canvas);
      this.titleEl = h('div', { class: 'pane-title', title: 'Double-click to rename this plot' });
      this.titleEl.addEventListener('dblclick', () => {
        const t = prompt('Plot title', model.title && model.title !== '...' ? model.title : '');
        if (t === null) return;
        model.title = t.trim() || '...';
        this.syncTitle(); saveLayoutSoon();
      });
      this.syncTitle();
      this.el = h('div', { class: 'pane' }, h('div', { class: 'pane-head' }, h('div', { class: 'pane-labels' }, this.titleEl, this.legend), tools), this.body);
      this.el.addEventListener('pointerdown', () => setActivePane(model), true);
      if (model.kind) this.body.append(h('div', { class: 'pane-note' }, `${model.kind} panes (jotpluggler) are not supported in this viewer`));
      this.bindDrop();
      this.bindPointer();
      this.buildLegend();
      this.syncTools();
    }
    syncTools() { this.ylockBtn.classList.toggle('hidden', !this.model._ylock); }
    syncTitle() {
      const t = this.model.title && this.model.title !== '...' ? this.model.title : '';
      this.titleEl.textContent = t;
      this.titleEl.classList.toggle('hidden', !t);
    }
    buildLegend() {
      this.legend.textContent = '';
      this.legendItems = [];
      if (!this.model.curves.length && !this.model.kind) this.legend.append(h('span', { class: 'hint' }, 'Click or drag series here'));
      this.model.curves.forEach((c, i) => {
        const v = h('span', { class: 'v' });
        const sw = h('span', { class: 'sw' });
        const nm = h('span', { class: 'nm', title: c.name }, c.name);
        const item = h('span', { class: 'item', title: 'Click to hide / show', onclick: () => { c._hidden = !c._hidden; this.dirty = true; this.updateLegend(true); requestRender(); saveLayoutSoon(); } },
          sw, nm, v, h('button', { class: 'rm', title: 'Remove', 'aria-label': 'Remove ' + c.name, onclick: (e) => { e.stopPropagation(); this.model.curves.splice(i, 1); refreshPanes(true); saveLayoutSoon(); treeChanged(); } }, '×'));
        this.legendItems.push({ c, item, v, sw, nm, last: null });
        this.legend.append(item);
      });
      this.updateLegend(true);
    }
    updateLegend(force) {
      for (const L of this.legendItems) {
        const d = curveData(L.c);
        L.sw.style.background = curveColor(L.c);
        L.item.classList.toggle('off', !!L.c._hidden);
        L.item.classList.toggle('err', !!d.error);
        const label = d.label || L.c.name;
        if (L.nm.textContent !== label) L.nm.textContent = label;
        let txt = '';
        if (d.error) txt = d.error;
        else if (d.pending) txt = 'decoding…';
        else if (state.cursor !== null) {
          const i = sampleIndex(d.t, state.cursor);
          txt = i >= 0 ? fmtValue(d.v[i], d.s) : '—';
        }
        if (force || txt !== L.last) { L.v.textContent = txt; L.last = txt; }
      }
    }
    px(t) { return M.l + (t - state.view.x0) / (state.view.x1 - state.view.x0) * (this.w - M.l - M.r); }
    tAt(x) { return state.view.x0 + (x - M.l) / (this.w - M.l - M.r) * (state.view.x1 - state.view.x0); }
    yRange(curves) {
      if (this.model._ylock) return this.model._ylock;
      let lo = Infinity, hi = -Infinity;
      const { x0, x1 } = state.view;
      for (const { d } of curves) {
        const i0 = Math.max(0, lowerBound(d.t, x0) - 1), i1 = Math.min(d.t.length, upperBound(d.t, x1) + 1);
        const v = d.v;
        for (let i = i0; i < i1; i++) { const y = v[i]; if (y < lo) lo = y; if (y > hi) hi = y; }
      }
      const lim = this.model.y_limits || {};
      if (Number.isFinite(lim.min)) lo = lim.min;
      if (Number.isFinite(lim.max)) hi = lim.max;
      if (!Number.isFinite(lo) || !Number.isFinite(hi)) return [0, 1];
      if (hi - lo < Math.max(Math.abs(hi) * 1e-9, 1e-12)) { const p = Math.abs(hi) * 0.1 || 1; lo -= p; hi += p; } else {
        const p = (hi - lo) * 0.06;
        if (!Number.isFinite(lim.min)) lo -= p;
        if (!Number.isFinite(lim.max)) hi += p;
      }
      return minSpan(lo, hi);
    }
    // Draws curves + axes into the offscreen base canvas when something changed; cursor drawn on top each frame.
    draw() {
      const cw = this.body.clientWidth, ch = this.body.clientHeight;
      if (!cw || !ch) return;
      const dpr = window.devicePixelRatio || 1;
      this.w = cw; this.h = ch;
      if (this.canvas.width !== Math.round(cw * dpr) || this.canvas.height !== Math.round(ch * dpr)) {
        this.canvas.width = this.base.width = Math.round(cw * dpr);
        this.canvas.height = this.base.height = Math.round(ch * dpr);
        this.dirty = true;
      }
      const key = `${state.view.x0}|${state.view.x1}|${cw}|${ch}|${dpr}|${themeVersion}|${state.shade}`;
      if (this.dirty || key !== this.key) { this.renderBase(dpr); this.key = key; this.dirty = false; }
      const ctx = this.canvas.getContext('2d');
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
      ctx.drawImage(this.base, 0, 0);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      this.drawOverlay(ctx);
    }
    renderBase(dpr) {
      const ctx = this.base.getContext('2d');
      const W = this.w, H = this.h;
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.clearRect(0, 0, this.base.width, this.base.height);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      const L = M.l, R = W - M.r, T = M.t, B = H - M.b;
      if (R - L < 10 || B - T < 10 || this.model.kind) return;
      const curves = [];
      for (const c of this.model.curves) {
        if (c._hidden) continue;
        const d = curveData(c);
        if (d.t && d.t.length) curves.push({ c, d });
      }
      if (!this.model.curves.length) { this.y0 = undefined; return; }
      const [y0, y1] = this.yRange(curves);
      this.y0 = y0; this.y1 = y1;
      const py = (y) => B - (y - y0) / (y1 - y0) * (B - T);
      const { x0, x1 } = state.view;
      ctx.font = `11px ${colors.sans}`;
      // engaged shading
      if (state.shade) {
        ctx.fillStyle = colors.shade;
        for (const [a, b] of engaged().lat) {
          if (b < x0 || a > x1) continue;
          const xa = Math.max(L, this.px(a)), xb = Math.min(R, this.px(b));
          ctx.fillRect(xa, T, Math.max(1, xb - xa), B - T);
        }
      }
      // grid + ticks
      ctx.lineWidth = 1;
      ctx.strokeStyle = colors.grid;
      ctx.fillStyle = colors.text;
      ctx.textAlign = 'right'; ctx.textBaseline = 'middle';
      const ys = niceStep(y1 - y0, Math.max(2, Math.floor((B - T) / 34)));
      ctx.beginPath();
      for (const y of ticks(y0, y1, ys)) {
        const yy = Math.round(py(y)) + 0.5;
        ctx.moveTo(L, yy); ctx.lineTo(R, yy);
        ctx.fillText(tickLabel(y, ys), L - 6, yy);
      }
      const xs = niceStep(x1 - x0, Math.max(2, Math.floor((R - L) / 90)));
      ctx.textAlign = 'center'; ctx.textBaseline = 'top';
      for (const x of ticks(x0, x1, xs)) {
        const xx = Math.round(this.px(x)) + 0.5;
        ctx.moveTo(xx, T); ctx.lineTo(xx, B);
        ctx.fillText(tickLabel(x, xs), xx, B + 4);
      }
      ctx.stroke();
      ctx.strokeStyle = colors.axis;
      ctx.beginPath(); ctx.moveTo(L + 0.5, T); ctx.lineTo(L + 0.5, B + 0.5); ctx.lineTo(R, B + 0.5); ctx.stroke();
      // curves
      ctx.save();
      ctx.beginPath(); ctx.rect(L, T - 1, R - L, B - T + 2); ctx.clip();
      ctx.lineJoin = 'round';
      for (const { c, d } of curves) this.drawCurve(ctx, d, curveColor(c), py, L, R);
      ctx.restore();
    }
    drawCurve(ctx, d, color, py, L, R) {
      const { x0, x1 } = state.view;
      const t = d.t, v = d.v;
      const i0 = Math.max(0, lowerBound(t, x0) - 1), i1 = Math.min(t.length, upperBound(t, x1) + 1);
      const n = i1 - i0;
      if (n <= 0) return;
      const width = R - L;
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.6;
      ctx.beginPath();
      const k = (width) / (x1 - x0);
      if (n > width * 2) {
        // min/max per pixel column
        let col = null, mn = 0, mx = 0, first = 0, lastY = 0, started = false;
        const flush = () => {
          if (col === null) return;
          if (started) ctx.lineTo(col, py(first)); else ctx.moveTo(col, py(first));
          ctx.lineTo(col, py(mn)); ctx.lineTo(col, py(mx)); ctx.lineTo(col, py(lastY));
          started = true;
        };
        for (let i = i0; i < i1; i++) {
          const y = v[i];
          if (y !== y) { flush(); col = null; started = false; continue; }
          const x = Math.round(L + (t[i] - x0) * k);
          if (x !== col) { flush(); col = x; mn = mx = first = lastY = y; } else { if (y < mn) mn = y; if (y > mx) mx = y; lastY = y; }
        }
        flush();
        ctx.stroke();
        return;
      }
      let started = false, prevY = 0;
      for (let i = i0; i < i1; i++) {
        const y = v[i];
        if (y !== y) { started = false; continue; }
        const x = L + (t[i] - x0) * k, Y = py(y);
        if (!started) { ctx.moveTo(x, Y); started = true; } else if (d.step) { ctx.lineTo(x, prevY); ctx.lineTo(x, Y); } else ctx.lineTo(x, Y);
        prevY = Y;
      }
      ctx.stroke();
      if (n < width / 7) {
        ctx.fillStyle = color;
        for (let i = i0; i < i1; i++) {
          const y = v[i];
          if (y !== y) continue;
          ctx.beginPath(); ctx.arc(L + (t[i] - x0) * k, py(y), 2.2, 0, 2 * Math.PI); ctx.fill();
        }
      }
    }
    drawOverlay(ctx) {
      const L = M.l, R = this.w - M.r, T = M.t, B = this.h - M.b;
      if (this.sel) {
        const a = clamp(Math.min(this.sel.a, this.sel.b), L, R), b = clamp(Math.max(this.sel.a, this.sel.b), L, R);
        ctx.fillStyle = colors.select; ctx.fillRect(a, T, b - a, B - T);
      }
      if (state.cursor === null || this.model.kind) return;
      const x = Math.round(this.px(state.cursor)) + 0.5;
      if (x < L || x > R) return;
      ctx.strokeStyle = colors.cursor; ctx.globalAlpha = 0.55; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(x, T); ctx.lineTo(x, B); ctx.stroke();
      ctx.globalAlpha = 1;
      // markers on each curve at the cursor sample
      if (this.y0 === undefined) return;
      const py = (y) => B - (y - this.y0) / (this.y1 - this.y0) * (B - T);
      for (const c of this.model.curves) {
        if (c._hidden) continue;
        const d = curveData(c);
        if (!d.t) continue;
        const i = sampleIndex(d.t, state.cursor);
        if (i < 0 || d.v[i] !== d.v[i]) continue;
        const Y = py(d.v[i]);
        if (Y < T || Y > B) continue;
        ctx.fillStyle = curveColor(c); ctx.strokeStyle = colors.surface; ctx.lineWidth = 2;
        ctx.beginPath(); ctx.arc(x, Y, 4, 0, 2 * Math.PI); ctx.fill(); ctx.stroke();
      }
    }
    bindPointer() {
      const cv = this.canvas;
      let drag = null;
      cv.addEventListener('pointerdown', (e) => {
        if (e.button !== 0 && e.button !== 1) return;
        cv.setPointerCapture(e.pointerId);
        const x = e.offsetX;
        drag = { x, y: e.offsetY, mode: e.shiftKey ? 'select' : 'pan', x0: state.view.x0, x1: state.view.x1, moved: false, ylock: this.model._ylock };
        if (drag.mode === 'select') this.sel = { a: x, b: x };
      });
      cv.addEventListener('pointermove', (e) => {
        state.cursor = this.tAt(e.offsetX);
        if (drag) {
          const dx = e.offsetX - drag.x;
          if (Math.abs(dx) > 2 || Math.abs(e.offsetY - drag.y) > 2) drag.moved = true;
          if (drag.mode === 'pan' && drag.moved) {
            const dt = dx / (this.w - M.l - M.r) * (drag.x1 - drag.x0);
            setView(drag.x0 - dt, drag.x1 - dt);
            if (drag.ylock) {
              const dy = (e.offsetY - drag.y) / (this.h - M.t - M.b) * (drag.ylock[1] - drag.ylock[0]);
              this.model._ylock = [drag.ylock[0] + dy, drag.ylock[1] + dy];
              this.dirty = true;
            }
          } else if (drag.mode === 'select') this.sel.b = e.offsetX;
        }
        requestRender();
      });
      const end = () => {
        if (drag && drag.mode === 'select' && this.sel) {
          const a = Math.min(this.sel.a, this.sel.b), b = Math.max(this.sel.a, this.sel.b);
          if (b - a > 4) setView(this.tAt(a), this.tAt(b));
        }
        this.sel = null; drag = null;
        requestRender();
      };
      cv.addEventListener('pointerup', end);
      cv.addEventListener('pointercancel', end);
      cv.addEventListener('dblclick', () => { this.model._ylock = null; this.syncTools(); this.dirty = true; fitAll(); });
      cv.addEventListener('wheel', (e) => {
        e.preventDefault();
        const f = Math.exp(clamp(e.deltaY, -300, 300) * 0.0015);
        if (e.ctrlKey || e.metaKey) {
          const [y0, y1] = this.model._ylock || [this.y0, this.y1];
          if (!Number.isFinite(y0)) return;
          const B = this.h - M.b, T = M.t;
          const yv = y0 + (B - e.offsetY) / (B - T) * (y1 - y0);
          this.model._ylock = minSpan(yv - (yv - y0) * f, yv + (y1 - yv) * f);
          this.dirty = true; this.syncTools(); requestRender();
          return;
        }
        zoomAround(this.tAt(e.offsetX), f);
      }, { passive: false });
    }
    bindDrop() {
      this.el.addEventListener('dragover', (e) => {
        if (![...e.dataTransfer.types].includes('text/x-series-path')) return;
        e.preventDefault(); e.dataTransfer.dropEffect = 'copy'; this.el.classList.add('drop');
      });
      this.el.addEventListener('dragleave', () => this.el.classList.remove('drop'));
      this.el.addEventListener('drop', (e) => {
        const path = e.dataTransfer.getData('text/x-series-path');
        this.el.classList.remove('drop');
        if (!path) return;
        e.preventDefault(); e.stopPropagation();
        for (const p of path.split('\n')) addCurve(this.model, p);
      });
    }
  }
  function svgIcon(kind) {
    const paths = {
      down: 'M2.5 2.5h11v11h-11z M2.5 8h11',
      right: 'M2.5 2.5h11v11h-11z M8 2.5v11',
      clear: 'M3 4.5h10 M6 4.5V3h4v1.5 M4.5 4.5l.7 9h5.6l.7-9',
      close: 'M4 4l8 8 M12 4l-8 8',
    };
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('viewBox', '0 0 16 16'); svg.setAttribute('width', '14'); svg.setAttribute('height', '14');
    const p = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    p.setAttribute('d', paths[kind]); p.setAttribute('fill', 'none'); p.setAttribute('stroke', 'currentColor'); p.setAttribute('stroke-width', '1.4');
    svg.append(p);
    return svg;
  }
  function setActivePane(model) {
    if (state.activePane === model) return;
    state.activePane = model;
    for (const p of state.panes) p.el.classList.toggle('active', p.model === model);
  }
  function refreshPanes(structural) {
    for (const p of state.panes) {
      if (structural) p.buildLegend(); else p.updateLegend(true);
      p.dirty = true;
    }
    if (structural) treeChanged();
    requestRender();
  }

  // ---- tabs + workspace --------------------------------------------------------------------------
  function renderTabs() {
    const el = $('#tabs');
    el.textContent = '';
    state.layout.tabs.forEach((tab, i) => {
      const name = h('span', { text: tab.name });
      const item = h('div', { class: 'tab' + (i === state.tabIndex ? ' active' : ''), title: 'Double-click to rename', role: 'tab' }, name);
      item.addEventListener('click', () => { if (state.tabIndex !== i) { state.tabIndex = i; renderTabs(); renderWorkspace(); loadCurvesOfTab(); saveLayoutSoon(); } });
      item.addEventListener('dblclick', () => {
        const nn = prompt('Tab name', tab.name);
        if (nn) { tab.name = nn; renderTabs(); saveLayoutSoon(); }
      });
      if (state.layout.tabs.length > 1) {
        item.append(h('button', { class: 'x', title: 'Close tab', 'aria-label': 'Close tab', onclick: (e) => {
          e.stopPropagation();
          state.layout.tabs.splice(i, 1);
          state.tabIndex = clamp(state.tabIndex >= i ? state.tabIndex - 1 : state.tabIndex, 0, state.layout.tabs.length - 1);
          renderTabs(); renderWorkspace(); loadCurvesOfTab(); saveLayoutSoon();
        } }, '×'));
      }
      el.append(item);
    });
    el.append(h('button', { class: 'tab-add', title: 'New tab', onclick: () => {
      state.layout.tabs.push({ name: `tab${state.layout.tabs.length + 1}`, root: emptyPane() });
      state.tabIndex = state.layout.tabs.length - 1;
      renderTabs(); renderWorkspace(); saveLayoutSoon();
    } }, '+'));
  }
  function renderWorkspace() {
    const ws = $('#workspace');
    ws.textContent = '';
    state.panes = [];
    const tab = currentTab();
    ws.append(buildNode(tab.root));
    if (!state.activePane || !state.panes.some((p) => p.model === state.activePane)) {
      const first = state.panes.find((p) => !p.model.kind);
      state.activePane = first ? first.model : null;
    }
    for (const p of state.panes) p.el.classList.toggle('active', p.model === state.activePane);
    treeChanged();
    requestRender();
  }
  function buildNode(node) {
    if (isPane(node)) {
      const pane = new PlotPane(node);
      state.panes.push(pane);
      return pane.el;
    }
    const el = h('div', { class: `split ${node.split}` });
    node.children.forEach((child, i) => {
      if (i > 0) el.append(splitter(node, i, el));
      const c = buildNode(child);
      c.style.flex = `${node.sizes[i]} 1 0`;
      el.append(c);
    });
    return el;
  }
  function splitter(node, i, container) {
    const s = h('div', { class: 'splitter' });
    s.addEventListener('pointerdown', (e) => {
      e.preventDefault();
      s.setPointerCapture(e.pointerId);
      s.classList.add('drag');
      const vertical = node.split === 'vertical';
      const total = vertical ? container.clientHeight : container.clientWidth;
      const start = vertical ? e.clientY : e.clientX;
      const a0 = node.sizes[i - 1], b0 = node.sizes[i];
      const kids = [...container.children].filter((c) => !c.classList.contains('splitter'));
      const move = (ev) => {
        const d = ((vertical ? ev.clientY : ev.clientX) - start) / Math.max(1, total);
        const a = clamp(a0 + d, 0.05, a0 + b0 - 0.05);
        node.sizes[i - 1] = a; node.sizes[i] = a0 + b0 - a;
        kids[i - 1].style.flex = `${node.sizes[i - 1]} 1 0`;
        kids[i].style.flex = `${node.sizes[i]} 1 0`;
        requestRender();
      };
      const up = () => { s.classList.remove('drag'); s.removeEventListener('pointermove', move); s.removeEventListener('pointerup', up); s.removeEventListener('pointercancel', up); saveLayoutSoon(); };
      s.addEventListener('pointermove', move);
      s.addEventListener('pointerup', up);
      s.addEventListener('pointercancel', up);
    });
    return s;
  }

  // ---- render loop ---------------------------------------------------------------------------------
  let renderQueued = false;
  function requestRender() {
    if (renderQueued) return;
    renderQueued = true;
    requestAnimationFrame(() => { renderQueued = false; renderFrame(); });
  }
  function renderFrame() {
    if (!colors) readColors();
    for (const p of state.panes) { p.draw(); p.updateLegend(false); }
    drawTimeline();
    updateTreeValues();
    updateCursorReadout();
    if (bottom.open === 'logs') logsFollow();
    if (bottom.open === 'inspector') renderInspector();
  }
  new ResizeObserver(() => requestRender()).observe($('#workspace'));

  // ---- timeline --------------------------------------------------------------------------------------
  const tl = { canvas: $('#timeline canvas'), drag: null };
  function drawTimeline() {
    const cv = tl.canvas, wrap = cv.parentElement;
    const W = wrap.clientWidth, H = wrap.clientHeight, dpr = window.devicePixelRatio || 1;
    if (!W || !H) return;
    if (cv.width !== Math.round(W * dpr) || cv.height !== Math.round(H * dpr)) { cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr); }
    const ctx = cv.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, W, H);
    if (!state.route) return;
    const [lo, hi] = routeRange();
    const L = M.l, R = W - M.r;
    const px = (t) => L + (t - lo) / (hi - lo) * (R - L);
    ctx.fillStyle = colors.grid;
    ctx.fillRect(L, 4, R - L, 8); ctx.fillRect(L, 15, R - L, 8);
    const eg = engaged();
    ctx.fillStyle = colors.lat;
    for (const [a, b] of eg.lat) ctx.fillRect(px(a), 4, Math.max(1, px(b) - px(a)), 8);
    ctx.fillStyle = colors.long;
    for (const [a, b] of eg.long) ctx.fillRect(px(a), 15, Math.max(1, px(b) - px(a)), 8);
    // view window
    const a = clamp(px(state.view.x0), L, R), b = clamp(px(state.view.x1), L, R);
    ctx.fillStyle = colors.select; ctx.fillRect(a, 1, Math.max(2, b - a), 25);
    ctx.strokeStyle = colors.axis; ctx.lineWidth = 1; ctx.strokeRect(a + 0.5, 1.5, Math.max(2, b - a) - 1, 24);
    ctx.fillStyle = colors.text; ctx.font = `10px ${colors.sans}`; ctx.textBaseline = 'top';
    ctx.textAlign = 'left'; ctx.fillText(tickLabel(lo, 1) + ' s', L, 25);
    ctx.textAlign = 'right'; ctx.fillText(tickLabel(hi, 0.1) + ' s', R, 25);
    if (state.cursor !== null) {
      const x = Math.round(px(state.cursor)) + 0.5;
      ctx.strokeStyle = colors.cursor; ctx.globalAlpha = 0.7;
      ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, 27); ctx.stroke(); ctx.globalAlpha = 1;
    }
  }
  function timelineT(e) {
    const W = tl.canvas.parentElement.clientWidth, [lo, hi] = routeRange();
    return lo + (e.offsetX - M.l) / (W - M.l - M.r) * (hi - lo);
  }
  tl.canvas.addEventListener('pointerdown', (e) => {
    if (!state.route) return;
    tl.canvas.setPointerCapture(e.pointerId);
    const t = timelineT(e), { x0, x1 } = state.view;
    tl.drag = t >= x0 && t <= x1 ? { off: t - x0 } : { off: (x1 - x0) / 2 };
    setView(t - tl.drag.off, t - tl.drag.off + (x1 - x0));
    state.cursor = clamp(t, ...routeRange());
  });
  tl.canvas.addEventListener('pointermove', (e) => {
    if (!tl.drag) return;
    const t = timelineT(e), span = state.view.x1 - state.view.x0;
    setView(t - tl.drag.off, t - tl.drag.off + span);
    state.cursor = clamp(t, ...routeRange());
  });
  tl.canvas.addEventListener('pointerup', () => { tl.drag = null; });
  tl.canvas.addEventListener('pointercancel', () => { tl.drag = null; });
  tl.canvas.addEventListener('wheel', (e) => { e.preventDefault(); zoomAround(state.cursor ?? (state.view.x0 + state.view.x1) / 2, Math.exp(clamp(e.deltaY, -300, 300) * 0.0015)); }, { passive: false });
  $('#chk-shade').addEventListener('change', (e) => { state.shade = e.target.checked; store.set('shade', state.shade); requestRender(); });
  function updateCursorReadout() {
    const el = $('#cursor-readout');
    const txt = state.route ? `t = ${state.cursor === null ? '—' : state.cursor.toFixed(3) + ' s'} · view ${(state.view.x1 - state.view.x0).toFixed(2)} s` : '';
    if (el.textContent !== txt) el.textContent = txt;
  }

  // ---- tree ------------------------------------------------------------------------------------------
  const ROW_H = 22;
  const tree = { el: $('#tree'), rowsEl: $('#tree .tree-rows'), spacer: $('#tree .tree-spacer'), expanded: new Set(), rows: [], search: '', dirty: true, rendered: [] };
  function treeChanged() { tree.dirty = true; requestRender(); }
  function trieLabel(node) { const p = node.path; return p.slice(p.lastIndexOf('/') + 1); }
  function sortedKids(node) {
    if (node._sorted) return node._sorted;
    const kids = Object.values(node.kids);
    kids.sort((a, b) => {
      const la = trieLabel(a), lb = trieLabel(b);
      const na = /^\d+$/.test(la), nb = /^\d+$/.test(lb);
      if (na && nb) return la - lb;
      if (na !== nb) return na ? 1 : -1;
      return la.localeCompare(lb, undefined, { sensitivity: 'base' });
    });
    node._sorted = kids;
    return kids;
  }
  function plottedPaths() {
    const set = new Set();
    if (state.layout) forEachPane(currentTab().root, (p) => p.curves.forEach((c) => set.add(c.name)));
    return set;
  }
  function svcMeta(svc) {
    const dur = svc.count > 1 ? svc.t[svc.count - 1] - svc.t[0] : 0;
    const hz = dur > 0 ? (svc.count - 1) / dur : 0;
    return `${fmtCount(svc.count)}${hz >= 0.1 ? ' · ' + (hz >= 10 ? hz.toFixed(0) : hz.toFixed(1)) + ' Hz' : ''}`;
  }
  function buildRows() {
    const rows = [];
    const route = state.route;
    if (!route) { tree.rows = rows; return; }
    const q = tree.search.trim().toLowerCase().split(/\s+/).filter(Boolean);
    if (q.length) {
      const match = (s) => { const l = s.toLowerCase(); return q.every((w) => l.includes(w)); };
      let notLoaded = 0;
      for (const name of route.serviceNames()) {
        const svc = route.services.get(name);
        if (name === 'can' || name === 'sendcan') {
          if (!svc.can) { notLoaded++; if (match(name)) rows.push({ kind: 'svc', name, depth: 0, label: name, key: 'svc:' + name, meta: svcMeta(svc) }); continue; }
          for (const r of canRows(name, 1, true)) if (r.leaf && match(r.path)) rows.push({ ...r, depth: 0, label: r.path });
          continue;
        }
        if (!svc.paths) { notLoaded++; if (match(name)) rows.push({ kind: 'svc', name, depth: 0, label: name, key: 'svc:' + name, meta: svcMeta(svc) }); continue; }
        for (const p of svc.paths) if (match(p)) rows.push({ kind: 'leaf', leaf: true, path: p, depth: 0, label: p });
        if (rows.length > 20000) break;
      }
      $('#tree-hint').textContent = notLoaded ? `${notLoaded} services not decoded yet` : '';
      tree.rows = rows;
      return;
    }
    $('#tree-hint').textContent = '';
    for (const name of route.serviceNames()) {
      const svc = route.services.get(name);
      const key = 'svc:' + name;
      const open = tree.expanded.has(key);
      rows.push({ kind: 'svc', name, depth: 0, label: name, key, open, meta: svcMeta(svc), expandable: true });
      if (!open) continue;
      if (name === 'can' || name === 'sendcan') {
        // event-level series (decoded with the service) and the frames by bus and address (indexed)
        if (svc.paths) for (const k of ['logMonoTime', 't', 'valid']) rows.push({ kind: 'leaf', leaf: true, path: `/${name}/${k}`, depth: 1, label: k });
        if (!svc.can) { rows.push({ kind: 'note', depth: 1, label: 'indexing frames…' }); continue; }
        rows.push(...canRows(name, 1, false));
        continue;
      }
      if (!svc.paths) { rows.push({ kind: 'note', depth: 1, label: 'decoding…' }); continue; }
      const walk = (node, depth) => {
        for (const k of sortedKids(node)) {
          if (k.s) { rows.push({ kind: 'leaf', leaf: true, path: k.path, depth, label: trieLabel(k) }); continue; }
          const kk = 'n:' + k.path;
          const o = tree.expanded.has(kk);
          rows.push({ kind: 'node', depth, label: trieLabel(k), key: kk, open: o, expandable: true });
          if (o) walk(k, depth + 1);
        }
      };
      walk(svc.trie, 1);
    }
    tree.rows = rows;
  }
  function canRows(svcName, depth, flat) {
    const rows = [];
    const groups = canGroups(svcName);
    const buses = [...new Set(groups.map((g) => g.bus))];
    for (const bus of buses) {
      const bkey = `can:${svcName}:${bus}`;
      const bOpen = flat || tree.expanded.has(bkey);
      const inBus = groups.filter((g) => g.bus === bus);
      if (!flat) rows.push({ kind: 'node', depth, label: `bus ${bus}`, key: bkey, open: bOpen, expandable: true, meta: `${inBus.length} ids` });
      if (!bOpen) continue;
      for (const g of inBus) {
        const msg = dbcMessage(g.address);
        const akey = `can:${svcName}:${bus}:${g.address}`;
        const aOpen = flat || tree.expanded.has(akey);
        const dur = g.t.length > 1 ? g.t[g.t.length - 1] - g.t[0] : 0;
        if (!flat) rows.push({ kind: 'node', depth: depth + 1, label: `${hex(g.address)}${msg ? ' ' + msg.name : ''}`, key: akey, open: aOpen, expandable: true, meta: `${fmtCount(g.t.length)}${dur ? ' · ' + ((g.t.length - 1) / dur).toFixed(0) + ' Hz' : ''}` });
        if (!aOpen) continue;
        if (msg) for (const sig of msg.signals) rows.push({ kind: 'leaf', leaf: true, depth: depth + 2, label: sig.name + (sig.unit ? ` [${sig.unit}]` : ''), path: `/${svcName}/${bus}/${msg.name}/${sig.name}` });
        for (let k = 0; k < g.maxLen; k++) rows.push({ kind: 'leaf', leaf: true, depth: depth + 2, label: `byte${k}`, path: `/${svcName}/${bus}/${hex(g.address)}/byte${k}`, dim: !!msg });
      }
    }
    return rows;
  }
  function renderTree() {
    if (tree.dirty) { buildRows(); tree.dirty = false; tree.plotted = plottedPaths(); tree.renderedKey = ''; }
    const el = tree.el, rows = tree.rows;
    tree.spacer.style.height = rows.length * ROW_H + 'px';
    const first = Math.max(0, Math.floor(el.scrollTop / ROW_H) - 5);
    const last = Math.min(rows.length, Math.ceil((el.scrollTop + el.clientHeight) / ROW_H) + 5);
    const key = `${first}|${last}|${rows.length}`;
    if (key === tree.renderedKey) return;
    tree.renderedKey = key;
    tree.rowsEl.style.top = first * ROW_H + 'px';
    tree.rowsEl.textContent = '';
    tree.rendered = [];
    for (let i = first; i < last; i++) {
      const r = rows[i];
      const caret = h('span', { class: 'caret' }, r.expandable ? (r.open ? '▾' : '▸') : '');
      const cls = ['row', r.kind === 'svc' ? 'svc' : '', r.leaf ? 'leaf' : '', r.dim ? 'dim' : '', r.leaf && tree.plotted.has(r.path) ? 'plotted' : ''].join(' ');
      const el2 = h('div', { class: cls, style: `padding-left:${4 + r.depth * 14}px`, title: r.path || r.label, 'data-i': i }, caret, h('span', { class: 'label' }, r.label));
      if (r.meta) el2.append(h('span', { class: 'meta' }, r.meta));
      if (r.kind === 'svc' && r.name !== 'can' && r.name !== 'sendcan') el2.append(h('button', { class: 'inspect', title: `Inspect ${r.name} messages at the cursor`, 'data-inspect': r.name }, '{ }'));
      let val = null;
      if (r.leaf) { val = h('span', { class: 'val' }); el2.append(val); el2.draggable = true; }
      tree.rowsEl.append(el2);
      tree.rendered.push({ r, val, last: null });
    }
    updateTreeValues(true);
  }
  function updateTreeValues(force) {
    renderTreeIfNeeded();
    if (!state.route) return;
    for (const item of tree.rendered) {
      if (!item.val) continue;
      let txt = '';
      if (state.cursor !== null) {
        const s = getSeries(item.r.path);
        if (s) { const i = sampleIndex(s.t, state.cursor); txt = i >= 0 ? fmtValue(s.v[i], s) : ''; }
      }
      if (force || txt !== item.last) { item.val.textContent = txt; item.last = txt; }
    }
  }
  let inTreeRender = false;
  function renderTreeIfNeeded() {
    if (inTreeRender) return;
    inTreeRender = true;
    try { renderTree(); } finally { inTreeRender = false; }
  }
  tree.el.addEventListener('scroll', () => renderTreeIfNeeded());
  new ResizeObserver(() => { tree.renderedKey = ''; renderTreeIfNeeded(); }).observe(tree.el);
  tree.el.addEventListener('click', (e) => {
    const insp = e.target.closest('[data-inspect]');
    if (insp) { e.stopPropagation(); openInspector(insp.getAttribute('data-inspect')); return; }
    const rowEl = e.target.closest('.row');
    if (!rowEl) return;
    const r = tree.rows[+rowEl.getAttribute('data-i')];
    if (!r) return;
    if (r.leaf) {
      let pane = state.activePane;
      if (!pane || pane.kind) { const p = state.panes.find((x) => !x.model.kind); pane = p && p.model; }
      if (e.shiftKey && pane) { splitPane(pane, 'vertical'); pane = state.activePane; }
      if (pane) addCurve(pane, r.path);
      return;
    }
    if (r.kind === 'svc' && !r.expandable) {
      tree.search = ''; $('#search').value = ''; tree.expanded.add(r.key);
      ensureService(r.name).then(() => { if (r.name === 'can' || r.name === 'sendcan') ensureCan(r.name); });
      treeChanged(); return;
    }
    if (r.key) {
      if (tree.expanded.has(r.key)) tree.expanded.delete(r.key); else {
        tree.expanded.add(r.key);
        if (r.kind === 'svc') {
          if (r.name === 'can' || r.name === 'sendcan') { ensureService(r.name).then(() => ensureCan(r.name)); } else { inspectDefault = r.name; ensureService(r.name); }
        }
      }
      treeChanged();
    }
  });
  tree.el.addEventListener('dragstart', (e) => {
    const rowEl = e.target.closest('.row');
    const r = rowEl && tree.rows[+rowEl.getAttribute('data-i')];
    if (!r || !r.leaf) { e.preventDefault(); return; }
    e.dataTransfer.setData('text/x-series-path', r.path);
    e.dataTransfer.setData('text/plain', r.path);
    e.dataTransfer.effectAllowed = 'copy';
  });
  $('#search').addEventListener('input', (e) => { tree.search = e.target.value; tree.el.scrollTop = 0; treeChanged(); });
  $('#btn-loadall').addEventListener('click', async () => {
    if (!state.route) return;
    const route = state.route;
    const names = route.serviceNames();
    const cans = names.filter((n) => n === 'can' || n === 'sendcan');
    const steps = names.length + cans.length;
    try {
      for (let i = 0; i < names.length && route === state.route; i++) {
        showProgress(`Decoding ${names[i]} (${i + 1}/${steps})`, i / steps);
        try { await ensureService(names[i]); } catch (e) { toast(`${names[i]}: ${e.message}`, true); }
      }
      for (let i = 0; i < cans.length && route === state.route; i++) {
        showProgress(`Indexing ${cans[i]} frames (${names.length + i + 1}/${steps})`, (names.length + i) / steps);
        try { await ensureCan(cans[i]); } catch (e) { toast(`${cans[i]}: ${e.message}`, true); }
      }
    } finally { hideProgress(); }
    treeChanged();
  });

  // ---- bottom panel: logs + inspector -------------------------------------------------------------
  const bottom = { open: null, last: 'logs' };
  function showPanel(name) {
    const b = $('#bottom');
    if (name === null) { b.classList.add('collapsed'); bottom.open = null; $('#btn-bottom-toggle').textContent = 'Show'; } else {
      b.classList.remove('collapsed'); bottom.open = name; bottom.last = name; $('#btn-bottom-toggle').textContent = 'Hide';
      b.style.height = store.get('bottomHeight', 240) + 'px';
    }
    if (bottom.open === null) b.style.height = '';
    for (const btn of document.querySelectorAll('.tab-btn')) btn.classList.toggle('active', btn.dataset.panel === bottom.last);
    for (const p of document.querySelectorAll('.panel-controls')) p.classList.toggle('show', p.dataset.for === name);
    $('#panel-logs').classList.toggle('show', name === 'logs');
    $('#panel-inspector').classList.toggle('show', name === 'inspector');
    if (name === 'logs') { buildLogs(); logs.renderedKey = ''; }
    if (name === 'inspector') { insp.key = ''; fillInspectSelect(); }
    requestRender();
  }
  for (const btn of document.querySelectorAll('.tab-btn')) btn.addEventListener('click', () => showPanel(bottom.open === btn.dataset.panel ? null : btn.dataset.panel));
  $('#btn-bottom-toggle').addEventListener('click', () => showPanel(bottom.open ? null : bottom.last));
  (function bottomResize() {
    const r = $('#bottom-resizer');
    r.addEventListener('pointerdown', (e) => {
      e.preventDefault(); r.setPointerCapture(e.pointerId); r.classList.add('drag');
      const b = $('#bottom'), y0 = e.clientY, h0 = b.clientHeight;
      const move = (ev) => { const hh = clamp(h0 - (ev.clientY - y0), 80, window.innerHeight * 0.75); b.style.height = hh + 'px'; requestRender(); };
      const up = () => { r.classList.remove('drag'); store.set('bottomHeight', b.clientHeight); r.removeEventListener('pointermove', move); r.removeEventListener('pointerup', up); r.removeEventListener('pointercancel', up); };
      r.addEventListener('pointermove', move); r.addEventListener('pointerup', up); r.addEventListener('pointercancel', up);
    });
  })();

  const LOG_H = 20;
  const LEVELS = { 10: 'DEBUG', 20: 'INFO', 30: 'WARNING', 40: 'ERROR', 50: 'CRITICAL' };
  const ANSI = /\u001b\[[0-9;]*[A-Za-z]/g;
  const logs = { all: null, rows: [], filter: '', listEl: $('#log-list'), rowsEl: $('#log-list .log-rows'), spacer: $('#log-list .log-spacer'), renderedKey: '', atIndex: -1 };
  function buildLogs() {
    if (logs.all || !state.route) return;
    const all = [];
    for (const name of ['logMessage', 'errorLogMessage']) {
      for (const { t, text } of state.route.texts(name)) {
        let level = name === 'errorLogMessage' ? 'ERROR' : '', src = '', msg = text;
        try {
          const j = JSON.parse(text);
          level = j.levelname || LEVELS[j.levelnum] || level;
          src = j.filename ? `${String(j.filename).split('/').pop()}:${j.lineno ?? ''}` : (j.ctx && j.ctx.daemon) || '';
          msg = j.msg === undefined ? text : typeof j.msg === 'string' ? j.msg : String(JSON.stringify(j.msg));
          if (j.ctx && j.ctx.daemon) src = `${j.ctx.daemon} ${src}`.trim();
        } catch (e) { /* not JSON: keep raw text */ }
        all.push({ t, svc: name, level: String(level), src: String(src), msg: String(msg).replace(ANSI, ''), raw: text });
      }
    }
    all.sort((a, b) => a.t - b.t);
    // as jotpluggler: an entry identical to the previous one (same time and text) is a repeat
    logs.all = all.filter((r, i) => i === 0 || r.t !== all[i - 1].t || r.raw !== all[i - 1].raw || r.svc !== all[i - 1].svc);
    filterLogs();
  }
  function filterLogs() {
    const q = logs.filter.trim().toLowerCase().split(/\s+/).filter(Boolean);
    logs.rows = q.length ? logs.all.filter((r) => { const s = (r.level + ' ' + r.src + ' ' + r.msg).toLowerCase(); return q.every((w) => s.includes(w)); }) : logs.all;
    logs.renderedKey = '';
    logs.t = Float64Array.from(logs.rows, (r) => r.t);
    renderLogs();
  }
  function renderLogs() {
    const el = logs.listEl, rows = logs.rows || [];
    logs.spacer.style.height = rows.length * LOG_H + 'px';
    const first = Math.max(0, Math.floor(el.scrollTop / LOG_H) - 5);
    const last = Math.min(rows.length, Math.ceil((el.scrollTop + el.clientHeight) / LOG_H) + 5);
    const key = `${first}|${last}|${rows.length}|${logs.atIndex}`;
    if (key === logs.renderedKey) return;
    logs.renderedKey = key;
    logs.rowsEl.style.top = first * LOG_H + 'px';
    logs.rowsEl.textContent = '';
    if (!rows.length) { logs.rowsEl.append(h('div', { class: 'log-row muted' }, state.route ? 'No logMessage / errorLogMessage entries' : '')); return; }
    for (let i = first; i < last; i++) {
      const r = rows[i];
      logs.rowsEl.append(h('div', { class: 'log-row' + (i === logs.atIndex ? ' at' : ''), 'data-i': i, title: r.raw },
        h('span', { class: 't' }, r.t.toFixed(3)), h('span', { class: 'lv ' + r.level }, r.level), h('span', { class: 'src' }, r.src), h('span', { class: 'msg' }, r.msg)));
    }
  }
  function logsFollow() {
    if (!logs.rows || !logs.t) return;
    const at = state.cursor === null ? -1 : upperBound(logs.t, state.cursor) - 1;
    if (at !== logs.atIndex) {
      logs.atIndex = at;
      if ($('#log-follow').checked && at >= 0) {
        const el = logs.listEl, y = at * LOG_H;
        if (y < el.scrollTop || y > el.scrollTop + el.clientHeight - LOG_H) el.scrollTop = y - el.clientHeight / 2;
      }
    }
    renderLogs();
  }
  logs.listEl.addEventListener('scroll', renderLogs);
  logs.listEl.addEventListener('click', (e) => {
    const row = e.target.closest('.log-row');
    const r = row && logs.rows[+row.getAttribute('data-i')];
    if (!r) return;
    state.cursor = r.t;
    const { x0, x1 } = state.view;
    if (r.t < x0 || r.t > x1) { const span = x1 - x0; setView(r.t - span / 2, r.t + span / 2); }
    requestRender();
  });
  $('#log-filter').addEventListener('input', (e) => { logs.filter = e.target.value; filterLogs(); });

  const insp = { key: '', open: new Map(), service: '' };
  let inspectDefault = 'carState';
  function fillInspectSelect() {
    const sel = $('#inspect-service');
    const names = state.route ? state.route.serviceNames().filter((n) => n !== 'can' && n !== 'sendcan') : [];
    const cur = sel.value || inspectDefault;
    sel.textContent = '';
    for (const n of names) sel.append(h('option', { value: n }, n));
    sel.value = names.includes(cur) ? cur : (names.includes(inspectDefault) ? inspectDefault : names[0] || '');
  }
  $('#inspect-service').addEventListener('change', () => { insp.key = ''; requestRender(); });
  function openInspector(name) { inspectDefault = name; showPanel('inspector'); $('#inspect-service').value = name; insp.key = ''; requestRender(); }
  function renderInspector() {
    const el = $('#inspector');
    const name = $('#inspect-service').value;
    const route = state.route;
    if (!route || !name || !route.services.has(name)) { el.textContent = route ? 'Choose a service.' : ''; return; }
    const t = state.cursor === null ? route.tMin : state.cursor;
    const j = route.messageAt(name, t);
    const key = `${name}|${j}|${themeVersion}`;
    if (key === insp.key) return;
    insp.key = key;
    const svc = route.services.get(name);
    $('#inspect-meta').textContent = j >= 0 ? `message ${j + 1} of ${svc.count} · t = ${svc.t[j].toFixed(3)} s` : '';
    if (insp.service !== name) { insp.service = name; insp.open = new Map(); }
    const scroll = el.scrollTop;
    el.textContent = '';
    if (j < 0) return;
    let obj;
    try { obj = route.messageObject(name, j, { maxList: 64 }); } catch (e) { el.textContent = 'Cannot decode: ' + e.message; return; }
    el.append(objNode(obj, 0, undefined, ''));
    el.scrollTop = scroll;
  }
  function objNode(v, depth, key, path) {
    const k = key !== undefined ? h('span', { class: 'k' }, key + ': ') : null;
    if (v !== null && typeof v === 'object') {
      const entries = Array.isArray(v) ? v.map((x, i) => [i, x]) : Object.entries(v);
      const remembered = insp.open.get(path);
      const d = h('details', (remembered !== undefined ? remembered : depth < 2) ? { open: true } : null, h('summary', null, k, Array.isArray(v) ? `[${v.length}]` : `{${entries.length}}`));
      d.addEventListener('toggle', () => insp.open.set(path, d.open));
      for (const [kk, vv] of entries) d.append(objNode(vv, depth + 1, kk, path + '/' + kk));
      return depth === 0 ? h('div', null, ...[...d.childNodes].slice(1)) : d;
    }
    const cls = typeof v === 'number' ? 'n' : typeof v === 'boolean' ? 'b' : typeof v === 'string' ? 's' : '';
    const txt = typeof v === 'string' ? JSON.stringify(v) : String(v);
    return h('div', { class: 'kv' }, k, h('span', { class: cls }, txt));
  }

  // ---- loading ------------------------------------------------------------------------------------
  function showProgress(text, frac) {
    $('#progress').classList.remove('hidden');
    $('#progress-text').textContent = text;
    $('#progress-bar').style.width = `${Math.round(clamp(frac, 0, 1) * 100)}%`;
  }
  function hideProgress() { $('#progress').classList.add('hidden'); }
  function setStatus(extra) {
    const r = state.route;
    let txt = '';
    if (r) {
      const events = r.files.reduce((a, f) => a + f.n, 0);
      txt = `${r.files.length} file${r.files.length === 1 ? '' : 's'} · ${(r.tMax - r.tMin).toFixed(1)} s · ${fmtCount(events)} events`;
    }
    if (extra) txt = (txt ? txt + ' · ' : '') + extra;
    $('#status').textContent = txt;
  }
  async function openFiles(fileList, append) {
    const all = [...fileList];
    const dbcs = all.filter((f) => /\.dbc$/i.test(f.name));
    const jsons = all.filter((f) => /\.json$/i.test(f.name));
    const logsIn = all.filter((f) => !dbcs.includes(f) && !jsons.includes(f));
    if (dbcs.length) await loadDbcs(dbcs);
    if (jsons.length) await importLayoutFile(jsons[0]);
    if (!logsIn.length) return;
    logsIn.sort((a, b) => (a.webkitRelativePath || a.name).localeCompare(b.webkitRelativePath || b.name, undefined, { numeric: true }));
    const files = append && state.route ? [...state.route.files] : [];
    const errors = [];
    try {
      for (let i = 0; i < logsIn.length; i++) {
        const f = logsIn[i];
        const label = f.webkitRelativePath || f.name;
        showProgress(`Reading ${label} (${i + 1}/${logsIn.length})`, i / logsIn.length);
        await nextFrame();
        try {
          const raw = new Uint8Array(await f.arrayBuffer());
          showProgress(`Decompressing ${label} (${i + 1}/${logsIn.length})`, (i + 0.3) / logsIn.length);
          await nextFrame();
          const { data, warning } = LR.decompress(raw);
          showProgress(`Indexing ${label} (${i + 1}/${logsIn.length})`, (i + 0.8) / logsIn.length);
          await nextFrame();
          const lf = new LR.LogFile(label, data, SCHEMA);
          if (warning) lf.warnings.unshift(warning);
          lf.size = f.size;
          if (!lf.n) throw new Error('no messages found (is this an rlog?)');
          files.push(lf);
        } catch (e) { errors.push(`${label}: ${e.message}`); }
      }
    } finally { hideProgress(); }
    if (errors.length) toast(errors.join(' · '), true);
    if (!files.length) return;
    const route = new LR.Route(SCHEMA);
    for (const f of files) route.addFile(f);
    route.build();
    state.route = route;
    state.extracting = new Map();
    state.canBuilding = new Map();
    state.curveCache = new WeakMap();
    state.engaged = null;
    state.cursor = null;
    logs.all = null; logs.rows = []; logs.t = null;
    insp.key = '';
    $('#empty').classList.add('hidden');
    for (const p of state.panes) p.dirty = true;
    fitAll();
    setStatus();
    const warns = [];
    for (let i = 1; i < route.files.length; i++) if (route.files[i].monoLo < route.files[i - 1].monoHi - 1e9) warns.push(`${route.files[i - 1].name} and ${route.files[i].name} overlap in time (different routes or boots?)`);
    for (const f of route.files) for (const w of f.warnings) warns.push(`${f.name}: ${w}`);
    if (warns.length) toast(warns.slice(0, 3).join(' · ') + (warns.length > 3 ? ` (+${warns.length - 3} more, see Info)` : ''), true);
    treeChanged();
    if (bottom.open === 'logs') buildLogs();
    if (bottom.open === 'inspector') fillInspectSelect();
    await ensureService('carControl');
    state.engaged = null;
    await loadCurvesOfTab();
    refreshPanes(true);
  }
  async function loadDbcs(files) {
    for (const f of files) {
      try {
        const d = DBC.parse(await f.text(), f.name);
        if (!d.byId.size) throw new Error('no messages found');
        state.dbcs = state.dbcs.filter((x) => x.name !== d.name);
        state.dbcs.unshift(d);
        if (d.warnings.length) toast(`Loaded ${f.name}: ${d.byId.size} messages. ${d.warnings.length} note(s): ${d.warnings.slice(0, 3).join('; ')}${d.warnings.length > 3 ? '; …' : ''}`, true);
        else toast(`Loaded ${f.name}: ${d.byId.size} messages`);
      } catch (e) { toast(`${f.name}: ${e.message}`, true); }
    }
    if (state.route) for (const [p] of state.route.series) if (/^\/(can|sendcan)\//.test(p)) state.route.series.delete(p);
    state.curveCache = new WeakMap();
    treeChanged();
    refreshPanes(true);
  }
  async function importLayoutFile(f) {
    try {
      setLayout(normalizeLayout(JSON.parse(await f.text())), !!state.route);
      $('#layout-select').value = '';
      state.layoutName = f.name.replace(/\.json$/i, '');
      toast(`Imported layout ${f.name}`);
    } catch (e) { toast(`${f.name}: ${e.message}`, true); }
  }

  // ---- top bar --------------------------------------------------------------------------------------
  const pick = (id) => { const el = $(id); el.value = ''; el.click(); };
  $('#btn-open').addEventListener('click', () => pick('#file-input'));
  $('#btn-add').addEventListener('click', () => pick('#add-input'));
  $('#btn-folder').addEventListener('click', () => pick('#folder-input'));
  $('#btn-dbc').addEventListener('click', () => pick('#dbc-input'));
  $('#btn-import').addEventListener('click', () => pick('#layout-input'));
  $('#file-input').addEventListener('change', (e) => openFiles(e.target.files, false));
  $('#add-input').addEventListener('change', (e) => openFiles(e.target.files, true));
  $('#folder-input').addEventListener('change', (e) => {
    const picked = [...e.target.files].filter((f) => /^rlog(\.zst|\.bz2)?$/i.test(f.name));
    if (!picked.length) { toast('No files named rlog, rlog.zst or rlog.bz2 in that folder', true); return; }
    openFiles(picked, false);
  });
  $('#dbc-input').addEventListener('change', (e) => loadDbcs([...e.target.files]));
  $('#layout-input').addEventListener('change', (e) => { if (e.target.files[0]) importLayoutFile(e.target.files[0]); });
  $('#btn-export').addEventListener('click', () => {
    const name = state.layoutName || 'layout';
    download(`${name}.json`, JSON.stringify(exportLayout(), null, 1), 'application/json');
  });
  $('#btn-csv').addEventListener('click', () => {
    if (!state.route) return;
    const { x0, x1 } = state.view;
    const lines = ['series,t,value'], omitted = [];
    forEachPane(currentTab().root, (p) => p.curves.forEach((c) => {
      if (c._hidden) return;
      const d = curveData(c);
      if (!d.t) { omitted.push(`${c.name} (${d.error || 'still decoding'})`); return; }
      let label = d.label || c.name;
      if (/^[=+\-@\t\r]/.test(label)) label = "'" + label; // keep spreadsheets from treating it as a formula
      const name = '"' + label.replace(/"/g, '""') + '"';
      for (let i = lowerBound(d.t, x0); i < d.t.length && d.t[i] <= x1; i++) lines.push(`${name},${d.t[i]},${d.v[i]}`);
    }));
    download(`${currentTab().name}_${x0.toFixed(1)}-${x1.toFixed(1)}s.csv`, lines.join('\n'), 'text/csv');
    if (omitted.length) toast(`CSV without ${omitted.length} curve(s) that have no data: ${omitted.join(', ')}`, true);
  });
  (function fillLayoutSelect() {
    const sel = $('#layout-select');
    sel.append(h('option', { value: '' }, '(current)'), h('option', { value: '__default' }, 'Starter'), h('option', { value: '__blank' }, 'Blank'));
    const og = h('optgroup', { label: 'jotpluggler layouts' });
    for (const name of Object.keys(BUILTIN_LAYOUTS).sort()) og.append(h('option', { value: name }, name.replace(/\.json$/, '')));
    sel.append(og);
    sel.addEventListener('change', () => {
      const v = sel.value;
      if (!v) return;
      try {
        if (v === '__default') setLayout(normalizeLayout(defaultLayout()), true);
        else if (v === '__blank') setLayout({ current_tab_index: 0, tabs: [{ name: 'tab1', root: emptyPane() }] }, true);
        else setLayout(normalizeLayout(BUILTIN_LAYOUTS[v]), true);
        state.layoutName = v.startsWith('__') ? 'layout' : v.replace(/\.json$/, '');
        toast(`Layout: ${sel.options[sel.selectedIndex].text}`);
      } catch (e) { toast(e.message, true); }
      sel.value = ''; // so choosing the same layout again reloads it
    });
  })();
  $('#btn-theme').addEventListener('click', () => {
    const order = ['auto', 'light', 'dark'];
    const next = order[(order.indexOf(store.get('theme', 'auto')) + 1) % 3];
    applyTheme(next);
    toast(`Theme: ${next}`);
  });
  $('#btn-help').addEventListener('click', () => $('#dlg-help').showModal());
  $('#btn-info').addEventListener('click', showInfo);

  function showInfo() {
    const body = $('#info-body');
    body.textContent = '';
    const rows = [];
    const add = (k, v, cls) => rows.push(h('tr', null, h('td', null, k), h('td', cls ? { class: cls } : null, v)));
    const r = state.route;
    if (r) {
      const get = (svc) => { try { return r.services.has(svc) ? r.messageObject(svc, 0, { maxList: 8 })[svc] : null; } catch (e) { return null; } };
      const init = get('initData');
      if (init) {
        add('version', init.version);
        add('git', `${init.gitBranch || ''} @ ${init.gitCommit || ''}${init.dirty ? ' (dirty)' : ''}`);
        if (init.gitRemote) add('remote', init.gitRemote);
        if (init.deviceType !== undefined) add('device type', String(init.deviceType));
        if (init.dongleId) add('dongle id', init.dongleId);
        if (init.wallTimeNanos) add('wall time at start', new Date(init.wallTimeNanos / 1e6).toISOString() + ' (device clock)');
      } else add('initData', 'not in these files (segment 0 holds it)');
      const cp = get('carParams');
      if (cp) add('car', `${cp.carFingerprint || ''}${cp.brand ? ' (' + cp.brand + ')' : ''}`);
      add('duration', `${(r.tMax - r.tMin).toFixed(3)} s`);
      add('services', String(r.services.size));
      for (const f of r.files) add('file', `${f.name} · t ${((f.monoLo - r.t0) / 1e9).toFixed(1)}–${((f.monoHi - r.t0) / 1e9).toFixed(1)} s · ${fmtCount(f.n)} events · ${(f.u8.length / 1e6).toFixed(1)} MB decoded`);
      for (const f of r.files) for (const w of f.warnings) add('warning', `${f.name}: ${w}`, 'warn');
      for (const svc of r.services.values()) {
        if (svc.errors) add('decode errors', `${svc.name}: ${svc.errors} message(s) skipped; first: ${svc.firstError}`, 'warn');
        if (svc.canErrors) add('decode errors', `${svc.name} frames: ${svc.canErrors} message(s) skipped; first: ${svc.canFirstError}`, 'warn');
      }
      for (const d of state.dbcs) {
        add('DBC', `${d.name} (${d.byId.size} messages)`);
        for (const w of d.warnings) add('DBC note', w, 'warn');
      }
    }
    add('schema', `${SCHEMA.source} @ ${SCHEMA.revision}`);
    add('layouts', BUILD.layouts || '');
    body.append(h('table', null, ...rows));
    $('#dlg-info').showModal();
  }

  // ---- drag and drop files ---------------------------------------------------------------------------
  let dragDepth = 0;
  const hasFiles = (e) => [...(e.dataTransfer?.types || [])].includes('Files');
  window.addEventListener('dragenter', (e) => { if (hasFiles(e)) { dragDepth++; $('#dropzone').classList.remove('hidden'); } });
  window.addEventListener('dragleave', (e) => { if (hasFiles(e) && --dragDepth <= 0) { dragDepth = 0; $('#dropzone').classList.add('hidden'); } });
  window.addEventListener('dragover', (e) => { if (hasFiles(e)) e.preventDefault(); });
  window.addEventListener('drop', (e) => {
    if (!hasFiles(e)) return;
    e.preventDefault();
    dragDepth = 0; $('#dropzone').classList.add('hidden');
    openFiles(e.dataTransfer.files, e.shiftKey);
  });

  // ---- keyboard --------------------------------------------------------------------------------------
  window.addEventListener('keydown', (e) => {
    if (e.target.closest && e.target.closest('input, select, textarea, dialog')) return;
    if (!state.route) return;
    const { x0, x1 } = state.view, span = x1 - x0, mid = state.cursor ?? (x0 + x1) / 2;
    if (e.key === 'ArrowLeft') setView(x0 - span * 0.1, x1 - span * 0.1);
    else if (e.key === 'ArrowRight') setView(x0 + span * 0.1, x1 + span * 0.1);
    else if (e.key === '+' || e.key === '=') zoomAround(mid, 0.7);
    else if (e.key === '-' || e.key === '_') zoomAround(mid, 1 / 0.7);
    else if (e.key === 'Home') fitAll();
    else if (e.key === 'Escape' && state.activePane) {
      state.activePane._ylock = null;
      for (const p of state.panes) { p.dirty = true; p.syncTools(); }
      requestRender();
    } else return;
    e.preventDefault();
  });

  // ---- sidebar resize ------------------------------------------------------------------------------
  (function sidebarResize() {
    const r = $('#sidebar-resizer'), sb = $('#sidebar');
    const w = store.get('sidebarWidth', null);
    if (w) sb.style.width = w + 'px';
    r.addEventListener('pointerdown', (e) => {
      e.preventDefault(); r.setPointerCapture(e.pointerId); r.classList.add('drag');
      const x0 = e.clientX, w0 = sb.clientWidth;
      const move = (ev) => { sb.style.width = clamp(w0 + ev.clientX - x0, 200, window.innerWidth * 0.7) + 'px'; requestRender(); };
      const up = () => { r.classList.remove('drag'); store.set('sidebarWidth', sb.clientWidth); r.removeEventListener('pointermove', move); r.removeEventListener('pointerup', up); r.removeEventListener('pointercancel', up); };
      r.addEventListener('pointermove', move); r.addEventListener('pointerup', up); r.addEventListener('pointercancel', up);
    });
  })();

  // ---- start ---------------------------------------------------------------------------------------
  // the empty-state card sits below the top bar, whose height changes when it wraps
  new ResizeObserver(() => document.documentElement.style.setProperty('--topbar-h', $('.topbar').offsetHeight + 'px')).observe($('.topbar'));
  applyTheme(store.get('theme', 'auto'));
  state.shade = store.get('shade', true);
  $('#chk-shade').checked = state.shade;
  $('#build-meta').textContent = `Schema: sunnypilot ${String(SCHEMA.revision).slice(0, 10)}. ${Object.keys(BUILTIN_LAYOUTS).length} jotpluggler layouts built in.`;
  let initial;
  try { initial = normalizeLayout(store.get('layout', null) || defaultLayout()); } catch (e) { initial = normalizeLayout(defaultLayout()); }
  setLayout(initial, true);
  setStatus();

  // test hook (used by the headless smoke test; harmless otherwise)
  window.__logViewer = { state, renderFrame, openFiles, getSeries, curveData, setView, ensureService, ensureCan, loadDbcs, setLayout, normalizeLayout, BUILTIN_LAYOUTS, compileCustom };
})();
