import glob, re, sys, collections
import numpy as np
from multiprocessing import Pool
from openpilot.tools.lib.logreader import LogReader

def seg(p):
  o = dict(name=p.split("/")[-2], btn=[], alerts=collections.Counter(), ev=collections.Counter(), lk_cam=0, lk_sent=0, spd=[], eng=[], txb=[None, None], mism=0, gapbars=collections.Counter())
  cs = cc = lp = None; prev_en = False; t0 = None; last_alert = None
  for m in LogReader(p):
    w = m.which(); t = m.logMonoTime / 1e9
    if t0 is None: t0 = t
    if w == "carState":
      cs = m.carState
      for b in cs.buttonEvents: o["btn"].append((round(t - t0, 2), str(b.type), b.pressed))
    elif w == "carControl":
      cc = m.carControl
      if cc.enabled and not prev_en and cs is not None: o["eng"].append((round(t - t0, 2), round(cs.vEgo * 2.237, 1), round(cs.vCruise * 0.6214, 1), [x for x in o["btn"] if t - t0 - x[0] < 1.5][-2:]))
      prev_en = cc.enabled
      if cc.longActive: o["gapbars"][cc.hudControl.leadDistanceBars] += 1
    elif w == "longitudinalPlan": lp = m.longitudinalPlan
    elif w == "selfdriveState":
      s = m.selfdriveState; a = s.alertText1 + " | " + s.alertText2
      if a != last_alert and s.alertText1: o["alerts"][a] += 1
      last_alert = a
    elif w == "onroadEvents":
      for e in m.onroadEvents: o["ev"][str(e.name)] += 1
    elif w == "pandaStates":
      ps = m.pandaStates[0]
      if o["txb"][0] is None: o["txb"][0] = ps.safetyTxBlocked
      o["txb"][1] = ps.safetyTxBlocked
      if cc is not None and cc.longActive and not ps.controlsAllowed: o["mism"] += 1
    elif w == "can":
      for c in m.can:
        if c.address == 0x53E:
          if c.src == 2 and bytes(c.dat)[4] & 1: o["lk_cam"] += 1
          elif c.src == 128 and bytes(c.dat)[4] & 1: o["lk_sent"] += 1
    if w == "carState" and cc is not None and lp is not None and cc.longActive and not cs.gasPressed and not lp.hasLead and cs.vEgo > 20 and abs(cs.aEgo) < 0.15 and str(lp.longitudinalPlanSource) == "cruise":
      o["spd"].append((cs.vEgo, cs.vEgoCluster, cs.vCruise / 3.6, cs.vCruiseCluster / 3.6))
  o["spd"] = np.array(o["spd"][::10]) if o["spd"] else np.zeros((0, 4))
  return o

if __name__ == "__main__":
  for r in sys.argv[1:]:
    paths = sorted(glob.glob(f"/data/media/0/realdata/{r}--*/rlog.zst"), key=lambda p: int(re.search(r"--(\d+)/rlog", p).group(1)))
    with Pool(4) as pool: res = pool.map(seg, paths)
    al = collections.Counter(); ev = collections.Counter(); bars = collections.Counter()
    for o in res: al.update(o["alerts"]); ev.update(o["ev"]); bars.update(o["gapbars"])
    print(f"\n=== {r}: {len(paths)} segments")
    print("alerts:", dict(al))
    print("events (frames):", {k: v for k, v in ev.items() if k in ("accFaulted", "controlsMismatch", "cruiseMismatch", "resumeBlocked", "buttonEnable", "personalityChanged", "brakeHold", "pedalPressed", "steerSaturated", "fcw", "stockFcw", "stockAeb")})
    print("panda: tx blocked", res[0]["txb"][0], "->", res[-1]["txb"][1], "| samples with longActive but controls not allowed:", sum(o["mism"] for o in res))
    print("lead-departure bit: frames set by camera", sum(o["lk_cam"] for o in res), "| frames set in what was sent to the car", sum(o["lk_sent"] for o in res))
    print("cluster gap bars while long active (bars: frames):", dict(sorted(bars.items())))
    print("engagements (segment, t in segment, speed mph, set speed mph, last buttons):")
    for o in res:
      for e in o["eng"]: print("  ", o["name"].split("--")[-1], e[0], e[1], e[2], [(b[1], "press" if b[2] else "release") for b in e[3]])
    S = np.vstack([o["spd"] for o in res])
    if len(S) > 20:
      k = 2.237
      print(f"holding speed, no lead, steady ({len(S) / 10:.0f} s): true speed {np.median(S[:, 0]) * k:.1f}  cluster speed {np.median(S[:, 1]) * k:.1f}  set (control) {np.median(S[:, 2]) * k:.1f}  set (cluster) {np.median(S[:, 3]) * k:.1f} mph")
      print(f"   true minus control set: median {np.median(S[:, 0] - S[:, 2]) * k:+.2f} mph;  cluster minus cluster set: median {np.median(S[:, 1] - S[:, 3]) * k:+.2f} (p10 {np.percentile(S[:, 1] - S[:, 3], 10) * k:+.2f}, p90 {np.percentile(S[:, 1] - S[:, 3], 90) * k:+.2f}) mph;  cluster / true speed ratio {np.median(S[:, 1] / S[:, 0]):.4f}")
