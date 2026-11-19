"""Baseline of speed control (longitudinal) from extract_long.py output.

  python long_baseline.py <dir with extract_long .pkl files> [route prefix ...]

Describes how the car's own smart cruise (SCC) drives, and what openpilot's planner asked for at the same moments
(the planner runs in the background even when it does not control speed). Everything is on a 20 Hz timeline.
"Cruising" = cruise engaged, no gas pedal, no brake pedal, above 1 m/s.
"""
import sys, os, re, glob, pickle, numpy as np

def load(D, only=()):
    segs = {}
    for f in glob.glob(os.path.join(D, "*.pkl")):
        r, n = re.match(r"(.*)--(\d+)\.pkl", os.path.basename(f)).groups()
        if only and not any(r.startswith(o) or r[:8].endswith(o) for o in only): continue
        segs.setdefault(r[:8], {})[int(n)] = pickle.load(open(f, "rb"))
    out = {}
    for r, ss in sorted(segs.items()):
        ns = sorted(ss); sig = ss[ns[0]]["sigs"]
        cat = lambda k: np.vstack([ss[n][k] for n in ns if len(ss[n][k])]) if any(len(ss[n][k]) for n in ns) else np.zeros((0, 2))
        cs = cat("cs"); t = cs[:, 0]
        def ip(a, c, near=False):
            if not len(a): return np.full(len(t), np.nan)
            if near: return a[np.clip(np.searchsorted(a[:, 0], t), 0, len(a) - 1), c]
            return np.interp(t, a[:, 0], a[:, c])
        rs, lp, ml, s11, s12, fca = cat("rs"), cat("lp"), cat("ml"), cat("scc11"), cat("scc12"), cat("fca11")
        i11 = {k: i + 1 for i, k in enumerate(sig[0x420])}; i12 = {k: i + 1 for i, k in enumerate(sig[0x421])}; ifc = {k: i + 1 for i, k in enumerate(sig[0x38D])}
        d = dict(t=t - t[0], v=cs[:, 1], a=cs[:, 2], gas=cs[:, 3] > 0.5, brake=cs[:, 4] > 0.5, en=cs[:, 5] > 0.5, vset=cs[:, 6], cstand=cs[:, 7] > 0.5, stand=cs[:, 8] > 0.5,
                 fcw=cs[:, 9] > 0.5, aeb=cs[:, 10] > 0.5,
                 lead=ip(rs, 1, True) > 0.5, d=ip(rs, 2), vrel=ip(rs, 3), vlead=ip(rs, 4), alead=ip(rs, 6), radar=ip(rs, 7, True) > 0.5,
                 op_a=ip(lp, 1), op_lead=ip(lp, 2, True) > 0.5, op_stop=ip(lp, 3, True) > 0.5, op_fcw=ip(lp, 7, True) > 0.5,
                 ml_prob=ip(ml, 1), ml_x=ip(ml, 2),
                 gapset=ip(s11, i11["TauGapSet"], True), scc_dist=ip(s11, i11["ACC_ObjDist"]), scc_obj=ip(s11, i11["ACC_ObjStatus"], True), scc_vset=ip(s11, i11["VSetDis"], True),
                 info=ip(s11, i11["SCCInfoDisplay"], True),
                 accmode=ip(s12, i12["ACCMode"], True), a_req=ip(s12, i12["aReqRaw"]), a_val=ip(s12, i12["aReqValue"]), stopreq=ip(s12, i12["StopReq"], True),
                 fca_cmd=ip(fca, ifc["FCA_CmdAct"], True), fca_warn=ip(fca, ifc["CF_VSM_Warn"], True))
        out[r] = d
    return out

def runs(m, minlen=1):
    idx = np.flatnonzero(np.diff(np.r_[0, m.astype(int), 0])); return [(a, b) for a, b in zip(idx[::2], idx[1::2]) if b - a >= minlen]
def smooth(x, n): return np.convolve(x, np.ones(n) / n, mode="same")
def pct(x, q): return float(np.percentile(x, q)) if len(x) else float("nan")
HZ = 20

