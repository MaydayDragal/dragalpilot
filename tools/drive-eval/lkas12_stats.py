# runs on the comma (offroad): statistics of 0x53E (LKAS12) over routes
import sys, glob, re, pickle
from multiprocessing import Pool
from collections import Counter
from openpilot.tools.lib.logreader import LogReader
def seg(path):
    c = Counter(); n = Counter(); ts = []; seq = []
    last = None
    for m in LogReader(path):
        if m.which() != "can": continue
        for x in m.can:
            if x.address == 0x53E:
                n[x.src] += 1
                if x.src == 2:
                    d = bytes(x.dat); c[d] += 1; ts.append(x.busTime if False else m.logMonoTime)
                    if d != last: seq.append((m.logMonoTime, d.hex())); last = d
    dts = [(b - a) / 1e6 for a, b in zip(ts, ts[1:])]
    return path, dict(n), c, (sum(dts) / len(dts) if dts else 0, max(dts) if dts else 0), seq
if __name__ == "__main__":
    paths = []
    for r in sys.argv[1:]: paths += sorted(glob.glob(f"/data/media/0/realdata/{r}--*/rlog.zst"), key=lambda p: int(re.search(r"--(\d+)/rlog", p).group(1)))
    with Pool(4) as p: res = p.map(seg, paths)
    tot = Counter(); n = Counter(); seqs = {}
    for path, nn, c, dt, seq in res:
        tot.update(c); n.update(nn); seqs[path.split("/")[-2]] = seq
    print("frames by bus:", dict(n)); print("mean/max gap ms (first seg):", res[0][3], "len", {len(k) for k in tot})
    print("distinct payloads:", len(tot))
    for i in range(8):
        print(" byte", i, sorted((f"{v:02x}", cnt) for v, cnt in Counter({b: sum(c for d, c in tot.items() if d[i] == b) for b in {d[i] for d in tot}}).items()))
    print("payloads with daw==6 or bit44:", [(d.hex(), c) for d, c in tot.items() if (d[5] & 7) == 6 or d[5] & 0x10])
    pickle.dump(seqs, open("/data/tmp/ext/lkas12_seq.pkl", "wb"))
