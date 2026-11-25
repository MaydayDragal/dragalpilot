"""One command to assess the quality of a drive from its rlogs, on the PC.

  python drive_quality.py <route> [<route> ...]          report each drive against the baseline
  python drive_quality.py --baseline <route> [<route> ...]  make these drives the baseline ("good" = like these)
  python drive_quality.py --trend                          one line per drive assessed so far

Environment:
  DRAGAL_DATA     data root holding recordings/ and analysis/ (default: ~/Documents/DragalPilot)
  CEREAL_DIR, CAR_CAPNP_DIR   schema of the branch that made the log (as for pclog.py)

A route is the 8-character name (`0000001a`). The rlogs are found under <data>/recordings/**/<route>--*/rlog.zst, read
once (in parallel) and cached in <data>/analysis/quality/<route>.npz. Results go to <data>/analysis/quality/:
<route>.html (the report), <route>.json, history.jsonl, baseline.json. Nothing is written to the repo and no position
data is read.

What is measured (all hands off, no blinker, steering active unless said otherwise):
  STEERING ON STRAIGHTS, per speed band (20-45, 45-60, above 60 mph), where both lane lines are seen:
    lane movement   rms of the lane-centre offset about its own 8 s average (cm)
    slow swings     side-to-side swings of 8 cm or more with a 2-20 s period, per minute; and of 15 cm or more
    wheel movement  rms of the steering angle about its 5 s average (deg); wheel swings (1 deg below 45 mph, 0.5 above)
    torque flips    reversals of the torque command by 13 counts or more, per minute
    tracking error  rms of the controller's own error (requested minus measured lateral acceleration, m/s2)
  LOW SPEED WITHOUT LANE LINES (15-45 mph): the wheel and torque measures only.
  CURVES (request above 0.5 m/s2 for 3 s or more, above 45 mph): position toward the inside while the request builds,
    mid-turn and 1.5 s after the exit (cm, relative to the car's position on straights), lane movement mid-turn.
  TAKE-OVERS: times the driver took the wheel while steering was active (not within 3 s of a blinker), per 10 minutes.
  SPEED CONTROL (while openpilot controls speed): time gap behind a lead above 34 mph, braking of 2.5 m/s2 or more held
    0.5 s, strongest braking, reversals of the acceleration command by 0.3 m/s2 per minute, gap at a stop behind a lead.
  MESSAGES AND FAULTS: SCC14 counter and checksum, MDPS12 to the camera, camera warnings re-sent to the car, panda
    invalid-receive count, car faults, alerts shown.
Ratings compare each number with the baseline drives: good = within 25 % of the baseline (or better), fair = within
75 %, poor beyond. A band with under 1.5 minutes of data (straights) is reported but not rated. Braking, the closest
following gap, stop distance and the message checks are rated against fixed limits, not the baseline."""
import sys, os, glob, json, time, html
import numpy as np

DATA = os.environ.get("DRAGAL_DATA", os.path.join(os.path.expanduser("~"), "Documents", "DragalPilot"))
OUT = os.path.join(DATA, "analysis", "quality")
BANDS = (("20-45 mph", 8.9, 20.1), ("45-60 mph", 20.1, 26.8), ("above 60 mph", 26.8, 99.0))
MIN_RATE_MIN = 1.5

