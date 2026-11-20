"""Does the car move in its lane more when it follows closer? PC.

  python sway_vs_lead.py <lateral extract dir> <long extract dir> <route> ...

Above 60 mph, steering active, hands off, no blinker, both lane lines seen. The lane-centre offset is band-passed
0.2-0.7 Hz; its rms and the count of side-to-side swings of 15 cm or more are given per lead-distance group, per
route and for all routes together. Also split by the car's own acceleration (speed see-saw)."""
import sys, glob, os, pickle, re
import numpy as np

LAT, LON = sys.argv[1], sys.argv[2]
BINS = (("no lead", None), ("lead > 45 m", (45, 1e9)), ("lead 30-45 m", (30, 45)), ("lead < 30 m", (0, 30)))

def bandpass(x, fs, lo, hi):
    X = np.fft.rfft(x - x.mean()); f = np.fft.rfftfreq(len(x), 1 / fs); X[(f < lo) | (f > hi)] = 0; return np.fft.irfft(X, len(x))

def swings(y, thr):
    d = np.sign(np.diff(y)); tp = np.flatnonzero(np.diff(d) != 0) + 1
    return int(np.sum(np.abs(np.diff(y[tp])) >= thr)) if len(tp) > 1 else 0

TOT = {b[0]: [0.0, 0.0, 0] for b in BINS}; ACC = {"|a| < 0.3": [0.0, 0.0, 0], "|a| >= 0.3": [0.0, 0.0, 0]}
for r in sys.argv[3:]:
    out = {b[0]: [0.0, 0.0, 0] for b in BINS}
    for f in sorted(glob.glob(os.path.join(LAT, r + "--*.pkl")), key=lambda p: int(re.search(r"--(\d+)\.pkl", p).group(1))):
        g = os.path.join(LON, os.path.basename(f))
        if not os.path.exists(g): continue
        A = pickle.load(open(f, "rb")); L = pickle.load(open(g, "rb"))
        cs, cc, md, rs = A["cs"], A["cc"], A["model"], np.array(L["rs"], float)
        if len(md) < 400 or len(cs) < 100 or len(rs) < 100: continue
        t = md[:, 0]; fs = 20.0
        ok = ((np.interp(t, cc[:, 0], cc[:, 1]) > 0.5) & (np.interp(t, cs[:, 0], cs[:, 1]) > 26.8) & (np.interp(t, cs[:, 0], cs[:, 7]) < 0.5) &
              (np.interp(t, cs[:, 0], cs[:, 10]) < 0.5) & (md[:, 3] > 0.5) & (md[:, 4] > 0.5))
        pres = np.interp(t, rs[:, 0], rs[:, 1]) > 0.5; d = np.interp(t, rs[:, 0], rs[:, 2]); a = np.interp(t, cs[:, 0], cs[:, 2])
        off = (md[:, 1] + md[:, 2]) / 2
        idx = np.flatnonzero(np.diff(np.r_[0, ok.astype(int), 0]))
        for i, j in zip(idx[::2], idx[1::2]):
            if j - i < 12 * fs: continue
            y = bandpass(off[i:j], fs, 0.2, 0.7); sl = slice(i, j)
            for name, rng in BINS:
                m = ~pres[sl] if rng is None else (pres[sl] & (d[sl] >= rng[0]) & (d[sl] < rng[1]))
                if m.sum() < 5 * fs: continue
                n = swings(y[m], 0.15) if m.mean() > 0.9 else int(round(swings(y, 0.15) * m.mean()))
                for T in (out, TOT): T[name][0] += float(np.sum(y[m] ** 2)); T[name][1] += m.sum() / fs; T[name][2] += n
            for name, m in (("|a| < 0.3", np.abs(a[sl]) < 0.3), ("|a| >= 0.3", np.abs(a[sl]) >= 0.3)):
                ACC[name][0] += float(np.sum(y[m] ** 2)); ACC[name][1] += m.sum() / fs
    print(r[-2:], " | ".join(f"{k}: {v[1] / 60:4.1f} min {100 * np.sqrt(v[0] / max(v[1] * 20, 1)):4.2f} cm {v[2] / max(v[1] / 60, 1e-9):4.1f} big/min" if v[1] > 20 else f"{k}: -" for k, v in out.items()))
print("ALL", " | ".join(f"{k}: {v[1] / 60:4.1f} min {100 * np.sqrt(v[0] / max(v[1] * 20, 1)):4.2f} cm {v[2] / max(v[1] / 60, 1e-9):4.1f} big/min" for k, v in TOT.items()))
print("by own acceleration:", " | ".join(f"{k}: {v[1] / 60:4.1f} min {100 * np.sqrt(v[0] / max(v[1] * 20, 1)):4.2f} cm" for k, v in ACC.items()))
