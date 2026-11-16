import sys, numpy as np
sys.path.insert(0, sys.argv[1]); from lib import load
R = load(sys.argv[2]); r, a, b, step = sys.argv[3], float(sys.argv[4]), float(sys.argv[5]), float(sys.argv[6])
d = R[r]; print("bookmarks", d["bm"])
print("   t   mph  angle  rate | desLA actLA   err |    p     i     f     d   out  cmd->sent can | drvTq act prs sat blk | laneC")
for tt in np.arange(a, b, step):
    i = np.searchsorted(d["t"], tt)
    lanec = (d["ll"][i] + d["rl"][i]) / 2
    print(f"{d['t'][i]:6.1f} {d['v'][i]*2.237:4.0f} {d['ang'][i]:6.1f} {d['rate'][i]:5.0f} | {d['desiredLateralAccel'][i]:5.2f} {d['actualLateralAccel'][i]:5.2f} {d['error'][i]:5.2f} | {d['p'][i]:5.2f} {d['i'][i]:5.2f} {d['f'][i]:5.2f} {d['d'][i]:5.2f} {d['output'][i]:5.2f} {d['cmd'][i]:5.2f}->{d['out'][i]:5.2f} {d['outcan'][i]:4.0f} | {d['drv'][i]:5.0f} {int(d['latActive'][i])}   {int(d['pressed'][i])}   {int(d['saturated'][i])}   {int(d['blink'][i])} | {lanec:5.2f}")
