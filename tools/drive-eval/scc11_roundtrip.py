# runs on the comma (offroad), read-only; pipe it in:  python - <route> [<route> ...] < scc11_roundtrip.py
# Stage 0 of docs/proposals/2026-11-17-g70-scc11-info-display-filter.md: every distinct camera SCC11 (0x420, bus 2)
# payload in the routes is decoded with the DBC, packed again, and must come back byte for byte. Then the proposed
# filter (SCCInfoDisplay 4 -> 0) is applied and must change only byte 0 bit 3, and only on frames that carry 4.
import sys, glob, re, collections
from multiprocessing import Pool
from opendbc.can import CANPacker
from opendbc.can.dbc import DBC
from openpilot.tools.lib.logreader import LogReader

DBC_NAME = "hyundai_can_generated"

def seg(path):
  seen = collections.Counter(); gaps = collections.Counter(); last_cnt = None; last_t = None; dts = []
  for m in LogReader(path):
    if m.which() != "can": continue
    for c in m.can:
      if c.address == 0x420 and c.src == 2:
        d = bytes(c.dat); seen[d] += 1; cnt = d[0] >> 4
        if last_cnt is not None: gaps[(cnt - last_cnt) % 16] += 1
        if last_t is not None: dts.append((m.logMonoTime - last_t) / 1e6)
        last_cnt = cnt; last_t = m.logMonoTime
  return seen, gaps, dts

def decode(msg, d):
  raw = int.from_bytes(d, "little"); out = {}
  for name, s in msg.sigs.items():
    assert s.is_little_endian, name
    v = (raw >> s.start_bit) & ((1 << s.size) - 1)
    if s.is_signed and v >> (s.size - 1): v -= 1 << s.size
    out[name] = v * s.factor + s.offset
  return out

if __name__ == "__main__":
  paths = []
  for r in sys.argv[1:]: paths += glob.glob(f"/data/media/0/realdata/{r}--*/rlog.zst")
  seen = collections.Counter(); gaps = collections.Counter(); dts = []
  with Pool(4) as p:
    for s, g, d in p.imap_unordered(seg, sorted(paths)):
      seen.update(s); gaps.update(g); dts += d
  dbc = DBC(DBC_NAME); msg = dbc.name_to_msg["SCC11"]; packer = CANPacker(DBC_NAME)
  bits = sorted((s.start_bit, s.size, n) for n, s in msg.sigs.items())
  cover = sum(sz for _, sz, _ in bits); overlap = any(a[0] + a[1] > b[0] for a, b in zip(bits, bits[1:]))
  print(f"segments {len(paths)}, SCC11 frames {sum(seen.values())}, distinct payloads {len(seen)}")
  print(f"DBC: {len(bits)} signals cover {cover} of {msg.size * 8} bits, overlap {overlap}")
  bad = 0; filt_changed = 0; filt_wrong = 0; with4 = 0; vals = collections.Counter()
  for d in seen:
    v = decode(msg, d); vals[int(v["SCCInfoDisplay"])] += seen[d]
    back = bytes(packer.make_can_msg("SCC11", 0, v)[1])
    if back != d:
      bad += 1
      if bad <= 3: print("  MISMATCH", d.hex(), "->", back.hex())
    f = dict(v)
    if int(f["SCCInfoDisplay"]) == 4:
      with4 += 1; f["SCCInfoDisplay"] = 0
    out = bytes(packer.make_can_msg("SCC11", 0, f)[1])
    if out != d:
      filt_changed += 1
      expect = bytes([d[0] & ~0x08]) + d[1:]
      if not (int(v["SCCInfoDisplay"]) == 4 and out == expect): filt_wrong += 1
  print(f"round-trip mismatches: {bad} of {len(seen)} distinct payloads")
  print(f"SCCInfoDisplay values (frames): {dict(vals)}")
  print(f"filter: {with4} distinct payloads carry 4; {filt_changed} payloads changed; changed in any other way than byte 0 bit 3: {filt_wrong}")
  import statistics
  print(f"camera counter step between frames: {dict(gaps)}")
  dts.sort(); n = len(dts)
  print(f"camera frame spacing as logged (ms): median {statistics.median(dts):.1f}, p1 {dts[n//100]:.1f}, p99 {dts[n*99//100]:.1f}, max {dts[-1]:.1f}; gaps > 60 ms: {sum(1 for x in dts if x > 60)}")
