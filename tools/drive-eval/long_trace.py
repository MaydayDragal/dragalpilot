# runs on the comma (offroad), read-only; pipe it in:  python - <route> <t0> <t1> [step_s] < long_trace.py
# Prints a time trace of speed control between t0 and t1 seconds into the route: speeds, set speed, engagement,
# acceleration command and plan, lead, and every cruise button press, event change and alert change.
import sys, glob, re
from openpilot.tools.lib.logreader import LogReader
route, t0, t1 = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]); step = float(sys.argv[4]) if len(sys.argv) > 4 else 0.5
paths = sorted(glob.glob(f"/data/media/0/realdata/{route}--*/rlog.zst"), key=lambda p: int(re.search(r"--(\d+)/rlog", p).group(1)))
T0 = None
for m in LogReader(paths[0]):
  if m.which() == "carState": T0 = m.logMonoTime; break
S = {}; nxt = t0; last_ev = None; last_alert = None
print("    t    v mph  vCruise  cluster  cs.en avail | cc.en long  accel  aTgt stop src  | lead   d m  vLead  radar | state")
for q in range(int(t0 // 60), min(int(t1 // 60) + 1, len(paths))):
  for m in LogReader(paths[q]):
    w = m.which(); t = (m.logMonoTime - T0) / 1e9
    if t < t0 - 1 or t > t1: continue
    if w == "carState":
      c = m.carState; S["cs"] = c
      for b in c.buttonEvents: print(f"{t:7.2f}   button {b.type} {'pressed' if b.pressed else 'released'}")
    elif w == "carControl": S["cc"] = m.carControl
    elif w == "longitudinalPlan": S["lp"] = m.longitudinalPlan
    elif w == "radarState": S["rs"] = m.radarState.leadOne
    elif w == "selfdriveState":
      s = m.selfdriveState; S["ss"] = s
      al = (s.alertText1, s.alertText2)
      if al != last_alert and t >= t0: print(f"{t:7.2f}   alert: {al[0]} | {al[1]}"); last_alert = al
    elif w == "onroadEvents":
      ev = sorted(str(e.name) for e in m.onroadEvents)
      if ev != last_ev and t >= t0: print(f"{t:7.2f}   events: {ev}"); last_ev = ev
    if w == "carState" and t >= nxt and all(k in S for k in ("cs", "cc", "lp", "rs", "ss")):
      nxt = t + step; c, cc, lp, l, s = S["cs"], S["cc"], S["lp"], S["rs"], S["ss"]
      print(f"{t:7.2f}  {c.vEgo * 2.237:5.1f}  {c.vCruise * 0.6214:6.1f}  {c.vCruiseCluster * 0.6214:6.1f}  {int(c.cruiseState.enabled):5d} {int(c.cruiseState.available):5d} | {int(cc.enabled):5d} {int(cc.longActive):4d} {cc.actuators.accel:+6.2f} {lp.aTarget:+5.2f} {int(lp.shouldStop):4d} {str(lp.longitudinalPlanSource):6s} | "
            f"{int(l.present):4d} {l.dRel:5.1f} {l.vLead * 2.237:6.1f} {int(l.radar):5d} | {s.state} {str(cc.actuators.longControlState)}")
