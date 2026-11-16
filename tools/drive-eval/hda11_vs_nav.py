# runs on the comma (offroad): camera HDA11_MFC (0x484) and Sign_Detection (0x4EC) content vs nav speed limit (0x544) and LKAS12 sign
import sys, glob
from multiprocessing import Pool
from collections import Counter
from openpilot.tools.lib.logreader import LogReader
def seg(path):
    last = {}; nb = Counter(); J = Counter(); P = Counter()
    for m in LogReader(path):
        if m.which() != "can": continue
        for x in m.can:
            a = x.address
            if a in (0x484, 0x4EC, 0x544, 0x53E, 0x485):
                nb[(hex(a), x.src)] += 1; d = bytes(x.dat); last[(a, x.src)] = d
                if a == 0x484 and x.src == 2:
                    nav = last.get((0x544, 0)); cam = last.get((0x53E, 2))
                    P[d.hex()] += 1
                    J[(nav[0] if nav else -1, cam[2] if cam else -1, cam[0] if cam else -1, d.hex())] += 1
    return dict(nb), J, P
if __name__ == "__main__":
    for r in sys.argv[1:]:
        with Pool(4) as p: res = p.map(seg, sorted(glob.glob(f"/data/media/0/realdata/{r}--*/rlog.zst")))
        nb = Counter(); J = Counter(); P = Counter()
        for a, b, c in res: nb.update(a); J.update(b); P.update(c)
        print("###", r, {f"{k[0]}@{k[1]}": v for k, v in sorted(nb.items(), key=str)})
        print("  distinct 0x484 payloads:", len(P))
        for k, v in J.most_common(22): print(f"   {v/ (sum(P.values())/ (len(res)*60.0)):6.0f}s nav={k[0]:3d} camSign={k[1]:3d} camB0={k[2]:02x} hda={k[3]}")
