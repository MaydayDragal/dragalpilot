import sys, pickle, glob, os, re, numpy as np
sys.path.insert(0, sys.argv[1]); from lib import load
R = {}; G = {}
for D in sys.argv[2:]:
    R.update(load(D))
    for f in glob.glob(os.path.join(D, "*.pkl")):
        r, n = re.match(r"(.*)--(\d+)\.pkl", os.path.basename(f)).groups()
        p = pickle.load(open(f, "rb"))
        if len(p["gps"]): G.setdefault(r[:8], []).append((int(n), p["gps"], p["cs"][0,0] if len(p["cs"]) else None))
CFG = {"000000a3":"5.0/.04 enf", "000000a4":"5.0/.04 enf+jerk", "000000a5":"5.0/.04 enf", "000000a6":"5.0/.04 enf", "000000a7":"4.0/.07 enf", "000000aa":"4.0/.07 enf+jerk", "000000ab":"4.0/.07 enf OFF", "000000ac":"4.5/.07 enf+jerk", "000000ad":"4.8/.07 enf+jerk", "000000ae":"4.8/.07 enf+jerk", "000000af":"4.8/.07 enf+jerk", "000000b0":"4.8/.07 enf+jerk", "000000b1":"4.8/.07 enf+jerk", "000000b4":"4.8/.07 enf+jerk"}
def runs(m, minlen):
    idx = np.flatnonzero(np.diff(np.r_[0, m.astype(int), 0])); return [(a, b) for a, b in zip(idx[::2], idx[1::2]) if b - a >= minlen]
def band(x, lo, hi):
    X = np.fft.rfft(x - x.mean()); f = np.fft.rfftfreq(len(x), 0.01); k = (f >= lo) & (f <= hi)
    return np.sqrt(2 * (np.abs(X[k]) ** 2).sum()) / len(x)
def lag(des, act):
    des = des - des.mean(); act = act - act.mean()
    return max(range(0, 80), key=lambda k: np.dot(des[:len(des)-k], act[k:])) / 100
print("route    config             band    secs  rms(des-act) mean|e|  lag  angW.2-.7  angT.7-4  laneW.2-.7  reqW.2-.7  tqRate  |I|   maxTq sat%")
for r in sorted(CFG):
    d = R[r]; e = d["desiredLateralAccel"] - d["actualLateralAccel"]
    ok = d["latActive"] & ~d["pressed"] & ~d["blink"] & (np.abs(d["drv"]) < 80)
    for name, lo, hi in (("35-60", 15.6, 26.8), (">60", 26.8, 99)):
        rr = runs(ok & (d["v"] >= lo) & (d["v"] < hi), 800)
        if not rr: continue
        rr = [(a + 100, b - 100) for a, b in rr]; w = [b - a for a, b in rr]; n = sum(w)
        cat = lambda x: np.concatenate([x[a:b] for a, b in rr]); av = lambda fn: np.average([fn(a, b) for a, b in rr], weights=w)
        lanec = (d["ll"] + d["rl"]) / 2
        print(f"{r} {CFG[r]:18s} {name:5s} {n/100:6.0f}  {np.sqrt((cat(e)**2).mean()):8.3f}   {np.abs(cat(e)).mean():6.3f} {av(lambda a,b: lag(d['desiredLateralAccel'][a:b], d['actualLateralAccel'][a:b])):5.2f}  {av(lambda a,b: band(d['ang'][a:b],.2,.7)):8.3f}  {av(lambda a,b: band(d['ang'][a:b],.7,4)):8.3f}  {av(lambda a,b: band(lanec[a:b],.2,.7)):9.4f}  {av(lambda a,b: band(d['desiredLateralAccel'][a:b],.2,.7)):9.4f}  {np.sqrt((np.diff(cat(d['out']))**2).mean())*100:6.3f} {np.abs(cat(d['i'])).mean():5.3f}  {np.abs(cat(d['out'])).max():5.2f} {cat(d['saturated']).mean()*100:4.1f}")
