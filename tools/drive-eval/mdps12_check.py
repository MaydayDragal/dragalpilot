"""MDPS12 (0x251) checks for the camera re-send. PC.

  CEREAL_DIR=... CAR_CAPNP_DIR=... python mdps12_check.py <recordings root> <route> [max segments]

On the steering unit's own frames (bus 0): does CRC8 (J1850, init 0xFD, xor 0xDF) over the frame without byte 3
reproduce byte 3 (also tried: plain sum), does byte 2 count up by one, and are any bits set outside the DBC signals (a re-pack would drop
them)? On frames openpilot sent to the camera (sendcan bus 2), if any: which bits differ from the car's frame just
before, and is the checksum valid."""
import sys, glob, os, collections
import pclog
def crc8(data, init=0xFD, xor=0xDF, poly=0x1D):
    c = init ^ xor      # as opendbc.car.crc.mk_crc8_fun
    for b in data:
        c ^= b
        for _ in range(8): c = ((c << 1) ^ poly) & 0xFF if c & 0x80 else (c << 1) & 0xFF
    return c ^ xor
SIG = {"CR_Mdps_StrColTq": (0, 11), "CF_Mdps_Def": (11, 1), "CF_Mdps_ToiUnavail": (12, 1), "CF_Mdps_ToiActive": (13, 1), "CF_Mdps_ToiFlt": (14, 1), "CF_Mdps_FailStat": (15, 1),
       "CF_Mdps_MsgCount2": (16, 8), "CF_Mdps_Chksum2": (24, 8), "CF_Mdps_SErr": (37, 1), "CR_Mdps_StrTq": (40, 12), "CR_Mdps_OutTq": (52, 12)}
MASK = 0
for s, n in SIG.values(): MASK |= ((1 << n) - 1) << s
root, route = sys.argv[1], sys.argv[2]; mx = int(sys.argv[3]) if len(sys.argv) > 3 else 99
ps = sorted(glob.glob(os.path.join(root, "**", route + "--*", "rlog.zst"), recursive=True), key=lambda p: int(os.path.basename(os.path.dirname(p)).rsplit("--", 1)[1]))[:mx]
n = ok = oks = step = 0; extra = collections.Counter(); last = None; lastcar = None; sent = okc = 0; diff = collections.Counter(); toi = collections.Counter(); cnt_step = collections.Counter(); lastsent = None
for p in ps:
    for m in pclog.read(p):
        w = m.which()
        if w == "can":
            for c in m.can:
                if c.address != 0x251 or c.src != 0: continue
                d = bytes(c.dat); n += 1; ok += crc8(d[:3] + d[4:]) == d[3]; oks += (sum(d[:3] + d[4:]) % 256) == d[3]
                if last is not None: step += ((d[2] - last) & 0xFF) == 1
                last = d[2]; v = int.from_bytes(d, "little"); x = v & ~MASK
                if x: extra[x] += 1
                toi[((v >> 12) & 1, (v >> 13) & 1)] += 1; lastcar = v
        elif w == "sendcan":
            for c in m.sendcan:
                if c.address != 0x251: continue
                d = bytes(c.dat); sent += 1; okc += crc8(d[:3] + d[4:]) == d[3]; v = int.from_bytes(d, "little")
                if lastsent is not None: cnt_step[(d[2] - lastsent) & 0xFF] += 1
                lastsent = d[2]
                if lastcar is not None:
                    x = (v ^ lastcar) & ~(0xFFFF << 16)          # ignore counter and checksum
                    for name, (s, k) in SIG.items():
                        if (x >> s) & ((1 << k) - 1) and name not in ("CF_Mdps_MsgCount2", "CF_Mdps_Chksum2"): diff[name] += 1
                    if x & ~MASK: diff["bits outside the DBC"] += 1
print(f"{route}: car MDPS12 frames {n} | checksum reproduced by CRC8 {ok} ({100 * ok / max(n, 1):.2f} %), by plain sum {oks} ({100 * oks / max(n, 1):.2f} %) | counter +1 steps {step} ({100 * step / max(n - 1, 1):.2f} %)")
print("   bits set outside the DBC signals:", {hex(k): v for k, v in extra.most_common(6)} or "none")
print("   car (ToiUnavail, ToiActive) counts:", dict(toi))
if sent: print(f"   sent to the camera: {sent} | checksum valid {okc} ({100 * okc / sent:.2f} %) | counter steps {dict(cnt_step.most_common(4))} | fields differing from the car's latest frame: {dict(diff)}")
