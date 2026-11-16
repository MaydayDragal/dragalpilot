import sys, numpy as np
sys.path.insert(0, sys.argv[1]); from lib import load
R = {}
for D in sys.argv[2:]: R.update(load(D))
CFG = {"000000a3":"5.0/.04 enf", "000000a4":"5.0/.04 enf+jerk", "000000a5":"5.0/.04 enf", "000000a6":"5.0/.04 enf", "000000a7":"4.0/.07 enf", "000000aa":"4.0/.07 enf+jerk", "000000ab":"enforce OFF"}
GROUPS = {"5.0/.04 enf": ["000000a3","000000a5","000000a6"], "4.0/.07 enf": ["000000a7"], "4.0/.07 enf+jerk": ["000000aa"], "enforce OFF": ["000000ab"], "4.5/.07 enf+jerk": ["000000ac"], "4.8/.07 enf+jerk": ["000000ad","000000ae","000000af","000000b0","000000b1","000000b4"]}
N = 2048  # 20.48 s windows, 0.049 Hz resolution
def runs(m, minlen):
    idx = np.flatnonzero(np.diff(np.r_[0, m.astype(int), 0])); return [(a, b) for a, b in zip(idx[::2], idx[1::2]) if b - a >= minlen]
def lowpass(x, n=500): return np.convolve(x, np.ones(n) / n, mode="same")
def windows(d, lo, hi):
    ok = d["latActive"] & ~d["pressed"] & ~d["blink"] & (np.abs(d["drv"]) < 80) & (d["v"] >= lo) & (d["v"] < hi) & (np.abs(lowpass(d["desiredLateralAccel"])) < 0.35) & (d["llp"] > 0.5) & (d["rlp"] > 0.5)
    for a, b in runs(ok, N + 200):
        for s in range(a + 100, b - 100 - N + 1, N // 2): yield slice(s, s + N)
f = np.fft.rfftfreq(N, 0.01); w = np.hanning(N)
def spec(x): return np.fft.rfft((x - x.mean()) * w)
bands = [(0.1, 0.2), (0.2, 0.3), (0.3, 0.45), (0.45, 0.7), (0.7, 1.0), (1.0, 2.0)]
for bandname, lo, hi in ((">60 mph", 26.8, 99), ("35-60 mph", 15.6, 26.8)):
    print(f"\n===== straight stretches, {bandname} =====")
    for g, routes in GROUPS.items():
        acc = dict(n=0); keys = ["lane", "des", "act", "ang", "tq", "des_act", "lane_des", "tq_act", "des_tq"]
        P = {k: 0 for k in keys}
        for r in routes:
            d = R[r]; lanec = (d["ll"] + d["rl"]) / 2
            for sl in windows(d, lo, hi):
                L, D_, A, G, T = spec(lanec[sl]), spec(d["desiredLateralAccel"][sl]), spec(d["actualLateralAccel"][sl]), spec(d["ang"][sl]), spec(d["out"][sl])
                P["lane"] += abs(L)**2; P["des"] += abs(D_)**2; P["act"] += abs(A)**2; P["ang"] += abs(G)**2; P["tq"] += abs(T)**2
                P["des_act"] += np.conj(D_) * A; P["lane_des"] += np.conj(L) * D_; P["tq_act"] += np.conj(T) * A; P["des_tq"] += np.conj(D_) * T
                acc["n"] += 1
        n = acc["n"]
        if n < 4: print(f"{g:18s} too little data ({n} windows)"); continue
        scale = 2 / (n * (w**2).sum() * N) * N  # power per bin -> amplitude^2 (approx)
        print(f"{g:18s} windows {n} ({n*N/200:.0f} s)")
        print("   band(Hz)   laneRMS(cm)  desLA   actLA  act/des gain  act lag(deg)  coh(des,act)  des per m of lane  coh(lane,des)  wheel(deg)")
        for a, b in bands:
            k = (f >= a) & (f < b)
            rms = lambda p: np.sqrt(p[k].sum() * 2 / (n * (w**2).sum() * N) * 1.0) * np.sqrt(N) / np.sqrt(N)
            amp = lambda p: np.sqrt(2 * p[k].sum() / n) / w.sum() * np.sqrt(2) / np.sqrt(2)
            H = P["des_act"][k].sum() / P["des"][k].sum(); coh = abs(P["des_act"][k].sum())**2 / (P["des"][k].sum() * P["act"][k].sum())
            Hl = P["lane_des"][k].sum() / P["lane"][k].sum(); cohl = abs(P["lane_des"][k].sum())**2 / (P["lane"][k].sum() * P["des"][k].sum())
            print(f"   {a:.2f}-{b:.2f}   {amp(P['lane'])*100:8.2f}   {amp(P['des']):6.3f}  {amp(P['act']):6.3f}   {abs(H):8.2f}   {-np.degrees(np.angle(H)):9.0f}   {coh:10.2f}   {abs(Hl):12.2f}   {cohl:10.2f}   {amp(P['ang']):8.3f}")
        pk = (f >= 0.1) & (f <= 2); lane_psd = P["lane"][pk] * f[pk]
        print(f"   lane-offset peak at {f[pk][np.argmax(P['lane'][pk])]:.2f} Hz; actual-LA peak at {f[pk][np.argmax(P['act'][pk])]:.2f} Hz; wheel peak at {f[pk][np.argmax(P['ang'][pk])]:.2f} Hz")
