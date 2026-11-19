# runs on the comma (offroad): compact per-segment extraction of speed-control (longitudinal) signals
#   python extract_long.py <route> [<route> ...]      writes /data/tmp/extl/<segment>.pkl
# Per segment: carState at 20 Hz, radarState lead, openpilot's longitudinal plan (it runs even while the car's own
# cruise controls speed), the model's lead, the camera's SCC11 / SCC12 / FCA11 as it sent them (bus 2) at 25 Hz, GPS.
import sys, os, pickle, glob
import numpy as np
from multiprocessing import Pool
from openpilot.tools.lib.logreader import LogReader
from opendbc.can.dbc import DBC
OUT = "/data/tmp/extl"
dbc = DBC("hyundai_can_generated")
SIGS = {0x420: ["MainMode_ACC", "SCCInfoDisplay", "VSetDis", "ObjValid", "TauGapSet", "ACC_ObjStatus", "ACC_ObjDist", "ACC_ObjRelSpd", "ACC_ObjLatPos"],
        0x421: ["ACCMode", "StopReq", "aReqRaw", "aReqValue", "CF_VSM_Warn", "CF_VSM_DecCmdAct", "CR_VSM_DecCmd", "AEB_CmdAct", "TakeOverReq"],
        0x38D: ["FCA_CmdAct", "CF_VSM_Warn", "FCA_StopReq", "FCA_Status", "FCA_TimetoCollision"]}

def dec(addr, d):
    out = []
    for name in SIGS[addr]:
        s = dbc.msgs[addr].sigs[name]
        if s.lsb // 8 >= len(d): out.append(np.nan); continue
        if s.is_little_endian: raw = (int.from_bytes(d, "little") >> s.lsb) & ((1 << s.size) - 1)
        else: raw = (int.from_bytes(d, "big") >> (8 * (len(d) - 1 - s.lsb // 8) + s.lsb % 8)) & ((1 << s.size) - 1)
        if s.is_signed and raw >> (s.size - 1): raw -= 1 << s.size
        out.append(raw * s.factor + s.offset)
    return out

def do(path):
    seg = os.path.basename(os.path.dirname(path)); out = os.path.join(OUT, seg + ".pkl")
    if os.path.exists(out): return seg
    R = {k: [] for k in ["cs", "rs", "lp", "ml", "scc11", "scc12", "fca11", "gps", "cc"]}; n = {0x420: 0, 0x421: 0, 0x38D: 0}; ncs = 0; ncc = 0
    key = {0x420: "scc11", 0x421: "scc12", 0x38D: "fca11"}
    for m in LogReader(path):
        w = m.which(); t = m.logMonoTime * 1e-9
        if w == "carState":
            ncs += 1
            if ncs % 5: continue
            c = m.carState; cr = c.cruiseState
            R["cs"].append((t, c.vEgo, c.aEgo, c.gasPressed, c.brakePressed, cr.enabled, cr.speed, cr.standstill, c.standstill, c.stockFcw, c.stockAeb, cr.available))
        elif w == "carControl":
            ncc += 1
            if ncc % 5: continue
            c = m.carControl
            R["cc"].append((t, c.enabled, c.longActive, c.latActive, c.actuators.accel, c.hudControl.setSpeed, c.hudControl.leadVisible))
        elif w == "radarState":
            l = m.radarState.leadOne
            R["rs"].append((t, l.present, l.dRel, l.vRel, l.vLead, l.vLeadK, l.aLeadK, l.radar, l.modelProb, l.yRel))
        elif w == "longitudinalPlan":
            p = m.longitudinalPlan
            R["lp"].append((t, p.aTarget, p.hasLead, p.shouldStop, p.accels[0] if len(p.accels) else np.nan, p.speeds[0] if len(p.speeds) else np.nan,
                            p.jerks[0] if len(p.jerks) else np.nan, p.fcw, ["cruise", "lead0", "lead1", "lead2", "e2e"].index(str(p.longitudinalPlanSource)) if str(p.longitudinalPlanSource) in ("cruise", "lead0", "lead1", "lead2", "e2e") else -1))
        elif w == "modelV2":
            md = m.modelV2
            if len(md.leadsV3): l = md.leadsV3[0]; R["ml"].append((t, l.prob, l.x[0], l.v[0], l.a[0]))
        elif w == "gpsLocationExternal":
            p = m.gpsLocationExternal; R["gps"].append((t, p.latitude, p.longitude, p.speed, p.bearingDeg, p.unixTimestampMillis))
        elif w == "can":
            for c in m.can:
                if c.src == 2 and c.address in n:
                    n[c.address] += 1
                    if n[c.address] % 2 == 0: R[key[c.address]].append([t] + dec(c.address, bytes(c.dat)))
    res = {k: np.array(v, dtype=np.float64) for k, v in R.items()}; res["sigs"] = SIGS
    with open(out, "wb") as f: pickle.dump(res, f)
    return seg

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True); paths = []
    for r in sys.argv[1:]: paths += glob.glob(f"/data/media/0/realdata/{r}--*/rlog.zst")
    with Pool(4) as p:
        for s in p.imap_unordered(do, sorted(paths)): print(s, flush=True)