# curves: events where |desLA| peaks > 1.0, hands off
print("\ncurve events (|desired LA| peak >= 1.0 m/s2, hands off, >35 mph): per route medians")
print("route    config              n   peakDes  worstUnder  under/peak  overshoot  laneSwing(m)  peakTq")
for r in sorted(CFG):
    d = R[r]; des = d["desiredLateralAccel"]; act = d["actualLateralAccel"]; lanec = (d["ll"] + d["rl"]) / 2
    ok = d["latActive"] & ~d["pressed"] & ~d["blink"] & (d["v"] > 15.6)
    ev = []
    for a, b in runs(ok & (np.abs(des) > 0.6), 150):
        a0, b0 = max(a - 200, 0), min(b + 200, len(des))
        if not ok[a0:b0].all(): continue
        pk = np.abs(des[a:b]).max()
        if pk < 1.0: continue
        s = np.sign(des[a:b][np.argmax(np.abs(des[a:b]))]); err = s * (des[a0:b0] - act[a0:b0])
        ev.append((pk, err.max(), err.max() / pk, -err.min(), np.ptp(lanec[a0:b0]), np.abs(d["out"][a0:b0]).max()))
    if ev:
        m = np.median(np.array(ev), axis=0)
        print(f"{r} {CFG[r]:18s} {len(ev):3d}   {m[0]:6.2f}   {m[1]:8.2f}   {m[2]:8.2f}   {m[3]:8.2f}   {m[4]:10.2f}   {m[5]:6.2f}")
# same place as the a5 bookmark turn
def gps_at(r):
    rows = []
    for n, g, t0 in sorted(G.get(r, []), key=lambda x: x[0]): rows.append(g)
    return np.vstack(rows) if rows else None
ga = gps_at("000000a5"); t0a = min(x[2] for x in G["000000a5"] if x[0] == 0) if any(x[0]==0 for x in G["000000a5"]) else None
segs0 = {r: min(x[1][0,0] for x in G[r]) for r in G}
def route_t0(r, D=None): return None
import bisect
# route start mono time = first carState time; recompute from R? lib subtracts cs[0,0]; re-read
T0 = {}
for D in sys.argv[2:]:
    for f in glob.glob(os.path.join(D, "*--0.pkl")):
        r = os.path.basename(f)[:8]; T0[r] = pickle.load(open(f, "rb"))["cs"][0,0]
i = np.argmin(np.abs(ga[:,0] - (T0["000000a5"] + 302.0))); lat0, lon0, brg0 = ga[i,1], ga[i,2], ga[i,4]
print(f"\npasses through the 11-12 bookmarked turn (within 40 m, same heading):")
print("route    config              t(s)  mph   peakDes  worstUnder  overshoot  laneMin  laneMax  peakTq  drvMax")
for r in sorted(CFG):
    g = gps_at(r)
    if g is None: continue
    dist = np.hypot((g[:,1] - lat0) * 111320, (g[:,2] - lon0) * 111320 * np.cos(np.radians(lat0)))
    dh = np.abs((g[:,4] - brg0 + 180) % 360 - 180)
    near = (dist < 40) & (dh < 30)
    for a, b in runs(near, 1):
        j = a + np.argmin(dist[a:b]); tc = g[j,0] - T0[r]; d = R[r]
        k = (d["t"] > tc - 5) & (d["t"] < tc + 7)
        if k.sum() < 100: continue
        des, act = d["desiredLateralAccel"][k], d["actualLateralAccel"][k]; s = np.sign(des[np.argmax(np.abs(des))]); err = s * (des - act); lc = ((d["ll"] + d["rl"]) / 2)[k]
        print(f"{r} {CFG[r]:18s} {tc:6.0f} {d['v'][k].mean()*2.237:4.0f}   {np.abs(des).max():6.2f}   {err.max():8.2f}   {-err.min():8.2f}   {lc.min():6.2f}   {lc.max():6.2f}  {np.abs(d['out'][k]).max():6.2f}  {np.abs(d['drv'][k]).max():5.0f}  active {d['latActive'][k].mean()*100:.0f}%")
