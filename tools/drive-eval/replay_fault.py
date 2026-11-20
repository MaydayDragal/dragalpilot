# runs on the comma against the scratch copy of opendbc (PYTHONPATH=/data/tmp/st): replays the CAN traffic of the
# cruise fault (route d7, 120-135 s) through the panda safety code and reports when controls are allowed and
# whether the SCC12 frames the panda rejected in the car would now be accepted.
import glob, sys
sys.path.insert(0, "/data/openpilot")           # only for the log reader
from openpilot.tools.lib.logreader import LogReader
sys.path.remove("/data/openpilot")
for k in [k for k in sys.modules if k == "opendbc" or k.startswith("opendbc.")]: del sys.modules[k]
sys.path.insert(0, "/data/tmp/st")
from opendbc.safety.tests.libsafety import libsafety_py
safety = libsafety_py.libsafety
segs = sorted(glob.glob("/data/media/0/realdata/000000d7--*--[012]/rlog.zst"))
CP = CPSP = None; T0 = None
for m in LogReader(segs[0]):
  if m.which() == "carParams": CP = m.carParams
  elif m.which() == "carParamsSP": CPSP = m.carParamsSP
  elif m.which() == "carState" and T0 is None: T0 = m.logMonoTime
cfg = CP.safetyConfigs[0]; mode = cfg.safetyModel.raw; param = cfg.safetyParam
sp = CPSP.safetyParam if hasattr(CPSP, "safetyParam") else 0
print("safety mode", cfg.safetyModel, "param", param, "sp param", sp)
safety.set_current_safety_param_sp(sp); print("set hooks:", safety.set_safety_hooks(mode, param))
last = None; rej = {"n": 0, "ok": 0}; first_ok = None
for seg in segs[1:]:
  for m in LogReader(seg):
    w = m.which()
    if w == "can":
      t = (m.logMonoTime - T0) / 1e9
      for c in m.can:
        if c.src in (0, 1, 2):
          safety.safety_rx_hook(libsafety_py.make_CANPacket(c.address, c.src, bytes(c.dat)))
        elif c.src in (128, 192) and c.address == 0x421 and 133.0 < t < 134.7:
          ok = bool(safety.safety_tx_hook(libsafety_py.make_CANPacket(c.address, 0, bytes(c.dat))))
          if c.src == 192:
            rej["n"] += 1; rej["ok"] += int(ok)
            if ok and first_ok is None: first_ok = t
      if 132.5 < t < 135.0:
        st = (bool(safety.get_controls_allowed()), bool(safety.get_acc_main_on()))
        if st != last: print(f"  {t:7.2f} s  controls_allowed {st[0]}  acc_main_on {st[1]}"); last = st
print(f"SCC12 frames the panda rejected in the car: {rej['n']}; accepted by the new rule: {rej['ok']}")
