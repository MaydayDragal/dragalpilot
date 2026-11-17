# runs on the comma (offroad), read-only; pipe it in:  python - <route> [window_s] < bookmark_bits.py
# For a route with several bookmarks set just after the same thing appeared: lists CAN bits that change in the
# window before EVERY chosen bookmark and are otherwise quiet, and prints the history of SCC11.SCCInfoDisplay.
#   BOOKMARKS=1,3,4 selects which bookmarks (1-based) must all show the change; default all.
import sys, glob, os, re
from collections import defaultdict
from openpilot.tools.lib.logreader import LogReader

route = sys.argv[1]; WIN = float(sys.argv[2]) if len(sys.argv) > 2 else 12.0
CAP = 400  # stop tracking a bit after this many transitions (counters, checksums, live values)
paths = sorted(glob.glob(f"/data/media/0/realdata/{route}--*/rlog.zst"), key=lambda p: int(re.search(r"--(\d+)/rlog", p).group(1)))

# pass 1: bookmarks and route start (cheap: only look at the message type)
T0 = None; bms = []
for p in paths:
  for m in LogReader(p):
    w = m.which()
    if T0 is None and w == "carState": T0 = m.logMonoTime
    if w == "userBookmark": bms.append(m.logMonoTime)
print("bookmarks at", [round((b - T0) / 1e9, 1) for b in bms])
sel = [int(x) - 1 for x in os.environ.get("BOOKMARKS", ",".join(str(i + 1) for i in range(len(bms)))).split(",")]
use = [bms[i] for i in sel]
segs = sorted({int((b - T0) / 1e9 // 60) + d for b in use for d in (-1, 0)} & set(range(len(paths))))
print("using bookmarks", [i + 1 for i in sel], "scanning segments", segs)

tr = defaultdict(list); dead = set(); last = {}; cnt = defaultdict(int); info = []
for q in segs:
  for m in LogReader(paths[q]):
    if m.which() != "can": continue
    t = (m.logMonoTime - T0) / 1e9
    for c in m.can:
      if c.src >= 128: continue
      k = (c.src, c.address); d = bytes(c.dat); cnt[k] += 1; p = last.get(k)
      if c.address == 0x420 and len(d) >= 1:
        v = (d[0] >> 1) & 7
        if not info or info[-1][1:] != (c.src, v): info.append((t, c.src, v)) if (not [x for x in info if x[1] == c.src] or [x for x in info if x[1] == c.src][-1][2] != v) else None
      if p is not None and p != d and len(p) == len(d):
        for i in range(len(d)):
          x = p[i] ^ d[i]
          if x:
            for b in range(8):
              if x >> b & 1:
                kk = (c.src, c.address, i, b)
                if kk in dead: continue
                tr[kk].append((t, d[i] >> b & 1))
                if len(tr[kk]) > CAP: dead.add(kk); del tr[kk]
      last[k] = d

ub = [(b - T0) / 1e9 for b in use]
print(f"\nbits that change within {WIN:.0f} s before each selected bookmark (bus, addr, byte, bit: transitions as t->value; * = inside a window):")
rows = []
for k, v in tr.items():
  if all(any(b - WIN <= t <= b + 0.5 for t, _ in v) for b in ub):
    inside = sum(1 for t, _ in v if any(b - WIN <= t <= b + 0.5 for b in ub))
    rows.append((len(v) - inside, len(v), k, v))
for outside, n, k, v in sorted(rows)[:60]:
  s = ", ".join(f"{t:.1f}->{b}" + ("*" if any(x - WIN <= t <= x + 0.5 for x in ub) else "") for t, b in v[:24])
  print(f"  bus {k[0]} 0x{k[1]:03X} byte {k[2]} bit {k[3]} ({n} changes, {outside} outside, {cnt[(k[0], k[1])] / (60 * len(segs)):.0f} Hz): {s}{' ...' if len(v) > 24 else ''}")
print("\nSCC11 (0x420) SCCInfoDisplay = (byte0 >> 1) & 7, changes per bus:")
for t, src, v in info: print(f"  {t:8.1f}  bus {src}  SCCInfoDisplay {v}")