# ---------------------------------------------------------------- reading
def read_segment(path):
    import collections
    import pclog
    T = []
    for i in range(256):
        c = i
        for _ in range(8): c = ((c << 1) ^ 0x1D) & 0xFF if c & 0x80 else (c << 1) & 0xFF
        T.append(c)
    def crc8(dat):
        c = 0xFD ^ 0xDF
        for b in dat: c = T[c ^ b]
        return c ^ 0xDF
    nib = lambda d: sum(sum(divmod(b, 16)) for b in d) % 16
    S = {k: [] for k in ("cs", "ctl", "cc", "co", "md", "rs")}
    ev, bm, alerts, info = [], [], set(), {}
    H = collections.Counter(); last = {}
    for m in pclog.read(path):
        w = m.which(); t = m.logMonoTime * 1e-9
        if w == "carState":
            c = m.carState
            S["cs"].append((t, c.vEgo, c.aEgo, c.steeringAngleDeg, c.steeringPressed, c.leftBlinker or c.rightBlinker, c.cruiseState.enabled,
                            c.standstill, c.gasPressed, c.brakePressed))
            for k in ("steerFaultTemporary", "steerFaultPermanent", "accFaulted"):
                if getattr(c, k, False): H[k] += 1
        elif w == "controlsState":
            c = m.controlsState; err = np.nan; act = 0
            if c.lateralControlState.which() == "torqueState":
                err = c.lateralControlState.torqueState.error; act = c.lateralControlState.torqueState.active
            S["ctl"].append((t, c.desiredCurvature, c.curvature, err, act))
        elif w == "carControl":
            c = m.carControl; S["cc"].append((t, c.latActive, c.longActive, c.actuators.accel))
        elif w == "carOutput":
            S["co"].append((t, m.carOutput.actuatorsOutput.torqueOutputCan))
        elif w == "modelV2":
            c = m.modelV2
            try: S["md"].append((t, c.laneLines[1].y[0], c.laneLines[2].y[0], c.laneLineProbs[1], c.laneLineProbs[2]))
            except Exception: pass
        elif w == "radarState":
            l = m.radarState.leadOne
            S["rs"].append((t, getattr(l, "status", False), l.dRel, l.vRel, l.vLead))
        elif w == "selfdriveState":
            a = str(m.selfdriveState.alertText1)
            if a: alerts.add(a)
        elif w == "onroadEvents":
            for e in m.onroadEvents: ev.append((t, str(e.name)))
        elif w in ("userBookmark", "bookmarkButton"):
            bm.append(t)
        elif w == "pandaStates":
            p = m.pandaStates[0]; H["rxInvalid"] = max(H["rxInvalid"], p.safetyRxInvalid)
        elif w == "initData":
            i = m.initData; info = dict(branch=str(i.gitBranch), commit=str(i.gitCommit)[:7])
        elif w == "can":
            for c in m.can:
                a, s = c.address, c.src
                if a == 0x389 and s == 128:
                    d = bytes(c.dat); H["scc14"] += 1; H["scc14_ok"] += nib(d) == 0
                    if "scc14" in last: H["scc14_step"] += ((d[6] & 15) - (last["scc14"] & 15)) % 15 == 1
                    last["scc14"] = d[6]
                elif a == 0x251 and s == 130:
                    d = bytes(c.dat); H["mdps"] += 1; H["mdps_ok"] += crc8(d[:3] + d[4:]) == d[3]
                    if "mdps" in last: H["mdps_step"] += (d[2] - last["mdps"]) % 256 == 1
                    last["mdps"] = d[2]
                elif a == 0x53E and len(c.dat) > 5:
                    d = bytes(c.dat); warn = ((d[5] >> 4) & 1) or (d[5] & 7) == 6
                    if s == 2: H["cam_lkas12"] += 1; H["cam_warn"] += warn
                    elif s == 128: H["tx_lkas12"] += 1; H["tx_warn"] += warn
    return {k: (np.array(v, dtype=float).reshape(len(v), -1) if v else np.zeros((0, 2))) for k, v in S.items()}, ev, bm, sorted(alerts), dict(H), info

def find_rlogs(route):
    paths = glob.glob(os.path.join(DATA, "recordings", "**", route + "--*", "rlog.zst"), recursive=True)
    return sorted(paths, key=lambda p: int(os.path.basename(os.path.dirname(p)).rsplit("--", 1)[1]))

def load(route):
    os.makedirs(OUT, exist_ok=True)
    cache = os.path.join(OUT, route + ".npz")
    if os.path.exists(cache):
        z = np.load(cache, allow_pickle=True); return {k: z[k] for k in z.files}
    paths = find_rlogs(route)
    if not paths: raise SystemExit(f"no rlogs found for {route} under {os.path.join(DATA, 'recordings')}")
    from multiprocessing import Pool
    with Pool(min(6, len(paths))) as p: R = p.map(read_segment, paths)
    S = {}
    for k in R[0][0]:
        parts = [r[0][k] for r in R if len(r[0][k])]; S[k] = np.concatenate(parts) if parts else np.zeros((0, 2))   # a stream a branch does not log
    H = {}
    for r in R:
        for k, v in r[4].items(): H[k] = max(H.get(k, 0), v) if k == "rxInvalid" else H.get(k, 0) + int(v)
    info = next((r[5] for r in R if r[5]), {})
    cs = S["cs"]; t = np.arange(cs[0, 0], cs[-1, 0], 0.01)
    I = lambda k, c, d=np.nan: np.interp(t, S[k][:, 0], S[k][:, c]) if len(S[k]) else np.full(len(t), d)
    d = dict(t=t, v=I("cs", 1), a=I("cs", 2), ang=I("cs", 3), hands=I("cs", 4), blink=I("cs", 5), cruise=I("cs", 6), still=I("cs", 7),
             gas=I("cs", 8), brake=I("cs", 9), req=I("ctl", 1), meas=I("ctl", 2), err=I("ctl", 3), lat=I("cc", 1, 0), long=I("cc", 2, 0),
             acmd=I("cc", 3, 0), tq=I("co", 1, 0), ll=I("md", 1), rl=I("md", 2), llp=I("md", 3, 0), rlp=I("md", 4, 0),
             lead=I("rs", 1, 0), drel=I("rs", 2), vlead=I("rs", 4),
             events=np.array([(e[0], e[1]) for r in R for e in r[1]], dtype=object).reshape(-1, 2), bookmarks=np.array([b for r in R for b in r[2]]),
             alerts=np.array(sorted({a for r in R for a in r[3]}), dtype=object), health=np.array(json.dumps(H)), info=np.array(json.dumps(info)),
             segments=np.array(len(paths)))
    np.savez_compressed(cache, **d)
    return d

