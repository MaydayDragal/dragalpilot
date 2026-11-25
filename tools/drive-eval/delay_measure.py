"""Measures the steering delay chain from delay_extract.py files, and where the car sits in the lane through curves.

  python delay_measure.py <label>=<file.npz> ...

Chain (all as lateral acceleration, band 0.1-2 Hz, hands off, steering active, no blinker):
  model request -> request the controller uses -> torque -> wheel (steering angle) -> vehicle (yaw rate x speed)
Each delay is the lag of the cross-correlation peak (parabola through the three points around it), and separately the
delay read from the phase of the cross-spectrum in three frequency bands (a pure delay gives the same value in each
band; a lag that shrinks with frequency is a first-order response, not dead time).
Curves: mean position toward the inside of the turn while the request is building, steady and unwinding. Late steering
runs wide on the way in and inside on the way out; early steering does the opposite."""
import sys, numpy as np

def ma(x, n): return np.convolve(x, np.ones(n) / n, "same")
def bp(x): return ma(x, 5) - ma(x, 500)                       # roughly 0.1-2 Hz at 100 Hz
def runs(m, minlen):
    idx = np.flatnonzero(np.diff(np.r_[0, m.astype(int), 0])); return [(a, b) for a, b in zip(idx[::2], idx[1::2]) if b - a >= minlen]
def xlag(x, y, m, lo=-30, hi=120):
    """seconds by which y trails x on the samples in mask m; positive = y later"""
    best = []
    L = np.arange(lo, hi + 1)
    c = np.array([np.corrcoef(x[m], np.roll(y, -l)[m])[0, 1] for l in L])
    i = int(np.argmax(c))
    if 0 < i < len(c) - 1:
        d = (c[i - 1] - c[i + 1]) / (2 * (c[i - 1] - 2 * c[i] + c[i + 1])); return (L[i] + d) / 100, c[i]
    return L[i] / 100, c[i]
def phase_delay(x, y, m, N=2048):
    f = np.fft.rfftfreq(N, 0.01); w = np.hanning(N); Sxy = 0; Sxx = 0; Syy = 0
    for a, b in runs(m, N):
        for s in range(a, b - N + 1, N // 2):
            X = np.fft.rfft((x[s:s + N] - x[s:s + N].mean()) * w); Y = np.fft.rfft((y[s:s + N] - y[s:s + N].mean()) * w)
            Sxy = Sxy + np.conj(X) * Y; Sxx = Sxx + abs(X) ** 2; Syy = Syy + abs(Y) ** 2
    out = []
    if np.isscalar(Sxx): return [(np.nan, np.nan, np.nan)] * 3
    for lo, hi in ((0.1, 0.3), (0.3, 0.6), (0.6, 1.2)):
        k = (f >= lo) & (f < hi); H = Sxy[k].sum() / Sxx[k].sum(); coh = abs(Sxy[k].sum()) ** 2 / (Sxx[k].sum() * Syy[k].sum())
        fc = (f[k] * Sxx[k]).sum() / Sxx[k].sum(); out.append((-np.angle(H) / (2 * np.pi * fc), abs(H), coh))
    return out

for arg in sys.argv[1:]:
    label, path = arg.split("=", 1); d = dict(np.load(path)); v = d["v"]
    req = d["req"] * v ** 2; mreq = d["mreq"] * v ** 2; wheel = d["meas"] * v ** 2; tq = d["tq"]
    g = np.c_[d["gx"], d["gy"], d["gz"]]
    ok0 = (d["lat"] > 0.5) & (d["hands"] < 0.5) & (d["blink"] < 0.5) & (v > 20.1) & np.isfinite(g[:, 0])
    cors = [np.corrcoef(bp(wheel)[ok0], bp(g[:, i] * v)[ok0])[0, 1] for i in range(3)]; ax = int(np.argmax(np.abs(cors)))
    yaw = np.sign(cors[ax]) * g[:, ax] * v
    tqs = np.sign(np.corrcoef(bp(tq)[ok0], bp(wheel)[ok0])[0, 1]) * tq
    print(f"\n===== {label}: published delay {np.nanmedian(d['delay']):.3f} s, lagd's own estimate {np.nanmedian(d['delay_est']):.3f} s; yaw from gyro axis {'xyz'[ax]} (corr with wheel {cors[ax]:+.2f})")
    B = {k: bp(x) for k, x in (("mreq", mreq), ("req", req), ("tq", tqs), ("wheel", wheel), ("yaw", yaw))}
    jerk = np.abs(np.gradient(ma(req, 40), 0.01))
    for cname, lo, hi in (("45-60 mph", 20.1, 26.8), ("above 60 mph", 26.8, 99)):
        base = (d["lat"] > 0.5) & (d["hands"] < 0.5) & (d["blink"] < 0.5) & (v >= lo) & (v < hi); base = ma(base.astype(float), 300) > 0.999
        for sub, m in (("all", base), ("turn entry / exit", base & (jerk > 0.25)), ("straights", base & (np.abs(ma(req, 300)) < 0.35) & (jerk < 0.15))):
            if m.sum() < 3000: continue
            row = []
            for a, b in (("mreq", "req"), ("req", "tq"), ("tq", "wheel"), ("req", "wheel"), ("wheel", "yaw"), ("req", "yaw"), ("mreq", "yaw")):
                l, c = xlag(B[a], B[b], m); row.append(f"{a}->{b} {l:+.2f}s ({c:.2f})")
            print(f"  {cname:12s} {sub:17s} {m.sum() / 6000:5.1f} min | " + " | ".join(row))
        if base.sum() > 6000:
            for a, b in (("req", "wheel"), ("wheel", "yaw"), ("req", "yaw"), ("mreq", "yaw")):
                P = phase_delay(B[a], B[b], base)
                print(f"  {cname:12s} by frequency  {a}->{b}: " + "  ".join(f"{n} Hz {x:+.2f}s gain {gn:.2f} coh {co:.2f}" for n, (x, gn, co) in zip(("0.1-0.3", "0.3-0.6", "0.6-1.2"), P)))
    # where the car sits through curves
    centre = (d["ll"] + d["rl"]) / 2; lanes = (d["llp"] > 0.5) & (d["rlp"] > 0.5)
    s = np.sign(ma(req, 100)); inside = -centre * s * 100      # cm toward the inside of the turn
    rate = np.gradient(np.abs(ma(req, 60)), 0.01); mag = np.abs(ma(req, 60))
    base = (d["lat"] > 0.5) & (d["hands"] < 0.5) & (d["blink"] < 0.5) & (v > 20.1) & lanes; base = ma(base.astype(float), 200) > 0.999
    straight = base & (mag < 0.15) & (np.abs(rate) < 0.05)
    ref = np.median(-centre[straight] * 100) if straight.sum() > 500 else 0.0    # the car's usual offset on straights (cm to the right)
    insideC = (-centre * 100 - ref) * s
    row = []
    for name, m in (("building", base & (mag > 0.3) & (rate > 0.15)), ("steady", base & (mag > 0.6) & (np.abs(rate) < 0.08)), ("unwinding", base & (mag > 0.3) & (rate < -0.15))):
        n = len(runs(m, 30)); row.append(f"{name} {np.mean(insideC[m]):+5.1f} cm ({m.sum() / 100:.0f} s, {n} stretches)" if m.sum() > 300 else f"{name} too little")
    print(f"  curves, position toward the inside (straight-road offset {ref:+.1f} cm removed): " + " | ".join(row))
