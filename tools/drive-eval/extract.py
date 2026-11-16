# runs on the comma (offroad): compact per-segment extraction of lateral-control signals
import sys, os, pickle, glob
import numpy as np
from multiprocessing import Pool
from openpilot.tools.lib.logreader import LogReader
OUT = "/data/tmp/ext"

def g(o, name, default=np.nan):
    try: return getattr(o, name)
    except Exception: return default

def do(path):
    seg = os.path.basename(os.path.dirname(path))
    out = os.path.join(OUT, seg + ".pkl")
    if os.path.exists(out): return seg
    R = {k: [] for k in ["cs","cc","co","ctl","ss","model","vp","ltp","ld","gps","events","bm","misc"]}
    tkeys = None
    for m in LogReader(path):
        w = m.which(); t = m.logMonoTime * 1e-9
        if w == "carState":
            c = m.carState
            R["cs"].append((t, c.vEgo, c.aEgo, c.steeringAngleDeg, c.steeringRateDeg, c.steeringTorque, c.steeringTorqueEps, c.steeringPressed,
                            c.steerFaultTemporary, c.steerFaultPermanent, c.leftBlinker or c.rightBlinker, c.cruiseState.enabled, c.standstill, c.yawRate))
        elif w == "carControl":
            c = m.carControl
            R["cc"].append((t, c.latActive, c.enabled, c.actuators.torque, c.actuators.curvature, c.currentCurvature, c.orientationNED[0] if len(c.orientationNED) else np.nan))
        elif w == "carOutput":
            a = m.carOutput.actuatorsOutput
            R["co"].append((t, a.torque, a.torqueOutputCan))
        elif w == "controlsState":
            c = m.controlsState
            row = [t, c.curvature, c.desiredCurvature]
            lcs = c.lateralControlState
            if lcs.which() == "torqueState":
                d = lcs.torqueState.to_dict()
                if tkeys is None: tkeys = sorted(k for k, v in d.items() if isinstance(v, (int, float, bool)))
                row += [float(d.get(k, np.nan)) for k in tkeys]
            R["ctl"].append(tuple(row))
        elif w == "selfdriveState":
            s = m.selfdriveState
            R["ss"].append((t, s.enabled, s.active, str(s.alertText1), str(s.alertText2), str(s.state)))
        elif w == "modelV2":
            md = m.modelV2
            try:
                R["model"].append((t, md.laneLines[1].y[0], md.laneLines[2].y[0], md.laneLineProbs[1], md.laneLineProbs[2],
                                   md.action.desiredCurvature, md.position.y[5] if len(md.position.y) > 5 else np.nan,
                                   md.roadEdges[0].y[0], md.roadEdges[1].y[0]))
            except Exception: pass
        elif w == "vehicleParameters":
            p = m.vehicleParameters
            R["vp"].append((t, g(p,"steerRatio"), g(p,"stiffnessFactor"), g(p,"angleOffsetDeg"), g(p,"angleOffsetAverageDeg"), g(p,"roll"), g(p,"valid")))
        elif w == "lateralTorqueParameters":
            p = m.lateralTorqueParameters
            R["ltp"].append((t, g(p,"latAccelFactorFiltered"), g(p,"frictionCoefficientFiltered"), g(p,"latAccelFactorRaw"), g(p,"frictionCoefficientRaw"),
                             g(p,"liveValid"), g(p,"useParams"), g(p,"totalBucketPoints"), g(p,"calPerc")))
        elif w == "lateralDelay":
            p = m.lateralDelay
            R["ld"].append((t, g(p,"lateralDelay"), g(p,"lateralDelayEstimate"), str(g(p,"status","")), g(p,"calPerc")))
        elif w == "gpsLocationExternal":
            p = m.gpsLocationExternal
            R["gps"].append((t, p.latitude, p.longitude, p.speed, p.bearingDeg, p.unixTimestampMillis))
        elif w == "onroadEvents":
            for e in m.onroadEvents: R["events"].append((t, str(e.name)))
        elif w in ("userBookmark", "bookmarkButton"):
            R["bm"].append((t, w))
        elif w == "carParams":
            cp = m.carParams
            R["misc"].append(("carParams", dict(fp=cp.carFingerprint, steerRatio=cp.steerRatio, lat=str(cp.lateralTuning), steerActuatorDelay=cp.steerActuatorDelay,
                             flags=cp.flags, fuzzy=cp.fuzzyFingerprint, dashcam=cp.dashcamOnly, safety=str(cp.safetyConfigs), maxLat=cp.maxLateralAccel, wheelbase=cp.wheelbase)))
        elif w == "carParamsSP":
            R["misc"].append(("carParamsSP", str(m.carParamsSP)[:3000]))
        elif w == "initData":
            try:
                pr = {e.key: bytes(e.value)[:80] for e in m.initData.params.entries}
                R["misc"].append(("params", {k: v for k, v in pr.items() if any(s in k for s in ("Jerk","Torque","Nnlc","NeuralNetwork","Lateral","Mads","Experimental","LiveDelay","LagdToggle","Enforce","Custom"))}))
            except Exception as e: R["misc"].append(("params_err", str(e)))
        elif w == "pandaStates":
            p = m.pandaStates[0]
            if int(t*2) % 20 == 0: R["misc"].append(("panda", (t, str(p.safetyModel), p.safetyParam, p.safetyTxBlocked, p.safetyRxInvalid, p.controlsAllowed, str(p.faultStatus), p.relayMalfunction if hasattr(p,"relayMalfunction") else None)))
    res = {"tkeys": tkeys}
    for k, v in R.items():
        res[k] = v if k in ("ss","events","bm","misc","ld") else np.array(v, dtype=np.float64)
    with open(out, "wb") as f: pickle.dump(res, f)
    return seg

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    paths = []
    for r in sys.argv[1:]: paths += glob.glob(f"/data/media/0/realdata/{r}--*/rlog.zst")
    with Pool(4) as p:
        for s in p.imap_unordered(do, sorted(paths)): print(s, flush=True)
