/* bunzip2.js: minimal bzip2 decoder (multi-stream, block and stream CRC checked) for older rlog.bz2 files. */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.bunzip2 = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  const CRC_TABLE = new Uint32Array(256);
  for (let i = 0; i < 256; i++) {
    let c = i << 24;
    for (let k = 0; k < 8; k++) c = c & 0x80000000 ? (c << 1) ^ 0x04c11db7 : c << 1;
    CRC_TABLE[i] = c >>> 0;
  }

  function buildTable(len) {
    let minLen = 32, maxLen = 0;
    for (const l of len) { if (l < minLen) minLen = l; if (l > maxLen) maxLen = l; }
    const perm = new Uint16Array(len.length);
    let pp = 0;
    for (let l = minLen; l <= maxLen; l++) for (let s = 0; s < len.length; s++) if (len[s] === l) perm[pp++] = s;
    const count = new Int32Array(maxLen + 1);
    for (const l of len) count[l]++;
    const base = new Int32Array(maxLen + 1), limit = new Int32Array(maxLen + 1);
    let code = 0, idx = 0;
    for (let l = minLen; l <= maxLen; l++) {
      base[l] = idx - code;
      code += count[l]; idx += count[l];
      limit[l] = code - 1;
      code <<= 1;
    }
    return { minLen, maxLen, perm, base, limit };
  }

  return function bunzip2(src) {
    let pos = 0, bitBuf = 0, bitCount = 0;
    const bits = (n) => {
      while (bitCount < n) {
        if (pos >= src.length) throw new Error('bz2: unexpected end of data');
        bitBuf = (bitBuf << 8) | src[pos++];
        bitCount += 8;
      }
      bitCount -= n;
      return (bitBuf >>> bitCount) & ((1 << n) - 1);
    };
    const bits32 = () => ((bits(16) << 16) | bits(16)) >>> 0;

    let out = new Uint8Array(Math.max(1 << 20, src.length * 8)), outLen = 0;
    const grow = (need) => {
      if (outLen + need <= out.length) return;
      let cap = out.length * 2;
      while (cap < outLen + need) cap *= 2;
      const o2 = new Uint8Array(cap); o2.set(out.subarray(0, outLen)); out = o2;
    };

    try {
    for (;;) { // streams
      if (bits(8) !== 0x42 || bits(8) !== 0x5a || bits(8) !== 0x68) throw new Error('bz2: bad stream header');
      const level = bits(8) - 0x30;
      if (level < 1 || level > 9) throw new Error('bz2: bad block size');
      const maxBlock = level * 100000;
      const tt = new Uint32Array(maxBlock);
      let combined = 0;
      for (;;) { // blocks
        const m1 = bits(24), m2 = bits(24);
        if (m1 === 0x177245 && m2 === 0x385090) {
          const want = bits32();
          if (want !== combined >>> 0) throw new Error('bz2: stream CRC mismatch');
          bitCount -= bitCount & 7; // streams end byte-aligned
          break;
        }
        if (m1 !== 0x314159 || m2 !== 0x265359) throw new Error('bz2: bad block header');
        const blockCrc = bits32();
        if (bits(1)) throw new Error('bz2: randomized blocks are not supported');
        const origPtr = bits(24);

        const used = bits(16), seqToUnseq = new Uint8Array(256);
        let nInUse = 0;
        for (let i = 0; i < 16; i++) {
          if (!(used & (0x8000 >>> i))) continue;
          const u = bits(16);
          for (let j = 0; j < 16; j++) if (u & (0x8000 >>> j)) seqToUnseq[nInUse++] = i * 16 + j;
        }
        if (!nInUse) throw new Error('bz2: empty symbol map');
        const alphaSize = nInUse + 2;
        const nGroups = bits(3);
        if (nGroups < 2 || nGroups > 6) throw new Error('bz2: bad group count');
        const nSelectors = bits(15);
        if (!nSelectors) throw new Error('bz2: no selectors');
        const mtfG = Uint8Array.from({ length: nGroups }, (_, i) => i), selectors = new Uint8Array(nSelectors);
        for (let i = 0; i < nSelectors; i++) {
          let j = 0;
          while (bits(1)) if (++j >= nGroups) throw new Error('bz2: bad selector');
          const v = mtfG[j];
          for (; j > 0; j--) mtfG[j] = mtfG[j - 1];
          selectors[i] = mtfG[0] = v;
        }
        const tables = [];
        for (let g = 0; g < nGroups; g++) {
          const len = new Uint8Array(alphaSize);
          let cur = bits(5);
          for (let s = 0; s < alphaSize; s++) {
            for (;;) {
              if (cur < 1 || cur > 20) throw new Error('bz2: bad code length');
              if (!bits(1)) break;
              cur += bits(1) ? -1 : 1;
            }
            len[s] = cur;
          }
          tables.push(buildTable(len));
        }

        const EOB = nInUse + 1, mtf = Uint8Array.from({ length: 256 }, (_, i) => i), unzftab = new Int32Array(256);
        let sel = -1, left = 0, t = null, nblock = 0, runLen = 0, runBit = 1;
        for (;;) {
          if (!left) {
            if (++sel >= nSelectors) throw new Error('bz2: ran out of selectors');
            t = tables[selectors[sel]]; left = 50;
          }
          left--;
          let l = t.minLen, code = bits(l), sym = -1;
          while (l <= t.maxLen) {
            if (code <= t.limit[l]) { sym = t.perm[code + t.base[l]]; break; }
            code = (code << 1) | bits(1); l++;
          }
          if (sym < 0) throw new Error('bz2: bad huffman code');
          if (sym <= 1) {
            runLen += (sym + 1) * runBit; runBit <<= 1;
            if (runLen > maxBlock) throw new Error('bz2: run too long');
            continue;
          }
          if (runLen) {
            const b = seqToUnseq[mtf[0]];
            if (nblock + runLen > maxBlock) throw new Error('bz2: block overflow');
            unzftab[b] += runLen; tt.fill(b, nblock, nblock + runLen); nblock += runLen;
            runLen = 0; runBit = 1;
          }
          if (sym === EOB) break;
          const idx = sym - 1, v = mtf[idx];
          mtf.copyWithin(1, 0, idx); mtf[0] = v;
          const b = seqToUnseq[v];
          if (nblock >= maxBlock) throw new Error('bz2: block overflow');
          unzftab[b]++; tt[nblock++] = b;
        }
        if (origPtr >= nblock) throw new Error('bz2: bad origPtr');

        const cftab = new Int32Array(257);
        for (let i = 0; i < 256; i++) cftab[i + 1] = cftab[i] + unzftab[i];
        for (let i = 0; i < nblock; i++) { const b = tt[i] & 0xff; tt[cftab[b]++] |= i << 8; }
        let tPos = tt[origPtr] >>> 8, last = -1, count = 0, crc = 0xffffffff;
        grow(nblock);
        for (let i = 0; i < nblock; i++) {
          const e = tt[tPos], b = e & 0xff;
          tPos = e >>> 8;
          if (count === 4) { // run-length byte after four equal bytes
            grow(b + (nblock - i));
            for (let k = 0; k < b; k++) { out[outLen++] = last; crc = (crc << 8) ^ CRC_TABLE[((crc >>> 24) ^ last) & 0xff]; }
            count = 0; last = -1;
            continue;
          }
          if (b === last) count++; else { last = b; count = 1; }
          out[outLen++] = b;
          crc = (crc << 8) ^ CRC_TABLE[((crc >>> 24) ^ b) & 0xff];
        }
        crc = ~crc >>> 0;
        if (crc !== blockCrc) throw new Error('bz2: block CRC mismatch');
        combined = (((combined << 1) | (combined >>> 31)) ^ crc) >>> 0;
      }
      if (bitCount === 0 && pos >= src.length) break;
      if (bitCount < 8 && src.length - pos < 4) break; // trailing padding
    }
    } catch (e) {
      // input cut off: keep the blocks that decoded completely (each was CRC-checked)
      if (/unexpected end/.test(e.message) && outLen > 0) {
        return { data: out.slice(0, outLen), warning: `compressed data ends early; decoded the first ${outLen} bytes` };
      }
      throw e;
    }
    return out.slice(0, outLen);
  };
});
