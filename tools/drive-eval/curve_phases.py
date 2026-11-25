"""Every curve split into entry, mid-turn and exit, from delay_extract.py files.

  python curve_phases.py <gyro_to_yaw.npy> "<group label>=<a.npz>,<b.npz>" ...

A curve: the request (desiredCurvature x v^2, 0.5 s average) stays above 0.5 m/s2 with one sign for 3 s or more, above
45 mph, steering active, hands off, no blinker, both lane lines seen, from 3 s before it to 3 s after.
  plateau  = median |request| over the middle half of the curve
  entry    = from the request passing 10 % of the plateau to passing 90 %; exit = the reverse on the way out
  mid      = between the two 90 % points
Per curve:
  timing   seconds by which the vehicle (yaw rate x speed) passes 50 % of the plateau after the request does
  delivery vehicle lateral acceleration / request, mid-turn (1.00 = holds exactly the requested curve)
  error    vehicle minus request, signed toward the turn (m/s2): negative = not turning enough yet
  position cm toward the inside of the turn, relative to where the car sits on straights of the same drive
  wheel    steering-wheel movement about its 1.5 s average, mid-turn (deg rms), and torque reversals per minute
  torque   largest |torque| in the curve, share of the limit given"""
import sys, numpy as np

def ma(x, n): return np.convolve(x, np.ones(n) / n, "same")
def runs(m, minlen):
    idx = np.flatnonzero(np.diff(np.r_[0, m.astype(int), 0])); return [(a, b) for a, b in zip(idx[::2], idx[1::2]) if b - a >= minlen]
def cross(x, level, i0, i1, rising):
    seg = x[i0:i1]; k = np.flatnonzero(seg >= level) if rising else np.flatnonzero(seg <= level)
    return i0 + k[0] if len(k) else None
def reversals(x, h):
    n = 0; st = 0; ext = x[0]
    for v in x:
        if st >= 0:
            if v > ext: ext = v
            elif ext - v > h: st = -1; ext = v; n += 1
        if st <= 0:
            if v < ext: ext = v
            elif v - ext > h: st = 1; ext = v; n += 1
    return n

