# runs on the comma (offroad): sunnypilot speed-limit sources over one route
import sys, glob, re
from multiprocessing import Pool
from collections import Counter
from openpilot.tools.lib.logreader import LogReader
def seg(path):
    c = Counter(); ex = {}; car = 0.0
    for m in LogReader(path):
        w = m.which()
        if w == "carStateSP": car = round(m.carStateSP.speedLimit * 2.237)
        elif w == "liveMapDataSP":
            d = m.liveMapDataSP; ex.setdefault("map", str(d)[:400])
            c[("map", bool(getattr(d, "speedLimitValid", False)), round(getattr(d, "speedLimit", 0) * 2.237), car > 0)] += 1
        elif w == "longitudinalPlanSP":
            d = m.longitudinalPlanSP; ex.setdefault("plan", str(d)[:900])
    return c, ex
if __name__ == "__main__":
    paths = sorted(glob.glob(f"/data/media/0/realdata/{sys.argv[1]}--*/rlog.zst"))
    with Pool(4) as p: res = p.map(seg, paths)
    C = Counter(); ex = {}
    for c, e in res:
        C.update(c)
        for k, v in e.items(): ex.setdefault(k, v)
    print("liveMapDataSP seconds by (valid, map mph, car limit present):")
    for k, v in C.most_common(12): print("  ", v, k[1:])
    for k, v in ex.items(): print("==", k); print(v)
