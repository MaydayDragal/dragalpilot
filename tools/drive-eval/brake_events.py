"""Every substantial braking event with openpilot longitudinal, from the long extracts. PC.

  python brake_events.py <long extract dir> <out.json> <route> ...

An event = measured deceleration of 1.5 m/s2 or more held 0.5 s, or a slowdown to a standstill from above 15 mph,
with openpilot longitudinal active. Each is cut from 5 s before braking begins (-0.5 m/s2) to 2 s after it ends,
at 4 Hz: speed, lead speed, gap, time gap, commanded and measured acceleration, plan source."""
import sys, glob, os, pickle, re, json
import numpy as np
D, OUT = sys.argv[1], sys.argv[2]; EV = []
for r in sys.argv[3:]:
    cs = []; cc = []; rs = []; lp = []
    for f in sorted(glob.glob(os.path.join(D, r + "--*.pkl")), key=lambda p: int(re.search(r"--(\d+)\.pkl", p).group(1))):
        L = pickle.load(open(f, "rb"))
        for k, a in (("cs", cs), ("cc", cc), ("rs", rs), ("lp", lp)):
            x = np.array(L[k], float)
            if len(x): a.append(x)
    cs, cc, rs, lp = [np.vstack(a) for a in (cs, cc, rs, lp)]
    t = cs[:, 0]; v = cs[:, 1]; a = cs[:, 2]; hz = 20
    la = np.interp(t, cc[:, 0], cc[:, 2]) > 0.5; cmd = np.interp(t, cc[:, 0], cc[:, 4])
    pres = np.interp(t, rs[:, 0], rs[:, 1]) > 0.5; d = np.interp(t, rs[:, 0], rs[:, 2]); vl = np.interp(t, rs[:, 0], rs[:, 4]); at = np.interp(t, lp[:, 0], lp[:, 1])
    brk = la & (a < -0.5); idx = np.flatnonzero(np.diff(np.r_[0, brk.astype(int), 0])); runs = list(zip(idx[::2], idx[1::2]))
    merged = []
    for i, j in runs:                                    # join braking stretches less than 2 s apart
        if merged and i - merged[-1][1] < 2 * hz: merged[-1][1] = j
        else: merged.append([i, j])
    for i, j in merged:
        seg = slice(i, j); hard = np.convolve((a[seg] < -1.5).astype(int), np.ones(10), "same").max() >= 10 if j - i >= 10 else False
        tostop = v[i] > 6.7 and v[j - 1] < 0.5
        if not (hard or tostop): continue
        k0 = max(i - 5 * hz, 0); k1 = min(j + 2 * hz, len(t)); w = np.arange(k0, k1, 5); jm = i + int(np.argmin(a[seg]))
        g = lambda x, n=1: [None if not np.isfinite(y) else round(float(y), n) for y in x]
        EV.append(dict(route=r[-2:], t=round(float(t[i] - t[0])), v0=round(float(v[i] * 2.237)), v1=round(float(v[j - 1] * 2.237)), dur=round((j - i) / hz, 1),
                       amin=round(float(a[seg].min()), 2), cmin=round(float(cmd[seg].min()), 2), v_at=round(float(v[jm] * 2.237)), gap_at=round(float(d[jm]), 1) if pres[jm] else None,
                       lead_at=round(float(vl[jm] * 2.237)) if pres[jm] else None, gap_min=round(float(d[seg][pres[seg]].min()), 1) if pres[seg].any() else None,
                       tg_min=round(float((d[seg] / np.maximum(v[seg], 2))[pres[seg]].min()), 2) if pres[seg].any() else None, gap0=round(float(d[i]), 1) if pres[i] else None,
                       lead0=round(float(vl[i] * 2.237)) if pres[i] else None,
                       x=g(t[w] - t[i]), v=g(v[w] * 2.237), vl=g(np.where(pres[w], vl[w] * 2.237, np.nan)), d=g(np.where(pres[w], d[w], np.nan)), a=g(a[w], 2), cmd=g(np.where(la[w], cmd[w], np.nan), 2)))
json.dump(EV, open(OUT, "w"))
for e in EV: print({k: e[k] for k in ("route", "t", "v0", "v1", "dur", "amin", "cmin", "v_at", "gap_at", "lead_at", "gap0", "lead0", "gap_min", "tg_min")})
print(len(EV), "events", os.path.getsize(OUT), "bytes")
