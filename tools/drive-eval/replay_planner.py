# runs on the comma: feeds the logged messages of route db (the approach to the 0.7 m stop, and a stretch of steady
# cruising) to the installed LongitudinalPlanner and prints what it asks for with the new settings.
import glob, re, collections
from openpilot.tools.lib.logreader import LogReader
from openpilot.selfdrive.controls.lib.longitudinal_planner import LongitudinalPlanner

class FakeSM(dict):
  def __init__(self): super().__init__(); self.logMonoTime = collections.defaultdict(int); self.updated = collections.defaultdict(bool); self.valid = collections.defaultdict(lambda: True); self.alive = collections.defaultdict(lambda: True)
  def all_checks(self, *a, **k): return True

paths = sorted(glob.glob("/data/media/0/realdata/000000db--*/rlog.zst"), key=lambda p: int(re.search(r"--(\d+)/rlog", p).group(1)))
CP = CPSP = None; T0 = None
for m in LogReader(paths[0]):
  if m.which() == "carParams": CP = m.carParams
  elif m.which() == "carParamsSP": CPSP = m.carParamsSP
  elif m.which() == "carState" and T0 is None: T0 = m.logMonoTime
def run(seg, t_from, t_to, step, label):
  p = LongitudinalPlanner(CP, CPSP); sm = FakeSM(); n = 0; nxt = t_from; errs = 0
  print(label); print("      t   v mph  cluster  set mph | logged aTgt stop | replay aTgt stop  ratio")
  for q in seg:
    for m in LogReader(paths[q]):
      w = m.which(); t = (m.logMonoTime - T0) / 1e9
      try: sm[w] = getattr(m, w)
      except Exception: continue
      sm.logMonoTime[w] = m.logMonoTime
      if w == "modelV2" and all(k in sm for k in ("carState", "controlsState", "selfdriveState", "radarState", "carControl", "longitudinalPlan")) and t > t_from - 20:
        try: p.update(sm)
        except Exception as e:
          errs += 1
          if errs < 3: print("   update failed:", type(e).__name__, str(e)[:160])
          continue
        if t_from <= t <= t_to and t >= nxt:
          nxt = t + step; cs = sm["carState"]; lp = sm["longitudinalPlan"]
          print(f"  {t:6.1f}  {cs.vEgo * 2.237:5.1f}  {cs.vEgoCluster * 2.237:6.1f}  {cs.vCruise * 0.6214:6.1f} | {lp.aTarget:+10.2f} {int(lp.shouldStop):4d} | {p.output_a_target:+10.2f} {int(p.output_should_stop):4d}  {p.g70_cluster_speed.ratio:.4f}")
  print("   update errors:", errs)
run((7, 8), 472.0, 483.0, 1.0, "approach to the stop (logged: stop requested at 0.6 mph, stopped 0.7 m behind)")
run((3, 4), 235.0, 275.0, 8.0, "steady cruising")
