// Decode every DBC signal in can/sendcan with the viewer's dbc.js and compare with ref_can.py.
// usage: node can_digest.js <schema.json> <rlog> <dbc> <ref.json>
'use strict';
const fs = require('fs');
const crypto = require('crypto');
const LR = require('../src/logreader.js');
const DBC = require('../src/dbc.js');
LR.codecs.zstd = LR.fzstdCodec(require('../vendor/fzstd.umd.js'));

const [schemaPath, rlogPath, dbcPath, refPath] = process.argv.slice(2);
const schema = LR.compileSchema(JSON.parse(fs.readFileSync(schemaPath, 'utf8')));
const file = new LR.LogFile('rlog', LR.decompress(new Uint8Array(fs.readFileSync(rlogPath))).data, schema);
const route = new LR.Route(schema);
route.addFile(file);
route.build();
const dbc = DBC.parse(fs.readFileSync(dbcPath, 'utf8'), 'dbc');
const dig = (a) => crypto.createHash('sha1').update(Buffer.from(Float64Array.from(a).buffer)).digest('hex');
const out = {};
for (const svc of ['can', 'sendcan']) {
  if (!route.services.has(svc)) continue;
  for (const g of route.canIndex(svc)) {
    const msg = dbc.byId.get(g.address);
    if (!msg) continue;
    for (const sig of msg.signals) {
      const t = [], v = [];
      for (let i = 0; i < g.t.length; i++) {
        const x = DBC.signalValue(msg, sig, route.canFrame(g, i));
        if (Number.isNaN(x)) continue;
        t.push(g.t[i]); v.push(x);
      }
      if (t.length) out[`/${svc}/${g.bus}/${msg.name}/${sig.name}`] = [t.length, dig(t), dig(v)];
    }
  }
}
const ref = JSON.parse(fs.readFileSync(refPath, 'utf8'));
const a = Object.keys(out), b = Object.keys(ref);
const onlyJs = a.filter((p) => !(p in ref)), onlyRef = b.filter((p) => !(p in out));
const diff = a.filter((p) => p in ref && JSON.stringify(out[p]) !== JSON.stringify(ref[p]));
console.log(`${dbc.byId.size} messages in DBC; series js=${a.length} ref=${b.length}; only js ${onlyJs.length}, only ref ${onlyRef.length}, differing ${diff.length}`);
for (const p of [...onlyJs.slice(0, 5), ...onlyRef.slice(0, 5), ...diff.slice(0, 8)]) console.log('  ', p, out[p], ref[p]);
console.log(onlyJs.length || onlyRef.length || diff.length ? 'MISMATCH' : 'MATCH');
process.exitCode = onlyJs.length || onlyRef.length || diff.length ? 1 : 0;
