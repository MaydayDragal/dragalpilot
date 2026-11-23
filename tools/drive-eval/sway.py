"""Sway / ping-pong / oscillation report for the extracted drives, and a diagnosis of what limits each setup.

  python sway.py <dir with extract .pkl files> [<dir> ...]        (PC; needs numpy only)
  Prints the tables and writes sway-latest.html (graphs of the same numbers, next to the extracts in ../sway, plus a
  dated copy) and opens it in the browser. The report holds GPS positions: keep it out of the public repo. Its map
  background is fetched from OpenStreetMap while the report is open. env NO_OPEN=1 skips opening; SWAY_OUT=<folder> changes where it goes.
  env: BASE="label" picks the setup used as the reference in the same-road section (default: the last one in SETUPS)

What it measures, on stretches with steering active, hands off, no blinker, both lane lines seen, >= 12 s long:

 1. SWINGS (time domain, what is felt). The lane-centre offset is band-passed 0.08-1.5 Hz and cut into swings
    (one side-to-side move, between turning points, ignoring reversals smaller than HYST). Each swing has a size
    (peak to peak) and a period (twice its duration). Classes by period: wander > 5 s, ping-pong 2-5 s, fast < 2 s.
    A "train" is 4 or more consecutive swings of ping-pong period that are all >= TRAIN_CM: a sustained
    side-to-side oscillation rather than one correction.
 2. WOBBLE. The same swing counting on lateral acceleration, period < 1.6 s, and steering-wheel reversals per minute.
 3. WHO MOVES. Lane offset = road/lines minus car. The car's own sideways movement is rebuilt from its lateral
    acceleration (divided by omega^2 in the band). "car share" is the part of the lane-offset power that is
    linearly explained by the car's movement; the rest is the lane lines moving (road shape or perception).
 4. LOOP. Around the loop: lane offset -> request (model and plan) -> lateral acceleration (controller and car)
    -> position. Per frequency: how hard the plan reacts (request per metre of offset), how well the car follows
    (gain and delay), and the open-loop gain |L| = plan stiffness x following gain / omega^2 with its phase margin.
    "amplifies x" = 1 / |1 + L|: above 1 the loop makes a lane disturbance at that frequency larger instead of
    removing it. This is estimated from normal driving, in closed loop, so treat it as a guide: the coherence
    columns say how much to trust it.
 6. VERDICT. Per setup above 60 mph: ping-pong and wobble counts, how late the car follows the request in the
    hunting band (0.2-0.45 Hz) and the largest amplification there, with a one-line reading.
 5. SAME ROAD. For each earlier setup, the stretches of road (about 100 m cells, same direction) that both it and
    the reference setup drove, so the comparison is not a comparison of roads.

Signs: lane-line y and the lane centre are positive to the right of the car; request and lateral acceleration are
positive for a right curve.
"""
import sys, os, re, glob, pickle, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import load

# setup label -> routes. Keep the labels short; the newest setup goes last. At most 8 (one colour each in the report);
# c5 (smoothing ramp 25-45 mph, 15 short segments) bc-be (V0 4.2/.07), c6-c7 (filter .3, look-ahead .2) d1 (gain 0.6), b5 (V0 4.5/.05), c0-c3 (V1 no smoothing) cd-d0 (delay 0.10) and ca-cc (delay 0.33) were dropped to make room.
SETUPS = {
    "ours: V1 ctrl delay .20 ramp .40 (d4)": ["000000d4"],
    "ours: + op long (dd, de)": ["000000dc", "000000dd", "000000de"],
    "ours: morning route (df, e0)": ["000000df", "000000e0"],
    "ours: afternoon route (e1)": ["000000e1"],
    "ours: factor 4.5 (e2)": ["000000e2"],
    "ours: factor 4.2 (e3)": ["000000e3"],
    "g70-2024-new (ffb5a06)": ["00000003"],
    "ours 2a81f61, factor 4.2 (05, 06)": ["00000005", "00000006"],
}
SPEEDS = (("20-45 mph", 8.9, 20.1), ("45-60 mph", 20.1, 26.8), (">60 mph", 26.8, 99.0))
HYST = 0.03       # m, reversals smaller than this do not end a swing
BIG_CM = 15.0     # a swing this large is counted as "large"
TRAIN_CM = 8.0    # minimum swing size inside a ping-pong train
MINLEN = 1200     # samples (12 s) for a stretch
TRACE = 4500      # samples (45 s) of the example trace in the report
PBINS = [1, 1.5, 2, 2.5, 3, 3.5, 4, 5, 6, 8, 12]   # swing-period bins (s) for the report
N = 2048          # spectral window, 20.48 s
DT = 0.01

