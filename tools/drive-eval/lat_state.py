"""What the steering controller was working with on each route: learned values, params, settings. PC.

  python lat_state.py <lateral extract dir> <route> ...

Per route: learned torque parameters (factor, friction, whether used), learned steer ratio / stiffness / angle offset,
learned delay, lateral params at start, and measured basics above 60 mph hands-off (speed, torque rms, lane probability,
lane width, share of time with a lead-free road is not known here)."""
import sys, glob, os, pickle, re
import numpy as np

D = sys.argv[1]
print("route segs | torque factor  friction  used  cal% | steerRatio stiff  offset deg | delay  est | >60 mph hands-off: min  speed  lane prob  lane width m  torque rms  angle-rate rms | params")
for r in sys.argv[2:]:
    fs = sorted(glob.glob(os.path.join(D, r + "--*.pkl")), key=lambda p: int(re.search(r"--(\d+)\.pkl", p).group(1)))
    if not fs: continue
    ltp = []; vp = []; ld = []; prm = None; acc = []
    for f in fs:
        R = pickle.load(open(f, "rb"))
        if len(R["ltp"]): ltp.append(R["ltp"])
        if len(R["vp"]): vp.append(R["vp"])
        ld += list(R["ld"])
        for k, v in R["misc"]:
            if k == "params" and prm is None: prm = v
        cs, cc, md = R["cs"], R["cc"], R["model"]
        if len(cs) < 100 or len(cc) < 100 or len(md) < 20: continue
        t = cs[:, 0]; lat = np.interp(t, cc[:, 0], cc[:, 1]) > 0.5
        m = lat & (cs[:, 1] > 26.8) & (cs[:, 7] < 0.5) & (cs[:, 10] < 0.5)
        if m.sum() < 200: continue
        pl = np.interp(t, md[:, 0], md[:, 3]); pr = np.interp(t, md[:, 0], md[:, 4]); w = np.interp(t, md[:, 0], md[:, 2] - md[:, 1])
        acc.append((m.sum() / 100, cs[m, 1].mean(), ((pl + pr) / 2)[m].mean(), np.median(w[m]), np.sqrt(np.mean(cs[m, 6] ** 2)), np.sqrt(np.mean(cs[m, 4] ** 2))))
    L = np.vstack(ltp) if ltp else np.full((1, 9), np.nan); V = np.vstack(vp) if vp else np.full((1, 7), np.nan)
    A = np.array(acc) if acc else np.full((1, 6), np.nan); wt = A[:, 0]
    av = lambda c: np.nansum(A[:, c] * wt) / np.nansum(wt)
    dl = [x[1] for x in ld]; de = [x[2] for x in ld]
    keep = {k: v.decode(errors="replace") for k, v in (prm or {}).items() if any(s in k for s in ("TorqueControlTune", "LateralTorque", "LiveTorque", "CustomTorque", "Nnlc", "NeuralNetwork", "Lagd", "EnforceTorque", "TorqueParams"))}
    print(f"{r[-2:]}  {len(fs):3d} | {L[0, 1]:.3f}->{L[-1, 1]:.3f}  {L[0, 2]:.3f}->{L[-1, 2]:.3f}  {np.nanmean(L[:, 6]):.0f}  {L[-1, 8]:3.0f} | "
          f"{V[0, 1]:.2f}->{V[-1, 1]:.2f} {V[-1, 2]:.2f} {V[0, 4]:+.2f}->{V[-1, 4]:+.2f} | {np.median(dl) if dl else float('nan'):.2f} {np.median(de) if de else float('nan'):.2f} | "
          f"{np.nansum(wt) / 60:4.1f} {av(1) * 2.237:5.1f} {av(2):.2f} {av(3):.2f} {av(4):6.1f} {av(5):5.2f} | {keep}")
