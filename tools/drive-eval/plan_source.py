"""Which part of the planner asked for each braking event: the lead plan, the cruise plan or the driving model. PC.

  CEREAL_DIR=... CAR_CAPNP_DIR=... python plan_source.py <recordings root> <route>

Prints the share of time each source holds the plan, overall and while braking, and for every braking stretch
(request below -1.0 m/s2 for 0.5 s) the source when the request first passes -0.5 and at its strongest, with the
model's own requested acceleration alongside."""
import sys, glob, re, os, collections
import numpy as np
import pclog
ROOT, R = sys.argv[1], sys.argv[2]
ps = glob.glob(os.path.join(ROOT, "**", R + "--*", "rlog.zst"), recursive=True); ps.sort(key=lambda p: int(os.path.basename(os.path.dirname(p)).rsplit("--", 1)[1]))
rows = []; v = 0.0; la = False; e2e = 0.0; e2estop = False; exp = False; t0 = None
SRC = {"cruise": 0, "lead0": 1, "lead1": 2, "lead2": 3, "e2e": 4}
for p in ps:
    for m in pclog.read(p):
        w = m.which()
        if w == "carState": v = m.carState.vEgo
        elif w == "carControl": la = m.carControl.longActive
        elif w == "controlsState" and False: exp = m.selfdriveState.experimentalMode if hasattr(m.selfdriveState, "experimentalMode") else False
        elif w == "modelV2": e2e = m.modelV2.action.desiredAcceleration; e2estop = m.modelV2.action.shouldStop
        elif w == "longitudinalPlan":
            l = m.longitudinalPlan; t = m.logMonoTime * 1e-9; t0 = t0 or t
            rows.append((t - t0, v, la, l.aTarget, SRC.get(str(l.longitudinalPlanSource), 9), e2e, l.hasLead, exp))
X = np.array(rows, float); t, v, la, at, src, e2e, lead, exp = X.T; on = la > 0.5
names = {0: "cruise", 1: "lead", 2: "lead (2nd)", 3: "lead2", 4: "model"}
print(f"experimental mode on {100 * exp[on].mean():.0f} % of active time")
for label, m in (("all active time", on), ("request below -0.5", on & (at < -0.5)), ("request below -1.5", on & (at < -1.5))):
    c = collections.Counter(src[m].astype(int)); print(f"{label:20s} {m.sum() / 20 / 60:5.1f} min: " + ", ".join(f"{names.get(k, k)} {100 * n / max(m.sum(), 1):.0f} %" for k, n in sorted(c.items())))
b = on & (at < -1.0); idx = np.flatnonzero(np.diff(np.r_[0, b.astype(int), 0])); tally = collections.Counter()
for i, j in zip(idx[::2], idx[1::2]):
    if j - i < 10: continue
    k = i
    while k > 0 and at[k - 1] < -0.5: k -= 1
    jm = i + int(np.argmin(at[i:j])); tally[(names[int(src[k])], names[int(src[jm])])] += 1
    print(f"  {int(t[i]) // 60:2d}:{int(t[i]) % 60:02d} {v[i] * 2.237:3.0f} mph | passes -0.5 by: {names[int(src[k])]:6s} (model itself asks {e2e[k]:+.2f}) | strongest {at[jm]:+.2f} by: {names[int(src[jm])]:6s} (model asks {e2e[jm]:+.2f})")
print("onset source, strongest source:", dict(tally))
