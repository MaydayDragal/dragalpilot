# runs on the comma (offroad): nav speed limit (0x544) vs camera LKAS12 (0x53E) joint statistics per route
import sys, glob, re
from multiprocessing import Pool
from collections import Counter
from openpilot.tools.lib.logreader import LogReader
def seg(path):
    last = {}; joint = Counter(); nbus = Counter(); navp = Counter()
    for m in LogReader(path):
        if m.which() != "can": continue
        for x in m.can:
            if x.address == 0x544:
                nbus[("544", x.src)] += 1; last[("544", x.src)] = bytes(x.dat)
                if x.src == 0: navp[bytes(x.dat).hex()] += 1
            elif x.address == 0x53E:
                nbus[("53e", x.src)] += 1; d = bytes(x.dat); last[("53e", x.src)] = d
                if x.src == 2:
                    nav = last.get(("544", 0)); tx = last.get(("53e", 128))
                    joint[(nav[0] if nav else -1, (nav[3] if nav else 0), d[0], d[1], d[2], d[3], d[6], d[7], (tx[2] if tx else -1))] += 1
    return dict(nbus), joint, navp
if __name__ == "__main__":
    for r in sys.argv[1:]:
        paths = sorted(glob.glob(f"/data/media/0/realdata/{r}--*/rlog.zst"))
        with Pool(4) as p: res = p.map(seg, paths)
        nb = Counter(); J = Counter(); NP = Counter()
        for a, b, c in res: nb.update(a); J.update(b); NP.update(c)
        print("###", r, "frames:", {f"{k[0]}@{k[1]}": v for k, v in sorted(nb.items(), key=str)})
        print("  nav payloads (bus 0):", NP.most_common(8))
        print("  seconds by (navSpeed, navByte3 | cam b0 b1 sign navfield b6 b7 | resent sign):")
        for k, v in J.most_common(14):
            print(f"   {v/10:7.0f}s  nav={k[0]:3d} nb3={k[1]:02x} | cam {k[2]:02x} {k[3]:02x} sign={k[4]:3d} navf={k[5]:3d} b6={k[6]:3d} b7={k[7]:02x} | resent sign={k[8]}")
