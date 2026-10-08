// Damaged-input regression tests for the decoder (crafted from one real segment).
// usage: node robustness.js <schema.json> <rlog.zst>
'use strict';
const fs = require('fs');
const LR = require('../src/logreader.js');
const bunzip2 = require('../src/bunzip2.js');
LR.codecs.zstd = LR.fzstdCodec(require('../vendor/fzstd.umd.js'));
LR.codecs.bz2 = bunzip2;

const [schemaPath, rlogPath] = process.argv.slice(2);
const schema = LR.compileSchema(JSON.parse(fs.readFileSync(schemaPath, 'utf8')));
const raw = new Uint8Array(fs.readFileSync(rlogPath));
const plain = LR.decompress(raw).data;
let failed = 0;
const check = (name, ok, detail) => { if (!ok) failed++; console.log(`${ok ? 'PASS' : 'FAIL'} ${name}${detail !== undefined ? ' :: ' + detail : ''}`); };

function routeOf(bytes) {
  const f = new LR.LogFile('x', bytes, schema);
  const r = new LR.Route(schema);
  r.addFile(f); r.build();
  return { f, r };
}
// message layout helpers (single-segment messages)
function messages(bytes) {
  const dv = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength), out = [];
  for (let p = 0; p + 8 <= bytes.length;) {
    const nseg = dv.getUint32(p, true) + 1, hsize = (4 * (nseg + 1) + 7) & ~7;
    let total = 0;
    for (let s = 0; s < nseg; s++) total += dv.getUint32(p + 4 + 4 * s, true);
    out.push({ p, nseg, seg0: p + hsize, end: p + hsize + total * 8 });
    p += hsize + total * 8;
  }
  return out;
}
const base = routeOf(plain);
const disc = schema.root.byName.carState.disc;

// 1. a message whose root is a far pointer to a missing segment (undecodable)
{
  const msgs = messages(plain);
  const bad = plain.slice();
  const dv = new DataView(bad.buffer);
  const m = msgs.find((x) => x.nseg === 1);
  dv.setUint32(m.seg0, (0 << 3) | 2, true); // far pointer, landing pad at word 0 ...
  dv.setUint32(m.seg0 + 4, 7, true);        // ... of segment 7, which does not exist
  const { f, r } = routeOf(bad);
  check('undecodable message: file still opens', f.n === base.f.n, `${f.n} events, warnings: ${f.warnings.slice(0, 1)}`);
  check('undecodable message: no "(undecodable)" service, finite time range', !r.services.has('(undecodable)') && Number.isFinite(r.tMax) && Number.isFinite(r.dataMax), `tMax ${r.tMax}`);
  let threw = null;
  try { for (const n of r.serviceNames()) r.extract(n); } catch (e) { threw = e.message; }
  check('undecodable message: every service extracts', threw === null, threw || '');
}

// 2. a corrupt pointer inside one carState message
{
  const bad = plain.slice();
  const dv = new DataView(bad.buffer);
  const { f } = base;
  const i = [...f.which].indexOf(disc);
  const m = messages(plain).find((x) => x.p === f.hdr[i]);
  const rootLo = dv.getInt32(m.seg0, true), rootHi = dv.getUint32(m.seg0 + 4, true);
  const data = m.seg0 + 8 + (rootLo >> 2) * 8, ptr0 = data + (rootHi & 0xffff) * 8;
  dv.setInt32(ptr0, 0x0fffffff << 2, true); // payload struct pointer far out of bounds
  const { r } = routeOf(bad);
  let threw = null, paths = [];
  try { paths = r.extract('carState'); } catch (e) { threw = e.message; }
  const svc = r.services.get('carState');
  const v = r.series.get('/carState/vEgo');
  check('corrupt pointer: carState still extracts, error counted', threw === null && svc.errors === 1 && paths.length > 10, `errors ${svc.errors}, ${paths.length} paths, first: ${svc.firstError}`);
  check('corrupt pointer: only that message is missing from vEgo', v && v.t.length === svc.count - 1, `${v && v.t.length} of ${svc.count}`);
}

