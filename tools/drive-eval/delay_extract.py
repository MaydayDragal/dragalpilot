"""Extracts the signals needed to measure steering delay from a route's rlogs on the PC (pclog), 100 Hz, into one .npz.

  CEREAL_DIR=... CAR_CAPNP_DIR=... python delay_extract.py <out.npz> <rlog glob>

Signals: speed, steering angle, hands, blinker, lat active, the request (controlsState.desiredCurvature), the
controller's measured curvature, torque sent (counts), the vehicle's yaw rate (livePose or liveLocationKalman, 20 Hz) and the raw gyroscope (100 Hz),
lane-line positions and probabilities, the model's own curvature request, lagd's delay and estimate, angle offset."""
import sys, glob, numpy as np
import pclog

out, pat = sys.argv[1], sys.argv[2]
paths = sorted(glob.glob(pat), key=lambda p: int(p.replace("\\", "/").split("/")[-2].rsplit("--", 1)[1]))
S = {k: [] for k in ("cs", "ctl", "co", "cc", "pose", "gyro", "model", "ld", "lp")}
for p in paths:
    for m in pclog.read(p):
        w = m.which(); t = m.logMonoTime * 1e-9
        if w == "carState":
            c = m.carState; S["cs"].append((t, c.vEgo, c.steeringAngleDeg, c.steeringPressed, c.leftBlinker or c.rightBlinker, c.steeringRateDeg))
        elif w == "controlsState":
            c = m.controlsState; S["ctl"].append((t, c.desiredCurvature, c.curvature))
        elif w == "carOutput":
            S["co"].append((t, m.carOutput.actuatorsOutput.torqueOutputCan))
        elif w == "carControl":
            S["cc"].append((t, m.carControl.latActive))
        elif w == "livePose":
            c = m.livePose
            S["pose"].append((t, c.angularVelocityDevice.z))
        elif w == "liveLocationKalman":
            c = m.liveLocationKalman
            if len(c.angularVelocityCalibrated.value) == 3: S["pose"].append((t, c.angularVelocityCalibrated.value[2]))
        elif w == "gyroscope":
            g = m.gyroscope.gyroUncalibrated.v
            if len(g) == 3: S["gyro"].append((t, g[0], g[1], g[2]))
        elif w == "modelV2":
            c = m.modelV2
            try: S["model"].append((t, c.laneLines[1].y[0], c.laneLines[2].y[0], c.laneLineProbs[1], c.laneLineProbs[2], c.action.desiredCurvature))
            except Exception: pass
        elif w == "lateralDelay":
            c = m.lateralDelay; S["ld"].append((t, c.lateralDelay, c.lateralDelayEstimate))
        elif w == "liveParameters":
            c = m.liveParameters; S["lp"].append((t, c.angleOffsetDeg, c.steerRatio, c.roll))
A = {k: np.array(v, dtype=float) for k, v in S.items()}
t = np.arange(A["cs"][0, 0], A["cs"][-1, 0], 0.01)
I = lambda k, c: np.interp(t, A[k][:, 0], A[k][:, c]) if len(A[k]) else np.full(len(t), np.nan)
np.savez_compressed(out, t=t, v=I("cs", 1), ang=I("cs", 2), hands=I("cs", 3), blink=I("cs", 4), rate=I("cs", 5),
                    req=I("ctl", 1), meas=I("ctl", 2), tq=I("co", 1), lat=I("cc", 1), yaw=I("pose", 1), gx=I("gyro", 1), gy=I("gyro", 2), gz=I("gyro", 3),
                    ll=I("model", 1), rl=I("model", 2), llp=I("model", 3), rlp=I("model", 4), mreq=I("model", 5),
                    delay=I("ld", 1), delay_est=I("ld", 2), ang_off=I("lp", 1), sr=I("lp", 2), roll=I("lp", 3))
print(out, len(paths), "segments", round(len(t) / 6000, 1), "min; pose", len(A["pose"]), "gyro", len(A["gyro"]), "model", len(A["model"]))
