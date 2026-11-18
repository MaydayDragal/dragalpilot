"""Open-loop comparison of ways to smooth the model's steering request, on logged planned paths.

  python smooth_methods.py <route>.plan.npy [...]        (files from plan_dump.py)

For every modelV2 frame the request is rebuilt from the logged plan exactly as modeld does
(get_curvature_from_plan), for any look-ahead, and each method is applied to that sequence. This shows what a
method does to the request on the same road; it does not show how the car and the model would then respond.
"""
import sys
import numpy as np

DT = 0.05
T = np.array([10.0 * (i / 32) ** 2 for i in range(33)])
BASE = 0.05 + 0.025          # frame delay + action delay added by modeld
MIN_STABLE_DELAY = 0.3

def curv(yaw, rate0, v, action_t):
    """get_curvature_from_plan for all frames at one look-ahead (array or scalar per frame)."""
    at = np.broadcast_to(np.asarray(action_t, float), v.shape)
    psi = np.array([np.interp(max(a, MIN_STABLE_DELAY), T, y) for a, y in zip(at, yaw)])
    psi = np.where(at < MIN_STABLE_DELAY, at / MIN_STABLE_DELAY * psi, psi)
    vv = np.clip(v, 1.0, None)
    return 2 * psi / (vv * at) - rate0 / vv

def lp1(x, tau, reset):
    if tau <= 0: return x.copy()
    a = 1 - np.exp(-DT / tau); y = np.empty_like(x); prev = x[0]
    for i in range(len(x)):
        if reset[i]: prev = x[i]
        prev = a * x[i] + (1 - a) * prev; y[i] = prev
    return y

def runs(m, minlen):
    idx = np.flatnonzero(np.diff(np.r_[0, m.astype(int), 0])); return [(a, b) for a, b in zip(idx[::2], idx[1::2]) if b - a >= minlen]

def band(x, lo, hi):
    X = np.fft.rfft(x - x.mean()); f = np.fft.rfftfreq(len(x), DT); k = (f >= lo) & (f <= hi)
    return np.sqrt(2 * (np.abs(X[k]) ** 2).sum()) / len(x)

