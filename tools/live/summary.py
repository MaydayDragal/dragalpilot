"""Summary of a live CSV (from live.py), using the drive-eval definitions at the live sample rate.

  python summary.py <csv> [--last SECONDS] [--from T0 --to T1]

Straight: 5 s moving mean of the request within +/-0.35 m/s^2, hands off, lat active, no blinker, both lane-line
probabilities > 0.5. Spectra: Hann windows of about 20.5 s, 50 % overlap (as tools/drive-eval/weave.py, which
runs at 100 Hz; here the data is 20 Hz, so content above a few Hz is not resolved).
"""
import argparse, sys
import numpy as np

FS = 20.0
BANDS = [(0.1, 0.2), (0.2, 0.3), (0.3, 0.45), (0.45, 0.7), (0.7, 1.0), (1.0, 2.0)]


def load(path):
  rows, cols = [], None
  for line in open(path):
    if line.startswith("#") or not line.strip():
      continue
    parts = line.rstrip("\n").split(",")
    if cols is None:
      if parts[0] == "t":
        cols = parts
      continue
    if len(parts) == len(cols):
      rows.append([float(x) if x else np.nan for x in parts])
  if cols is None or len(rows) < 2:
    sys.exit("no data rows in " + path)
  a = np.array(rows)
  t = a[:, 0]
  grid = np.arange(t[0], t[-1], 1 / FS)
  d = {}
  for i, k in enumerate(cols):
    col = a[:, i]
    ok = ~np.isnan(col)
    d[k] = np.interp(grid, t[ok], col[ok], left=np.nan, right=np.nan) if ok.sum() > 1 else np.full(len(grid), np.nan)
  d["t"] = grid - t[0]
  d["gap_max"] = float(np.diff(t).max())
  d["rate"] = (len(t) - 1) / (t[-1] - t[0])
  return d


def runs(m, minlen):
  idx = np.flatnonzero(np.diff(np.r_[0, m.astype(int), 0]))
  return [(a, b) for a, b in zip(idx[::2], idx[1::2]) if b - a >= minlen]


def flag(x):
  return np.nan_to_num(x, nan=0.0) > 0.5


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("csv")
  ap.add_argument("--last", type=float)
  ap.add_argument("--from", dest="t0", type=float)
  ap.add_argument("--to", dest="t1", type=float)
  a = ap.parse_args()
  d = load(a.csv)
  t = d["t"]
  sel = np.ones(len(t), bool)
  if a.last:
    sel &= t >= t[-1] - a.last
  if a.t0 is not None:
    sel &= t >= a.t0
  if a.t1 is not None:
    sel &= t <= a.t1
  gap, rate = d["gap_max"], d["rate"]
  d = {k: v[sel] for k, v in d.items() if isinstance(v, np.ndarray)}
  t = d["t"]
  if len(t) < 2:
    sys.exit("empty selection")
  print(f"{a.csv}\n  span {t[0]:.0f}-{t[-1]:.0f} s ({t[-1]-t[0]:.0f} s), sample rate {rate:.1f} Hz, largest gap {gap:.2f} s")

  lat = flag(d["latActive"])
  v = d["v"]
  have_ctl = ~np.isnan(d["desiredLateralAccel"])
  print(f"  onroad {flag(d['started']).mean()*100:.0f} %, lat active {lat.mean()*100:.0f} % ({lat.sum()/FS:.0f} s), "
        f"torque state present {have_ctl.mean()*100:.0f} %")
  if not have_ctl.any() or not lat.any():
    print("  no lateral-control data in this span (device offroad or not engaged)")
    return
  for k, name in (("delay", "steering delay"), ("laf", "lat accel factor (learned)"), ("fric", "friction (learned)"), ("version", "torque controller version")):
    x = d[k][~np.isnan(d[k])]
    if len(x):
      print(f"  {name}: {np.median(x):.3g} (min {x.min():.3g}, max {x.max():.3g})")

  des, act = d["desiredLateralAccel"], d["actualLateralAccel"]
  hands_off = lat & ~flag(d["pressed"]) & have_ctl
  print("\n  tracking, lat active and hands off:   seconds   RMS error   RMS request   saturated %")
  for name, lo, hi in ((">60 mph", 26.8, 99), ("35-60 mph", 15.6, 26.8), ("<35 mph", 0.5, 15.6)):
    m = hands_off & (v >= lo) & (v < hi)
    if m.sum() < FS * 5:
      print(f"    {name:10s} too little data"); continue
    print(f"    {name:10s} {m.sum()/FS:22.0f}   {np.sqrt(np.mean((des[m]-act[m])**2)):9.3f}   {np.sqrt(np.mean(des[m]**2)):11.3f}   {flag(d['saturated'])[m].mean()*100:11.1f}")

  N = int(round(20.5 * FS)); N += N % 2
  w = np.hanning(N); f = np.fft.rfftfreq(N, 1 / FS)
  spec = lambda x: np.fft.rfft((x - x.mean()) * w)
  n5 = int(5 * FS)
  des_lp = np.convolve(np.nan_to_num(des), np.ones(n5) / n5, mode="same")
  lane = (d["ll"] + d["rl"]) / 2
  margin = int(FS)
  for name, lo, hi in ((">60 mph", 26.8, 99), ("35-60 mph", 15.6, 26.8)):
    ok = hands_off & ~flag(d["blink"]) & (np.abs(np.nan_to_num(d["drv"])) < 80) & (v >= lo) & (v < hi) & (np.abs(des_lp) < 0.35) \
         & (np.nan_to_num(d["llp"]) > 0.5) & (np.nan_to_num(d["rlp"]) > 0.5) & ~np.isnan(lane) & ~np.isnan(d["out"]) & ~np.isnan(d["ang"])
    P = dict.fromkeys(["lane", "des", "act", "ang", "tq"], 0.0); X = 0.0; n = 0
    for s0, s1 in runs(ok, N + 2 * margin):
      for s in range(s0 + margin, s1 - margin - N + 1, N // 2):
        sl = slice(s, s + N)
        L, D, A, G, T = spec(lane[sl]), spec(des[sl]), spec(act[sl]), spec(d["ang"][sl]), spec(d["out"][sl])
        P["lane"] += abs(L)**2; P["des"] += abs(D)**2; P["act"] += abs(A)**2; P["ang"] += abs(G)**2; P["tq"] += abs(T)**2
        X = X + np.conj(D) * A; n += 1
    print(f"\n  straight stretches, {name}: {n} windows ({n*N/2/FS + (N/2/FS if n else 0):.0f} s of data)")
    if n < 2:
      print("    too little data (need two 20.5 s windows on a straight)"); continue
    if n < 4:
      print("    few windows: treat the numbers as rough")
    amp = lambda p, k: np.sqrt(2 * p[k].sum() / n) / w.sum()
    print("    band(Hz)    lane(cm)  request   actual   gain   lag(deg)   coh   wheel(deg)   torque")
    for b0, b1 in BANDS:
      k = (f >= b0) & (f < b1)
      H = X[k].sum() / P["des"][k].sum(); coh = abs(X[k].sum())**2 / (P["des"][k].sum() * P["act"][k].sum())
      print(f"    {b0:.2f}-{b1:.2f}  {amp(P['lane'], k)*100:8.2f}  {amp(P['des'], k):7.3f}  {amp(P['act'], k):7.3f}  {abs(H):5.2f}  {-np.degrees(np.angle(H)):8.0f}  {coh:5.2f}  {amp(P['ang'], k):10.3f}  {amp(P['tq'], k):7.4f}")


if __name__ == "__main__":
  main()
