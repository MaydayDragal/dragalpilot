import sys, numpy as np
sys.path.insert(0, sys.argv[1]); from lib import load
R = {}
for D in sys.argv[2:]: R.update(load(D))
for r in sorted(R):
    d = R[r]; ts = sorted(t for t, e in d["events"] if e == "espDisabled")
    if not ts: continue
    grp = [[ts[0]]]
    for t in ts[1:]:
        (grp[-1].append(t) if t - grp[-1][-1] < 3 else grp.append([t]))
    out = []
    for g in grp:
        i = np.searchsorted(d["t"], g[0]); j = np.searchsorted(d["t"], g[-1])
        out.append(f"t={g[0]:.0f}s n={len(g)} {d['v'][i]*2.237:.0f}mph act={int(d['latActive'][i])}->{int(d['latActive'][min(j+100,len(d['t'])-1)])} angle={d['ang'][i]:.0f} blink={int(d['blink'][i])}")
    print(r, " | ".join(out))