# ---------------------------------------------------------------- helpers
def ma(x, n): return np.convolve(x, np.ones(n) / n, "same")
def runs(m, minlen):
    idx = np.flatnonzero(np.diff(np.r_[0, m.astype(int), 0])); return [(a, b) for a, b in zip(idx[::2], idx[1::2]) if b - a >= minlen]
def dilate(m, n): return ma(m.astype(float), 2 * n + 1) > 1e-9
def swings(x, h):
    """turning points of x, ignoring reversals smaller than h: list of (index, value)"""
    out = []; ext = x[0]; ei = 0; d = 1
    for i, v in enumerate(x):
        if d > 0:
            if v > ext: ext, ei = v, i
            elif ext - v > h: out.append((ei, ext)); d = -1; ext, ei = v, i
        else:
            if v < ext: ext, ei = v, i
            elif v - ext > h: out.append((ei, ext)); d = 1; ext, ei = v, i
    return out[1:]                      # the first turning point depends on the assumed starting direction
def count_swings(x, h, vv, lo, hi, pmin=0.0, pmax=1e9, big=None):
    s = swings(x, h); n = nb = 0
    for (i0, e0), (i1, e1) in zip(s, s[1:]):
        per = 2 * (i1 - i0) / 100
        if pmin <= per <= pmax and lo <= vv[i1] < hi:
            n += 1; nb += big is not None and abs(e1 - e0) >= big
    return n, nb

