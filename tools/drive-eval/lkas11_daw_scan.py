# runs on the comma (offroad), read-only; pipe it in:  python - <route> [<route> ...] < lkas11_daw_scan.py
# Counts the camera's LKAS11 (0x340, bus 2) frames by (byte 1 bit 7 = CF_Lkas_FcwBasReq, CF_Lkas_SysWarning,
# camera LKAS12 Driver Attention Warning active), to see when the camera sets the bit that accompanies the
# attention-assist chime and whether its own warning fields mark those frames.
import sys, glob, collections
from multiprocessing import Pool
from openpilot.tools.lib.logreader import LogReader

def seg(p):
  c = collections.Counter(); daw = 0
  for m in LogReader(p):
    if m.which() == "can":
      for x in m.can:
        if x.src == 2 and x.address == 0x53E:
          d = bytes(x.dat); daw = int((d[5] & 7) == 6 or (d[5] >> 3) & 2)
        elif x.src == 2 and x.address == 0x340:
          d = bytes(x.dat); c[((d[1] >> 7) & 1, (d[0] >> 6) | ((d[1] & 3) << 2), daw)] += 1
  return p.split("/")[-2], c

if __name__ == "__main__":
  paths = []
  for r in sys.argv[1:]: paths += glob.glob(f"/data/media/0/realdata/{r}--*/rlog.zst")
  with Pool(4) as pool: res = pool.map(seg, sorted(paths))
  tot = collections.Counter(); routes = collections.defaultdict(collections.Counter)
  for name, c in res: tot.update(c); routes[name[:8]].update(c)
  print("routes:", sorted(routes), "segments:", len(paths))
  print("camera LKAS11 frames by (byte1.bit7, SysWarning, LKAS12 warning active):")
  for k, v in sorted(tot.items(), key=lambda kv: -kv[1]): print("  ", k, v)
  print("routes with the bit set:", {r: sum(v for k, v in c.items() if k[0] == 1) for r, c in routes.items() if any(k[0] == 1 for k in c)})
  print("routes with SysWarning 15:", {r: sum(v for k, v in c.items() if k[1] == 15) for r, c in routes.items() if any(k[1] == 15 for k in c)})
