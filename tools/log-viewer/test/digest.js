// Digest every series the JS decoder extracts from one rlog (same format as ref_flatten.py),
// then compare with a reference digest if one is given.
// usage: node digest.js <schema.json> <rlog> <out.json> [ref.json] [max_scalar_list=64]
'use strict';
const fs = require('fs');
const crypto = require('crypto');
const path = require('path');
const LR = require('../src/logreader.js');
LR.codecs.zstd = LR.fzstdCodec(require('../vendor/fzstd.umd.js'));
LR.codecs.bz2 = require('../src/bunzip2.js');

const [schemaPath, rlogPath, outPath, refPath, maxList] = process.argv.slice(2);
const schema = LR.compileSchema(JSON.parse(fs.readFileSync(schemaPath, 'utf8')));
let t = process.hrtime.bigint();
const lap = (label) => { const n = process.hrtime.bigint(); console.log(`${label}: ${(Number(n - t) / 1e6).toFixed(0)} ms`); t = n; };
const raw = new Uint8Array(fs.readFileSync(rlogPath));
const { kind, data, warning } = LR.decompress(raw);
lap(`decompress (${kind}, ${raw.length} -> ${data.length} bytes)`);
if (warning) console.log('warning:', warning);
const file = new LR.LogFile(path.basename(rlogPath), data, schema);
lap(`index (${file.n} events)`);
if (file.warnings.length) console.log('warnings:', file.warnings);
const route = new LR.Route(schema, { maxScalarList: maxList ? Number(maxList) : 64 });
route.addFile(file);
route.build();
let total = 0;
const timing = [];
for (const name of route.serviceNames()) {
  const t1 = process.hrtime.bigint();
  total += route.extract(name).length;
  timing.push([name, Number(process.hrtime.bigint() - t1) / 1e6]);
}
lap(`extract all services (${total} series)`);
timing.sort((a, b) => b[1] - a[1]);
console.log('slowest:', timing.slice(0, 6).map(([n, ms]) => `${n} ${ms.toFixed(0)}ms`).join(', '));
const dig = (a) => {
  const c = Float64Array.from(a, (x) => (Number.isNaN(x) ? NaN : x));
  return crypto.createHash('sha1').update(Buffer.from(c.buffer)).digest('hex');
};
const series = {};
let points = 0;
for (const [p, s] of route.series) { series[p] = [s.t.length, dig(s.t), dig(s.v)]; points += s.t.length; }
fs.writeFileSync(outPath, JSON.stringify({ events: file.n, series }));
console.log(`${file.n} events, ${Object.keys(series).length} series, ${points} points, heap ${(process.memoryUsage().heapUsed / 1e6).toFixed(0)} MB`);
if (refPath) {
  const ref = JSON.parse(fs.readFileSync(refPath, 'utf8'));
  const a = new Set(Object.keys(series)), b = new Set(Object.keys(ref.series));
  const onlyJs = [...a].filter((p) => !b.has(p)), onlyRef = [...b].filter((p) => !a.has(p));
  const diff = [...a].filter((p) => b.has(p) && JSON.stringify(series[p]) !== JSON.stringify(ref.series[p]));
  console.log(`events js=${file.n} ref=${ref.events}; only in js: ${onlyJs.length}; only in ref: ${onlyRef.length}; differing: ${diff.length}`);
  for (const p of [...onlyJs.slice(0, 5), ...onlyRef.slice(0, 5), ...diff.slice(0, 10)]) console.log('  ', p, series[p], ref.series[p]);
  process.exitCode = onlyJs.length || onlyRef.length || diff.length || file.n !== ref.events ? 1 : 0;
  console.log(process.exitCode ? 'MISMATCH' : 'MATCH');
}