# ---------------------------------------------------------------- metrics
def assess(d):
    v = d["v"]; mph = v * 2.237; req = d["req"] * v ** 2
    eng = (d["lat"] > 0.5) & ~dilate(d["hands"] > 0.5, 100) & ~dilate(d["blink"] > 0.5, 200)
    lanes = (d["llp"] > 0.5) & (d["rlp"] > 0.5)
    straight = np.abs(ma(req, 300)) < 0.35
    off = (d["ll"] + d["rl"]) / 2 * 100
    M = {"steering": {}, "low_speed_wheel": {}, "curves": {}, "takeovers": {}, "speed": {}, "health": {}}
    # steering on straights by band
    acc = {b[0]: dict(n=0, sq=0.0, s8=0, s15=0, wsq=0.0, ws=0, tf=0, esq=0.0) for b in BANDS}
    for a, b in runs(eng & lanes & straight & (v > 8.9), 1200):
        o = ma(off[a:b] - ma(off[a:b], 800), 30); w = d["ang"][a:b] - ma(d["ang"][a:b], 500); core = slice(400, -400)
        vv = v[a:b][core]; oc, wc, tc, ec = o[core], w[core], d["tq"][a:b][core], d["err"][a:b][core]
        for name, lo, hi in BANDS:
            k = (vv >= lo) & (vv < hi); A = acc[name]
            if not k.any(): continue
            A["n"] += k.sum(); A["sq"] += (oc[k] ** 2).sum(); A["wsq"] += (wc[k] ** 2).sum(); A["esq"] += np.nansum(ec[k] ** 2)
            n8, n15 = count_swings(oc, 8.0, vv, lo, hi, 2.0, 20.0, big=15.0); A["s8"] += n8; A["s15"] += n15
            A["ws"] += count_swings(wc, 1.0 if hi <= 20.2 else 0.5, vv, lo, hi)[0]; A["tf"] += count_swings(tc, 13.0, vv, lo, hi)[0]
    for name, A in acc.items():
        mn = A["n"] / 6000
        M["steering"][name] = dict(minutes=round(mn, 1)) if mn < 0.3 else dict(
            minutes=round(mn, 1), lane_rms_cm=round(float(np.sqrt(A["sq"] / A["n"])), 2), swings8_per_min=round(A["s8"] / mn, 1),
            swings15_per_min=round(A["s15"] / mn, 2), wheel_rms_deg=round(float(np.sqrt(A["wsq"] / A["n"])), 3), wheel_swings_per_min=round(A["ws"] / mn, 1),
            torque_flips_per_min=round(A["tf"] / mn, 1), tracking_error=round(float(np.sqrt(A["esq"] / A["n"])), 4))
    # low speed, lane lines not required
    A = dict(n=0, wsq=0.0, ws=0, tf=0)
    for a, b in runs(eng & (np.abs(ma(req, 300)) < 0.6) & (v > 6.7) & (v < 20.1), 800):
        w = d["ang"][a:b] - ma(d["ang"][a:b], 500); core = slice(200, -200); vv = v[a:b][core]
        A["n"] += len(vv); A["wsq"] += (w[core] ** 2).sum(); A["ws"] += count_swings(w[core], 1.0, vv, 0, 99)[0]; A["tf"] += count_swings(d["tq"][a:b][core], 13.0, vv, 0, 99)[0]
    mn = A["n"] / 6000
    M["low_speed_wheel"] = dict(minutes=round(mn, 1)) if mn < 0.3 else dict(minutes=round(mn, 1), wheel_rms_deg=round(float(np.sqrt(A["wsq"] / A["n"])), 3),
                                wheel_swings_per_min=round(A["ws"] / mn, 1), torque_flips_per_min=round(A["tf"] / mn, 1))
    # curves
    okc = eng & lanes & (v > 20.1); rs = ma(req, 50); still = okc & (np.abs(ma(req, 200)) < 0.1)
    ref = np.median(-off[still]) if still.sum() > 500 else 0.0
    C = []
    for sgn in (1, -1):
        for a, b in runs(sgn * rs > 0.5, 300):
            lo, hi = a - 300, b + 300
            if lo < 0 or hi >= len(v) or not okc[lo:hi].all(): continue
            r = sgn * rs[lo:hi]; n = b - a; P = np.median(r[300 + n // 4: 300 + 3 * n // 4])
            up = np.flatnonzero(r[:300 + n // 2] >= 0.9 * P); dn = np.flatnonzero(r[300 + n // 2:] <= 0.9 * P)
            dn10 = np.flatnonzero(r[300 + n // 2:] <= 0.1 * P)
            if not len(up) or not len(dn) or not len(dn10): continue
            e90 = up[0]; x90 = 300 + n // 2 + dn[0]; x10 = 300 + n // 2 + dn10[0]
            below = np.flatnonzero(r[:e90] < 0.1 * P); e10 = below[-1] + 1 if len(below) else 0
            if x90 - e90 < 100 or e90 - e10 < 10: continue
            ins = (-off[lo:hi] - ref) * sgn; mid = ins[e90:x90]
            C.append((ins[e10:e90].mean(), mid.mean(), ins[x10:x10 + 150].mean() if x10 + 150 <= len(ins) else np.nan,
                      np.std(ma(mid - ma(mid, 400), 30)[100:-100]) if len(mid) > 500 else np.nan, np.abs(d["tq"][lo:hi]).max(), P))
    C = np.array(C)
    M["curves"] = dict(count=len(C)) if len(C) < 3 else dict(count=len(C), plateau=round(float(np.median(C[:, 5])), 2),
        inside_entry_cm=round(float(np.median(C[:, 0])), 1), inside_mid_cm=round(float(np.median(C[:, 1])), 1),
        after_exit_cm=round(float(np.nanmedian(C[:, 2])), 1), mid_lane_rms_cm=round(float(np.nanmedian(C[:, 3])), 2), peak_torque_counts=int(np.median(C[:, 4])))
    # take-overs
    latmin = (d["lat"] > 0.5).sum() / 6000; nearblink = dilate(d["blink"] > 0.5, 300)
    on = np.flatnonzero(np.diff((d["hands"] > 0.5).astype(int)) == 1)
    to = sum(1 for i in on if d["lat"][i] > 0.5 and not nearblink[i])
    names = [e[1] for e in d["events"]]; first = lambda n: sum(1 for i, x in enumerate(names) if x == n and (i == 0 or names[i - 1] != n))
    ev_t = {}
    for tt, nm in d["events"]: ev_t.setdefault(nm, []).append(float(tt))
    episodes = lambda n: len(runs(np.isin(np.round(d["t"], 1), np.round(ev_t.get(n, []), 1)), 1)) if n in ev_t else 0
    M["takeovers"] = dict(steering_active_min=round(latmin, 1), takeovers=to, per_10_min=round(10 * to / max(latmin, 0.1), 1),
                          steer_saturated=episodes("steerSaturated"), hands_off_min=round(eng.sum() / 6000, 1))
    # speed control
    lg = d["long"] > 0.5; lmin = lg.sum() / 6000
    if lmin > 1.0:
        a = ma(d["a"], 30); hard = runs(lg & (a <= -2.5), 50)
        foll = lg & (d["lead"] > 0.5) & (v > 15.2) & (d["drel"] > 1) & (d["drel"] < 150)
        gap = (d["drel"] / np.maximum(v, 1))[foll]
        flips = len(swings(ma(d["acmd"], 20)[lg], 0.3)) if lg.sum() > 100 else 0
        stops = []
        for i in np.flatnonzero(np.diff((d["still"] > 0.5).astype(int)) == 1):
            if lg[max(i - 100, 0)] and d["lead"][i] > 0.5 and 0.3 < d["drel"][i] < 15: stops.append(d["drel"][i])
        M["speed"] = dict(minutes=round(lmin, 1), hard_brakes=len(hard), hard_brakes_per_10_min=round(10 * len(hard) / lmin, 2),
                          strongest_braking=round(float(a[lg].min()), 2), accel_flips_per_min=round(flips / lmin, 1),
                          following_min=round(foll.sum() / 6000, 1), time_gap_median=round(float(np.median(gap)), 2) if foll.sum() > 600 else None,
                          time_gap_p10=round(float(np.percentile(gap, 10)), 2) if foll.sum() > 600 else None,
                          stops_behind_lead=len(stops), stop_gap_min_m=round(float(min(stops)), 1) if stops else None,
                          stop_gap_median_m=round(float(np.median(stops)), 1) if stops else None)
    else:
        M["speed"] = dict(minutes=round(lmin, 1))
    # messages and faults
    H = json.loads(str(d["health"])); nseg = int(d["segments"])
    def pct(a, b, steps=False):       # counter steps are counted inside a segment, so each segment has one fewer
        den = H.get(b, 0) - (nseg if steps else 0)
        return round(min(100.0, 100 * H.get(a, 0) / den), 2) if den > 0 else None
    M["health"] = dict(scc14_frames=H.get("scc14", 0), scc14_checksum_valid_pct=pct("scc14_ok", "scc14"), scc14_counter_ok_pct=pct("scc14_step", "scc14", True),
                       mdps12_frames=H.get("mdps", 0), mdps12_checksum_valid_pct=pct("mdps_ok", "mdps"), mdps12_counter_ok_pct=pct("mdps_step", "mdps", True),
                       camera_warning_frames=H.get("cam_warn", 0), warning_frames_sent_to_car=H.get("tx_warn", 0), panda_invalid_rx=H.get("rxInvalid", 0),
                       steer_fault_frames=H.get("steerFaultTemporary", 0) + H.get("steerFaultPermanent", 0), cruise_fault_frames=H.get("accFaulted", 0),
                       alerts=[str(a) for a in d["alerts"]], bookmarks=len(d["bookmarks"]))
    M["info"] = dict(json.loads(str(d["info"])), segments=int(d["segments"]), minutes=round(len(v) / 6000, 1), top_speed_mph=round(float(mph.max())))
    return M

# ---------------------------------------------------------------- rating and report
# (section, key, label, unit, lower is better, floor: differences below this are not rated worse)
RATED = [("lane_rms_cm", "lane movement", "cm", 0.3), ("swings8_per_min", "slow swings of 8 cm+", "/min", 1.0), ("swings15_per_min", "large swings of 15 cm+", "/min", 0.4),
         ("wheel_rms_deg", "wheel movement", "deg", 0.03), ("wheel_swings_per_min", "wheel swings", "/min", 2.0), ("torque_flips_per_min", "torque flips", "/min", 8.0),
         ("tracking_error", "tracking error", "m/s2", 0.004)]
def rate(val, base, floor):
    if val is None or base is None: return ""
    if val <= base * 1.25 + floor: return "good"
    if val <= base * 1.75 + 2 * floor: return "fair"
    return "poor"
def rows(M, B):
    R = []
    for band, _, _ in BANDS:
        s = M["steering"].get(band, {}); b = (B or {}).get("steering", {}).get(band, {})
        rated = s.get("minutes", 0) >= MIN_RATE_MIN
        R.append(("h", f"Steering on straights, {band}", f"{s.get('minutes', 0)} min" + ("" if rated or s.get("minutes", 0) < 0.3 else " (too little to rate)")))
        for key, label, unit, floor in RATED:
            if key in s: R.append(("r", label, s[key], unit, b.get(key), rate(s[key], b.get(key), floor) if rated else ""))
    s = M["low_speed_wheel"]; b = (B or {}).get("low_speed_wheel", {})
    R.append(("h", "Low speed, lane lines not needed (15-45 mph)", f"{s.get('minutes', 0)} min"))
    for key, label, unit, floor in (("wheel_rms_deg", "wheel movement", "deg", 0.05), ("wheel_swings_per_min", "wheel swings of 1 deg+", "/min", 2.0), ("torque_flips_per_min", "torque flips", "/min", 8.0)):
        if key in s: R.append(("r", label, s[key], unit, b.get(key), rate(s[key], b.get(key), floor) if s["minutes"] >= MIN_RATE_MIN else ""))
    s = M["curves"]; b = (B or {}).get("curves", {})
    R.append(("h", "Curves above 45 mph", f"{s.get('count', 0)} curves"))
    for key, label, unit in (("inside_entry_cm", "position toward the inside, entry", "cm"), ("inside_mid_cm", "mid-turn", "cm"), ("after_exit_cm", "1.5 s after the exit", "cm"),
                             ("mid_lane_rms_cm", "lane movement mid-turn", "cm"), ("peak_torque_counts", "largest torque", "counts")):
        if key in s:
            r = rate(abs(s[key]), abs(b[key]) if b.get(key) is not None else None, 4.0 if key != "mid_lane_rms_cm" else 0.4) if key in ("after_exit_cm", "mid_lane_rms_cm") and s["count"] >= 5 else ""
            R.append(("r", label, s[key], unit, b.get(key), r))
    s = M["takeovers"]; b = (B or {}).get("takeovers", {})
    R.append(("h", "Take-overs", f"{s['steering_active_min']} min with steering active, {s['hands_off_min']} min hands off"))
    R.append(("r", "driver took the wheel", s["per_10_min"], "/10 min", b.get("per_10_min"), rate(s["per_10_min"], b.get("per_10_min"), 1.5) if s["steering_active_min"] >= 5 else ""))
    R.append(("r", "steering at its torque limit", s["steer_saturated"], "times", None, "good" if s["steer_saturated"] == 0 else "fair"))
    s = M["speed"]; b = (B or {}).get("speed", {})
    R.append(("h", "Speed control", f"{s.get('minutes', 0)} min under openpilot's control" if s.get("minutes", 0) > 1 else "not used on this drive"))
    if "hard_brakes" in s:
        R.append(("r", "braking of 2.5 m/s2+ held 0.5 s", s["hard_brakes_per_10_min"], "/10 min", b.get("hard_brakes_per_10_min"), "good" if s["hard_brakes"] == 0 else ("fair" if s["hard_brakes_per_10_min"] <= 1.0 else "poor")))
        R.append(("r", "strongest braking", s["strongest_braking"], "m/s2", b.get("strongest_braking"), "good" if s["strongest_braking"] > -2.0 else ("fair" if s["strongest_braking"] > -3.0 else "poor")))
        R.append(("r", "acceleration command flips", s["accel_flips_per_min"], "/min", b.get("accel_flips_per_min"), rate(s["accel_flips_per_min"], b.get("accel_flips_per_min"), 1.0)))
        if s.get("time_gap_median") is not None:
            R.append(("r", f"time gap behind a lead above 34 mph ({s['following_min']} min)", s["time_gap_median"], "s", b.get("time_gap_median"), ""))
            R.append(("r", "closest tenth of that", s["time_gap_p10"], "s", b.get("time_gap_p10"), "good" if s["time_gap_p10"] >= 0.6 else "poor"))
        if s.get("stops_behind_lead"):
            R.append(("r", f"closest stop behind a lead ({s['stops_behind_lead']} stops)", s["stop_gap_min_m"], "m", b.get("stop_gap_min_m"), "good" if s["stop_gap_min_m"] >= 2.5 else ("fair" if s["stop_gap_min_m"] >= 1.5 else "poor")))
    s = M["health"]
    R.append(("h", "Messages and faults", ""))
    def ok(label, val, good, unit=""):
        if val is not None: R.append(("r", label, val, unit, None, "good" if good else "poor"))
    if s["scc14_frames"]: ok(f"SCC14 checksum valid ({s['scc14_frames']} frames)", s["scc14_checksum_valid_pct"], s["scc14_checksum_valid_pct"] == 100, "%"); ok("SCC14 counter steps correct", s["scc14_counter_ok_pct"], s["scc14_counter_ok_pct"] > 99.9, "%")
    if s["mdps12_frames"]: ok(f"MDPS12 reaching the camera, checksum valid ({s['mdps12_frames']} frames)", s["mdps12_checksum_valid_pct"], s["mdps12_checksum_valid_pct"] == 100, "%"); ok("MDPS12 counter steps correct", s["mdps12_counter_ok_pct"], s["mdps12_counter_ok_pct"] > 99.9, "%")
    R.append(("r", "camera warning frames (take-a-break)", s["camera_warning_frames"], "frames", None, ""))
    ok("of those, sent on to the car", s["warning_frames_sent_to_car"], s["warning_frames_sent_to_car"] == 0, "frames")
    ok("panda invalid-receive count", s["panda_invalid_rx"], s["panda_invalid_rx"] == 0)
    ok("steering fault frames", s["steer_fault_frames"], s["steer_fault_frames"] == 0); ok("cruise fault frames", s["cruise_fault_frames"], s["cruise_fault_frames"] == 0)
    return R

def summary(R):
    c = {"good": 0, "fair": 0, "poor": 0}
    for r in R:
        if r[0] == "r" and r[5] in c: c[r[5]] += 1
    return c

def print_report(route, M, R, B):
    i = M["info"]; c = summary(R)
    print(f"\n===== {route}  {i.get('branch', '?')} @ {i.get('commit', '?')}  {i['segments']} segments, {i['minutes']} min   rated: {c['good']} good, {c['fair']} fair, {c['poor']} poor" + ("" if B else "   (no baseline yet: run --baseline)"))
    for r in R:
        if r[0] == "h": print(f"\n{r[1]}  [{r[2]}]")
        else: print(f"   {r[1]:52s} {str(r[2]):>8s} {r[3]:8s} baseline {str(r[4]) if r[4] is not None else '-':>7s}   {r[5]}")
    h = M["health"]
    print(f"\nalerts shown: {', '.join(h['alerts']) if h['alerts'] else 'none'}   bookmarks: {h['bookmarks']}")

CSS = """body{font:15px/1.45 system-ui,Segoe UI,sans-serif;margin:24px auto;max-width:860px;padding:0 16px;background:#f7f6f3;color:#161616}
h1{font-size:22px;margin:0 0 4px}.sub{color:#5d5b57;margin-bottom:18px}table{border-collapse:collapse;width:100%;margin-bottom:6px}
td{padding:5px 8px;border-bottom:1px solid #e3e1dc}tr.h td{font-weight:600;padding-top:18px;border-bottom:2px solid #c9c6bf}
td.n{text-align:right;font-variant-numeric:tabular-nums}td.u,td.b{color:#5d5b57}.good{color:#1b6e3c;font-weight:600}.fair{color:#8a5a00;font-weight:600}.poor{color:#b3261e;font-weight:600}
.pill{display:inline-block;padding:2px 10px;border-radius:12px;margin-right:6px;background:#e9e7e1}
@media(prefers-color-scheme:dark){body{background:#17181a;color:#ecebe8}td{border-color:#2c2e31}tr.h td{border-color:#44474b}.sub,td.u,td.b{color:#a3a09a}.pill{background:#2a2c2f}.good{color:#6fcf97}.fair{color:#e6b450}.poor{color:#f2857d}}"""
def write_html(route, M, R, B):
    i = M["info"]; c = summary(R); e = html.escape
    out = [f"<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>Drive {e(route)}</title><style>{CSS}</style>",
           f"<h1>Drive {e(route)}</h1><div class=sub>{e(i.get('branch', '?'))} @ {e(i.get('commit', '?'))} &middot; {i['segments']} segments, {i['minutes']} min &middot; baseline: {e(', '.join(B['routes'])) if B else 'none set'}</div>",
           f"<div><span class='pill good'>{c['good']} good</span><span class='pill fair'>{c['fair']} fair</span><span class='pill poor'>{c['poor']} poor</span></div><table>"]
    for r in R:
        if r[0] == "h": out.append(f"<tr class=h><td colspan=3>{e(r[1])}</td><td colspan=2 class=b>{e(str(r[2]))}</td></tr>")
        else: out.append(f"<tr><td>{e(r[1])}</td><td class=n>{e(str(r[2]))}</td><td class=u>{e(r[3])}</td><td class=b>{'baseline ' + e(str(r[4])) if r[4] is not None else ''}</td><td class='{r[5]}'>{r[5]}</td></tr>")
    h = M["health"]
    out.append(f"</table><p class=sub>Alerts shown: {e(', '.join(h['alerts'])) if h['alerts'] else 'none'}. Bookmarks: {h['bookmarks']}.<br>good = within 25 % of the baseline or better, fair = within 75 %, poor beyond. Unrated rows had too little data or no baseline.</p>")
    p = os.path.join(OUT, route + ".html"); open(p, "w", encoding="utf-8").write("\n".join(out)); return p

def baseline_from(Ms, routes):
    def med(vals):
        vals = [x for x in vals if isinstance(x, (int, float))]; return round(float(np.median(vals)), 4) if vals else None
    B = {"routes": routes, "steering": {}, "made": time.strftime("%Y-%m-%d")}
    for band, _, _ in BANDS:
        keys = {k for M in Ms for k in M["steering"].get(band, {})}
        B["steering"][band] = {k: med([M["steering"].get(band, {}).get(k) for M in Ms if M["steering"].get(band, {}).get("minutes", 0) >= MIN_RATE_MIN or k == "minutes"]) for k in keys}
    for sec in ("low_speed_wheel", "curves", "takeovers", "speed"):
        keys = {k for M in Ms for k in M[sec]}; B[sec] = {k: med([M[sec].get(k) for M in Ms]) for k in keys}
    return B

def main():
    args = sys.argv[1:]
    os.makedirs(OUT, exist_ok=True); bpath = os.path.join(OUT, "baseline.json"); hpath = os.path.join(OUT, "history.jsonl")
    if not args: print(__doc__); return
    if args[0] == "--trend":
        if not os.path.exists(hpath): print("no drives assessed yet"); return
        last = {}
        for l in open(hpath, encoding="utf-8"):
            j = json.loads(l); last[j["route"]] = j
        print(f"{'route':9s} {'commit':8s} {'min':>5s} | {'>60 lane cm':>11s} {'swings/min':>10s} {'wheel deg':>9s} | {'curve exit cm':>13s} | {'take-overs/10':>13s} | {'hard brakes/10':>14s} | good fair poor")
        for r, j in sorted(last.items()):
            s = j["metrics"]["steering"].get("above 60 mph", {}); c = j["metrics"]["curves"]; t = j["metrics"]["takeovers"]; sp = j["metrics"]["speed"]; g = j["rated"]
            f = lambda x: "-" if x is None else str(x)
            print(f"{r:9s} {j['metrics']['info'].get('commit', '?'):8s} {j['metrics']['info']['minutes']:5.1f} | {f(s.get('lane_rms_cm')):>11s} {f(s.get('swings8_per_min')):>10s} {f(s.get('wheel_rms_deg')):>9s} | {f(c.get('after_exit_cm')):>13s} | {f(t.get('per_10_min')):>13s} | {f(sp.get('hard_brakes_per_10_min')):>14s} | {g['good']:4d} {g['fair']:4d} {g['poor']:4d}")
        return
    make_base = args[0] == "--baseline"; routes = args[1:] if make_base else args
    Ms = [assess(load(r)) for r in routes]
    if make_base:
        B = baseline_from(Ms, routes); json.dump(B, open(bpath, "w", encoding="utf-8"), indent=1); print("baseline written from", ", ".join(routes), "->", bpath)
    B = json.load(open(bpath, encoding="utf-8")) if os.path.exists(bpath) else None
    for route, M in zip(routes, Ms):
        R = rows(M, B); print_report(route, M, R, B)
        json.dump(M, open(os.path.join(OUT, route + ".json"), "w", encoding="utf-8"), indent=1)
        with open(hpath, "a", encoding="utf-8") as f: f.write(json.dumps(dict(route=route, assessed=time.strftime("%Y-%m-%d %H:%M"), metrics=M, rated=summary(R))) + "\n")
        print("report:", write_html(route, M, R, B))

if __name__ == "__main__":
    main()
