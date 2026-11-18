"""Tracking, lane/wheel motion and curve events with a request that means the same for V0 and V1.

  python compare_req.py <scripts dir> <dir> [<dir> ...]

V1 (TorqueControlTune 1.0) logs the delayed setpoint as desiredLateralAccel, V0 the future request, so the error,
gain and lag from compare.py are not comparable between them. Here the request is controlsState.desiredCurvature
times v squared for every route (on V0 this equals the logged setpoint). Edit CFG for the routes to show; routes
that are not loaded are skipped.
"""
import sys, numpy as np
sys.path.insert(0, sys.argv[1]); from lib import load
R = {}
for D in sys.argv[2:]: R.update(load(D))
CFG = {"000000b5": "V0 4.5/.05 r.20 +.12", "000000bc": "V0 4.2/.07 r.28 +.15", "000000bd": "V0 4.2/.07 r.28 +.12", "000000be": "V0 4.2/.07 r.35 +.12",
       "000000bf": "V0 4.5/.07 r.28 +.12", "000000c0": "V1 4.5/.07 r.28 +.135", "000000c1": "V1 4.5/.07 r.28 +.135",
       "000000c2": "V1 4.5/.07 r.24 +.135", "000000c3": "V1 4.5/.07 r.24 +.135", "000000c4": "V1 r.24 fix.33 sm.2", "000000c5": "V1 fix.33 sm.2@25-45"}
CFG = {r: c for r, c in CFG.items() if r in R}
def runs(m, minlen):
    idx = np.flatnonzero(np.diff(np.r_[0, m.astype(int), 0])); return [(a, b) for a, b in zip(idx[::2], idx[1::2]) if b - a >= minlen]
def band(x, lo, hi):
    X = np.fft.rfft(x - x.mean()); f = np.fft.rfftfreq(len(x), 0.01); k = (f >= lo) & (f <= hi)
    return np.sqrt(2 * (np.abs(X[k]) ** 2).sum()) / len(x)
def lag(des, act):
    des = des - des.mean(); act = act - act.mean()
    return max(range(0, 80), key=lambda k: np.dot(des[:len(des)-k], act[k:])) / 100
print("request = desiredCurvature x v^2")
print("route    config                band    secs  rms(req-act)  lag(s)  wheel.2-.7  wheel.7-4  lane.2-.7  req.2-.7  maxTq")
for r in CFG:
    d = R[r]; req = d["dcurv"] * d["v"]**2; act = d["actualLateralAccel"]; lanec = (d["ll"] + d["rl"]) / 2
    ok = d["latActive"] & ~d["pressed"] & ~d["blink"] & (np.abs(d["drv"]) < 80)
    for name, lo, hi in (("35-60", 15.6, 26.8), (">60", 26.8, 99)):
        rr = runs(ok & (d["v"] >= lo) & (d["v"] < hi), 800)
        if not rr: continue
        rr = [(a + 100, b - 100) for a, b in rr]; w = [b - a for a, b in rr]; n = sum(w)
        cat = lambda x: np.concatenate([x[a:b] for a, b in rr]); av = lambda fn: np.average([fn(a, b) for a, b in rr], weights=w)
        print(f"{r} {CFG[r]:21s} {name:5s} {n/100:6.0f}  {np.sqrt((cat(req-act)**2).mean()):10.3f}  {av(lambda a,b: lag(req[a:b], act[a:b])):6.2f}  {av(lambda a,b: band(d['ang'][a:b],.2,.7)):9.3f}  "
              f"{av(lambda a,b: band(d['ang'][a:b],.7,4)):9.3f}  {av(lambda a,b: band(lanec[a:b],.2,.7)):9.4f}  {av(lambda a,b: band(req[a:b],.2,.7)):8.4f}  {np.abs(cat(d['out'])).max():5.2f}")
print("\ncurve events (|request| peak >= 1.0 m/s2, hands off, >35 mph): medians per config")
print("config                  n  peakReq  shortfall  short/peak  overshoot  over/peak  laneSwing(m)  peakTq")
ev = {}
for r in CFG:
    d = R[r]; des = d["dcurv"] * d["v"]**2; act = d["actualLateralAccel"]; lanec = (d["ll"] + d["rl"]) / 2
    ok = d["latActive"] & ~d["pressed"] & ~d["blink"] & (d["v"] > 15.6)
    for a, b in runs(ok & (np.abs(des) > 0.6), 150):
        a0, b0 = max(a - 200, 0), min(b + 200, len(des))
        if not ok[a0:b0].all(): continue
        pk = np.abs(des[a:b]).max()
        if pk < 1.0: continue
        s = np.sign(des[a:b][np.argmax(np.abs(des[a:b]))]); err = s * (des[a0:b0] - act[a0:b0])
        ev.setdefault(CFG[r], []).append((pk, err.max(), err.max() / pk, -err.min(), -err.min() / pk, np.ptp(lanec[a0:b0]), np.abs(d["out"][a0:b0]).max()))
for c, e in ev.items():
    m = np.median(np.array(e), axis=0)
    print(f"{c:21s} {len(e):3d}  {m[0]:6.2f}  {m[1]:9.2f}  {m[2]:9.2f}  {m[3]:9.2f}  {m[4]:9.2f}  {m[5]:10.2f}  {m[6]:7.2f}")
