import sys, pickle, numpy as np
d = pickle.load(open("loopfit.pkl", "rb")); P = d["Pa"]; BANDS = d["BANDS"]
fc = np.array([(a + b) / 2 for a, b in BANDS]); W = 2j * np.pi * fc
TAU, KP, KI, TD = 0.19, 0.8, 0.15, 0.15
def predict(laf, fr, thr=0.2, kd=0.0, lp_hz=1.2, kp=KP):
    sf = fr / thr; D = np.exp(-W * TAU); lp = 1 / (1 + W / (2 * np.pi * lp_hz))
    num = 1 / laf + kp * D / laf + KI * D / (W * laf) + sf + kd * W * lp / laf     # jerk-aware law, fitted: no look-ahead jerk on straights
    den = kp / laf + KI / (W * laf) + sf
    T = P * num / (1 + P * den) * np.exp(-W * TD)
    return T / D, num / (1 + P * den)
print("jerk-aware controller, fitted model.  per band: gain|lag(deg)   then torque per unit request at 0.45-0.7 / 0.7-1.0 / 1.0-1.5 Hz, and feedback gain on error (torque per m/s2)")
print("bands: " + "  ".join(f"{a:.2f}-{b:.2f}" for a, b in BANDS))
rows = [("now 4.8 / .07", 4.8, .07, .2, 0), ("4.5 / .07", 4.5, .07, .2, 0), ("4.5 / .05", 4.5, .05, .2, 0), ("4.5 / .04", 4.5, .04, .2, 0), ("4.5 / .03", 4.5, .03, .2, 0),
        ("3.7 / .04", 3.7, .04, .2, 0), ("3.7 / .03", 3.7, .03, .2, 0),
        ("4.5 / .07 +lead .2", 4.5, .07, .2, .2), ("4.5 / .04 +lead .2", 4.5, .04, .2, .2), ("4.5 / .04 +lead .4", 4.5, .04, .2, .4), ("4.5 / .04 +lead .6", 4.5, .04, .2, .6),
        ("4.5 / .03 +lead .4", 4.5, .03, .2, .4), ("4.5 / .03 +lead .6", 4.5, .03, .2, .6), ("3.7 / .03 +lead .4", 3.7, .03, .2, .4), ("3.7 / .03 +lead .6", 3.7, .03, .2, .6),
        ("3.7 / .02 +lead .6", 3.7, .02, .2, .6), ("3.7 / .02 +lead .8", 3.7, .02, .2, .8)]
for name, laf, fr, thr, kd in rows:
    H, U = predict(laf, fr, thr, kd)
    print(f" {name:20s} " + " ".join(f"{abs(h):.2f}|{-np.degrees(np.angle(h)):3.0f}" for h in H) + f"   u: {abs(U[3]):.2f} {abs(U[4]):.2f} {abs(U[5]):.2f}   fb {KP/laf + fr/thr:.2f}")
