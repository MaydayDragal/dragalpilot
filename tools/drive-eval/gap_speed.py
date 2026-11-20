"""Following distance against speed, per setup, from extract_long.py output (PC).

  python gap_speed.py <dir with extract_long .pkl files>

Steady following: cruise engaged, no pedals, lead present, closing speed within 1 m/s, |acceleration| < 0.3 m/s2,
held for 2 s. Median distance per 5 mph speed bin with at least 8 s of data. Stock = the car's own cruise on its
closest setting (camera TauGapSet 1). The openpilot groups were on gap setting 1 throughout their steady following
(gap_check.py). Expected = following time x speed + 6 m + extra lead distance."""
import sys, json
import numpy as np
import long_baseline as L

GROUPS = [  # label, routes, stock?, following time, extra
    ("stock cruise, closest setting", ["000000c4", "000000c5", "000000c8", "000000c9", "000000ca", "000000cb", "000000cd", "000000cf", "000000d1", "000000d2", "000000d3", "000000d4"], True, None, 0.0),
    ("openpilot 1.25 s", ["000000d5"], False, 1.25, 0.0),
    ("openpilot 1.05 s + 2 m", ["000000d6"], False, 1.05, 2.0),
    ("openpilot 0.99 s + 2 m", ["000000da", "000000db"], False, 0.99, 2.0),
    ("openpilot 0.75 s + 2 m", ["000000dc", "000000dd", "000000de"], False, 0.75, 2.0),
    ("openpilot 0.69 s + 2 m", ["000000df", "000000e0"], False, 0.69, 2.0),
]
BINS = np.arange(20, 90, 5)
out = {"bins": [int(b) for b in BINS[:-1]], "groups": []}
print("median distance to the lead, m, by speed bin (mph); blank = under 8 s of steady following")
print("setup".ljust(34) + "".join(f"{b:>6d}" for b in BINS[:-1]) + "   total min")
for label, routes, stock, tf, extra in GROUPS:
    R = L.load(sys.argv[1], routes)
    if not R: print(label.ljust(34) + "  no data"); continue
    v = np.concatenate([d["v"] for d in R.values()]); a = np.concatenate([d["a"] for d in R.values()]); dist = np.concatenate([d["d"] for d in R.values()])
    m = np.concatenate([d["en"] & ~d["gas"] & ~d["brake"] & d["lead"] & (np.abs(d["vrel"]) < 1.0) & (np.abs(d["a"]) < 0.3) & (d["v"] > 8) & ((d["gapset"] == 1) if stock else True) for d in R.values()])
    keep = np.zeros(len(m), bool)
    for i, j in L.runs(m, 40): keep[i + 20:j] = True
    mph = v * 2.237; row = []; secs = []
    for lo, hi in zip(BINS[:-1], BINS[1:]):
        k = keep & (mph >= lo) & (mph < hi); secs.append(k.sum() / 20)
        row.append(round(float(np.median(dist[k])), 1) if k.sum() >= 160 else None)
    print(label.ljust(34) + "".join(f"{x:6.1f}" if x is not None else "      " for x in row) + f"   {keep.sum() / 1200:6.1f}")
    fit = None
    if keep.sum() > 400:
        A = np.c_[v[keep], np.ones(keep.sum())]; s, c = np.linalg.lstsq(A, dist[keep], rcond=None)[0]; fit = (round(float(s), 2), round(float(c), 1))
        print(" " * 34 + f"   straight-line fit: distance = {s:.2f} s x speed + {c:.1f} m" + (f"   (setting: {tf:.2f} s x speed + {6 + extra:.0f} m)" if tf else ""))
    out["groups"].append(dict(label=label, median=row, secs=[round(x) for x in secs], time=tf, extra=extra, fit=fit))
print("\nJSON " + json.dumps(out, separators=(",", ":")))
