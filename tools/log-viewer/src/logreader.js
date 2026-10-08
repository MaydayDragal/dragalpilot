/* logreader.js: decode openpilot rlogs (a stream of capnp Event messages) without any DOM use.
 *
 * Decoding is driven by the schema JSON from export_schema.py. Series are flattened the way
 * openpilot's jotpluggler does (tools/jotpluggler/generate_event_extractors.py), so layout paths
 * such as "/carState/vEgo" or "/longitudinalPlan/accels/0" mean the same thing here:
 *   - every event adds /<service>/valid, /<service>/logMonoTime and /<service>/t
 *   - bool, integer, float and enum fields are series (enums keep their names)
 *   - union members only when set, pointer fields only when present
 *   - scalar lists by index when short (see maxScalarList), struct lists by index always
 *   - text, data, void and anyPointer fields are not series
 * Time is logMonoTime / 1e9 minus the earliest logMonoTime of all loaded files.
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.LogReader = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  // ---- schema -------------------------------------------------------------------------------
  const K = { VOID: 0, BOOL: 1, I8: 2, I16: 3, I32: 4, I64: 5, U8: 6, U16: 7, U32: 8, U64: 9,
    F32: 10, F64: 11, TEXT: 12, DATA: 13, ANY: 14, ENUM: 15, STRUCT: 16, LIST: 17 };
  const PRIM = { v: 0, b: 1, i8: 2, i16: 3, i32: 4, i64: 5, u8: 6, u16: 7, u32: 8, u64: 9, f32: 10, f64: 11, t: 12, d: 13, a: 14 };
  const SCALAR = new Set([K.BOOL, K.I8, K.I16, K.I32, K.I64, K.U8, K.U16, K.U32, K.U64, K.F32, K.F64, K.ENUM]);
  const KIND_NAME = ['void', 'bool', 'int8', 'int16', 'int32', 'int64', 'uint8', 'uint16', 'uint32', 'uint64',
    'float32', 'float64', 'text', 'data', 'anyPointer', 'enum', 'struct', 'list'];

  // current message buffer (set by openMessage); single-threaded, so module-level state is safe
  let U8 = null, DV = null, SEGS = [], SEGE = []; // segment start / end byte positions of the open message
  const scratch = new DataView(new ArrayBuffer(8));

  function compileSchema(json) {
    const nodes = {};
    for (const id of Object.keys(json.nodes)) {
      const n = json.nodes[id];
      nodes[id] = n.k === 'e'
        ? { id, kind: 'enum', name: n.n, names: n.v }
        : { id, kind: 'struct', name: n.n, ds: n.dw * 8, pc: n.pc, discOff: n.do >= 0 ? n.do * 2 : -1, raw: n.f };
    }
    const type = (t) => {
      if (typeof t === 'string') return { k: PRIM[t] };
      if (t.e) return { k: K.ENUM, node: nodes[t.e] };
      if (t.s) return { k: K.STRUCT, node: nodes[t.s] };
      return { k: K.LIST, elem: type(t.l) };
    };
    for (const n of Object.values(nodes)) {
      if (n.kind !== 'struct') continue;
      n.fields = n.raw.map((f, i) => {
        const out = { name: f.n, idx: i, disc: f.d === undefined ? -1 : f.d, off: f.o };
        if (f.g) { out.k = K.STRUCT; out.group = nodes[f.g]; out.node = out.group; } else Object.assign(out, type(f.t));
        out.get = SCALAR.has(out.k) ? makeGetter(out.k, f.o, f.dv) : null;
        return out;
      });
      n.byName = Object.create(null);
      for (const f of n.fields) n.byName[f.name] = f;
      delete n.raw;
    }
    // mark fields that can never produce a series (saves work in the hot loop)
    const memo = new Map();
    const typeEmits = (t, seen) => {
      if (SCALAR.has(t.k)) return true;
      if (t.k === K.STRUCT) return structEmits(t.node, seen);
      if (t.k === K.LIST) return typeEmits(t.elem, seen);
      return false;
    };
    const structEmits = (n, seen) => {
      if (memo.has(n.id)) return memo.get(n.id);
      if (seen.has(n.id)) return false;
      seen.add(n.id);
      const r = n.fields.some((f) => typeEmits(f, seen));
      seen.delete(n.id);
      if (seen.size === 0) memo.set(n.id, r);
      return r;
    };
    for (const n of Object.values(nodes)) if (n.kind === 'struct') for (const f of n.fields) f.emits = typeEmits(f, new Set());
    return { nodes, root: nodes[json.root], revision: json.revision, source: json.source };
  }

  // Scalar getter for a struct field. Values are stored XORed with the field default (capnp rule).
  function makeGetter(k, o, dv) {
    switch (k) {
      case K.BOOL: {
        const byte = o >>> 3, bit = o & 7, d = dv ? 1 : 0;
        return (S) => (byte < S.ds ? (U8[S.d + byte] >>> bit) & 1 : 0) ^ d;
      }
      case K.I8: case K.U8: {
        const d = dv ? Number(BigInt.asUintN(8, BigInt(dv))) : 0, signed = k === K.I8;
        return (S) => { const r = (o < S.ds ? U8[S.d + o] : 0) ^ d; return signed ? (r << 24) >> 24 : r; };
      }
      case K.I16: case K.U16: case K.ENUM: {
        const b = o * 2, d = dv ? Number(BigInt.asUintN(16, BigInt(dv))) : 0, signed = k === K.I16;
        return (S) => { const r = (b + 2 <= S.ds ? DV.getUint16(S.d + b, true) : 0) ^ d; return signed ? (r << 16) >> 16 : r; };
      }
      case K.I32: case K.U32: {
        const b = o * 4, d = dv ? Number(BigInt.asUintN(32, BigInt(dv))) : 0, signed = k === K.I32;
        return (S) => { const r = (b + 4 <= S.ds ? DV.getUint32(S.d + b, true) : 0) ^ d; return signed ? r | 0 : r >>> 0; };
      }
      case K.I64: case K.U64: {
        const b = o * 8, signed = k === K.I64;
        const big = dv ? BigInt.asUintN(64, BigInt(dv)) : 0n;
        const dlo = Number(big & 0xffffffffn), dhi = Number(big >> 32n);
        return (S) => {
          if (b + 8 > S.ds) return signed ? (dhi | 0) * 4294967296 + dlo : dhi * 4294967296 + dlo;
          const lo = (DV.getUint32(S.d + b, true) ^ dlo) >>> 0, hi = DV.getUint32(S.d + b + 4, true) ^ dhi;
          return (signed ? (hi | 0) : (hi >>> 0)) * 4294967296 + lo;
        };
      }
      case K.F32: {
        const b = o * 4;
        if (dv === undefined) return (S) => (b + 4 <= S.ds ? DV.getFloat32(S.d + b, true) : 0);
        scratch.setFloat32(0, Number(dv), true);
        const d = scratch.getUint32(0, true);
        return (S) => { scratch.setUint32(0, (b + 4 <= S.ds ? DV.getUint32(S.d + b, true) : 0) ^ d, true); return scratch.getFloat32(0, true); };
      }
      case K.F64: {
        const b = o * 8;
        if (dv === undefined) return (S) => (b + 8 <= S.ds ? DV.getFloat64(S.d + b, true) : 0);
        scratch.setFloat64(0, Number(dv), true);
        const dlo = scratch.getUint32(0, true), dhi = scratch.getUint32(4, true);
        return (S) => {
          const ok = b + 8 <= S.ds;
          scratch.setUint32(0, (ok ? DV.getUint32(S.d + b, true) : 0) ^ dlo, true);
          scratch.setUint32(4, (ok ? DV.getUint32(S.d + b + 4, true) : 0) ^ dhi, true);
          return scratch.getFloat64(0, true);
        };
      }
    }
    throw new Error('not a scalar kind ' + k);
  }

  // ---- capnp wire format -------------------------------------------------------------------
  // Every struct and list reference carries the segment it lives in (g). A pointer's target must
  // lie inside its own segment, as capnp requires: typed-array reads past an end return undefined
  // (and a NaN offset reads byte 0) instead of failing, so all bounds are checked here, once.
  function inSeg(g, a, b, what) {
    const s = SEGS[g];
    if (s === undefined) throw new Error(`${what}: missing segment ${g}`);
    if (!(a >= s && b <= SEGE[g] && a <= b)) throw new Error(`${what} out of bounds`);
  }
  // Resolve the pointer word at absolute byte position pos (in segment g). Sets R_* and returns false for null.
  let R_pos = 0, R_lo = 0, R_hi = 0, R_seg = 0;
  function resolve(pos, g) {
    let lo = DV.getInt32(pos, true), hi = DV.getUint32(pos + 4, true);
    if (lo === 0 && hi === 0) return false;
    if ((lo & 3) === 2) { // far pointer: landing pad in segment hi
      const tg = hi, landing = SEGS[tg] + (lo >>> 3) * 8;
      if (lo & 4) { // double-far: landing pad = far pointer to the content + tag word
        inSeg(tg, landing, landing + 16, 'double-far landing pad');
        const plo = DV.getInt32(landing, true), phi = DV.getUint32(landing + 4, true);
        if ((plo & 7) !== 2) throw new Error('double-far landing pad is not a single far pointer');
        R_seg = phi; R_pos = SEGS[phi] + (plo >>> 3) * 8;
        if (SEGS[phi] === undefined) throw new Error(`double-far content: missing segment ${phi}`);
        R_lo = DV.getInt32(landing + 8, true); R_hi = DV.getUint32(landing + 12, true);
        if ((R_lo & 3) > 1 || (R_lo >> 2) !== 0) throw new Error('bad double-far tag');
        return true;
      }
      inSeg(tg, landing, landing + 8, 'far landing pad');
      lo = DV.getInt32(landing, true); hi = DV.getUint32(landing + 4, true);
      if ((lo & 3) > 1) throw new Error('far landing pad is not a struct or list pointer');
      pos = landing; g = tg;
    } else if ((lo & 3) === 3) throw new Error('capability pointer in a log');
    R_seg = g; R_pos = pos + 8 + (lo >> 2) * 8;
    R_lo = lo; R_hi = hi;
    return true;
  }

  function structAt(pos, g) {
    if (!resolve(pos, g)) return null;
    if ((R_lo & 3) !== 0) throw new Error('expected struct pointer');
    const ds = (R_hi & 0xffff) * 8, pc = R_hi >>> 16;
    inSeg(R_seg, R_pos, R_pos + ds + pc * 8, 'struct pointer');
    return { d: R_pos, ds, p: R_pos + ds, pc, g: R_seg };
  }
  function ptrField(S, idx) { return idx < S.pc ? S.p + idx * 8 : -1; }
  function readStruct(S, idx) { const p = ptrField(S, idx); return p < 0 ? null : structAt(p, S.g); }

  // list: { start, n, es (element size code), stride (bytes), ds, pc, g }
  function listAt(pos, g) {
    if (!resolve(pos, g)) return null;
    if ((R_lo & 3) !== 1) throw new Error('expected list pointer');
    const es = R_hi & 7;
    if (es === 7) {
      inSeg(R_seg, R_pos, R_pos + 8 + (R_hi >>> 3) * 8, 'list pointer'); // count = words after the tag
      const tlo = DV.getInt32(R_pos, true), thi = DV.getUint32(R_pos + 4, true);
      const ds = (thi & 0xffff) * 8, pc = thi >>> 16, n = tlo >> 2;
      if ((tlo & 3) !== 0 || n < 0 || n * (ds + pc * 8) > (R_hi >>> 3) * 8) throw new Error('inconsistent composite list tag');
      return { start: R_pos + 8, n, es, stride: ds + pc * 8, ds, pc, g: R_seg };
    }
    const bytes = [0, 0, 1, 2, 4, 8, 8][es], n = R_hi >>> 3;
    inSeg(R_seg, R_pos, R_pos + (es === 1 ? Math.ceil(n / 8) : n * bytes), 'list pointer');
    return { start: R_pos, n, es, stride: bytes, ds: es === 6 ? 0 : bytes, pc: es === 6 ? 1 : 0, g: R_seg };
  }
  function readList(S, idx) { const p = ptrField(S, idx); return p < 0 ? null : listAt(p, S.g); }
  function listStruct(L, i) {
    if (L.es === 1) throw new Error('bit list read as struct list');
    const d = L.start + i * L.stride;
    return { d, ds: L.ds, p: d + L.ds, pc: L.pc, g: L.g };
  }
  function listScalar(L, i, k) {
    if (k === K.BOOL) return (U8[L.start + (i >>> 3)] >>> (i & 7)) & 1;
    if (L.es === 7) { // struct list where a scalar list was expected: first data field of each element
      const S = listStruct(L, i);
      return makeGetterCached(k)(S);
    }
    const a = L.start + i * L.stride;
    switch (k) {
      case K.I8: return DV.getInt8(a);
      case K.U8: return U8[a];
      case K.I16: return DV.getInt16(a, true);
      case K.U16: case K.ENUM: return DV.getUint16(a, true);
      case K.I32: return DV.getInt32(a, true);
      case K.U32: return DV.getUint32(a, true);
      case K.I64: return DV.getInt32(a + 4, true) * 4294967296 + DV.getUint32(a, true);
      case K.U64: return DV.getUint32(a + 4, true) * 4294967296 + DV.getUint32(a, true);
      case K.F32: return DV.getFloat32(a, true);
      case K.F64: return DV.getFloat64(a, true);
    }
    return NaN;
  }
  const getterCache = new Map();
  function makeGetterCached(k) { if (!getterCache.has(k)) getterCache.set(k, makeGetter(k, 0)); return getterCache.get(k); }

  const utf8 = new TextDecoder('utf-8');
  function listBytes(L) {
    if (!L) return null;
    if (L.es !== 2) throw new Error('expected byte list');
    return U8.subarray(L.start, L.start + L.n);
  }
  function readText(S, idx) {
    const b = listBytes(readList(S, idx));
    if (!b) return '';
    return utf8.decode(b.length && b[b.length - 1] === 0 ? b.subarray(0, b.length - 1) : b);
  }
  function unionWhich(S, node) {
    return node.discOff + 2 <= S.ds ? DV.getUint16(S.d + node.discOff, true) : 0;
  }

  // ---- decompression -----------------------------------------------------------------------
  const codecs = { zstd: null, bz2: null };
  function sniff(u8) {
    if (u8.length >= 4 && u8[0] === 0x28 && u8[1] === 0xb5 && u8[2] === 0x2f && u8[3] === 0xfd) return 'zstd';
    if (u8.length >= 4 && u8[0] === 0x42 && u8[1] === 0x5a && u8[2] === 0x68) return 'bz2';
    return 'raw';
  }
  // A codec returns the bytes, or { data, warning } when it could only decode part of the input.
  function decompress(u8) {
    const kind = sniff(u8);
    if (kind === 'raw') return { kind, data: u8, warning: null };
    if (!codecs[kind]) throw new Error('no ' + kind + ' decoder available');
    const r = codecs[kind](u8);
    return r instanceof Uint8Array ? { kind, data: r, warning: null } : { kind, data: r.data, warning: r.warning };
  }
  // zstd codec from fzstd's streaming decoder: keeps every block decoded before an error, so a
  // file cut off mid-write (e.g. the last segment of a route) still opens up to the cut.
  // Frames whose header sets the content-checksum flag are decoded one by one and verified
  // (XXH64, low 32 bits); openpilot's rlog.zst frames normally carry no checksum.
  function fzstdCodec(fzstd) {
    const stream = (u8) => {
      const chunks = [];
      let total = 0, error = null;
      const d = new fzstd.Decompress((chunk) => { chunks.push(chunk); total += chunk.length; });
      try { d.push(u8, true); } catch (e) { error = e; }
      return { chunks, total, error };
    };
    const concat = (chunks, total) => {
      if (chunks.length === 1) return chunks[0];
      const out = new Uint8Array(total);
      let o = 0;
      for (const c of chunks) { out.set(c, o); o += c.length; }
      return out;
    };
    return (u8) => {
      const frames = zstdFrames(u8);
      if (!frames.some((f) => f.checksum)) {
        const { chunks, total, error } = stream(u8);
        if (error && !total) throw error;
        const data = concat(chunks, total);
        return error ? { data, warning: `compressed data ends early (${error.message}); decoded the first ${total} bytes` } : data;
      }
      const parts = [];
      let total = 0, warning = null;
      for (const f of frames) {
        const r = stream(u8.subarray(f.start, f.end));
        const data = concat(r.chunks, r.total);
        if (r.error || f.truncated) {
          if (!total && !r.total) throw r.error || new Error('zstd frame ends early');
          parts.push(data); total += data.length;
          warning = `compressed data ends early${r.error ? ' (' + r.error.message + ')' : ''}; decoded the first ${total} bytes`;
          break;
        }
        if (f.checksum) {
          const want = new DataView(u8.buffer, u8.byteOffset + f.end - 4, 4).getUint32(0, true);
          if (xxh64Low32(data) !== want) throw new Error(`zstd content checksum mismatch in the frame at byte ${f.start}`);
        }
        parts.push(data); total += data.length;
      }
      const data = concat(parts, total);
      return warning ? { data, warning } : data;
    };
  }
  // Split a zstd stream into frames by walking frame and block headers (no decoding).
  function zstdFrames(u8) {
    const dv = new DataView(u8.buffer, u8.byteOffset, u8.byteLength), len = u8.length, out = [];
    let p = 0;
    while (p + 4 <= len) {
      const magic = dv.getUint32(p, true);
      if ((magic & 0xfffffff0) === 0x184d2a50) { // skippable frame
        if (p + 8 > len) break;
        p += 8 + dv.getUint32(p + 4, true);
        continue;
      }
      if (magic !== 0xfd2fb528 || p + 5 > len) break; // not zstd: leave it to the decoder
      const fhd = u8[p + 4], single = (fhd >> 5) & 1, checksum = !!((fhd >> 2) & 1);
      let q = p + 5 + (single ? 0 : 1) + [0, 1, 2, 4][fhd & 3] + [single, 2, 4, 8][fhd >> 6];
      let truncated = false;
      for (;;) {
        if (q + 3 > len) { truncated = true; break; }
        const b = u8[q] | (u8[q + 1] << 8) | (u8[q + 2] << 16);
        q += 3 + (((b >> 1) & 3) === 1 ? 1 : b >>> 3);
        if (q > len) { truncated = true; break; }
        if (b & 1) break;
      }
      if (!truncated && checksum) { q += 4; if (q > len) truncated = true; }
      out.push({ start: p, end: Math.min(q, len), checksum, truncated });
      if (truncated) break;
      p = q;
    }
    return out;
  }
  // XXH64 (seed 0) of a byte array, low 32 bits: what a zstd frame checksum stores.
  function xxh64Low32(u8) {
    const M = (1n << 64n) - 1n, P1 = 11400714785074694791n, P2 = 14029467366897019727n,
      P3 = 1609587929392839161n, P4 = 9650029242287828579n, P5 = 2870177450012600261n;
    const dv = new DataView(u8.buffer, u8.byteOffset, u8.byteLength), len = u8.length;
    const rotl = (x, r) => ((x << r) | (x >> (64n - r))) & M;
    const round = (acc, x) => (rotl((acc + x * P2) & M, 31n) * P1) & M;
    const merge = (h, v) => (((h ^ round(0n, v)) * P1) + P4) & M;
    let p = 0, h;
    if (len >= 32) {
      let v1 = (P1 + P2) & M, v2 = P2, v3 = 0n, v4 = (M + 1n - P1) & M;
      for (; p + 32 <= len; p += 32) {
        v1 = round(v1, dv.getBigUint64(p, true)); v2 = round(v2, dv.getBigUint64(p + 8, true));
        v3 = round(v3, dv.getBigUint64(p + 16, true)); v4 = round(v4, dv.getBigUint64(p + 24, true));
      }
      h = (rotl(v1, 1n) + rotl(v2, 7n) + rotl(v3, 12n) + rotl(v4, 18n)) & M;
      h = merge(merge(merge(merge(h, v1), v2), v3), v4);
    } else h = P5;
    h = (h + BigInt(len)) & M;
    for (; p + 8 <= len; p += 8) h = ((rotl(h ^ round(0n, dv.getBigUint64(p, true)), 27n) * P1) + P4) & M;
    if (p + 4 <= len) { h = ((rotl(h ^ ((BigInt(dv.getUint32(p, true)) * P1) & M), 23n) * P2) + P3) & M; p += 4; }
    for (; p < len; p++) h = (rotl(h ^ ((BigInt(u8[p]) * P5) & M), 11n) * P1) & M;
    h ^= h >> 33n; h = (h * P2) & M; h ^= h >> 29n; h = (h * P3) & M; h ^= h >> 32n;
    return Number(h & 0xffffffffn);
  }

  // ---- log file: message index --------------------------------------------------------------
  class LogFile {
    constructor(name, data, schema) {
      this.name = name;
      this.u8 = data;
      this.dv = new DataView(data.buffer, data.byteOffset, data.byteLength);
      this.schema = schema;
      this.warnings = [];
      this.index();
    }
    index() {
      const u8 = this.u8, dv = this.dv, len = u8.length;
      let cap = 1 << 16, n = 0;
      let hdr = new Uint32Array(cap), mono = new Float64Array(cap), which = new Uint16Array(cap);
      const ev = this.schema.root;
      const monoGet = ev.byName.logMonoTime.get;
      U8 = u8; DV = dv;
      let p = 0, stopped = false;
      while (p + 8 <= len) {
        const nseg = dv.getUint32(p, true) + 1;
        if (nseg > 1024) { this.warnings.push(`bad segment count at byte ${p}; stopped`); stopped = true; break; }
        const hsize = (4 * (nseg + 1) + 7) & ~7;
        if (p + 4 * (nseg + 1) > len) { this.warnings.push(`truncated message header at byte ${p} (file ends early)`); stopped = true; break; }
        let total = 0;
        for (let s = 0; s < nseg; s++) total += dv.getUint32(p + 4 + 4 * s, true);
        const end = p + hsize + total * 8;
        if (end > len) { this.warnings.push(`truncated message at byte ${p} (file ends early)`); stopped = true; break; }
        if (n === cap) {
          cap *= 2;
          const h2 = new Uint32Array(cap); h2.set(hdr); hdr = h2;
          const m2 = new Float64Array(cap); m2.set(mono); mono = m2;
          const w2 = new Uint16Array(cap); w2.set(which); which = w2;
        }
        hdr[n] = p;
        try {
          const S = this.openAt(p);
          mono[n] = monoGet(S);
          which[n] = unionWhich(S, ev);
        } catch (e) {
          this.warnings.push(`undecodable message at byte ${p}: ${e.message}`);
          mono[n] = NaN; which[n] = 0xffff;
        }
        n++;
        p = end;
      }
      if (p < len && !stopped) this.warnings.push(`${len - p} trailing bytes ignored`);
      this.n = n;
      this.hdr = hdr.subarray(0, n);
      this.mono = mono.subarray(0, n);
      this.which = which.subarray(0, n);
      let lo = Infinity, hi = -Infinity;
      for (let i = 0; i < n; i++) { const m = this.mono[i]; if (m < lo) lo = m; if (m > hi) hi = m; }
      this.monoMin = lo; this.monoMax = hi;
      // Each segment repeats a few messages stamped at the route start (e.g. initData), so the
      // true minimum is not where a segment's data begins. Order and compare files by percentiles.
      // Start from the 1st/99th percentile and extend outwards until a gap of 1 s or more.
      const sorted = Float64Array.from(this.mono.filter((m) => m === m)).sort();
      const ns = sorted.length;
      if (ns) {
        let a = Math.floor(ns * 0.01), b = Math.min(ns - 1, Math.ceil(ns * 0.99));
        while (a > 0 && sorted[a] - sorted[a - 1] < 1e9) a--;
        while (b < ns - 1 && sorted[b + 1] - sorted[b] < 1e9) b++;
        this.monoLo = sorted[a]; this.monoHi = sorted[b];
      } else { this.monoLo = lo; this.monoHi = hi; }
    }
    // Make message at header position p current and return its root struct.
    openAt(p) {
      U8 = this.u8; DV = this.dv;
      const nseg = DV.getUint32(p, true) + 1;
      let s0 = p + ((4 * (nseg + 1) + 7) & ~7);
      SEGS.length = nseg; SEGE.length = nseg;
      for (let s = 0; s < nseg; s++) { SEGS[s] = s0; s0 += DV.getUint32(p + 4 + 4 * s, true) * 8; SEGE[s] = s0; }
      return structAt(SEGS[0], 0);
    }
    open(i) { return this.openAt(this.hdr[i]); }
  }

  // ---- route: files + per-service extraction --------------------------------------------------
  const CAN_SERVICES = new Set(['can', 'sendcan']);

  class Route {
    constructor(schema, opts = {}) {
      this.schema = schema;
      this.files = [];
      this.maxScalarList = opts.maxScalarList ?? 64;
      this.reset();
    }
    reset() {
      this.t0 = 0;
      this.services = new Map();     // name -> { name, field, disc, count, refs (file,msg pairs), series(trie) }
      this.series = new Map();       // path -> series
      this.enumInfo = new Map();
    }
    addFile(file) { this.files.push(file); }
    // Build the service table across all files. Call after adding files.
    build() {
      this.reset();
      this.files.sort((a, b) => a.monoLo - b.monoLo);
      const ev = this.schema.root;
      const byDisc = [];
      for (const f of ev.fields) if (f.disc >= 0) byDisc[f.disc] = f;
      const counts = new Map();
      // time origin: earliest event of a service this schema knows (as jotpluggler's x_min)
      let t0 = Infinity;
      this.files.forEach((file, fi) => {
        for (let i = 0; i < file.n; i++) {
          const w = file.which[i], m = file.mono[i];
          if (w === 0xffff || m !== m) continue; // undecodable (reported in file.warnings)
          if (byDisc[w] && m < t0) t0 = m;
          let c = counts.get(w);
          if (!c) counts.set(w, c = []);
          c.push(fi, i);
        }
      });
      if (t0 === Infinity) for (const f of this.files) if (f.monoMin < t0) t0 = f.monoMin;
      this.t0 = t0;
      for (const [w, refs] of counts) {
        const field = byDisc[w];
        const name = field ? field.name : (w === 0xffff ? '(undecodable)' : `unknown${w}`);
        const nmsg = refs.length / 2;
        // sort by time (rlogs are near-sorted; a stable index sort keeps file order on ties)
        const order = new Uint32Array(nmsg);
        const tt = new Float64Array(nmsg);
        for (let j = 0; j < nmsg; j++) { order[j] = j; tt[j] = this.files[refs[2 * j]].mono[refs[2 * j + 1]]; }
        let sorted = true;
        for (let j = 1; j < nmsg; j++) if (tt[j] < tt[j - 1]) { sorted = false; break; }
        if (!sorted) order.sort((a, b) => tt[a] - tt[b] || a - b);
        const fileIdx = new Uint16Array(nmsg), msgIdx = new Uint32Array(nmsg), t = new Float64Array(nmsg);
        for (let j = 0; j < nmsg; j++) {
          const o = order[j];
          fileIdx[j] = refs[2 * o]; msgIdx[j] = refs[2 * o + 1]; t[j] = (tt[o] - t0) / 1e9;
        }
        this.services.set(name, { name, field, disc: w, count: nmsg, fileIdx, msgIdx, t, extracted: false, trie: null, paths: null });
      }
      const all = [...this.services.values()];
      this.tMin = 0;
      this.tMax = all.reduce((m, s) => Math.max(m, s.t.length ? s.t[s.t.length - 1] : 0), 0);
      // span of the bulk of the data (files' 1st..99th percentile), for the initial view
      this.dataMin = Math.max(0, (Math.min(...this.files.map((f) => f.monoLo)) - t0) / 1e9);
      this.dataMax = Math.min(this.tMax, (Math.max(...this.files.map((f) => f.monoHi)) - t0) / 1e9);
      if (!(this.dataMax > this.dataMin)) { this.dataMin = this.tMin; this.dataMax = this.tMax; }
    }
    serviceNames() { return [...this.services.keys()].sort((a, b) => a.localeCompare(b)); }

    // Iterate messages of a service: cb(rootStruct, payloadField, j)
    forEachMessage(svc, cb) {
      for (let j = 0; j < svc.count; j++) {
        const S = this.files[svc.fileIdx[j]].open(svc.msgIdx[j]);
        cb(S, j);
      }
    }

    // Extract all series of one service. Returns the list of its series paths.
    extract(name) {
      const it = this.extractIter(name);
      while (!it.next().done);
      const svc = this.services.get(name);
      return svc ? svc.paths : [];
    }
    // Same, as a generator yielding progress (0..1) every few thousand messages so a UI can stay
    // responsive. Callers must not start a second extraction of the same service meanwhile.
    *extractIter(name) {
      const svc = this.services.get(name);
      if (!svc || svc.extracted) return;
      svc.extracted = true;
      const ev = this.schema.root;
      const validGet = ev.byName.valid.get;
      const field = svc.field;
      const trie = newTrie('/' + name, svc.count);
      trie.isRoot = true;
      svc.trie = trie;
      const base = ['valid', 'logMonoTime', 't'].map((k) => trieChild(trie, 'e' + k, k));
      const maxList = this.maxScalarList;
      const payload = field && field.emits && !CAN_SERVICES.has(name) ? field : null;
      const files = this.files;
      svc.errors = 0;
      try {
        for (let j = 0; j < svc.count; j++) {
          if ((j & 1023) === 1023) yield j / svc.count;
          const file = files[svc.fileIdx[j]];
          const mi = svc.msgIdx[j];
          TOUCHED.length = 0;
          try {
            const S = file.open(mi);
            push(base[0], j, validGet(S), K.BOOL);
            push(base[1], j, file.mono[mi], K.U64);
            push(base[2], j, svc.t[j], K.F64);
            if (!payload) continue;
            if (payload.k === K.STRUCT) {
              const P = readStruct(S, payload.off);
              if (P) visitStruct(P, payload.node, trie, j, maxList);
            } else if (payload.k === K.LIST) {
              const L = readList(S, payload.off);
              if (L) visitList(L, payload.elem, trie, j, maxList);
            }
          } catch (e) {
            // a corrupt pointer inside one message: drop everything read from it, count it, go on
            for (const s of TOUCHED) s.n--;
            if (!svc.errors++) svc.firstError = `message ${j} (t ${svc.t[j].toFixed(3)} s): ${e.message}`;
          }
        }
      } finally {
        const out = [];
        finalize(trie, svc.t, (s) => { this.series.set(s.path, s); out.push(s.path); });
        svc.paths = out;
      }
    }

    // CAN frames of can/sendcan grouped by (bus, address). Frames point into the decoded file
    // buffers (file, pos, len); a message with a corrupt frame list contributes no frames.
    canIndex(name) {
      const it = this.canIndexIter(name);
      while (!it.next().done);
      const svc = this.services.get(name);
      return svc ? svc.can : null;
    }
    *canIndexIter(name) {
      const svc = this.services.get(name);
      if (!svc || svc.can || svc.canBuilding) return;
      svc.canBuilding = true;
      const field = svc.field, cd = field.elem.node;
      const gAddr = cd.byName.address.get, gSrc = cd.byName.src.get, datIdx = cd.byName.dat.off;
      const groups = new Map(), pending = [];
      const grow = (g) => {
        const cap = g.t.length * 2;
        const t = new Float64Array(cap); t.set(g.t); g.t = t;
        const f = new Uint16Array(cap); f.set(g.file); g.file = f;
        const p = new Uint32Array(cap); p.set(g.pos); g.pos = p;
        const l = new Uint8Array(cap); l.set(g.len); g.len = l;
      };
      svc.canErrors = 0;
      for (let j = 0; j < svc.count; j++) {
        if ((j & 255) === 255) yield j / svc.count;
        const fi = svc.fileIdx[j];
        pending.length = 0;
        try {
          const S = this.files[fi].open(svc.msgIdx[j]);
          const L = readList(S, field.off);
          if (!L) continue;
          for (let i = 0; i < L.n; i++) {
            const E = listStruct(L, i);
            const D = readList(E, datIdx);
            if (D && D.es !== 2) throw new Error('CAN data is not a byte list');
            if (D && D.n > 255) throw new Error('CAN frame longer than 255 bytes');
            pending.push(gSrc(E), gAddr(E), D ? D.start : 0, D ? D.n : 0);
          }
        } catch (e) {
          if (!svc.canErrors++) svc.canFirstError = `message ${j} (t ${svc.t[j].toFixed(3)} s): ${e.message}`;
          continue;
        }
        for (let k = 0; k < pending.length; k += 4) {
          const bus = pending[k], addr = pending[k + 1], key = bus * 4294967296 + addr;
          let g = groups.get(key);
          if (!g) groups.set(key, g = { bus, address: addr, n: 0, t: new Float64Array(64), file: new Uint16Array(64), pos: new Uint32Array(64), len: new Uint8Array(64), maxLen: 0 });
          if (g.n === g.t.length) grow(g);
          g.t[g.n] = svc.t[j]; g.file[g.n] = fi; g.pos[g.n] = pending[k + 2]; g.len[g.n] = pending[k + 3];
          if (pending[k + 3] > g.maxLen) g.maxLen = pending[k + 3];
          g.n++;
        }
      }
      const list = [...groups.values()].sort((a, b) => a.bus - b.bus || a.address - b.address);
      for (const g of list) {
        g.t = g.t.slice(0, g.n); g.file = g.file.slice(0, g.n); g.pos = g.pos.slice(0, g.n); g.len = g.len.slice(0, g.n);
      }
      svc.can = list;
      svc.canBuilding = false;
    }
    canBytes(g, k) {
      const v = new Float64Array(g.t.length);
      for (let i = 0; i < v.length; i++) v[i] = k < g.len[i] ? this.files[g.file[i]].u8[g.pos[i] + k] : NaN;
      return v;
    }
    canFrame(g, i) {
      const u8 = this.files[g.file[i]].u8;
      return u8.subarray(g.pos[i], g.pos[i] + g.len[i]);
    }

    // Text payload services (logMessage, errorLogMessage, ...): [{t, text}]
    texts(name) {
      const svc = this.services.get(name);
      if (!svc || !svc.field || svc.field.k !== K.TEXT) return [];
      if (svc.textCache) return svc.textCache;
      const out = [];
      for (let j = 0; j < svc.count; j++) {
        try {
          const S = this.files[svc.fileIdx[j]].open(svc.msgIdx[j]);
          out.push({ t: svc.t[j], text: readText(S, svc.field.off) });
        } catch (e) { out.push({ t: svc.t[j], text: `(undecodable message: ${e.message})` }); }
      }
      svc.textCache = out;
      return out;
    }

    // Index of the last message of a service at or before time t (or the first one)
    messageAt(name, t) {
      const svc = this.services.get(name);
      if (!svc || !svc.count) return -1;
      return Math.max(0, upperBound(svc.t, t) - 1);
    }
    // Full decode of one message to a plain JS object (text included, data as hex)
    messageObject(name, j, opts) {
      const svc = this.services.get(name);
      const S = this.files[svc.fileIdx[j]].open(svc.msgIdx[j]);
      return toObject(S, this.schema.root, opts || {});
    }
  }

  // ---- flattening -----------------------------------------------------------------------------
  // total: message count of the service. A path gets at most one sample per message, so a series
  // first seen at message j never holds more than total - j samples: storage is allocated once.
  function newTrie(path, total) { return { path, total, kids: Object.create(null), s: null, isRoot: false }; }
  // Values keep their wire type (exact), which takes far less memory than float64 for most fields.
  const STORE = [Float64Array, Uint8Array, Int8Array, Int16Array, Int32Array, Float64Array, Uint8Array, Uint16Array,
    Uint32Array, Float64Array, Float32Array, Float64Array];
  STORE[K.ENUM] = Uint16Array;
  // Event-level series every service gets. A payload field with one of these names would share
  // the path; jotpluggler keeps the event-level series there, so the payload one is renamed.
  const EVENT_BASE = new Set(['valid', 'logMonoTime', 't']);
  function trieChild(T, key, name) {
    let c = T.kids[key];
    if (!c) T.kids[key] = c = newTrie(T.path + '/' + name, T.total);
    return c;
  }

  function push(C, j, v, k, enumNode) {
    let s = C.s;
    if (!s) {
      C.s = s = { path: C.path, kind: KIND_NAME[k], first: j, n: 0, dense: true, idx: null, vals: new STORE[k](C.total - j),
        t: null, v: null, enumNames: enumNode ? enumNode.names : null, integer: k !== K.F32 && k !== K.F64 };
    }
    if (s.dense && j !== s.first + s.n) {
      s.dense = false;
      s.idx = new Uint32Array(C.total - s.first);
      for (let i = 0; i < s.n; i++) s.idx[i] = s.first + i;
    }
    if (!s.dense) s.idx[s.n] = j;
    s.vals[s.n++] = v;
    TOUCHED.push(s); // each series at most once per message, so a failed message can be rolled back
  }
  const TOUCHED = [];

  // Returns whether the subtree holds any samples; empty branches (only rolled-back data) are dropped.
  function finalize(T, svcT, emit) {
    const s = T.s;
    let has = false;
    if (s && s.n === 0) T.s = null;
    else if (s) {
      has = true;
      if (s.dense) s.t = svcT.subarray(s.first, s.first + s.n);
      else { s.t = new Float64Array(s.n); for (let i = 0; i < s.n; i++) s.t[i] = svcT[s.idx[i]]; }
      s.v = s.n === s.vals.length ? s.vals : s.vals.slice(0, s.n);
      s.idx = null; s.vals = null;
      emit(s);
    }
    for (const key in T.kids) {
      if (finalize(T.kids[key], svcT, emit)) has = true; else delete T.kids[key];
    }
    return has;
  }

  function visitStruct(S, node, T, j, maxList) {
    const fields = node.fields;
    const which = node.discOff >= 0 ? unionWhich(S, node) : -1;
    for (let i = 0; i < fields.length; i++) {
      const f = fields[i];
      if (!f.emits || (f.disc >= 0 && f.disc !== which)) continue;
      const C = T.kids[i] || (T.kids[i] = newTrie(T.path + '/' + (T.isRoot && EVENT_BASE.has(f.name) ? f.name + ' (payload)' : f.name), T.total));
      if (f.group) { visitStruct(S, f.group, C, j, maxList); continue; }
      if (f.get) { push(C, j, f.get(S), f.k, f.node); continue; }
      if (f.k === K.STRUCT) { const c = readStruct(S, f.off); if (c) visitStruct(c, f.node, C, j, maxList); continue; }
      if (f.k === K.LIST) { const L = readList(S, f.off); if (L) visitList(L, f.elem, C, j, maxList); }
    }
  }

  function visitList(L, elem, T, j, maxList) {
    const n = L.n;
    if (SCALAR.has(elem.k)) {
      if (n > maxList) return;
      for (let i = 0; i < n; i++) {
        const C = T.kids['#' + i] || (T.kids['#' + i] = newTrie(T.path + '/' + i, T.total));
        push(C, j, listScalar(L, i, elem.k), elem.k, elem.node);
      }
    } else if (elem.k === K.STRUCT) {
      for (let i = 0; i < n; i++) {
        const C = T.kids['#' + i] || (T.kids['#' + i] = newTrie(T.path + '/' + i, T.total));
        visitStruct(listStruct(L, i), elem.node, C, j, maxList);
      }
    } else if (elem.k === K.LIST) {
      for (let i = 0; i < n; i++) {
        const sub = listAt(L.start + i * 8, L.g);
        if (!sub) continue;
        const C = T.kids['#' + i] || (T.kids['#' + i] = newTrie(T.path + '/' + i, T.total));
        visitList(sub, elem.elem, C, j, maxList);
      }
    }
  }

  // ---- full object decode (inspector) -------------------------------------------------------------
  const HEX = Array.from({ length: 256 }, (_, i) => i.toString(16).padStart(2, '0'));
  function hex(b, max) {
    let s = '';
    const n = Math.min(b.length, max);
    for (let i = 0; i < n; i++) s += HEX[b[i]];
    return b.length > max ? s + `… (${b.length} bytes)` : s;
  }
  function toObject(S, node, opts, depth = 0) {
    const maxList = opts.maxList ?? 100;
    const out = {};
    const which = node.discOff >= 0 ? unionWhich(S, node) : -1;
    for (const f of node.fields) {
      if (f.disc >= 0 && f.disc !== which) continue;
      out[f.name] = fieldValue(S, f, opts, depth, maxList);
    }
    return out;
  }
  // shortest decimal that reads back as the same float32 (display only)
  function f32(v) {
    if (!Number.isFinite(v)) return v;
    for (let p = 6; p < 9; p++) { const s = Number(v.toPrecision(p)); if (Math.fround(s) === v) return s; }
    return Number(v.toPrecision(9));
  }
  function enumName(node, v) { return node && node.names[v] ? node.names[v] : v; }
  function fieldValue(S, f, opts, depth, maxList) {
    if (f.group) return toObject(S, f.group, opts, depth + 1);
    if (f.get) return f.k === K.ENUM ? enumName(f.node, f.get(S)) : f.k === K.BOOL ? !!f.get(S) : f.k === K.F32 ? f32(f.get(S)) : f.get(S);
    switch (f.k) {
      case K.VOID: return null;
      case K.TEXT: return readText(S, f.off);
      case K.DATA: { const b = listBytes(readList(S, f.off)); return b ? hex(b, 256) : null; }
      case K.ANY: return '(anyPointer)';
      case K.STRUCT: { const c = readStruct(S, f.off); return c ? toObject(c, f.node, opts, depth + 1) : null; }
      case K.LIST: { const L = readList(S, f.off); return L ? listValue(L, f.elem, opts, depth, maxList) : null; }
    }
    return undefined;
  }
  function listValue(L, elem, opts, depth, maxList) {
    const out = [];
    const n = Math.min(L.n, maxList);
    for (let i = 0; i < n; i++) {
      if (SCALAR.has(elem.k)) {
        const v = listScalar(L, i, elem.k);
        out.push(elem.k === K.ENUM ? enumName(elem.node, v) : elem.k === K.BOOL ? !!v : elem.k === K.F32 ? f32(v) : v);
      } else if (elem.k === K.STRUCT) out.push(toObject(listStruct(L, i), elem.node, opts, depth + 1));
      else if (elem.k === K.TEXT) { const b = listBytes(listAt(L.start + i * 8, L.g)); out.push(b ? utf8.decode(b.subarray(0, Math.max(0, b.length - 1))) : ''); }
      else if (elem.k === K.DATA) { const b = listBytes(listAt(L.start + i * 8, L.g)); out.push(b ? hex(b, 256) : null); }
      else if (elem.k === K.LIST) { const sub = listAt(L.start + i * 8, L.g); out.push(sub ? listValue(sub, elem.elem, opts, depth + 1, maxList) : null); }
      else out.push(null);
    }
    if (L.n > n) out.push(`… ${L.n - n} more`);
    return out;
  }

  // ---- helpers ------------------------------------------------------------------------------------
  function upperBound(a, x) { let lo = 0, hi = a.length; while (lo < hi) { const m = (lo + hi) >>> 1; if (a[m] <= x) lo = m + 1; else hi = m; } return lo; }
  function lowerBound(a, x) { let lo = 0, hi = a.length; while (lo < hi) { const m = (lo + hi) >>> 1; if (a[m] < x) lo = m + 1; else hi = m; } return lo; }

  return { K, compileSchema, LogFile, Route, codecs, sniff, decompress, fzstdCodec, upperBound, lowerBound };
});
