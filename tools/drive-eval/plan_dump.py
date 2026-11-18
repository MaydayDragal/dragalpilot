# runs on the comma (offroad), read-only, writes nothing on the device: the result goes to stdout as .npy
#   ssh ... 'python - <route>' < plan_dump.py > <route>.plan.npy
# One row per modelV2 frame (20 Hz):
#   0 t(s)  1 vEgo  2 latActive  3 steeringPressed  4 blinker  5 published lateralDelay  6 action.desiredCurvature
#   7 left lane y0  8 right lane y0  9 left prob  10 right prob  11..43 plan yaw (33)  44..76 plan yaw rate (33)
import sys, glob, re
import numpy as np
from multiprocessing import Pool
from openpilot.tools.lib.logreader import LogReader

def seg(path):
  rows = []; v = 0.0; act = 0.0; pressed = 0.0; blink = 0.0; delay = np.nan
  for m in LogReader(path):
    w = m.which()
    if w == "carState":
      c = m.carState; v = c.vEgo; pressed = float(c.steeringPressed); blink = float(c.leftBlinker or c.rightBlinker)
    elif w == "carControl": act = float(m.carControl.latActive)
    elif w == "lateralDelay": delay = m.lateralDelay.lateralDelay
    elif w == "modelV2":
      md = m.modelV2
      try:
        yaw = list(md.orientation.z); rate = list(md.orientationRate.z)
        if len(yaw) != 33 or len(rate) != 33: continue
        rows.append([m.logMonoTime * 1e-9, v, act, pressed, blink, delay, md.action.desiredCurvature,
                     md.laneLines[1].y[0], md.laneLines[2].y[0], md.laneLineProbs[1], md.laneLineProbs[2]] + yaw + rate)
      except Exception:
        pass
  return int(re.search(r"--(\d+)/rlog", path).group(1)), np.array(rows, dtype=np.float64)

if __name__ == "__main__":
  paths = glob.glob(f"/data/media/0/realdata/{sys.argv[1]}--*/rlog.zst")
  with Pool(4) as p: res = sorted(p.map(seg, paths), key=lambda x: x[0])
  a = np.vstack([r for _, r in res if len(r)])
  import io
  buf = io.BytesIO(); np.save(buf, a)  # np.save needs a seekable file, a pipe is not
  sys.stdout.buffer.write(buf.getvalue()); sys.stdout.buffer.flush()
