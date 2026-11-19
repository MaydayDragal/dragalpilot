"""Where the car sits in the lane through sustained curves, and how much of the request it delivers.

  python curve_position.py <scripts dir> <dir> [<dir> ...]

Curves: |desiredCurvature x v^2| > 0.8 m/s2 for 2.5 s or more, lat active, hands off, no blinker, both lane-line
probabilities > 0.5, > 35 mph, with 1 s of the same conditions before and after.
Signs (checked on route c1): model lane-line y is positive to the RIGHT (left line negative), and
controlsState.desiredCurvature is positive for a RIGHT curve (correlation with steeringAngleDeg is -0.93).
"Inside" = the car is on the inner side of the lane centre (the mean of the two lane lines at their first point).
Edit G for the routes to group; routes that are not loaded are skipped.
"""
import sys, numpy as np
sys.path.insert(0, sys.argv[1]); from lib import load
R = {}
for D in sys.argv[2:]: R.update(load(D))
G = {"V0 4.5/.05, delay ~0.30 (b5)": ["000000b5"], "V0 4.2, delay 0.31-0.34 (bc,bd,be)": ["000000bc", "000000bd", "000000be"],
     "V1 no smoothing, delay 0.35-0.37 (c0-c3)": ["000000c0", "000000c1", "000000c2", "000000c3"],
     "V1 smoothing, delay 0.33 fixed (c4-c7)": ["000000c4", "000000c5", "000000c6", "000000c7"],
     "V0 smoothing (c8,c9)": ["000000c8", "000000c9"], "V1 smoothing, controller delay 0.33 (ca-cc)": ["000000ca", "000000cb", "000000cc"]}
def runs(m, minlen):
    idx = np.flatnonzero(np.diff(np.r_[0, m.astype(int), 0])); return [(a, b) for a, b in zip(idx[::2], idx[1::2]) if b - a >= minlen]
print("offset toward the inside of the curve, m (+ = inside of lane centre); delivered = actual / requested lateral acceleration mid-curve")
print("group                                       n   entry (1 s before -> 1 s after)   middle   exit (last 1 s -> 1 s after)   swing p50   delivered   left of centre on straights")
for g, rs in G.items():
    ent = []; mid = []; ex = []; sw = []; dl = []; sb = []
    for r in rs:
        if r not in R: continue
        d = R[r]; req = d["dcurv"] * d["v"] ** 2; act = d["actualLateralAccel"]
        c_right = (d["ll"] + d["rl"]) / 2                     # lane centre relative to the car, + = right of the car
        base = d["latActive"] & ~d["pressed"] & ~d["blink"] & (d["v"] > 15.6) & (d["llp"] > 0.5) & (d["rlp"] > 0.5)
        st = base & (np.abs(req) < 0.25)
        if st.sum() > 500: sb.append(np.nanmean(c_right[st]))  # + = lane centre right of the car = car left of centre
        for a, b in runs(base & (np.abs(req) > 0.8), 250):
            if a < 150 or b + 150 > len(req) or not base[a - 100:b + 100].all(): continue
            s = np.sign(np.mean(req[a:b]))                    # + = right curve
            pos = -c_right * s                                # car offset toward the inside of the curve
            ent.append((np.mean(pos[a - 100:a]), np.mean(pos[a:a + 100]))); ex.append((np.mean(pos[b - 100:b]), np.mean(pos[b:b + 100])))
            m0, m1 = (a + 100, b - 100) if b - a > 300 else (a, b)
            mid.append(np.mean(pos[m0:m1])); sw.append(np.ptp(pos[a - 100:b + 100])); dl.append(np.mean(act[m0:m1]) / np.mean(req[m0:m1]))
    if ent:
        e = np.median(np.array(ent), axis=0); x = np.median(np.array(ex), axis=0)
        print(f"{g:42s} {len(ent):3d}      {e[0]:+.2f} -> {e[1]:+.2f}                  {np.median(mid):+.2f}       {x[0]:+.2f} -> {x[1]:+.2f}               {np.median(sw):.2f}       {np.median(dl):.2f}        {np.mean(sb) if sb else float('nan'):+.2f}")