C = np.load(sys.argv[1])
def curves(path, limit):
    d = dict(np.load(path)); v = d["v"]; req = d["req"] * v ** 2
    ok = (d["lat"] > 0.5) & (d["hands"] < 0.5) & (d["blink"] < 0.5) & (v > 20.1) & (d["llp"] > 0.5) & (d["rlp"] > 0.5) & np.isfinite(d["gx"])
    g = np.c_[d["gx"], d["gy"], d["gz"]] @ C
    still = ok & (np.abs(ma(req, 200)) < 0.1)
    g = g - np.median(g[still])                                    # gyro bias from straights
    act = g * v; act = act * np.sign(np.corrcoef(req[ok], act[ok])[0, 1]); act = ma(act, 30)
    rs = ma(req, 50); centre = (d["ll"] + d["rl"]) / 2
    ref = np.median(-centre[still]) * 100
    out = []
    for sgn in (1, -1):
        for a, b in runs(sgn * rs > 0.5, 300):
            lo, hi = a - 300, b + 300
            if lo < 0 or hi >= len(v) or not ok[lo:hi].all(): continue
            r = sgn * rs[lo:hi]; y = sgn * act[lo:hi]; n = b - a
            P = np.median(r[300 + n // 4: 300 + 3 * n // 4])
            e10, e50, e90 = (cross(r, f * P, 0, 300 + n // 2, True) for f in (0.1, 0.5, 0.9))
            x90, x50, x10 = (cross(r, f * P, 300 + n // 2, len(r), False) for f in (0.9, 0.5, 0.1))
            if None in (e10, e50, e90, x90, x50, x10) or x90 - e90 < 100: continue
            # the 10 % point: last time below it before the 50 % point (the request can wander before a curve)
            below = np.flatnonzero(r[:e50] < 0.1 * P); e10 = below[-1] + 1 if len(below) else e10
            ye = cross(y, 0.5 * P, max(e10 - 50, 0), min(e90 + 200, len(y)), True); yx = cross(y, 0.5 * P, x90, min(x10 + 200, len(y)), False)
            ins = (-centre[lo:hi] * 100 - ref) * sgn
            ang = d["ang"][lo:hi]; tq = d["tq"][lo:hi]
            mid = slice(e90, x90); ent = slice(e10, e90); ext = slice(x90, x10)
            if ent.stop - ent.start < 10 or ext.stop - ext.start < 10: continue
            err = y - r
            out.append(dict(v=v[lo:hi][mid].mean() * 2.237, P=P, dur=(x90 - e90) / 100, ent_dur=(e90 - e10) / 100, ext_dur=(x10 - x90) / 100,
                            lag_in=(ye - e50) / 100 if ye is not None else np.nan, lag_out=(yx - x50) / 100 if yx is not None else np.nan,
                            deliver=np.median(y[mid]) / np.median(r[mid]),
                            err_in=err[ent].mean(), err_mid=err[mid].mean(), err_out=err[ext].mean(),
                            ins_pre=ins[max(e10 - 150, 0):e10].mean(), ins_in=ins[ent].mean(), ins_mid=ins[mid].mean(), ins_out=ins[ext].mean(), ins_post=ins[x10:x10 + 150].mean(),
                            ins_in_min=ins[ent].min(), ins_mid_max=ins[mid].max(), ins_mid_min=ins[mid].min(), ins_mid_rng=ins[mid].max() - ins[mid].min(),
                            wheel=np.std((ang - ma(ang, 150))[mid][75:-75]) if x90 - e90 > 300 else np.nan,
                            trev=reversals(tq[mid], 13) / ((x90 - e90) / 6000), tmax=np.abs(tq).max() / limit, over=(y[mid].max() - P) / P))
    return out

def q(x, f="%.2f"):
    x = np.array([a for a in x if np.isfinite(a)])
    return "   --   " if len(x) < 3 else (f + " (" + f + " to " + f + ")") % (np.median(x), np.percentile(x, 25), np.percentile(x, 75))

for arg in sys.argv[2:]:
    label, files = arg.split("=", 1); limit = 270 if "270" in label else 384
    cs = [c for f in files.split(",") for c in curves(f, limit)]
    print(f"\n===== {label}: {len(cs)} curves")
    for name, sel in (("all", lambda c: True), ("gentle (plateau under 1.0 m/s2)", lambda c: c["P"] < 1.0), ("firm (1.0 m/s2 and up)", lambda c: c["P"] >= 1.0),
                      ("45-60 mph", lambda c: c["v"] < 60), ("above 60 mph", lambda c: c["v"] >= 60)):
        k = [c for c in cs if sel(c)]
        if len(k) < 4: print(f"  {name}: {len(k)} curves, too few"); continue
        G = lambda key, f="%.2f": q([c[key] for c in k], f)
        print(f"  {name}: {len(k)} curves, speed {np.median([c['v'] for c in k]):.0f} mph, plateau {G('P')} m/s2, mid-turn lasts {G('dur', '%.1f')} s")
        print(f"     entry   takes {G('ent_dur', '%.1f')} s | vehicle trails the request by {G('lag_in')} s | error {G('err_in', '%+.2f')} m/s2 | position {G('ins_in', '%+.0f')} cm inside (before: {G('ins_pre', '%+.0f')}) | widest point {G('ins_in_min', '%+.0f')}")
        print(f"     mid     delivers {G('deliver')} of the request | error {G('err_mid', '%+.3f')} | overshoot past plateau {G('over', '%+.2f')} | position {G('ins_mid', '%+.0f')} cm inside, range within the curve {G('ins_mid_rng', '%.0f')} cm | wheel {G('wheel', '%.3f')} deg rms | torque reversals {G('trev', '%.0f')} /min")
        print(f"     exit    takes {G('ext_dur', '%.1f')} s | vehicle trails the request by {G('lag_out')} s | error {G('err_out', '%+.2f')} | position {G('ins_out', '%+.0f')} cm inside (after: {G('ins_post', '%+.0f')}) | peak torque {G('tmax')} of the limit")