// 2b. nested damage in carState message 100: the whole message is dropped from every series,
// never decoded from the wrong place. Payload pointer = Event pointer 0 (single segment).
{
  const { f } = base;
  const idx = [...f.which].map((w, i) => (w === disc ? i : -1)).filter((i) => i >= 0);
  const msgs = messages(plain);
  const at = (k) => msgs.find((x) => x.p === f.hdr[idx[k]]);
  const payload = (dv, m) => {
    const rootLo = dv.getInt32(m.seg0, true), rootHi = dv.getUint32(m.seg0 + 4, true);
    const ptr = m.seg0 + 8 + (rootLo >> 2) * 8 + (rootHi & 0xffff) * 8;
    const lo = dv.getInt32(ptr, true), hi = dv.getUint32(ptr + 4, true);
    const d = ptr + 8 + (lo >> 2) * 8;
    return { ptr, lo, hi, d, p: d + (hi & 0xffff) * 8 };
  };
  const clean = base.r;
  clean.extract('carState');
  const cleanCount = (p) => (clean.series.get(p) ? clean.series.get(p).t.length : 0);
  const cases = {
    'double-far to a missing segment (cruiseState)': (dv) => {
      const P = payload(dv, at(100));
      const q = P.p + schema.root.byName.carState.node.byName.cruiseState.off * 8;
      dv.setInt32(q, (0 << 3) | 4 | 2, true); dv.setUint32(q + 4, 7, true);
    },
    'payload pointer into the previous message': (dv) => {
      const prev = payload(dv, at(99)), cur = payload(dv, at(100));
      dv.setInt32(cur.ptr, (((prev.d - (cur.ptr + 8)) / 8) << 2) | 0, true); dv.setUint32(cur.ptr + 4, prev.hi, true);
    },
  };
  for (const [name, damage] of Object.entries(cases)) {
    const bad = plain.slice();
    damage(new DataView(bad.buffer));
    const { r } = routeOf(bad);
    r.extract('carState');
    const svc = r.services.get('carState');
    const diffs = [...r.series.values()].filter((s) => s.path.startsWith('/carState/')).filter((s) => {
      const c = clean.series.get(s.path);
      if (!c) return true;
      // every series loses at most that one message, and keeps every other sample unchanged
      const t100 = clean.services.get('carState').t[100];
      const keep = [...c.t.keys()].filter((i) => c.t[i] !== t100);
      return s.t.length !== keep.length || keep.some((i, k) => s.t[k] !== c.t[i] || !Object.is(s.v[k], c.v[i]));
    });
    const lost = ['/carState/vEgo', '/carState/cruiseState/speed'].map((p) => `${p.split('/').pop()} ${r.series.get(p)?.t.length}/${cleanCount(p)}`);
    check(`${name}: counted, message 100 dropped everywhere, rest identical`, svc.errors === 1 && diffs.length === 0 && r.series.get('/carState/vEgo').t.length === cleanCount('/carState/vEgo') - 1,
      `errors ${svc.errors} (${svc.firstError}); series differing beyond message 100: ${diffs.length}; ${lost.join(', ')}`);
  }
}

// 3. a file cut inside a multi-segment message header
for (const [nseg, extra] of [[3, 8], [2, 8], [2, 11]]) {
  const cut = new Uint8Array(plain.length + extra);
  cut.set(plain);
  new DataView(cut.buffer).setUint32(plain.length, nseg - 1, true);
  let r = null, threw = null;
  try { r = routeOf(cut); } catch (e) { threw = e.message; }
  check(`cut header (nseg ${nseg}, ${extra} bytes): opens with a warning`, !threw && r.f.n === base.f.n && r.f.warnings.length > 0, threw || r.f.warnings[0]);
}

