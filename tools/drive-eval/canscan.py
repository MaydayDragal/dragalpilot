# runs on the comma (offroad). usage: canscan.py <route> ; scans 0x53E over the route and all bits near the bookmark
import sys, glob, os, re
from multiprocessing import Pool
from collections import defaultdict
from openpilot.tools.lib.logreader import LogReader
route = sys.argv[1]
def seg(path):
    n = int(re.search(r"--(\d+)/rlog", path).group(1)); out = []; bm = []; t0 = None; last = {}
    for m in LogReader(path):
        w = m.which()
        if t0 is None and w == "carState": t0 = m.logMonoTime
        if w == "userBookmark": bm.append(m.logMonoTime)
        elif w == "can":
            for c in m.can:
                if c.address in (0x53E, 0x420, 0x485, 0x484, 0x340) or True:
                    k = (c.src, c.address); d = bytes(c.dat)
                    if c.address == 0x53E and last.get(k) != d: out.append((m.logMonoTime, c.src, d.hex()))
                    last[k] = d
    return n, t0, bm, out
def full(path, tb):
    # per-bit transitions in the segment
    tr = defaultdict(list); last = {}; cnt = defaultdict(int)
    for m in LogReader(path):
        if m.which() != "can": continue
        for c in m.can:
            k = (c.src, c.address); d = bytes(c.dat); cnt[k] += 1; p = last.get(k)
            if p is not None and p != d and len(p) == len(d):
                for i in range(len(d)):
                    x = p[i] ^ d[i]
                    if x:
                        for b in range(8):
                            if x >> b & 1: tr[(c.src, c.address, i, b)].append(((m.logMonoTime - tb) / 1e9, d[i] >> b & 1))
            last[k] = d
    return tr, cnt
if __name__ == "__main__":
    paths = sorted(glob.glob(f"/data/media/0/realdata/{route}--*/rlog.zst"), key=lambda p: int(re.search(r"--(\d+)/rlog", p).group(1)))
    with Pool(4) as p: res = sorted(p.map(seg, paths))
    T0 = res[0][1]; bms = [b for r in res for b in r[2]]
    print("bookmarks at", [round((b - T0) / 1e9, 1) for b in bms])
    print("0x53E changes over the whole route (t, bus, data, DawStatus=byte5&7, Daw_USM=(byte4>>5)&7):")
    rows = [x for r in res for x in r[3]]; prev = {}
    for t, src, h in rows:
        d = bytes.fromhex(h); key = (src, d[5] & 7, (d[4] >> 5) & 7)
        if prev.get(src) != key[1:]:
            print(f"  {(t - T0) / 1e9:8.1f}  bus {src}  {h}  daw={d[5] & 7} usm={(d[4] >> 5) & 7}"); prev[src] = key[1:]
    print("  total distinct-data changes:", len(rows))
    if bms:
        tb = bms[0]; n = int((tb - T0) / 1e9 // 60)
        allt = defaultdict(list); cnt = defaultdict(int)
        for q in (n - 1, n):
            tr, c = full(paths[q], tb)
            for k, v in tr.items(): allt[k] += v
            for k, v in c.items(): cnt[k] += v
        print(f"\nbits with <=6 transitions in segs {n-1}-{n} and one in the 40 s before the bookmark (bus, addr, byte, bit: [t rel bookmark -> value]):")
        for k in sorted(allt):
            v = allt[k]
            if len(v) <= 6 and any(-40 <= t <= 2 for t, _ in v) and k[0] < 128:
                print(f"  bus {k[0]} 0x{k[1]:03X} byte {k[2]} bit {k[3]}: " + ", ".join(f"{t:+.1f}->{b}" for t, b in v))