for path in sys.argv[1:]:
    a = np.load(path); t, v, act, pressed, blink, delay, logged = (a[:, i] for i in range(7))
    llp, rlp = a[:, 9], a[:, 10]; yaw = a[:, 11:44]; rate0 = a[:, 44]
    delay = np.where(np.isnan(delay), np.nanmedian(delay), delay); d = delay + BASE
    gap = np.r_[True, np.diff(t) > 0.2]; reset = gap | (np.r_[0, act[:-1]] < 0.5)   # modeld restarts the filter when lat is not active
    base = curv(yaw, rate0, v, d)
    ok = (act > 0.5) & (v > 0.3)
    err = (base - logged)[ok] * v[ok] ** 2
    print(f"\n{path}\n  frames {len(a)}, {t[-1]-t[0]:.0f} s, published delay {np.nanmin(delay):.3f}-{np.nanmax(delay):.3f} s")
    print(f"  reconstruction check (no smoothing, lat active): request rebuilt from the plan vs logged action, in m/s2: RMS diff {np.sqrt(np.mean(err**2)):.4f}, "
          f"p99 |diff| {np.percentile(np.abs(err), 99):.4f}; RMS of the logged request {np.sqrt(np.mean((logged[ok]*v[ok]**2)**2)):.3f}")

    def avg_plan(center, w, n=9):
        return np.mean([curv(yaw, rate0, v, center + u) for u in np.linspace(-w / 2, w / 2, n)], axis=0)
    M = {
        "A  no smoothing":                        base,
        "B  filter 0.2 s + look-ahead 0.2":       lp1(curv(yaw, rate0, v, d + 0.2), 0.2, reset),
        "B' filter 0.2 s, no extra look-ahead":   lp1(base, 0.2, reset),
        "C  filter 0.3 s + look-ahead 0.3":       lp1(curv(yaw, rate0, v, d + 0.3), 0.3, reset),
        "D  filter 0.2 s + look-ahead 0.3":       lp1(curv(yaw, rate0, v, d + 0.2 + 0.1), 0.2, reset),
        "E  plan average +/-0.2 s, no filter":    avg_plan(d, 0.4),
        "E' plan average +/-0.4 s, no filter":    avg_plan(d + 0.2, 0.8),
        "F  two-stage 2x0.1 s + look-ahead 0.2":  lp1(lp1(curv(yaw, rate0, v, d + 0.2), 0.1, reset), 0.1, reset),
        "F' two-stage 2x0.15 s + look-ahead 0.3": lp1(lp1(curv(yaw, rate0, v, d + 0.3), 0.15, reset), 0.15, reset),
        "G  filter 0.2 s + look-ahead 0.10":      lp1(curv(yaw, rate0, v, d + 0.10), 0.2, reset),
        "G' filter 0.2 s + look-ahead 0.15":      lp1(curv(yaw, rate0, v, d + 0.15), 0.2, reset),
        "H  filter 0.3 s + look-ahead 0.15":      lp1(curv(yaw, rate0, v, d + 0.15), 0.3, reset),
        "H' filter 0.3 s + look-ahead 0.20":      lp1(curv(yaw, rate0, v, d + 0.20), 0.3, reset),
        "I  no filter, look-ahead -0.10":         curv(yaw, rate0, v, d - 0.10),
        "I' no filter, look-ahead +0.10":         curv(yaw, rate0, v, d + 0.10),
    }
    LA = {k: x * v ** 2 for k, x in M.items()}
    N = 512; w = np.hanning(N); f = np.fft.rfftfreq(N, DT)
    for name, lo, hi in ((">60 mph", 26.8, 99), ("25-45 mph", 11, 20)):
        sel = (act > 0.5) & (pressed < 0.5) & (blink < 0.5) & (v >= lo) & (v < hi)
        rr = [(s + 20, e - 20) for s, e in runs(sel, 240)]; wts = [e - s for s, e in rr]
        if not rr: print(f"\n  {name}: no data"); continue
        straight = sel & (np.abs(np.convolve(LA["A  no smoothing"], np.ones(100) / 100, mode="same")) < 0.35) & (llp > 0.5) & (rlp > 0.5)
        win = [slice(s, s + N) for s0, e0 in runs(straight, N + 40) for s in range(s0 + 20, e0 - 20 - N + 1, N // 2)]
        print(f"\n  {name}: {sum(wts)*DT:.0f} s hands-off; {len(win)} straight windows of 25.6 s")
        print("    method                                  step RMS   0.7-4 Hz   1-4 Hz  | vs A on straights: gain / phase lead(+) deg at 0.2-0.3, 0.3-0.45, 0.45-0.7 Hz | RMS diff vs A")
        ref = LA["A  no smoothing"]
        for k, x in LA.items():
            step = np.sqrt(np.average([np.mean(np.diff(x[s:e]) ** 2) for s, e in rr], weights=wts)) / DT
            b1 = np.average([band(x[s:e], 0.7, 4) for s, e in rr], weights=wts); b2 = np.average([band(x[s:e], 1, 4) for s, e in rr], weights=wts)
            dif = np.sqrt(np.average([np.mean((x[s:e] - ref[s:e]) ** 2) for s, e in rr], weights=wts))
            ph = ""
            if len(win) >= 3:
                Pxx = 0; Pxy = 0
                for sl in win:
                    X = np.fft.rfft((ref[sl] - ref[sl].mean()) * w); Y = np.fft.rfft((x[sl] - x[sl].mean()) * w); Pxx = Pxx + abs(X) ** 2; Pxy = Pxy + np.conj(X) * Y
                for b0, b1_ in ((0.2, 0.3), (0.3, 0.45), (0.45, 0.7)):
                    kk = (f >= b0) & (f < b1_); H = Pxy[kk].sum() / Pxx[kk].sum(); ph += f"  {abs(H):4.2f}/{np.degrees(np.angle(H)):+4.0f}"
            print(f"    {k:40s} {step:7.3f}   {b1:7.4f}  {b2:7.4f}  |{ph or '   (too few windows)':60s} | {dif:.4f}")
    print("    step RMS = RMS change of the requested lateral acceleration from one model frame to the next, per second (m/s3)")
