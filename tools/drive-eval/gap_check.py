"""Measured following distance per gap setting, against what the planner's setting should give. Runs on the PC.

  CEREAL_DIR=... CAR_CAPNP_DIR=... python gap_check.py <recordings root>

Steady following = openpilot longitudinal active, no gas, lead present, above 45 mph, closing speed within 1 m/s,
|acceleration| < 0.3 m/s2, for at least 3 s. Expected distance = following time x speed + 6 m + extra lead distance
(the solver's desired distance at equal speeds). "implied time" = (distance - 6 - extra) / speed.
Edit SETUPS when the settings change: routes, following times by bars shown (1-4), extra lead distance."""
import sys, glob, re, os, collections
import numpy as np
import pclog

SETUPS = [
    ("d5: stock times, no extra", ["000000d5"], {1: 1.25, 2: 1.45, 3: 1.75}, 0.0),
    ("d6: 1.05 / 1.25 / 1.45 / 1.75, +2 m", ["000000d6"], {1: 1.05, 2: 1.25, 3: 1.45, 4: 1.75}, 2.0),
    ("da, db: 0.99 / 1.25 / 1.45 / 1.75, +2 m", ["000000da", "000000db"], {1: 0.99, 2: 1.25, 3: 1.45, 4: 1.75}, 2.0),
    ("dc on: 0.75 / 1.25 / 1.45 / 1.75, +2 m", ["000000dc", "000000dd", "000000de", "000000df"], {1: 0.75, 2: 1.25, 3: 1.45, 4: 1.75}, 2.0),
]
ROOT = sys.argv[1]

def route_rows(route):
    paths = glob.glob(os.path.join(ROOT, "**", route + "--*", "rlog.zst"), recursive=True)
    paths.sort(key=lambda p: int(re.search(r"--(\d+)[\\/]rlog", p).group(1)))
    rows = []; v = a = 0.0; gas = False; bars = 0; la = False; src = ""; atgt = 0.0
    for p in paths:
        for m in pclog.read(p):
            w = m.which()
            if w == "carState": c = m.carState; v, a, gas = c.vEgo, c.aEgo, c.gasPressed
            elif w == "carControl": c = m.carControl; la, bars = c.longActive, c.hudControl.leadDistanceBars
            elif w == "longitudinalPlan": src, atgt = str(m.longitudinalPlan.longitudinalPlanSource), m.longitudinalPlan.aTarget
            elif w == "radarState":
                l = m.radarState.leadOne
                rows.append((m.logMonoTime * 1e-9, v, a, gas, la, bars, l.present, l.dRel, l.vRel, src == "e2e", atgt))
    return np.array(rows, dtype=float) if rows else np.zeros((0, 11)), len(paths)

def runs(m, n):
    idx = np.flatnonzero(np.diff(np.r_[0, m.astype(int), 0])); return [(a, b) for a, b in zip(idx[::2], idx[1::2]) if b - a >= n]

print("setup / bars   minutes  speed mph  distance m (p10 / median / p90)  time gap s  | setting s  expected m  implied time s  | plan held by the model, %")
for name, routes, times, extra in SETUPS:
    R = []; nseg = 0
    for r in routes:
        x, n = route_rows(r); nseg += n
        if len(x): R.append(x)
    if not R: print(f"{name}: no logs on this PC"); continue
    X = np.vstack(R); hz = 20.0
    steady = (X[:, 4] > 0.5) & (X[:, 3] < 0.5) & (X[:, 6] > 0.5) & (X[:, 1] > 20) & (np.abs(X[:, 8]) < 1.0) & (np.abs(X[:, 2]) < 0.3)
    keep = np.zeros(len(X), bool)
    for a, b in runs(steady, int(3 * hz)): keep[a + int(hz):b] = True          # drop the first second of each stretch
    print(f"{name}  ({nseg} segments, {keep.sum() / hz / 60:.1f} min of steady following)")
    for bars in sorted(times):
        m = keep & (X[:, 5] == bars)
        if m.sum() < hz * 20: print(f"   {bars} bar{'s' if bars > 1 else ' '}     {m.sum() / hz / 60:5.1f}   too little"); continue
        v, d = X[m, 1], X[m, 7]; t = times[bars]
        print(f"   {bars} bar{'s' if bars > 1 else ' '}     {m.sum() / hz / 60:5.1f}   {np.median(v) * 2.237:7.0f}    {np.percentile(d, 10):5.1f} / {np.median(d):5.1f} / {np.percentile(d, 90):5.1f}            {np.median(d / v):5.2f}     |   {t:.2f}      {t * np.median(v) + 6 + extra:6.1f}        {np.median((d - 6 - extra) / v):5.2f}        |   {100 * X[m, 9].mean():3.0f}")
