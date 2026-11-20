"""Replays g70_long.QuickStart over logged drives: where it would have started, against what the plan did. PC.

  CEREAL_DIR=... CAR_CAPNP_DIR=... python replay_quick_start.py <checkout> <recordings root> <route> ...

For each start: time into the route, gap, the lead's speed, how much earlier than the logged stop-request release it
comes, and whether the lead really left (its speed 3 s later). The car's own response is the logged one, so this
shows when it starts and ends, not how much sooner the car moves."""
import sys, glob, re, os, importlib.util
import numpy as np
import pclog

spec = importlib.util.spec_from_file_location("g70_long", os.path.join(sys.argv[1], "openpilot/sunnypilot/selfdrive/controls/lib/g70_long.py"))
G = importlib.util.module_from_spec(spec); spec.loader.exec_module(G)
ROOT = sys.argv[2]; n_all = 0; EARLY = float(os.environ["EARLY"]) if os.environ.get("EARLY") else None
for r in sys.argv[3:]:
    ps = glob.glob(os.path.join(ROOT, "**", r + "--*", "rlog.zst"), recursive=True)
    ps.sort(key=lambda p: int(re.search(r"--(\d+)[\\/]rlog", p).group(1)))
    q = G.QuickStart(1.2, 0.05, EARLY); v = 0.0; la = stand = False; rows = []; lead = None; t0 = None
    for p in ps:
        for m in pclog.read(p):
            w = m.which()
            if w == "carState": v, stand = m.carState.vEgo, m.carState.standstill
            elif w == "carControl": la = m.carControl.longActive
            elif w == "radarState": lead = m.radarState.leadOne
            elif w == "longitudinalPlan" and lead is not None:
                t = m.logMonoTime * 1e-9; t0 = t0 or t
                out = q.update(v, lead.present, lead.dRel, lead.vLead, lead.aLeadK, 2.0) if la else (q.reset() or None)
                rows.append((t - t0, out is not None, m.longitudinalPlan.shouldStop, v, lead.dRel, lead.vLead, lead.aLeadK, la, lead.present))
    X = np.array(rows, float)
    if not len(X): continue
    on = X[:, 1] > 0.5; idx = np.flatnonzero(np.diff(np.r_[0, on.astype(int), 0]))
    stops = np.flatnonzero(np.diff(np.r_[0, ((X[:, 3] < 0.05) & (X[:, 7] > 0.5) & (X[:, 8] > 0.5)).astype(int), 0]))[::2]
    print(f"{r[-2:]}: {len(idx) // 2} starts; {len(stops)} standstills with a lead while active")
    for i, j in zip(idx[::2], idx[1::2]):
        n_all += 1
        k = np.flatnonzero(X[i - 100:i + 200, 2] < 0.5); rel = (X[i - 100 + k[0], 0] - X[i, 0]) if len(k) else float("nan")
        later = X[min(i + 60, len(X) - 1), 5]
        print(f"   t={X[i, 0]:6.0f}s gap {X[i, 4]:4.1f} m lead {X[i, 5]:.2f} m/s a {X[i, 6]:+.2f} | active {(j - i) * 0.05:.2f} s, ended at ego {X[j - 1, 3]:.2f} m/s | "
              f"logged stop release {rel:+.2f} s after this | lead 3 s later {later:.1f} m/s")
print("total starts:", n_all)