if __name__ == "__main__":
    R = load(sys.argv[1], sys.argv[2:])
    A = {k: np.concatenate([d[k] for d in R.values()]) for k in next(iter(R.values()))}
    cruise = A["en"] & ~A["gas"] & ~A["brake"] & (A["v"] > 1.0)
    mins = lambda m: m.sum() / HZ / 60
    print(f"routes {len(R)} ({' '.join(r[-2:] for r in R)}), total {len(A['t']) / HZ / 60:.0f} min; cruise engaged {mins(A['en']):.0f} min; cruising (no pedals) {mins(cruise):.0f} min; "
          f"with a lead {mins(cruise & A['lead']):.0f} min; lead from radar {100 * (cruise & A['lead'] & A['radar']).sum() / max((cruise & A['lead']).sum(), 1):.0f} %")

    print("\n1. Following distance (steady following: lead present, > 45 mph, closing speed within 1 m/s, |accel| < 0.3)")
    st = cruise & A["lead"] & (A["v"] > 20) & (np.abs(A["vrel"]) < 1.0) & (np.abs(A["a"]) < 0.3)
    print("   gap setting   minutes   time gap s: p10 / median / p90    distance m at median speed")
    for g in sorted(set(A["gapset"][st & np.isfinite(A["gapset"])].astype(int))):
        m = st & (A["gapset"] == g); tg = A["d"][m] / A["v"][m]
        if m.sum() > HZ * 20: print(f"   {g:11d}   {mins(m):7.1f}   {pct(tg, 10):.2f} / {pct(tg, 50):.2f} / {pct(tg, 90):.2f}                 {np.median(A['d'][m]):.0f} m at {np.median(A['v'][m]) * 2.237:.0f} mph")
    both = cruise & A["lead"] & A["radar"] & (A["scc_obj"] > 0) & (A["scc_dist"] < 200)
    if both.sum(): print(f"   openpilot's lead distance minus the cruise's own object distance: median {np.median(A['d'][both] - A['scc_dist'][both]):+.1f} m, p5..p95 {pct(A['d'][both] - A['scc_dist'][both], 5):+.1f}..{pct(A['d'][both] - A['scc_dist'][both], 95):+.1f} m ({mins(both):.0f} min)")

    print("\n2. Comfort while cruising")
    jerk = np.gradient(smooth(A["a"], 10)) * HZ
    for name, m in (("all cruising", cruise), ("with a lead", cruise & A["lead"]), ("no lead", cruise & ~A["lead"]), ("below 35 mph", cruise & (A["v"] < 15.6)), ("above 60 mph", cruise & (A["v"] > 26.8))):
        if m.sum() < HZ * 30: continue
        a = A["a"][m]; j = jerk[m]
        print(f"   {name:14s} {mins(m):5.0f} min  accel rms {np.sqrt(np.mean(a ** 2)):.2f}  p1 {pct(a, 1):+.2f}  p99 {pct(a, 99):+.2f} m/s2 | jerk rms {np.sqrt(np.mean(j ** 2)):.2f}  p1 {pct(j, 1):+.2f}  p99 {pct(j, 99):+.2f} m/s3 | braking harder than 1.5 m/s2: {100 * np.mean(a < -1.5):.2f} % of time")
    hb = runs(cruise & (smooth(A["a"], 6) < -2.0), 6)
    print(f"   hard-braking events (below -2.0 m/s2 for 0.3 s or more): {len(hb)} in {mins(cruise):.0f} min" + (f"; strongest {min(A['a'][a:b].min() for a, b in hb):.1f} m/s2" if hb else ""))
    # speed see-saw while following: swings of acceleration of 0.4 m/s2 or more, period under 12 s
    def swings(x, hyst):
        tp = []; hi = lo = x[0]; ihi = ilo = 0; dd = 0
        for i in range(1, len(x)):
            v = x[i]
            if v > hi: hi, ihi = v, i
            if v < lo: lo, ilo = v, i
            if dd >= 0 and hi - v > hyst: tp.append(ihi); dd = -1; lo, ilo = v, i
            elif dd <= 0 and v - lo > hyst: tp.append(ilo); dd = 1; hi, ihi = v, i
        return [(a, b, abs(x[b] - x[a])) for a, b in zip(tp[:-1], tp[1:])]
    for name, base in (("with a lead", cruise & A["lead"] & (A["v"] > 8)), ("no lead", cruise & ~A["lead"] & (A["v"] > 8))):
        n = 0; secs = 0
        for a, b in runs(base, HZ * 20):
            x = smooth(A["a"][a:b], 10); secs += (b - a) / HZ
            n += sum(1 for i, j, p in swings(x, 0.2) if p >= 0.4 and 2 * (j - i) / HZ < 12)
        if secs > 60: print(f"   speed see-saw, {name}: {n / (secs / 60):.1f} accel swings of 0.4 m/s2 or more per minute ({secs / 60:.0f} min)")

    print("\n3. Holding the set speed (no lead, cruising, steady for 10 s, not accelerating toward a new set speed)")
    m = cruise & ~A["lead"] & (A["v"] > 15) & (np.abs(A["v"] - A["vset"]) < 3.0)
    if m.sum() > HZ * 30: e = (A["v"] - A["vset"])[m] * 2.237; print(f"   {mins(m):.0f} min: speed minus set speed median {np.median(e):+.1f} mph, p5..p95 {pct(e, 5):+.1f}..{pct(e, 95):+.1f} mph")

    print("\n4. Stops and starts with cruise engaged")
    stops = [(a, b) for a, b in runs(A["en"] & A["stand"], HZ * 1)]
    dstop = [A["d"][a + HZ // 2] for a, b in stops if A["lead"][a + HZ // 2]]
    held = sum((b - a) / HZ for a, b in stops)
    print(f"   {len(stops)} stops held by cruise ({held / 60:.1f} min standing); distance to the lead when stopped: median {np.median(dstop) if dstop else float('nan'):.1f} m, min {min(dstop) if dstop else float('nan'):.1f} m ({len(dstop)} with a lead)")
    dec = []
    for a, b in stops:
        w = slice(max(a - HZ * 12, 0), a); k = cruise[w]
        if k.sum() > HZ * 4: dec.append((A["a"][w][k].min(), np.abs(np.gradient(smooth(A["a"][w], 10)) * HZ)[k].max()))
    if dec: print(f"   final 12 s before a stop: strongest braking median {np.median([x[0] for x in dec]):.2f} m/s2 (worst {min(x[0] for x in dec):.2f}); peak jerk median {np.median([x[1] for x in dec]):.2f} m/s3")
    # restarts: after standing, time from the lead moving away (vlead > 0.5) to the car moving (v > 0.3), when the driver did not press the pedal first
    rs_ = []; pedal = 0
    for a, b in stops:
        e = min(b + HZ * 8, len(A["v"]) - 1); seg = slice(a, e)
        lm = np.flatnonzero(A["lead"][seg] & (A["vlead"][seg] > 0.5)); cm = np.flatnonzero(A["v"][seg] > 0.3)
        if len(lm) and len(cm) and cm[0] > lm[0]:
            if A["gas"][a + lm[0]:a + cm[0] + 1].any(): pedal += 1
            else: rs_.append((cm[0] - lm[0]) / HZ)
    print(f"   restarts: {len(rs_)} by cruise alone, delay after the lead moves median {np.median(rs_) if rs_ else float('nan'):.1f} s (p90 {pct(rs_, 90):.1f} s); {pedal} where the gas pedal was used first")
    print(f"   cruise asking for switch or pedal (SCCInfoDisplay 4): {mins(A['info'] == 4):.1f} min in {len(runs(A['info'] == 4))} episodes")

    print("\n5. Driver take-overs while cruise was engaged")
    eng = mins(A["en"])
    gas_ev = runs(A["en"] & A["gas"], 4); br = [a for a, b in runs(A["brake"], 1) if a > 0 and A["en"][a - 1]]
    gl = sum(1 for a, b in gas_ev if A["lead"][a]); gs = sum(1 for a, b in gas_ev if A["v"][a] < 2.0)
    print(f"   gas-pedal overrides: {len(gas_ev)} ({len(gas_ev) / eng * 10:.1f} per 10 min), {gl} with a lead ahead, {gs} from a standstill; total {sum(b - a for a, b in gas_ev) / HZ / 60:.1f} min on the pedal")
    print(f"   brake-pedal take-overs: {len(br)} ({len(br) / eng * 10:.1f} per 10 min)")
    if br:
        tg = [A["d"][a] / max(A["v"][a], 0.1) for a in br if A["lead"][a] and A["v"][a] > 5]
        print(f"   at the brake press: time gap to the lead median {np.median(tg) if tg else float('nan'):.1f} s ({len(tg)} with a lead above 11 mph); cruise was already braking harder than 0.5 m/s2 in {sum(1 for a in br if A['a_req'][a] < -0.5)} of {len(br)}")
    print(f"   stock forward-collision warnings: {len(runs(A['fcw']))}; stock automatic braking: {len(runs(A['aeb']))}; FCA command active: {len(runs(A['fca_cmd'] > 0))}; openpilot planner FCW: {len(runs(A['op_fcw']))}")

    print("\n6. What openpilot's planner asked for, against the stock cruise, while cruising (the planner is not in control)")
    m = cruise & np.isfinite(A["op_a"]) & np.isfinite(A["a_req"]) & (A["accmode"] > 0)
    for name, mm in (("with a lead", m & A["lead"]), ("no lead", m & ~A["lead"])):
        if mm.sum() < HZ * 60: continue
        o, s = A["op_a"][mm], A["a_req"][mm]
        print(f"   {name:12s} {mins(mm):4.0f} min  stock request mean {s.mean():+.2f} rms {np.sqrt(np.mean(s ** 2)):.2f} | openpilot mean {o.mean():+.2f} rms {np.sqrt(np.mean(o ** 2)):.2f} | correlation {np.corrcoef(o, s)[0, 1]:.2f} | "
              f"openpilot braking 0.5 m/s2 harder: {100 * np.mean(o < s - 0.5):.1f} % of time, stock braking 0.5 harder: {100 * np.mean(s < o - 0.5):.1f} %")
    # who brakes first on a closing lead: episodes where the lead closes faster than 2 m/s
    first = []
    for a, b in runs(m & A["lead"] & (A["vrel"] < -2.0) & (A["v"] > 8), HZ * 2):
        w = slice(max(a - HZ * 5, 0), min(b + HZ * 5, len(A["v"])))
        so = np.flatnonzero(A["a_req"][w] < -0.4); oo = np.flatnonzero(A["op_a"][w] < -0.4)
        if len(so) and len(oo): first.append((oo[0] - so[0]) / HZ)
    if first: print(f"   closing on a lead ({len(first)} episodes): openpilot's planner asks for braking {np.median(first):+.1f} s relative to the stock cruise (negative = earlier); earlier in {sum(1 for x in first if x < -0.3)}, later in {sum(1 for x in first if x > 0.3)}")
    tgo = A["d"] / np.maximum(A["v"], 0.1); stf = cruise & A["lead"] & (A["v"] > 20) & (np.abs(A["vrel"]) < 1.0) & (np.abs(A["a"]) < 0.3)
    if stf.sum(): print(f"   in steady following the planner asks for {np.mean(A['op_a'][stf]):+.2f} m/s2 on average (positive = it wants to be closer than the stock gap, negative = further)")

    print("\n7. Per route")
    print("   route  cruise min  lead %  gas overrides  brake take-overs  stops  hard brakes  accel rms  jerk rms")
    for r, d in R.items():
        c = d["en"] & ~d["gas"] & ~d["brake"] & (d["v"] > 1.0)
        if c.sum() < HZ * 60: continue
        j = np.gradient(smooth(d["a"], 10)) * HZ
        print(f"   {r[-2:]}     {c.sum() / HZ / 60:8.1f}  {100 * (c & d['lead']).sum() / c.sum():6.0f}  {len(runs(d['en'] & d['gas'], 4)):13d}  {sum(1 for a, b in runs(d['brake'], 1) if a > 0 and d['en'][a - 1]):16d}  {len(runs(d['en'] & d['stand'], HZ)):5d}  "
              f"{len(runs(c & (smooth(d['a'], 6) < -2.0), 6)):11d}  {np.sqrt(np.mean(d['a'][c] ** 2)):9.2f}  {np.sqrt(np.mean(j[c] ** 2)):8.2f}")
