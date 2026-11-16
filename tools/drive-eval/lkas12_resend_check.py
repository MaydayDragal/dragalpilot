# runs on the comma (offroad): LKAS12 (0x53E) camera vs re-sent stream over one route
import sys, glob, re
from multiprocessing import Pool
from collections import Counter
from openpilot.tools.lib.logreader import LogReader
def seg(path):
    n = Counter(); last = {}; ch = []; t0 = None; tx_t = []; mism = 0; cmpn = 0; panda = []
    for m in LogReader(path):
        w = m.which()
        if t0 is None and w == "carState": t0 = m.logMonoTime
        if w == "pandaStates":
            p = m.pandaStates[0]; panda.append((str(p.safetyModel), p.safetyTxBlocked, p.safetyRxInvalid, bool(getattr(p, "relayMalfunction", False)) if hasattr(p, "relayMalfunction") else None, str(p.faultStatus)))
        elif w in ("can", "sendcan"):
            for x in (m.can if w == "can" else m.sendcan):
                if x.address != 0x53E: continue
                src = ("send%d" % x.src) if w == "sendcan" else x.src
                d = bytes(x.dat); n[src] += 1
                if last.get(src) != d: ch.append((m.logMonoTime, src, d.hex())); last[src] = d
                if src == 128:
                    tx_t.append(m.logMonoTime); cmpn += 1
                    c = last.get(2)
                    if c is not None and c != d: mism += 1
    gaps = [(b - a) / 1e6 for a, b in zip(tx_t, tx_t[1:])]
    return int(re.search(r"--(\d+)/rlog", path).group(1)), t0, dict(n), ch, (max(gaps) if gaps else None, sum(gaps) / len(gaps) if gaps else None), mism, cmpn, panda[-1] if panda else None
if __name__ == "__main__":
    paths = sorted(glob.glob(f"/data/media/0/realdata/{sys.argv[1]}--*/rlog.zst"), key=lambda p: int(re.search(r"--(\d+)/rlog", p).group(1)))
    with Pool(4) as p: res = sorted(p.map(seg, paths))
    T0 = res[0][1]; tot = Counter(); mm = 0; cn = 0
    for r in res: tot.update(r[2]); mm += r[5]; cn += r[6]
    print("frames by source:", dict(tot)); print("re-sent frames differing from camera's latest:", mm, "of", cn)
    print("max / mean gap of re-sent stream (ms) per segment:", [(r[0], round(r[4][0] or 0), round(r[4][1] or 0)) for r in res][:40])
    print("panda last state per segment (model, txBlocked, rxInvalid, relayMalf, fault):", sorted(set(r[7] for r in res if r[7])))
    print("changes (t, src, payload, daw):")
    for r in res:
        for t, src, h in r[3]:
            d = bytes.fromhex(h)
            if src in (2, 128, 0): print(f"  {(t - T0) / 1e9:8.1f} {str(src):>4} {h} daw={d[5] & 7} warn={(d[5] >> 3) & 31}")
