"""How the car handled slowdowns at each following setting, the set speed against the cluster, and stops. PC.

  CEREAL_DIR=... CAR_CAPNP_DIR=... python gap_safety.py <recordings root>

Following = openpilot longitudinal active, no gas, lead present, above 34 mph. Edit GROUPS for new drives."""
import sys, glob, re, os
import numpy as np
import pclog

ROOT = sys.argv[1]
GROUPS = (("0.75 s (dc, dd, de)", ["000000dc", "000000dd", "000000de"]), ("0.99 s (da, db)", ["000000da", "000000db"]), ("1.05 s (d6)", ["000000d6"]))

def seg_no(p): return int(re.split(r"--", os.path.basename(os.path.dirname(p)))[-1])

def rows(routes):
    R = []
    for r in routes:
        ps = sorted(glob.glob(os.path.join(ROOT, "**", r + "--*", "rlog.zst"), recursive=True), key=seg_no)
        v = a = vc = vcrc = at = acc = 0.0; gas = brk = la = ss = stand = False; bars = 0
        for p in ps:
            for m in pclog.read(p):
                w = m.which()
                if w == "carState": c = m.carState; v, a, gas, brk, vc, vcrc, stand = c.vEgo, c.aEgo, c.gasPressed, c.brakePressed, c.vEgoCluster, c.vCruiseCluster, c.standstill
                elif w == "carControl": c = m.carControl; la, bars, acc = c.longActive, c.hudControl.leadDistanceBars, c.actuators.accel
                elif w == "longitudinalPlan": at = m.longitudinalPlan.aTarget; ss = m.longitudinalPlan.shouldStop
                elif w == "radarState":
                    l = m.radarState.leadOne
                    R.append((m.logMonoTime * 1e-9, v, a, gas, brk, la, bars, l.present, l.dRel, l.vRel, at, acc, vc, vcrc / 3.6, ss, stand))
    return np.array(R, float)

def runs(m, n):
    idx = np.flatnonzero(np.diff(np.r_[0, m.astype(int), 0])); return [(a, b) for a, b in zip(idx[::2], idx[1::2]) if b - a >= n]

for name, rs in GROUPS:
    X = rows(rs)
    if not len(X): print(f"\n{name}: no logs"); continue
    t, v, a, gas, brk, la, bars, lead, d, vr, at, acc, vc, vsetc, ss, stand = X.T
    f = (la > 0.5) & (gas < 0.5) & (lead > 0.5) & (v > 15)
    tg = d[f] / v[f]; closing = f & (vr < -1.0); ttc = d[closing] / -vr[closing]
    print(f"\n{name}: following above 34 mph for {f.sum() / 1200:.1f} min")
    print(f"   time gap s: p1 {np.percentile(tg, 1):.2f}  p5 {np.percentile(tg, 5):.2f}  median {np.median(tg):.2f} | shortest distance {d[f].min():.1f} m | "
          f"time to collision while closing: p1 {np.percentile(ttc, 1) if len(ttc) else float('nan'):.1f} s, min {ttc.min() if len(ttc) else float('nan'):.1f} s")
    print(f"   braking command: p1 {np.percentile(acc[f], 1):+.2f}, strongest {acc[f].min():+.2f} m/s2 | strongest measured {a[f].min():+.2f} | time under a 0.8 s gap {100 * np.mean(tg < 0.8):.1f} %, under 0.6 s {100 * np.mean(tg < 0.6):.2f} %")
    for i, j in runs(f & (acc < -1.5), 10)[:10]:
        k = slice(max(i - 40, 0), j + 40)
        print(f"      braking event {(j - i) / 20:.1f} s: {v[i] * 2.237:.0f} -> {v[j - 1] * 2.237:.0f} mph, closing at {-vr[i] * 2.237:.0f} mph at the start, smallest gap {np.min(d[k] / np.maximum(v[k], 1)):.2f} s / {d[k].min():.0f} m, strongest command {acc[i:j].min():+.2f}")
    s = (la > 0.5) & (gas < 0.5) & (v > 20) & (np.abs(a) < 0.15) & (np.abs(at) < 0.1) & ((lead < 0.5) | (d > 80)) & (vsetc > 1)
    if s.sum() > 100: print(f"   holding the set speed ({s.sum() / 20:.0f} s): cluster {np.median(vc[s]) * 2.237:.1f} mph, set {np.median(vsetc[s]) * 2.237:.1f} mph, cluster minus set {np.median(vc[s] - vsetc[s]) * 2.237:+.2f} mph")
    for i, j in runs((la > 0.5) & (stand > 0.5), 20):
        w = slice(max(i - 400, 0), i + 1); k = np.flatnonzero(ss[w] > 0.5)
        print(f"   stop held {(j - i) / 20:.0f} s: lead {'yes, ' + format(d[i + 10], '.1f') + ' m ahead' if lead[i + 10] else 'none'}; stop first requested at {v[w][k[0]] * 2.237 if len(k) else float('nan'):.1f} mph")
