import pickle, glob, os, sys, re, numpy as np
D = sys.argv[1]
segs = {}
for f in glob.glob(os.path.join(D, "*.pkl")):
    r, n = re.match(r"(.*)--(\d+)\.pkl", os.path.basename(f)).groups()
    segs.setdefault(r, {})[int(n)] = pickle.load(open(f, "rb"))
for r in sorted(segs):
    ss = segs[r]; ns = [n for n in sorted(ss) if len(ss[n]["cs"]) and len(ss[n]["cc"])]
    cs = np.vstack([ss[n]["cs"] for n in ns]); cc = np.vstack([ss[n]["cc"] for n in ns])
    t0 = cs[0,0]
    print(f"\n=== {r}: {len(ns)} segs, {cs[-1,0]-t0:.0f}s, vmax {cs[:,1].max()*2.237:.0f} mph, mean {cs[:,1].mean()*2.237:.0f} mph, latActive {cc[:,1].mean()*100:.0f}%")
    for n in ns:
        for k, v in ss[n]["misc"]:
            if k in ("carParams", "params", "params_err") and n == ns[0]: print(" ", k, v)
            if k == "carParamsSP" and n == ns[0]: print("  carParamsSP", v[:600].replace("\n", " "))
    print("  tkeys", ss[ns[0]]["tkeys"])
    pandas = [v for n in ns for k, v in ss[n]["misc"] if k == "panda"]
    if pandas: print("  panda first", pandas[0][1:], "last", pandas[-1][1:])
    bms = [(t - t0, w) for n in ns for t, w in ss[n]["bm"]]
    print("  bookmarks:", [(round(t,1), w) for t, w in bms])
    ev = {}
    for n in ns:
        for t, name in ss[n]["events"]: ev.setdefault(name, []).append(t - t0)
    print("  events:", {k: (len(v), round(v[0]), round(v[-1])) for k, v in ev.items()})
    al = {}
    for n in ns:
        for row in ss[n]["ss"]:
            if row[3]: al.setdefault((row[3], row[4]), []).append(row[0] - t0)
    print("  alerts:", {k: (round(v[0]), round(v[-1]), len(v)) for k, v in al.items()})
    for key in ("vp", "ltp"):
        a = np.vstack([ss[n][key] for n in ns if len(ss[n][key])])
        print(" ", key, "first", np.round(a[0,1:], 3), "last", np.round(a[-1,1:], 3))
    ld = [x for n in ns for x in ss[n]["ld"]]
    if ld: print("  ld first", ld[0][1:], "last", ld[-1][1:])
    print("  faults: tempFault samples", int(cs[:,8].sum()), "perm", int(cs[:,9].sum()), "steeringPressed %", round(cs[:,7].mean()*100,1))
