/* dbc.js: parse a DBC file and decode CAN signals (Intel/Motorola, signed, multiplexed, value tables). */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.DBC = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  const BO_RE = /^BO_\s+(\d+)\s+(\w+)\s*:\s*(\d+)\s+(\S+)/;
  // Multiplex indicators as jotpluggler reads them (tools/jotpluggler/dbc.h): "M" is the switch,
  // "m<n>" (also "m<n>M", extended multiplexing) is multiplexed with value n under that switch.
  const SG_RE = /^SG_\s+(\w+)\s*(M|m\d+M?)?\s*:\s*(\d+)\|(\d+)@([01])([+-])\s*\(\s*([^,]+)\s*,\s*([^)]+)\)\s*\[\s*([^|\]]*)\|([^\]]*)\]\s*"([^"]*)"/;
  const VAL_RE = /^VAL_\s+(\d+)\s+(\w+)\s+(.*);/;

  function parse(text, name) {
    const byId = new Map(), byName = new Map(), warnings = [];
    let cur = null, lineNo = 0;
    for (const raw of text.split(/\r?\n/)) {
      lineNo++;
      const line = raw.trim();
      let m;
      if ((m = BO_RE.exec(line))) {
        const id = Number(m[1]) & 0x1fffffff; // bit 31 flags an extended id
        cur = { id, name: m[2], size: Number(m[3]), signals: [], mux: null, extendedMux: false };
        byId.set(id, cur); byName.set(cur.name, cur);
      } else if (/^BO_\s/.test(line)) {
        cur = null; // its signals must not attach to the previous message
        warnings.push(`line ${lineNo}: unreadable message definition`);
      } else if (/^SG_\s/.test(line)) {
        if (!cur) continue; // belongs to a message that was skipped (already reported)
        if (!(m = SG_RE.exec(line))) { warnings.push(`line ${lineNo}: unreadable signal in ${cur.name}`); continue; }
        const ind = m[2] || '';
        const sig = {
          name: m[1], start: Number(m[3]), size: Number(m[4]), little: m[5] === '1', signed: m[6] === '-',
          factor: Number(m[7]), offset: Number(m[8]), min: Number(m[9]), max: Number(m[10]), unit: m[11],
          muxSwitch: ind === 'M', muxValue: ind.startsWith('m') ? parseInt(ind.slice(1), 10) : null, values: null,
        };
        if (ind.length > 1 && ind.endsWith('M')) cur.extendedMux = true;
        if (sig.muxSwitch) {
          if (cur.mux) warnings.push(`line ${lineNo}: second multiplexor in ${cur.name}`);
          else cur.mux = sig;
        }
        cur.signals.push(sig);
      } else if ((m = VAL_RE.exec(line))) {
        const msg = byId.get(Number(m[1]) & 0x1fffffff);
        const sig = msg && msg.signals.find((s) => s.name === m[2]);
        if (!sig) continue;
        const values = {};
        const re = /(-?\d+)\s+"([^"]*)"/g;
        let v;
        while ((v = re.exec(m[3]))) values[Number(v[1])] = v[2];
        sig.values = values;
      } else if (line === '') {
        cur = null;
      }
    }
    const ext = [...byId.values()].filter((msg) => msg.extendedMux).map((msg) => msg.name);
    if (ext.length) warnings.push(`extended multiplexing in ${ext.join(', ')}: decoded as simple multiplexing under the one switch (as jotpluggler does)`);
    return { name, byId, byName, warnings };
  }

  // Raw unsigned bit field of one signal, or NaN when the frame is too short.
  function rawBits(sig, dat) {
    let v = 0;
    if (sig.little) {
      const end = sig.start + sig.size - 1;
      if ((end >> 3) >= dat.length) return NaN;
      for (let b = end; b >= sig.start; b--) v = v * 2 + ((dat[b >> 3] >> (b & 7)) & 1);
    } else {
      let b = sig.start;
      for (let i = 0; i < sig.size; i++) {
        if ((b >> 3) >= dat.length) return NaN;
        v = v * 2 + ((dat[b >> 3] >> (b & 7)) & 1);
        b = (b & 7) === 0 ? b + 15 : b - 1;
      }
    }
    return v;
  }

  function decode(sig, dat) {
    let v = rawBits(sig, dat);
    if (Number.isNaN(v)) return NaN;
    if (sig.signed && v >= 2 ** (sig.size - 1)) v -= 2 ** sig.size;
    return v * sig.factor + sig.offset;
  }

  // Value of signal sig in message msg for one frame, honoring multiplexing (NaN when not present).
  // A multiplexed signal in a message without a switch decodes on every frame, as in jotpluggler.
  function signalValue(msg, sig, dat) {
    if (sig.muxValue !== null && msg.mux && rawBits(msg.mux, dat) !== sig.muxValue) return NaN;
    return decode(sig, dat);
  }

  return { parse, decode, signalValue, rawBits };
});
