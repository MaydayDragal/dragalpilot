# runs on the comma (offroad), read-only; pipe it in:  python - <route> [<route> ...] < bookmark_context.py
# Finds every bookmark in the routes and prints what changed in the WIN seconds before it (and 5 s after):
# openpilot alerts, the HUD visual alert, hands-on state, and every field of the steering / lane messages the
# cluster reads (LKAS11 0x340, LFAHDA_MFC 0x485, HDA11_MFC 0x484, LKAS12 0x53E, MDPS12 0x251), both as the camera
# sent them (bus 2) and as they went to the car (echo of bus 0, src 128).
import sys, glob, re, os
from openpilot.tools.lib.logreader import LogReader
from opendbc.can.dbc import DBC

WIN = float(os.environ.get("WIN", "40"))
dbc = DBC("hyundai_can_generated")
WATCH = {0x340: "LKAS11", 0x485: "LFAHDA_MFC", 0x484: "HDA11_MFC", 0x53E: "LKAS12", 0x251: "MDPS12"}
SKIP = ("Counter", "Chksum", "Checksum", "AliveCnt", "CR_Lkas_StrToqReq", "CR_Mdps_StrColTq", "CR_Mdps_OutTq", "CR_Mdps_DrvTq",
        "CF_Mdps_MsgCount2", "CF_Mdps_Chksum2", "CF_Lkas_MsgCount", "CF_Lkas_Chksum", "CR_Lkas_StrToqReq")

def decode(addr, d):
  msg = dbc.msgs.get(addr)
  out = {}
  if msg is None: return out
  for name, s in msg.sigs.items():
    if any(k in name for k in SKIP): continue
    if s.lsb // 8 >= len(d): continue
    if s.is_little_endian: raw = (int.from_bytes(d, "little") >> s.lsb) & ((1 << s.size) - 1)
    else: raw = (int.from_bytes(d, "big") >> (8 * (len(d) - 1 - s.lsb // 8) + s.lsb % 8)) & ((1 << s.size) - 1)
    out[name] = raw
  return out

for route in sys.argv[1:]:
  paths = sorted(glob.glob(f"/data/media/0/realdata/{route}--*/rlog.zst"), key=lambda p: int(re.search(r"--(\d+)/rlog", p).group(1)))
  T0 = None; bms = []
  for p in paths:
    for m in LogReader(p):
      w = m.which()
      if T0 is None and w == "carState": T0 = m.logMonoTime
      if w == "userBookmark": bms.append(m.logMonoTime)
  print(f"\n=== {route}: {len(paths)} segments, bookmarks at {[round((b - T0) / 1e9, 1) for b in bms]} s")
  for b in bms:
    tb = (b - T0) / 1e9
    segs = sorted({int(x // 60) for x in (tb - WIN, tb, tb + 5)} & set(range(len(paths))))
    print(f"--- bookmark at {tb:.1f} s (segment {int(tb // 60)}), scanning segments {segs}; times below are relative to the bookmark")
    last = {}; rows = []; raw_last = {}; rawrows = []
    def ch(t, key, val):
      if last.get(key) != val:
        if tb - WIN <= t <= tb + 5: rows.append((t - tb, key, last.get(key), val))
        last[key] = val
    for q in segs:
      for m in LogReader(paths[q]):
        w = m.which(); t = (m.logMonoTime - T0) / 1e9
        if w == "selfdriveState":
          s = m.selfdriveState
          ch(t, "op alert", (s.alertText1, s.alertText2, str(s.alertStatus), str(s.alertSound) if hasattr(s, "alertSound") else ""))
          ch(t, "op enabled/active", (s.enabled, s.active))
        elif w == "carControl":
          h = m.carControl.hudControl
          ch(t, "hud visualAlert", str(h.visualAlert)); ch(t, "hud audibleAlert", str(h.audibleAlert)); ch(t, "latActive", m.carControl.latActive)
        elif w == "carState":
          c = m.carState
          ch(t, "steeringPressed", c.steeringPressed); ch(t, "steerFaultTemporary", c.steerFaultTemporary); ch(t, "cruise enabled", c.cruiseState.enabled)
          ch(t, "v mph (5s)", round(c.vEgo * 2.237 / 5) * 5)
        elif w == "can":
          for c in m.can:
            if c.address not in WATCH or c.src not in (0, 2, 128, 130): continue
            d = bytes(c.dat); k = (c.src, c.address)
            for name, v in decode(c.address, d).items(): ch(t, f"src {c.src:3d} {WATCH[c.address]}.{name}", v)
    for dt, key, a, v in rows:
      if a is None: continue
      print(f"  {dt:+7.2f}  {key}: {a} -> {v}")
    print("  state at the bookmark:", {k: v for k, v in last.items() if k.startswith(("src 128 LKAS11.CF_Lkas_SysWarning", "src 128 LKAS11.CF_Lkas_LdwsSysState", "src   2 LKAS11.CF_Lkas_SysWarning", "src 128 LFAHDA_MFC", "op alert"))})
