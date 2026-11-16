# Small-signal model of the straight-road steering loop, from logs.
#  1) identify the plant P(f): torque sent -> measured lateral accel, using the request as instrument
#  2) write the controller's small-signal law from the source (standard and jerk-aware), predict request->actual response
#  3) validate against the measured response per configuration, then predict candidate settings
import sys, numpy as np
sys.path.insert(0, sys.argv[1]); from lib import load
R = {}
for D in sys.argv[2:]: R.update(load(D))
N = 2048; f = np.fft.rfftfreq(N, 0.01); w = np.hanning(N); W = 2j * np.pi * f
def runs(m, minlen):
    idx = np.flatnonzero(np.diff(np.r_[0, m.astype(int), 0])); return [(a, b) for a, b in zip(idx[::2], idx[1::2]) if b - a >= minlen]
def lowpass(x, n=500): return np.convolve(x, np.ones(n) / n, mode="same")
def windows(d, lo=26.8, hi=99):
    r = d["dcurv"] * d["v"] ** 2
    ok = d["latActive"] & ~d["pressed"] & ~d["blink"] & (np.abs(d["drv"]) < 80) & (d["v"] >= lo) & (d["v"] < hi) & (np.abs(lowpass(r)) < 0.35) & (d["llp"] > 0.5) & (d["rlp"] > 0.5)
    for a, b in runs(ok, N + 200):
        for s in range(a + 100, b - 100 - N + 1, N // 2): yield slice(s, s + N)
sp = lambda x: np.fft.rfft((x - x.mean()) * w)
def spectra(routes):
    S = dict(rr=0, ry=0, ru=0, yy=0, uu=0, dd=0, dy=0, n=0, v=[])
    for r_ in routes:
        d = R[r_]; req = d["dcurv"] * d["v"] ** 2
        for sl in windows(d):
            Rq, Y, U, Dd = sp(req[sl]), sp(d["actualLateralAccel"][sl]), sp(-d["out"][sl]), sp(d["desiredLateralAccel"][sl])
            S["rr"] += abs(Rq) ** 2; S["ry"] += np.conj(Rq) * Y; S["ru"] += np.conj(Rq) * U; S["yy"] += abs(Y) ** 2; S["uu"] += abs(U) ** 2
            S["dd"] += abs(Dd) ** 2; S["dy"] += np.conj(Dd) * Y; S["n"] += 1; S["v"].append(d["v"][sl].mean())
    return S
BANDS = [(0.1, 0.2), (0.2, 0.3), (0.3, 0.45), (0.45, 0.7), (0.7, 1.0), (1.0, 1.5)]
def bandavg(num, den):
    return [num[(f >= a) & (f < b)].sum() / den[(f >= a) & (f < b)].sum() for a, b in BANDS]
JERK = ["000000aa", "000000ac", "000000ad", "000000ae", "000000af", "000000b0", "000000b1", "000000b4"]
STD = ["000000a3", "000000a5", "000000a6", "000000a7"]
CONF = {"std 5.0/.04": (["000000a3","000000a5","000000a6"], 5.0, 0.04, False), "std 4.0/.07": (["000000a7"], 4.0, 0.07, False),
        "jerk 4.0/.07": (["000000aa"], 4.0, 0.07, True), "jerk 4.5/.07": (["000000ac"], 4.5, 0.07, True),
        "jerk 4.8/.07": (["000000ad","000000ae","000000af","000000b0","000000b1","000000b4"], 4.8, 0.07, True)}
# --- plant
Sj, Ss, Sa = spectra(JERK), spectra(STD), spectra(JERK + STD)
Pj, Ps, Pa = (np.array(bandavg(S["ry"], S["ru"])) for S in (Sj, Ss, Sa))
print(f"plant P = lat accel per unit torque (instrument: request).  windows jerk {Sj['n']} std {Ss['n']}, mean speed {np.mean(Sa['v'])*2.237:.0f} mph")
print(" band      |P| jerk-on  phase   |P| std  phase   |P| all  phase(deg)")
for (a, b), pj, ps, pa in zip(BANDS, Pj, Ps, Pa):
    print(f" {a:.2f}-{b:.2f}   {abs(pj):6.2f}  {np.degrees(np.angle(pj)):6.0f}   {abs(ps):6.2f}  {np.degrees(np.angle(ps)):6.0f}   {abs(pa):6.2f}  {np.degrees(np.angle(pa)):6.0f}")
fc = np.array([(a + b) / 2 for a, b in BANDS]); Wc = 2j * np.pi * fc
TAU = 0.19; KP = 0.8; KI = 0.15; THR = 0.2
def predict(P, laf, fr, jerk, a=1.0, kj=None, thr=THR, kp=KP, tau=TAU, lead=0.0):
    """returns (H = actual / delayed setpoint, U = torque per unit request). lead: extra seconds the friction input looks ahead"""
    sf = fr / thr; D = np.exp(-Wc * tau); lp = 1 / (1 + Wc / (2 * np.pi * 1.2))
    if jerk:
        kj = 0.4 if kj is None else kj
        num = 1 / laf + kp * D / laf + KI * D / (Wc * laf) + sf * (a * np.exp(Wc * lead) + kj * Wc)
        den_fb = kp / laf + KI / (Wc * laf) + sf * a
    else:
        kj = 0.3 if kj is None else kj
        num = 1 / laf + kp * D / laf + KI * D / (Wc * laf) + sf * (D + kj * Wc * lp)
        den_fb = kp / laf + KI / (Wc * laf) + sf
    T = P * num / (1 + P * den_fb)        # y / r
    return T / D, num / (1 + P * den_fb)   # y / r_delayed, u / r
print("\nvalidation: measured vs predicted (actual / delayed setpoint)  gain, lag(deg)")
for name, (routes, laf, fr, jerk) in CONF.items():
    S = spectra(routes); Hm = np.array(bandavg(S["dy"], S["dd"])); Hp, _ = predict(Pa, laf, fr, jerk)
    print(f" {name:13s} n={S['n']:3d} " + "  ".join(f"{abs(m):.2f}/{abs(p):.2f} {-np.degrees(np.angle(m)):3.0f}/{-np.degrees(np.angle(p)):3.0f}" for m, p in zip(Hm, Hp)))
print("   bands: " + "  ".join(f"{a:.2f}-{b:.2f}" for a, b in BANDS) + "   (measured/predicted)")
print("\ncandidates (jerk on unless noted): gain | lag(deg) per band, then torque per unit request at 0.45-1.0 Hz (wheel business proxy)")
C = [("now: 4.8 / 0.07", dict(laf=4.8, fr=0.07, jerk=True)), ("4.5 / 0.07", dict(laf=4.5, fr=0.07, jerk=True)), ("4.5 / 0.05", dict(laf=4.5, fr=0.05, jerk=True)),
     ("4.5 / 0.04", dict(laf=4.5, fr=0.04, jerk=True)), ("4.5 / 0.03", dict(laf=4.5, fr=0.03, jerk=True)), ("4.0 / 0.04", dict(laf=4.0, fr=0.04, jerk=True)),
     ("3.7 / 0.04", dict(laf=3.7, fr=0.04, jerk=True)), ("3.7 / 0.03", dict(laf=3.7, fr=0.03, jerk=True)), ("3.7 / 0.02", dict(laf=3.7, fr=0.02, jerk=True)),
     ("4.0 / 0.07 thr 0.4", dict(laf=4.0, fr=0.07, jerk=True, thr=0.4)), ("3.7 / 0.07 thr 0.5", dict(laf=3.7, fr=0.07, jerk=True, thr=0.5)),
     ("std 4.0 / 0.04", dict(laf=4.0, fr=0.04, jerk=False)), ("std 3.7 / 0.03", dict(laf=3.7, fr=0.03, jerk=False))]
for name, kw in C:
    H, U = predict(Pa, **kw)
import itertools
meas = {}
for name, (routes, laf, fr, jerk) in CONF.items():
    S = spectra(routes); meas[name] = (np.array(bandavg(S["dy"], S["dd"])), S["n"])
def err(kjj, kjs, a, td):
    e = 0; nn = 0
    for name, (routes, laf, fr, jerk) in CONF.items():
        Hm, n = meas[name]
        Hp, _ = predict(Pa, laf, fr, jerk, a=a, kj=(kjj if jerk else kjs))
        Hp = Hp * np.exp(-Wc * td)
        e += n * np.sum(np.abs(np.log(Hp[:5] / Hm[:5])) ** 2); nn += n * 5
    return np.sqrt(e / nn)
best = min(((err(kjj, kjs, a, td), kjj, kjs, a, td) for kjj in (0, 0.05, 0.1, 0.2, 0.4) for kjs in (0, 0.1, 0.3) for a in (0.7, 1.0) for td in (0, 0.05, 0.1, 0.15, 0.2, 0.3)), key=lambda x: x[0])
print("\nbest fit (rms log error, kj_jerk, kj_std, a, extra delay s):", [round(x, 3) for x in best])
for kjj, kjs, a, td in [(0.4, 0.3, 1.0, 0.0), (0, 0, 1.0, 0.0), best[1:]]:
    print(f" kj_jerk={kjj} kj_std={kjs} a={a} td={td}: err {err(kjj, kjs, a, td):.3f}")
kjj, kjs, a, td = best[1:]
print("validation with fitted terms: measured/predicted gain, lag")
for name, (routes, laf, fr, jerk) in CONF.items():
    Hm, n = meas[name]; Hp, _ = predict(Pa, laf, fr, jerk, a=a, kj=(kjj if jerk else kjs)); Hp = Hp * np.exp(-Wc * td)
    print(f" {name:13s} n={n:3d} " + "  ".join(f"{abs(m):.2f}/{abs(p):.2f} {-np.degrees(np.angle(m)):3.0f}/{-np.degrees(np.angle(p)):3.0f}" for m, p in zip(Hm, Hp)))
import pickle; pickle.dump(dict(Pa=Pa, fit=best, BANDS=BANDS), open("loopfit.pkl", "wb"))
