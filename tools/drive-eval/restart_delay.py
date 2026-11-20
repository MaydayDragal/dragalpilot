"""How long the car waits behind a lead that pulls away from a standstill. PC.

  CEREAL_DIR=... CAR_CAPNP_DIR=... python restart_delay.py <recordings root> <route> [<route> ...] [--trace]

For every standstill with openpilot longitudinal active and a lead: when the lead starts moving (0.3 m/s), when the
plan stops asking for a stop, when the controller leaves "stopping", when the command goes positive, when the car
moves (0.1 m/s) and reaches 1 m/s, and how far the lead has gone by then. --trace prints each one at 0.25 s steps."""
import sys, glob, re, os
import numpy as np
import pclog

ROOT = sys.argv[1]; ROUTES = [a for a in sys.argv[2:] if not a.startswith("--")]; TRACE = "--trace" in sys.argv

def rows(route):
    ps = glob.glob(os.path.join(ROOT, "**", route + "--*", "rlog.zst"), recursive=True)
    ps.sort(key=lambda p: int(re.search(r"--(\d+)[\\/]rlog", p).group(1)))
    R = []; v = a = at = acc = 0.0; gas = brk = stand = cstand = la = ss = False; st = ""; src = ""; btn = 0
    for p in ps:
        for m in pclog.read(p):
            w = m.which()
            if w == "carState":
                c = m.carState; v, a, gas, brk, stand, cstand = c.vEgo, c.aEgo, c.gasPressed, c.brakePressed, c.standstill, c.cruiseState.standstill
                if len(c.buttonEvents): btn = 1
            elif w == "carControl": c = m.carControl; la, acc, st = c.longActive, c.actuators.accel, str(c.actuators.longControlState)
            elif w == "longitudinalPlan": l = m.longitudinalPlan; at, ss, src = l.aTarget, l.shouldStop, str(l.longitudinalPlanSource)
            elif w == "radarState":
                l = m.radarState.leadOne
                R.append((m.logMonoTime * 1e-9, v, a, gas, brk, stand, cstand, la, acc, {"off": 0, "pid": 1, "stopping": 2, "starting": 3}.get(st, 9), at, ss,
                          {"cruise": 0, "lead0": 1, "lead1": 2, "lead2": 3, "e2e": 4}.get(src, 9), l.present, l.dRel, l.vLead, l.aLeadK, btn)); btn = 0
    return np.array(R, float)

def first(m, i, j):
    k = np.flatnonzero(m[i:j]); return i + k[0] if len(k) else None

ALL = []
for r in ROUTES:
    X = rows(r)
    if not len(X): continue
    t, v, a, gas, brk, stand, cstand, la, acc, st, at, ss, src, lead, d, vl, al, btn = X.T
    m = (stand > 0.5) & (la > 0.5); idx = np.flatnonzero(np.diff(np.r_[0, m.astype(int), 0]))
    for i, j in zip(idx[::2], idx[1::2]):
        if j - i < 20 or lead[i:j].mean() < 0.5: continue
        end = min(j + 200, len(t))
        k0 = None
        for k in np.flatnonzero((vl[i:end] > 0.3) & (lead[i:end] > 0.5)) + i:      # lead start: stays above 0.3 for 0.5 s
            if np.all(vl[k:k + 10] > 0.3): k0 = k; break
        if k0 is None: continue
        f = lambda mm: first(mm, k0 - 40, end)
        e = dict(route=r[-2:], held=(j - i) / 20, d0=d[k0], nostop=f(ss < 0.5), leave=f(st != 2), pos=f(acc > 0.05), move=f(v > 0.1), v1=f(v > 1.0), v3=f(v > 3.0),
                 gas=bool(gas[k0:end].max() > 0.5), btn=bool(btn[k0 - 20:end].max() > 0.5), cstand=cstand[i:j].mean())
        rel = lambda k: float("nan") if k is None else t[k] - t[k0]
        dd = lambda k: float("nan") if k is None else d[k]
        ALL.append((rel(e["nostop"]), rel(e["leave"]), rel(e["pos"]), rel(e["move"]), rel(e["v1"]), rel(e["v3"]), dd(e["move"]) - e["d0"], e["gas"]))
        print(f"{e['route']} t={t[i] - t[0]:6.0f}s held {e['held']:5.1f}s gap {e['d0']:4.1f} m | stop request off {rel(e['nostop']):+5.2f}  leaves stopping {rel(e['leave']):+5.2f}  command>0 {rel(e['pos']):+5.2f}  "
              f"moves {rel(e['move']):+5.2f}  1 m/s {rel(e['v1']):+5.2f}  3 m/s {rel(e['v3']):+5.2f} | lead gained {dd(e['move']) - e['d0']:4.1f} m at move, {dd(e['v1']) - e['d0']:4.1f} m at 1 m/s"
              f"{' | GAS' if e['gas'] else ''}{' | button' if e['btn'] else ''}{' | cruise standstill flag' if e['cstand'] > 0.5 else ''}")
        if TRACE:
            for k in range(k0 - 10, min(k0 + 120, len(t)), 5):
                print(f"      {t[k] - t[k0]:+5.2f}s lead v {vl[k]:5.2f} a {al[k]:+5.2f} d {d[k]:5.1f} | plan a {at[k]:+5.2f} stop {int(ss[k])} src {int(src[k])} | state {int(st[k])} cmd {acc[k]:+5.2f} | ego v {v[k]:5.2f} a {a[k]:+5.2f} gas {int(gas[k])}")
if ALL:
    A = np.array([x[:7] for x in ALL if not x[7]], float)
    if len(A):
        n = ["stop request off", "leaves stopping", "command > 0", "car moves", "1 m/s", "3 m/s", "lead gained at move (m)"]
        print(f"\n{len(A)} restarts without gas (median, range), seconds after the lead starts:")
        for c in range(7): print(f"   {n[c]:26s} {np.nanmedian(A[:, c]):5.2f}  ({np.nanmin(A[:, c]):.2f} to {np.nanmax(A[:, c]):.2f})")