// 4. truncated zstd and bz2 open partially with a warning
{
  const z = LR.decompress(raw.subarray(0, raw.length >> 1));
  check('truncated zstd: partial data + warning', z.data.length > 0 && !!z.warning, `${z.data.length} bytes; ${z.warning}`);
}
const bzPath = process.argv[4];
if (bzPath) {
  const bz = new Uint8Array(fs.readFileSync(bzPath));
  const full = bunzip2(bz);
  const part = LR.decompress(bz.subarray(0, Math.floor(bz.length * 0.6)));
  const prefixOk = part.data.length > 0 && part.data.every((b, i) => b === full[i]);
  check('truncated bz2: partial data is an exact prefix + warning', prefixOk && !!part.warning, `${part.data.length} of ${full.length} bytes; ${part.warning}`);
  const corrupt = bz.slice(); corrupt[5000] ^= 0x10;
  let err = null;
  try { bunzip2(corrupt); } catch (e) { err = e.message; }
  check('corrupt bz2 still raises', !!err, err);
}
// 5. zstd with content checksums (written by python zstandard, write_checksum=True)
const zckPath = process.argv[5];
if (zckPath) {
  const zck = new Uint8Array(fs.readFileSync(zckPath));
  const got = LR.decompress(zck);
  check('checksummed zstd decodes to the same bytes', !got.warning && got.data.length === plain.length && got.data.every((b, i) => b === plain[i]), `${got.data.length} bytes`);
  let detected = 0, trials = 0;
  for (let k = 0; k < 12; k++) {
    const bad = zck.slice();
    bad[Math.floor(bad.length * (0.1 + 0.07 * k))] ^= 1 << (k % 8);
    trials++;
    try { const r = LR.decompress(bad); if (r.warning || r.data.length !== plain.length || r.data.some((b, i) => b !== plain[i])) detected += 0; else detected++; }
    catch (e) { detected++; }
  }
  check('checksummed zstd: every corrupted copy is rejected (or decodes identically)', detected === trials, `${detected}/${trials}`);
}

// 6. DBC parser edge cases
{
  const DBC = require('../src/dbc.js');
  const d = DBC.parse([
    'BO_ 100 A: 8 X',
    ' SG_ SW M : 0|8@1+ (1,0) [0|255] "" X',
    ' SG_ S1 m1 : 8|8@1+ (1,0) [0|255] "" X',
    ' SG_ S2 m2M : 16|8@1+ (1,0) [0|255] "" X',
    '',
    'BO_ 200 B: 8 X',
    ' SG_ LONE m3 : 0|8@1+ (1,0) [0|255] "" X',
    '',
    'BO_ 300 BROKEN',
    ' SG_ ORPHAN : 0|8@1+ (1,0) [0|255] "" X',
    'BO_ 400 C: 8 X',
    ' SG_ BAD : nonsense',
  ].join('\n'), 't.dbc');
  const A = d.byName.get('A'), B = d.byName.get('B');
  const s2 = A.signals.find((s) => s.name === 'S2');
  const f = new Uint8Array([2, 11, 22, 0, 0, 0, 0, 0]);
  check('DBC: m<n>M kept as multiplexed value n (as jotpluggler)', s2 && s2.muxValue === 2 && DBC.signalValue(A, s2, f) === 22 && Number.isNaN(DBC.signalValue(A, A.signals[1], f)), JSON.stringify(s2 && { mux: s2.muxValue }));
  check('DBC: multiplexed signal without a switch decodes', DBC.signalValue(B, B.signals[0], f) === 2);
  check('DBC: unreadable lines reported, no orphan attached to the previous message', !B.signals.some((s) => s.name === 'ORPHAN') && d.warnings.length >= 3, d.warnings.join(' | '));
}

console.log(failed ? `${failed} FAILED` : 'all passed');
process.exitCode = failed ? 1 : 0;
