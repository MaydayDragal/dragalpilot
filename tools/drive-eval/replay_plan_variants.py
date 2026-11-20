# runs on the comma (offroad): replays a route through the installed LongitudinalPlanner in several variants side by
# side and writes one row per planner cycle to <out.npy>:
#   t, vEgo, aEgo, logged aTarget, lead present, dRel, vLead, aLeadK, aLeadTau, longActive, then one column per variant
#   python replay_plan_variants.py <out.npy> <route> <variant> ...      variant = "jerk=<scale>,ahead=<extra s>" (either part optional, "base" for none)
# jerk scales the planner's smoothness weights (change-of-acceleration and jerk cost); ahead reads the plan that much
# further into the future than the 0.5 s actuator delay. The car's response is the logged one.
import sys, glob, re, collections
import numpy as np
from openpilot.tools.lib.logreader import LogReader
from openpilot.selfdrive.controls.lib import longitudinal_planner as LP
from openpilot.selfdrive.controls.lib.longitudinal_mpc_lib import long_mpc as M
OUT, ROUTE = sys.argv[1], sys.argv[2]
VARS = [dict((kv.split("=")[0], float(kv.split("=")[1])) for kv in a.split(",") if "=" in kv) for a in sys.argv[3:]]
_jf, _gap = M.get_jerk_factor, LP.get_accel_from_plan

class FakeSM(dict):
  def __init__(self): super().__init__(); self.logMonoTime = collections.defaultdict(int); self.updated = collections.defaultdict(bool); self.valid = collections.defaultdict(lambda: True); self.alive = collections.defaultdict(lambda: True)
  def all_checks(self, *a, **k): return True

def run(p, var, sm):
  M.get_jerk_factor = (lambda *a, **k: _jf(*a, **k) * var["jerk"]) if "jerk" in var else _jf
  LP.get_accel_from_plan = (lambda s, a, t, action_t=0.0, **k: _gap(s, a, t, action_t=action_t + var["ahead"], **k)) if "ahead" in var else _gap
  try: p.update(sm)
  finally: M.get_jerk_factor, LP.get_accel_from_plan = _jf, _gap
  return float(p.output_a_target)

paths = sorted(glob.glob(f"/data/media/0/realdata/{ROUTE}--*/rlog.zst"), key=lambda p: int(re.search(r"--(\d+)/rlog", p).group(1)))
CP = CPSP = None
for m in LogReader(paths[0]):
  if m.which() == "carParams": CP = m.carParams
  elif m.which() == "carParamsSP": CPSP = m.carParamsSP
PL = [LP.LongitudinalPlanner(CP, CPSP) for _ in VARS]
sm = FakeSM(); rows = []; errs = 0; T0 = None
for path in paths:
  for m in LogReader(path):
    w = m.which()
    try: sm[w] = getattr(m, w)
    except Exception: continue
    sm.logMonoTime[w] = m.logMonoTime
    if w != "modelV2" or not all(k in sm for k in ("carState", "controlsState", "selfdriveState", "radarState", "carControl", "longitudinalPlan")): continue
    T0 = T0 or m.logMonoTime; out = []
    for p, var in zip(PL, VARS):
      try: out.append(run(p, var, sm))
      except Exception as e:
        errs += 1; out.append(float("nan"))
        if errs < 4: print("update failed:", type(e).__name__, str(e)[:200], flush=True)
    cs = sm["carState"]; l = sm["radarState"].leadOne
    rows.append([(m.logMonoTime - T0) / 1e9, cs.vEgo, cs.aEgo, sm["longitudinalPlan"].aTarget, l.present, l.dRel, l.vLead, l.aLeadK, l.aLeadTau, sm["carControl"].longActive] + out)
np.save(OUT, np.array(rows, float)); print("rows", len(rows), "errors", errs, "variants", VARS)
