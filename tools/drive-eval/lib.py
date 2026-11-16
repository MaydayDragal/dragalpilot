import pickle, glob, os, re, numpy as np
TK = ['active','actualLateralAccel','d','desiredLateralAccel','desiredLateralJerk','error','errorRate','f','i','output','p','saturated','version']
def load(D):
    segs = {}
    for f in glob.glob(os.path.join(D, "*.pkl")):
        r, n = re.match(r"(.*)--(\d+)\.pkl", os.path.basename(f)).groups()
        segs.setdefault(r[:8], {})[int(n)] = pickle.load(open(f, "rb"))
    out = {}
    for r, ss in segs.items():
        ns = sorted(ss)
        cat = lambda k: np.vstack([ss[n][k] for n in ns if len(ss[n][k])])
        cs, cc, co, ctl, md = cat("cs"), cat("cc"), cat("co"), cat("ctl"), cat("model")
        t = ctl[:,0]; t0 = cs[0,0]
        ip = lambda a, c: np.interp(t, a[:,0], a[:,c])
        d = dict(t=t-t0, v=ip(cs,1), ang=ip(cs,3), rate=ip(cs,4), drv=ip(cs,5), eps=ip(cs,6), pressed=ip(cs,7)>0.5, blink=ip(cs,10)>0.5,
                 yaw=ip(cs,13), latActive=ip(cc,1)>0.5, cmd=ip(cc,3), roll=ip(cc,6), out=ip(co,1), outcan=ip(co,2), curv=ctl[:,1], dcurv=ctl[:,2],
                 ll=ip(md,1), rl=ip(md,2), llp=ip(md,3), rlp=ip(md,4), mcurv=ip(md,5))
        for i, k in enumerate(TK): d[k] = ctl[:,3+i]
        d["bm"] = [tt - t0 for n in ns for tt, w in ss[n]["bm"] if w == "userBookmark"]
        d["events"] = [(tt - t0, e) for n in ns for tt, e in ss[n]["events"]]
        out[r] = d
    return out
