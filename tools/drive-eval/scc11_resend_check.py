# runs on the comma (offroad), read-only; pipe it in:  python - <route> < scc11_resend_check.py
# Stage 2/3 of docs/proposals/2026-11-17-g70-scc11-info-display-filter.md: compares the camera's SCC11 (0x420, bus 2)
# with what openpilot asked the panda to send (sendcan, bus 0) and what the panda reports as sent (can, src 128),
# and summarises panda state, cruise state and events.
import sys, glob, re, collections, statistics
from openpilot.tools.lib.logreader import LogReader

route = sys.argv[1]
paths = sorted(glob.glob(f"/data/media/0/realdata/{route}--*/rlog.zst"), key=lambda p: int(re.search(r"--(\d+)/rlog", p).group(1)))
T0 = None
cam = []      # (t, data) bus 2
req = []      # (t, data) sendcan bus 0
echo = []     # (t, data) can src 128 (tx echo bus 0)
rx0 = 0       # 0x420 received on bus 0 (should be none once the relay is engaged)
rx0_t = []
ps = collections.Counter(); blocked = []; rxinv = []; faults = collections.Counter(); ev = {}; alerts = collections.Counter()
cruise_en = 0; cs_n = 0; stand4 = 0; started_t = None; sm_modes = collections.Counter()
for p in paths:
  for m in LogReader(p):
    w = m.which(); t = m.logMonoTime
    if w == "carState":
      if T0 is None: T0 = t
      cs_n += 1; cruise_en += m.carState.cruiseState.enabled; stand4 += m.carState.cruiseState.standstill
    elif w == "can":
      for c in m.can:
        if c.address == 0x420:
          d = bytes(c.dat)
          if c.src == 2: cam.append((t, d))
          elif c.src == 128: echo.append((t, d))
          elif c.src == 0: rx0 += 1; rx0_t.append(t)
    elif w == "sendcan":
      for c in m.sendcan:
        if c.address == 0x420 and c.src == 0: req.append((t, bytes(c.dat)))
    elif w == "pandaStates":
      for s in m.pandaStates:
        sm_modes[str(s.safetyModel)] += 1; blocked.append(s.safetyTxBlocked); rxinv.append(s.safetyRxInvalid)
        ps[("controlsAllowed", bool(s.controlsAllowed))] += 1
        for f in s.faults: faults[str(f)] += 1
        if str(s.faultStatus) != "none": faults["faultStatus:" + str(s.faultStatus)] += 1
    elif w == "onroadEvents" and T0 is not None:
      for e in m.onroadEvents: ev.setdefault(str(e.name), []).append(round((t - T0) / 1e9, 1))
    elif w == "selfdriveState":
      a = m.selfdriveState.alertText1
      if a: alerts[str(a) + " | " + str(m.selfdriveState.alertText2)] += 1

sec = lambda t: (t - T0) / 1e9
print(f"route {route}: {len(paths)} segments, {cs_n / 100:.0f} s; cruise enabled {cruise_en / 100:.0f} s; cruise standstill (camera SCCInfoDisplay 4) {stand4 / 100:.0f} s")
print(f"camera SCC11 on bus 2: {len(cam)} frames; requested by openpilot (sendcan bus 0): {len(req)}; reported sent by the panda (echo): {len(echo)}; received on bus 0 from elsewhere: {rx0}" + (f" (t {sec(rx0_t[0]):.1f}..{sec(rx0_t[-1]):.1f} s)" if rx0 else ""))
if req:
  t_first, t_last = req[0][0], req[-1][0]
  camw = [(t, d) for t, d in cam if t_first - 2e7 <= t <= t_last]
  print(f"re-send active {sec(t_first):.1f}..{sec(t_last):.1f} s; camera frames in that span: {len(camw)}; requested/camera = {len(req) / max(len(camw), 1):.4f}; echoed/requested = {len(echo) / len(req):.4f}")
  cnt = lambda d: d[0] >> 4
  for name, seq in (("camera", camw), ("requested", req), ("echoed", echo)):
    steps = collections.Counter((cnt(b[1]) - cnt(a[1])) % 16 for a, b in zip(seq, seq[1:])); dts = sorted((b[0] - a[0]) / 1e6 for a, b in zip(seq, seq[1:]))
    n = len(dts)
    if n > 10: print(f"  {name:9s} counter steps {dict(sorted(steps.items()))}; spacing ms: median {statistics.median(dts):.1f}, p1 {dts[n // 100]:.1f}, p99 {dts[n * 99 // 100]:.1f}, max {dts[-1]:.1f}; gaps > 60 ms: {sum(1 for x in dts if x > 60)}, > 100 ms: {sum(1 for x in dts if x > 100)}")
  # match each requested frame to the camera frame with the same payload just before it
  ci = 0; delays = []; unmatched = 0; changed = collections.Counter(); camd = {}
  cams = camw
  j = 0
  for t, d in req:
    while j + 1 < len(cams) and cams[j + 1][0] <= t: j += 1
    k = None
    for q in range(j, max(j - 4, -1), -1):
      if cams[q][1] == d and cams[q][0] <= t: k = q; break
    if k is None:
      unmatched += 1
      c0 = cams[j][1]
      if (c0[0] >> 4) == (d[0] >> 4): changed[tuple(i for i in range(8) if c0[i] != d[i])] += 1
    else: delays.append((t - cams[k][0]) / 1e6)
  delays.sort(); n = len(delays)
  print(f"  payload equal to a camera frame: {n} of {len(req)} ({unmatched} not equal; byte positions differing vs same-counter camera frame: {dict(changed)})")
  if n: print(f"  camera -> request delay ms (log timestamps): median {statistics.median(delays):.1f}, p99 {delays[n * 99 // 100]:.1f}, max {delays[-1]:.1f}")
  sent = collections.Counter(d for _, d in req); dup = sum(v - 1 for v in collections.Counter((t // 1, d) for t, d in req).values() if v > 1)
  disp = collections.Counter((d[0] >> 1) & 7 for _, d in req); dispc = collections.Counter((d[0] >> 1) & 7 for _, d in camw)
  print(f"  SCCInfoDisplay in requested frames {dict(disp)}; in camera frames {dict(dispc)}")
print(f"panda: safety models {dict(sm_modes)}; safetyTxBlocked {min(blocked)} -> {max(blocked)}; safetyRxInvalid {min(rxinv)} -> {max(rxinv)}; {dict(ps)}; faults {dict(faults) or 'none'}")
keep = {k: (len(v), v[0], v[-1]) for k, v in ev.items() if k not in ("wrongGear", "seatbeltNotLatched", "parkBrake", "gasPressedOverride", "steerOverride", "preEnableStandstill", "selfdriveInitializing", "laneChange", "preLaneChangeRight", "preLaneChangeLeft", "doorOpen", "reverseGear")}
print("events (count, first s, last s):", keep)
print("alerts:", dict(alerts.most_common(10)))
