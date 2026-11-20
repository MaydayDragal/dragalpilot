# runs on the comma (offroad): replays a route through the installed LongitudinalPlanner three times side by side:
# as installed, and with g70_long.lead_brake_tau at two settings (the function is loaded from the file given, so it
# can be tried before it is installed). Writes one row per planner cycle to <out.npy>:
#   t, vEgo, aEgo, logged aTarget, lead present, dRel, vLead, aLeadK, aLeadTau, longActive, replay base, replay A, replay B
#   python replay_lead_brake.py <g70_long.py> <out.npy> <route> "<tauA> <thrA>" "<tauB> <thrB>"
# The car's response is the logged one: each planner integrates its own request, the lead and gap stay as logged.
import sys, glob, re, collections, importlib.util
import numpy as np
from openpilot.tools.lib.logreader import LogReader
from openpilot.selfdrive.controls.lib.longitudinal_planner import LongitudinalPlanner
from openpilot.selfdrive.controls.lib.longitudinal_mpc_lib import long_mpc as M
spec = importlib.util.spec_from_file_location("g70_new", sys.argv[1]); G = importlib.util.module_from_spec(spec); spec.loader.exec_module(G)
OUT, ROUTE = sys.argv[2], sys.argv[3]; SETS = [None] + [tuple(float(x) for x in a.split()) for a in sys.argv[4:6]]

class Proxy:
  def __init__(self, lead, tau): self._l = lead; self.aLeadTau = tau
  def __getattr__(self, k): return getattr(self._l, k)
_orig = M.LongitudinalMpc.process_lead
def process_lead(self, lead):
  st = getattr(self, "g70_setting", None)
  if st is not None and lead is not None and lead.present:
    lead = Proxy(lead, G.lead_brake_tau(lead.aLeadK, lead.aLeadTau, st))
  return _orig(self, lead)
M.LongitudinalMpc.process_lead = process_lead

class FakeSM(dict):
  def __init__(self): super().__init__(); self.logMonoTime = collections.defaultdict(int); self.updated = collections.defaultdict(bool); self.valid = collections.defaultdict(lambda: True); self.alive = collections.defaultdict(lambda: True)
  def all_checks(self, *a, **k): return True

paths = sorted(glob.glob(f"/data/media/0/realdata/{ROUTE}--*/rlog.zst"), key=lambda p: int(re.search(r"--(\d+)/rlog", p).group(1)))
CP = CPSP = None
for m in LogReader(paths[0]):
  if m.which() == "carParams": CP = m.carParams
  elif m.which() == "carParamsSP": CPSP = m.carParamsSP
PL = []
for st in SETS:
  p = LongitudinalPlanner(CP, CPSP); p.mpc.g70_setting = st; PL.append(p)
sm = FakeSM(); rows = []; errs = 0; T0 = None
for path in paths:
  for m in LogReader(path):
    w = m.which()
    try: sm[w] = getattr(m, w)
    except Exception: continue
    sm.logMonoTime[w] = m.logMonoTime
    if w != "modelV2" or not all(k in sm for k in ("carState", "controlsState", "selfdriveState", "radarState", "carControl", "longitudinalPlan")): continue
    T0 = T0 or m.logMonoTime; out = []
    for p in PL:
      try: p.update(sm); out.append(float(p.output_a_target))
      except Exception as e:
        errs += 1; out.append(float("nan"))
        if errs < 4: print("update failed:", type(e).__name__, str(e)[:200], flush=True)
    cs = sm["carState"]; l = sm["radarState"].leadOne
    rows.append([(m.logMonoTime - T0) / 1e9, cs.vEgo, cs.aEgo, sm["longitudinalPlan"].aTarget, l.present, l.dRel, l.vLead, l.aLeadK, l.aLeadTau, sm["carControl"].longActive] + out)
  print(path.split("--")[-1].split("/")[0], len(rows), flush=True)
np.save(OUT, np.array(rows, float)); print("rows", len(rows), "errors", errs)