def runs(m, minlen):
    idx = np.flatnonzero(np.diff(np.r_[0, m.astype(int), 0])); return [(a, b) for a, b in zip(idx[::2], idx[1::2]) if b - a >= minlen]

def bandpass(x, lo, hi, integrate2=False):
    """zero-phase FFT band-pass of one stretch; integrate2 divides by -omega^2 (acceleration -> displacement)"""
    n = len(x); X = np.fft.rfft((x - x.mean()) * np.r_[np.hanning(200)[:100], np.ones(n - 200), np.hanning(200)[100:]])
    f = np.fft.rfftfreq(n, DT); k = (f >= lo) & (f <= hi); X[~k] = 0
    if integrate2: X[k] /= -(2 * np.pi * f[k]) ** 2
    return np.fft.irfft(X, n)

def swings(x, hyst):
    """turning points of x with hysteresis -> list of (start index, end index, peak-to-peak)"""
    tp = []; i0 = 0; hi = lo = x[0]; ihi = ilo = 0; d = 0
    for i in range(1, len(x)):
        v = x[i]
        if v > hi: hi, ihi = v, i
        if v < lo: lo, ilo = v, i
        if d >= 0 and hi - v > hyst:      # was rising (or unknown), now fell by hyst: hi is a turning point
            tp.append(ihi); d = -1; lo, ilo = v, i
        elif d <= 0 and v - lo > hyst:    # was falling, now rose: lo is a turning point
            tp.append(ilo); d = 1; hi, ihi = v, i
    return [(a, b, abs(x[b] - x[a])) for a, b in zip(tp[:-1], tp[1:])]

def stretches(d, lo, hi):
    ok = d["latActive"] & ~d["pressed"] & ~d["blink"] & (np.abs(d["drv"]) < 80) & (d["v"] >= lo) & (d["v"] < hi) & (d["llp"] > 0.5) & (d["rlp"] > 0.5)
    return [(a + 100, b - 100) for a, b in runs(ok, MINLEN + 200)]

