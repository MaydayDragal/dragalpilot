# Runs ON THE COMMA, fed over ssh stdin by live.py. Writes nothing to the device.
# Subscribes (read-only, conflated) to a few services and prints one CSV row per sample to stdout.
# Stops when stdout closes (ssh ends), on SIGTERM, or after MAX_SECONDS.
import os, sys, time

RATE = float(os.environ.get("LIVE_RATE", "20"))          # Hz; modelV2 is 20 Hz, so 20 gets every model frame
MAX_SECONDS = float(os.environ.get("LIVE_MAX_SECONDS", "7200"))
FLUSH_EVERY = float(os.environ.get("LIVE_FLUSH", "0.5"))  # s between stdout flushes

import openpilot.cereal.messaging as messaging

SERVICES = ["deviceState", "carState", "carControl", "carOutput", "controlsState", "modelV2", "lateralDelay", "liveTorqueParameters"]
try:
  from openpilot.cereal.services import SERVICE_LIST
  SERVICES = [s for s in SERVICES if s in SERVICE_LIST]
  if "lateralTorqueParameters" in SERVICE_LIST and "liveTorqueParameters" not in SERVICE_LIST:
    SERVICES.append("lateralTorqueParameters")
except Exception:
  pass
LTP = "liveTorqueParameters" if "liveTorqueParameters" in SERVICES else ("lateralTorqueParameters" if "lateralTorqueParameters" in SERVICES else None)

COLS = ["t", "started", "v", "aEgo", "ang", "rate", "drv", "pressed", "blink", "latActive", "out",
        "desiredLateralAccel", "actualLateralAccel", "error", "p", "i", "f", "output", "saturated", "version",
        "ll", "rl", "llp", "rlp", "mcurv", "delay", "laf", "fric", "fresh"]


def num(x):
  if x is None:
    return ""
  if isinstance(x, bool):
    return "1" if x else "0"
  return f"{x:.5g}"


def main():
  sm = messaging.SubMaster(SERVICES, frequency=RATE)
  out = sys.stdout
  out.write("#services " + " ".join(SERVICES) + "\n")
  out.write(",".join(COLS) + "\n")
  out.flush()
  dt = 1.0 / RATE
  t_end = time.monotonic() + MAX_SECONDS
  nxt = time.monotonic()
  last_flush = nxt
  while True:
    now = time.monotonic()
    if now > t_end:
      break
    sm.update(0)
    r = dict.fromkeys(COLS)
    r["t"] = now
    seen = sm.seen
    fresh = 0
    for bit, s in enumerate(SERVICES):
      if sm.updated[s]:
        fresh |= 1 << bit
    r["fresh"] = fresh
    try:
      if seen.get("deviceState"):
        r["started"] = bool(sm["deviceState"].started)
      if seen.get("carState"):
        c = sm["carState"]
        r["v"], r["aEgo"], r["ang"], r["rate"], r["drv"] = c.vEgo, c.aEgo, c.steeringAngleDeg, c.steeringRateDeg, c.steeringTorque
        r["pressed"], r["blink"] = bool(c.steeringPressed), bool(c.leftBlinker or c.rightBlinker)
      if seen.get("carControl"):
        r["latActive"] = bool(sm["carControl"].latActive)
      if seen.get("carOutput"):
        r["out"] = sm["carOutput"].actuatorsOutput.torque
      if seen.get("controlsState"):
        lcs = sm["controlsState"].lateralControlState
        if lcs.which() == "torqueState":
          ts = lcs.torqueState
          r["desiredLateralAccel"], r["actualLateralAccel"], r["error"] = ts.desiredLateralAccel, ts.actualLateralAccel, ts.error
          r["p"], r["i"], r["f"], r["output"] = ts.p, ts.i, ts.f, ts.output
          r["saturated"], r["version"] = bool(ts.saturated), int(ts.version)
      if seen.get("modelV2"):
        md = sm["modelV2"]
        if len(md.laneLines) > 2 and len(md.laneLines[1].y) and len(md.laneLineProbs) > 2:
          r["ll"], r["rl"] = md.laneLines[1].y[0], md.laneLines[2].y[0]
          r["llp"], r["rlp"] = md.laneLineProbs[1], md.laneLineProbs[2]
        r["mcurv"] = md.action.desiredCurvature
      if seen.get("lateralDelay"):
        r["delay"] = sm["lateralDelay"].lateralDelay
      if LTP and seen.get(LTP):
        p = sm[LTP]
        r["laf"], r["fric"] = p.latAccelFactorFiltered, p.frictionCoefficientFiltered
    except Exception as e:  # never die on one odd message; note it and carry on
      out.write(f"#err {type(e).__name__}: {e}\n")
    try:
      out.write(",".join(num(r[k]) for k in COLS) + "\n")
      if now - last_flush >= FLUSH_EVERY:
        out.flush()
        last_flush = now
    except (BrokenPipeError, OSError):
      break
    nxt += dt
    sleep = nxt - time.monotonic()
    if sleep > 0:
      time.sleep(sleep)
    else:
      nxt = time.monotonic()  # fell behind; do not try to catch up


main()