def time_stats(d, st):
    """swing statistics over a list of stretches of one route"""
    lane = (d["ll"] + d["rl"]) / 2; req = d["dcurv"] * d["v"] ** 2
    o = dict(secs=0.0, sw=[], acc=[], rev=0, train_s=0.0, trains=0, strsecs=0.0, curvesw=[], curvesecs=0.0, best=(-1, None))
    for a, b in st:
        x = bandpass(lane[a:b], 0.08, 1.5); o["secs"] += (b - a) * DT
        straight = np.abs(np.convolve(req[a:b], np.ones(500) / 500, mode="same")) < 0.35
        sw = swings(x, HYST); run = []
        mids = np.array([(i + j) // 2 for i, j, p in sw if 2.0 <= 2 * (j - i) * DT <= 5.0 and p * 100 >= TRAIN_CM and straight[(i + j) // 2]])
        for s0 in range(0, len(x) - TRACE + 1, 500):      # busiest TRACE-long window, kept as an example trace
            c = int(np.sum((mids >= s0) & (mids < s0 + TRACE))) if len(mids) else 0
            if straight[s0:s0 + TRACE].mean() > 0.9 and c > o["best"][0]: o["best"] = (c, (x[s0:s0 + TRACE:10] * 100).round(2).tolist())
        for i, j, p in sw:
            per = 2 * (j - i) * DT; mid = (i + j) // 2
            (o["sw"] if straight[mid] else o["curvesw"]).append((per, p * 100))
            if straight[mid] and 2.0 <= per <= 5.0 and p * 100 >= TRAIN_CM: run.append((i, j))
            else:
                if len(run) >= 4: o["trains"] += 1; o["train_s"] += (run[-1][1] - run[0][0]) * DT
                run = []
        if len(run) >= 4: o["trains"] += 1; o["train_s"] += (run[-1][1] - run[0][0]) * DT
        o["strsecs"] += straight.sum() * DT; o["curvesecs"] += (~straight).sum() * DT
        ya = bandpass(d["actualLateralAccel"][a:b], 0.5, 3.0)
        o["acc"] += [(2 * (j - i) * DT, p) for i, j, p in swings(ya, 0.04)]
        o["rev"] += len(swings(d["ang"][a:b], 0.15))
    return o

def merge(os_):
    m = dict(secs=0.0, sw=[], acc=[], rev=0, train_s=0.0, trains=0, strsecs=0.0, curvesw=[], curvesecs=0.0)
    for o in os_:
        for k in m: m[k] = m[k] + o[k]
    m["best"] = max((o["best"] for o in os_), key=lambda b: b[0])
    return m

def spectra(d, st):
    lane = (d["ll"] + d["rl"]) / 2; req = d["dcurv"] * d["v"] ** 2; act = d["actualLateralAccel"]; w = np.hanning(N)
    P = dict(n=0, LL=0, RR=0, AA=0, WW=0, LR=0, RA=0, LA=0)
    lp = np.abs(np.convolve(req, np.ones(500) / 500, mode="same")) < 0.35
    for a, b in st:
        for s in range(a, b - N + 1, N // 2):
            if not lp[s:s + N].all(): continue
            F = lambda x: np.fft.rfft((x[s:s + N] - x[s:s + N].mean()) * w)
            L, R_, A, W = F(lane), F(req), F(act), F(d["ang"])
            P["LL"] += abs(L) ** 2; P["RR"] += abs(R_) ** 2; P["AA"] += abs(A) ** 2; P["WW"] += abs(W) ** 2
            P["LR"] += np.conj(L) * R_; P["RA"] += np.conj(R_) * A; P["LA"] += np.conj(L) * A; P["n"] += 1
    return P

def addP(a, b):
    return {k: a[k] + b[k] for k in a}

FREQ = np.fft.rfftfreq(N, DT)
BANDS = [(0.10, 0.20), (0.20, 0.30), (0.30, 0.45), (0.45, 0.70), (0.70, 1.00), (1.00, 1.60)]
SCALE = 2.0 / (N * N * 0.375)   # one-sided power of a Hann-windowed segment -> mean square per bin

def band_rows(P):
    rows = []
    for lo, hi in BANDS:
        k = (FREQ >= lo) & (FREQ < hi); n = P["n"]; fc = float(np.sqrt(lo * hi)); om2 = (2 * np.pi * FREQ[k]) ** 2
        s = lambda x: np.sum(x[k])
        lane = np.sqrt(s(P["LL"]) / n * SCALE); req = np.sqrt(s(P["RR"]) / n * SCALE); act = np.sqrt(s(P["AA"]) / n * SCALE); wheel = np.sqrt(s(P["WW"]) / n * SCALE)
        car = np.sqrt(np.sum(P["AA"][k] / om2 ** 2) / n * SCALE)                       # car's own sideways movement, m rms
        # lane offset explained by the car's movement: cross-spectrum of lane with act / -omega^2
        LC = P["LA"][k] / -om2; CC = P["AA"][k] / om2 ** 2
        share = abs(np.sum(LC)) ** 2 / (s(P["LL"]) * np.sum(CC))
        Hm = np.sum(P["LR"][k]) / s(P["LL"]); cohm = abs(np.sum(P["LR"][k])) ** 2 / (s(P["LL"]) * s(P["RR"]))   # lane -> request
        Hc = np.sum(P["RA"][k]) / s(P["RR"]); cohc = abs(np.sum(P["RA"][k])) ** 2 / (s(P["RR"]) * s(P["AA"]))   # request -> act
        lag = -np.degrees(np.angle(Hc)); delay = lag / 360 / fc
        # open loop: offset e (lane centre right of car) -> request (should be positive: steer right) -> accel -> car moves right -> e falls
        Lmag = abs(Hm) * abs(Hc) / (2 * np.pi * fc) ** 2
        Lph = np.degrees(np.angle(Hm)) + np.degrees(np.angle(Hc)) - 180.0              # phase of the loop transfer; -180 is the edge
        pm = (Lph + 180.0 + 180.0) % 360.0 - 180.0                                     # phase margin, deg
        amp = 1.0 / abs(1.0 + Lmag * np.exp(1j * np.radians(Lph)))                     # how much the loop magnifies a lane disturbance
        rows.append(dict(amp=amp, lo=lo, hi=hi, lane=lane * 100, car=car * 100, share=share, req=req, act=act, wheel=wheel, stiff=abs(Hm), mph=np.degrees(np.angle(Hm)),
                         cohm=cohm, gain=abs(Hc), lag=lag, delay=delay, cohc=cohc, L=Lmag, pm=pm))
    return rows

def load_gps(dirs):
    G = {}
    for D in dirs:
        for f in glob.glob(os.path.join(D, "*.pkl")):
            r, n = re.match(r"(.*)--(\d+)\.pkl", os.path.basename(f)).groups()
            p = pickle.load(open(f, "rb"))
            if len(p["gps"]) and len(p["cs"]): G.setdefault(r[:8], []).append((int(n), p["gps"], p["cs"][0, 0]))
    out = {}
    for r, v in G.items():
        v.sort(key=lambda x: x[0]); g = np.vstack([x[1] for x in v]); g = g[np.abs(g[:, 1]) > 1]   # rows without a fix are zeros
        if len(g): g = g[(np.abs(g[:, 1] - np.median(g[:, 1])) < 3) & (np.abs(g[:, 2] - np.median(g[:, 2])) < 3)]   # and stray fixes
        if len(g) > 10: out[r] = (g, v[0][2] if v[0][0] == 0 else None)
    return out

def road_keys(d, g, t0):
    t = d["t"] + t0
    lat = np.interp(t, g[:, 0], g[:, 1]); lon = np.interp(t, g[:, 0], g[:, 2]); brg = np.interp(t, g[:, 0], np.unwrap(np.radians(g[:, 4])))
    ok = (t >= g[0, 0]) & (t <= g[-1, 0]) & (np.abs(lat) > 1)
    key = np.round(lat * 1000).astype(np.int64) * 10_000_000 + np.round(lon * 1000 + 500_000).astype(np.int64) * 10 + (np.round(np.degrees(brg) / 45.0).astype(np.int64) % 8)
    key[~ok] = -1
    return key

def fmt_sw(o):
    sw = np.array(o["sw"]) if o["sw"] else np.zeros((0, 2)); m = max(o["strsecs"], 1e-9) / 60
    cls = lambda lo, hi, amp: np.sum((sw[:, 0] >= lo) & (sw[:, 0] < hi) & (sw[:, 1] >= amp)) / m
    pp = sw[(sw[:, 0] >= 2) & (sw[:, 0] < 5)]
    acc = np.array(o["acc"]) if o["acc"] else np.zeros((0, 2)); allm = max(o["secs"], 1e-9) / 60
    hist = [float(np.sum((sw[:, 0] >= a) & (sw[:, 0] < b) & (sw[:, 1] >= TRAIN_CM)) / m) for a, b in zip(PBINS[:-1], PBINS[1:])]
    return dict(hist=hist, trace=o["best"][1], mins=m, wander=cls(5, 99, TRAIN_CM), pp=cls(2, 5, TRAIN_CM), ppbig=cls(2, 5, BIG_CM), fast=cls(0, 2, TRAIN_CM),
                p90=np.percentile(pp[:, 1], 90) if len(pp) else np.nan, per=np.median(pp[pp[:, 1] >= TRAIN_CM, 0]) if np.any(pp[:, 1] >= TRAIN_CM) else np.nan,
                trains=o["trains"] / m * 10, trainpct=100 * o["train_s"] / max(o["strsecs"], 1e-9),
                wob=np.sum((acc[:, 0] < 1.6) & (acc[:, 1] >= 0.15)) / allm, rev=o["rev"] / allm)

if __name__ == "__main__":
    dirs = sys.argv[1:]; R = {}
    for D in dirs: R.update(load(D))
    GPS = load_gps(dirs)
    base = os.environ.get("BASE", list(SETUPS)[-1])
    res = {}
    for name, lo, hi in SPEEDS:
        print(f"\n================ {name} ================")
        print(f"1-2. swings on straights (per minute, size >= {TRAIN_CM:.0f} cm unless noted), trains, wobble")
        print(f"{'setup':30s} {'min':>5s} {'wander':>7s} {'pingpong':>8s} {'>=15cm':>7s} {'fast':>5s} {'pp p90cm':>8s} {'period s':>8s} {'trains/10min':>12s} {'% in train':>10s} {'wobble/min':>10s} {'wheel rev/min':>13s}")
        for g, rs in SETUPS.items():
            T = []; P = None
            for r in rs:
                if r not in R: continue
                st = stretches(R[r], lo, hi)
                if not st: continue
                T.append(time_stats(R[r], st)); p = spectra(R[r], st); P = p if P is None else addP(P, p)
            if not T or merge(T)["strsecs"] < 45: print(f"{g:30s} too little data"); continue
            s = fmt_sw(merge(T)); res[(name, g)] = (s, band_rows(P) if P and P["n"] >= 6 else None, P["n"] if P else 0)
            print(f"{g:30s} {s['mins']:5.1f} {s['wander']:7.1f} {s['pp']:8.1f} {s['ppbig']:7.2f} {s['fast']:5.1f} {s['p90']:8.1f} {s['per']:8.1f} {s['trains']:12.1f} {s['trainpct']:10.1f} {s['wob']:10.1f} {s['rev']:13.0f}")
        print("\n3-4. who moves, and the loop (straight windows of 20.48 s)")
        for g in SETUPS:
            if (name, g) not in res or res[(name, g)][1] is None: continue
            print(f"  {g}  ({res[(name, g)][2]} windows)")
            print("     band Hz   lane cm  car cm  car share | plan: req per m  phase  coh | car: gain  lag deg  delay s  coh | loop |L|  margin deg  amplifies x | wheel deg")
            for b in res[(name, g)][1]:
                print(f"   {b['lo']:.2f}-{b['hi']:.2f}  {b['lane']:7.2f} {b['car']:7.2f} {b['share']:9.2f} | {b['stiff']:14.2f} {b['mph']:6.0f} {b['cohm']:5.2f} | {b['gain']:9.2f} {b['lag']:8.0f} {b['delay']:8.2f} {b['cohc']:5.2f} | {b['L']:8.2f} {b['pm']:10.0f} {b['amp']:12.2f} | {b['wheel']:8.3f}")

    verdict = []; same = []
    print("\n================ verdict, > 60 mph ================")
    print(f"{'setup':30s} {'pingpong/min':>12s} {'wobble/min':>10s} {'follow delay s':>14s} {'follow gain .7-1Hz':>18s} {'max amplification':>17s}   reading")
    for g in SETUPS:
        k = (">60 mph", g)
        if k not in res or res[k][1] is None: continue
        s, B, _ = res[k]; hb = [b for b in B if 0.2 <= b["lo"] < 0.45]
        dly = float(np.mean([b["delay"] for b in hb])); amp = max(b["amp"] for b in hb); g7 = [b for b in B if b["lo"] == 0.70][0]["gain"]
        if s["wob"] >= 10: why = "wobble: the car over-answers fast requests (follow gain near or above 1 at 0.7-1 Hz)"
        elif dly > 0.5 and amp > 1.25: why = "ping-pong: the car follows late, so the loop magnifies 0.2-0.45 Hz"
        elif amp > 1.25: why = "ping-pong: the loop magnifies 0.2-0.45 Hz"
        else: why = "balanced"
        print(f"{g:30s} {s['pp']:12.1f} {s['wob']:10.1f} {dly:14.2f} {g7:18.2f} {amp:17.2f}   {why}")
        verdict.append(dict(setup=g, pp=s["pp"], wob=s["wob"], delay=dly, g7=g7, amp=amp, why=why))

    # same-road comparison against the reference setup
    print(f"\n================ same road as \"{base}\" (hands off, steering active, > 35 mph) ================")
    keys = {}
    for r, d in R.items():
        if r in GPS and GPS[r][1] is not None: keys[r] = road_keys(d, GPS[r][0], GPS[r][1])
    def evalmask(d): return d["latActive"] & ~d["pressed"] & ~d["blink"] & (np.abs(d["drv"]) < 80) & (d["v"] >= 15.6) & (d["llp"] > 0.5) & (d["rlp"] > 0.5)
    def cellset(rs): return set(np.unique(np.concatenate([keys[r][evalmask(R[r]) & (keys[r] >= 0)] for r in rs if r in keys] or [np.zeros(0, np.int64)])).tolist())
    def on(rs, common):
        T = []; lane2 = []; wheel2 = []; w = []
        for r in rs:
            if r not in keys: continue
            d = R[r]; m = evalmask(d) & np.isin(keys[r], common); st = [(a + 50, b - 50) for a, b in runs(m, MINLEN + 100)]
            if not st: continue
            T.append(time_stats(d, st)); lane = (d["ll"] + d["rl"]) / 2
            for a, b in st:
                lane2.append(np.mean(bandpass(lane[a:b], 0.2, 0.7) ** 2)); wheel2.append(np.mean(bandpass(d["ang"][a:b], 0.2, 4.0) ** 2)); w.append(b - a)
        if not T: return None
        s = fmt_sw(merge(T)); s["lane"] = 100 * np.sqrt(np.average(lane2, weights=w)); s["wheel"] = np.sqrt(np.average(wheel2, weights=w)); s["secs"] = sum(w) * DT
        return s
    bset = cellset(SETUPS[base]); bset.discard(-1)
    print(f"{'setup':30s} {'shared min':>10s} | {'pingpong/min':>12s} {'ref':>6s} | {'% in train':>10s} {'ref':>6s} | {'lane .2-.7 cm':>13s} {'ref':>6s} | {'wheel .2-4 deg':>14s} {'ref':>6s} | {'wobble/min':>10s} {'ref':>6s}")
    for g, rs in SETUPS.items():
        if g == base: continue
        common = np.array(sorted(bset & cellset(rs)), dtype=np.int64)
        if not len(common): print(f"{g:30s} no shared road"); continue
        a, b = on(rs, common), on(SETUPS[base], common)
        if a is None or b is None or min(a["secs"], b["secs"]) < 90: print(f"{g:30s} too little shared road"); continue
        same.append(dict(setup=g, mins=min(a["secs"], b["secs"]) / 60, a={k: a[k] for k in ("pp", "trainpct", "lane", "wheel", "wob")}, b={k: b[k] for k in ("pp", "trainpct", "lane", "wheel", "wob")}))
        print(f"{g:30s} {min(a['secs'], b['secs']) / 60:10.1f} | {a['pp']:12.1f} {b['pp']:6.1f} | {a['trainpct']:10.1f} {b['trainpct']:6.1f} | {a['lane']:13.2f} {b['lane']:6.2f} | {a['wheel']:14.3f} {b['wheel']:6.3f} | {a['wob']:10.1f} {b['wob']:6.1f}")

    # ---- map data: where each ping-pong swing and wobble happened, and the spots where several drives swing
    def map_data():
        tracks = []; pp = []; wob = []; passes = {}; hits = {}
        for si, (g, rs) in enumerate(SETUPS.items()):
            for r in rs:
                if r not in R or r not in keys: continue
                d = R[r]; gps, t0 = GPS[r]; t = d["t"] + t0
                lat = np.interp(t, gps[:, 0], gps[:, 1]); lon = np.interp(t, gps[:, 0], gps[:, 2]); key = keys[r]
                good = (key >= 0) & (d["v"] > 2.0)
                for a, b in runs(good, 400): tracks.append(dict(s=si, r=r[-2:], pts=np.c_[lat[a:b:200], lon[a:b:200]].round(5).tolist()))
                lane = (d["ll"] + d["rl"]) / 2; req = d["dcurv"] * d["v"] ** 2
                em = evalmask(d) & (key >= 0)
                for c in np.unique(key[em]): passes.setdefault(int(c), set()).add(r)
                for a, b in [(a + 100, b - 100) for a, b in runs(em, MINLEN + 200)]:
                    x = bandpass(lane[a:b], 0.08, 1.5); straight = np.abs(np.convolve(req[a:b], np.ones(500) / 500, mode="same")) < 0.35
                    for i, j, pk in swings(x, HYST):
                        per = 2 * (j - i) * DT; m = a + (i + j) // 2
                        if 2.0 <= per <= 5.0 and pk * 100 >= TRAIN_CM:
                            pp.append([si, r[-2:], round(float(lat[m]), 5), round(float(lon[m]), 5), round(pk * 100, 1), round(per, 1), int(round(d["v"][m] * 2.237)), int(straight[(i + j) // 2])])
                            if straight[(i + j) // 2]: hits.setdefault(int(key[m]), set()).add(r)
                    ya = bandpass(d["actualLateralAccel"][a:b], 0.5, 3.0)
                    for i, j, pk in swings(ya, 0.04):
                        m = a + (i + j) // 2
                        if 2 * (j - i) * DT < 1.6 and pk >= 0.15: wob.append([si, r[-2:], round(float(lat[m]), 5), round(float(lon[m]), 5), round(float(pk), 2), int(round(d["v"][m] * 2.237))])
        hot = []
        for c, hr in hits.items():
            n = len(passes.get(c, ()))
            if n >= 3 and len(hr) >= 3 and len(hr) / n >= 0.6:
                hot.append([round((c // 10_000_000) / 1000.0, 4), round(((c % 10_000_000) // 10 - 500_000) / 1000.0, 4), len(hr), n, len({k for k, v in SETUPS.items() for r in v if r in hr})])
        return dict(tracks=tracks, pp=pp, wob=wob, hot=hot)
    MAP = map_data()
    print(f"\nmap: {len(MAP['pp'])} ping-pong swings, {len(MAP['wob'])} wobble swings, {len(MAP['hot'])} repeat spots (road cells where at least 3 drives, and 60 % of the drives that passed, swing on a straight)")

    # ---- HTML report: the same numbers as graphs. Written next to the extracts and opened in the browser.
    import json, datetime, webbrowser
    def clean(o):
        if isinstance(o, dict): return {k: clean(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)): return [clean(v) for v in o]
        if isinstance(o, (float, np.floating)): return None if not np.isfinite(o) else round(float(o), 4)
        if isinstance(o, np.integer): return int(o)
        return o
    data = clean(dict(generated=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), base=base, train_cm=TRAIN_CM, big_cm=BIG_CM, pbins=PBINS,
                      setups=[dict(name=g, routes=[r[-2:] for r in rs if r in R]) for g, rs in SETUPS.items()], speeds=[n for n, _, _ in SPEEDS],
                      bands=[f"{lo:.2f}-{hi:.2f}" for lo, hi in BANDS],
                      res={n: {g: dict(s=res[(n, g)][0], bands=res[(n, g)][1], windows=res[(n, g)][2]) for g in SETUPS if (n, g) in res} for n, _, _ in SPEEDS},
                      verdict=verdict, same=same, map=MAP))
    here = os.path.dirname(os.path.abspath(__file__))
    outdir = os.environ.get("SWAY_OUT", os.path.join(os.path.dirname(os.path.abspath(dirs[0])), "sway")); os.makedirs(outdir, exist_ok=True)
    html = open(os.path.join(here, "sway_report.html"), encoding="utf-8").read().replace("/*DATA*/null", json.dumps(data, separators=(",", ":")))
    stamp = datetime.datetime.now().strftime("%Y-%m-%d-%H%M")
    for name in (f"sway-{stamp}.html", "sway-latest.html"):
        with open(os.path.join(outdir, name), "w", encoding="utf-8", newline="\n") as f: f.write(html)
    print(f"\nreport: {os.path.join(outdir, 'sway-latest.html')}  (also kept as sway-{stamp}.html)")
    if not os.environ.get("NO_OPEN"): webbrowser.open("file:///" + os.path.join(outdir, "sway-latest.html").replace(os.sep, "/"))
