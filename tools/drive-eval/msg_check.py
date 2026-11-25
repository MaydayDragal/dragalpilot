"""Checks what our branch sent on a drive: SCC14 counter and checksum, MDPS12 to the camera (checksum, counter, what
differs from the steering unit's own frame), the camera's LKAS12 against the copy re-sent to the car, panda and car faults.

  CEREAL_DIR=... CAR_CAPNP_DIR=... python msg_check.py <route folder prefix without --N> <first seg> <last seg>"""
import sys, collections
import pclog

base, s0, s1 = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
T = []
for i in range(256):
    c = i
    for _ in range(8): c = ((c << 1) ^ 0x1D) & 0xFF if c & 0x80 else (c << 1) & 0xFF
    T.append(c)
def crc8(dat):                     # as opendbc's hyundai_checksum: register starts at init XOR xor-out
    c = 0xFD ^ 0xDF
    for b in dat: c = T[c ^ b]
    return c ^ 0xDF
nib = lambda d: sum(sum(divmod(b, 16)) for b in d) % 16

F = collections.defaultdict(list); P = collections.Counter(); faults = collections.Counter(); ev = collections.Counter()
for seg in range(s0, s1 + 1):
    for m in pclog.read(f"{base}--{seg}/rlog.zst"):
        w = m.which()
        if w == "can":
            for c in m.can:
                if c.address in (0x53E, 0x251, 0x389, 0x420, 0x340): F[(c.address, c.src)].append(bytes(c.dat))
        elif w == "pandaStates":
            p = m.pandaStates[0]; P["n"] += 1; P["rxInvalid"] = max(P["rxInvalid"], p.safetyRxInvalid); P["txBlocked"] = max(P["txBlocked"], p.safetyTxBlocked)
            faults[str(p.faultStatus)] += 1
            for f in p.faults: faults["fault:" + str(f)] += 1
        elif w == "carState":
            c = m.carState
            for k in ("steerFaultTemporary", "steerFaultPermanent", "accFaulted"):
                if getattr(c, k): ev[k] += 1
print("frames", {f"{a:#x}/src{s}": len(v) for (a, s), v in sorted(F.items())})
fr = F[(0x389, 128)]
if fr:
    st = collections.Counter(((b[6] & 15) - (a[6] & 15)) % 15 for a, b in zip(fr, fr[1:]))
    print(f"SCC14 sent: nibble checksum valid {sum(nib(d) == 0 for d in fr)} of {len(fr)}; counter values {sorted(set(d[6] & 15 for d in fr))}; step of one on {st.get(1, 0)} of {len(fr) - 1}")
fr = F[(0x251, 130)]; car = F[(0x251, 0)]
if fr:
    st = collections.Counter((b[2] - a[2]) % 256 for a, b in zip(fr, fr[1:]))
    print(f"MDPS12 to camera: CRC valid {sum(crc8(d[:3] + d[4:]) == d[3] for d in fr)} of {len(fr)}; counter steps {st.most_common(3)}; relayed {len(fr)} of {len(car)} of the steering unit's frames")
    for i in (0, 1, 4, 5, 6, 7):
        a = collections.Counter(d[i] for d in car).most_common(3); b = collections.Counter(d[i] for d in fr).most_common(3)
        if [x[0] for x in a] != [x[0] for x in b]: print(f"   byte {i}: steering unit's own most common {[hex(x[0]) for x in a]}, sent to the camera {[hex(x[0]) for x in b]}")
cam = F[(0x53E, 2)]; tx = F[(0x53E, 128)]
if cam:
    print(f"LKAS12 camera: status values {sorted(collections.Counter(d[5] & 7 for d in cam).items())}, warning-bit frames {sum((d[5] >> 4) & 1 for d in cam)}")
    print(f"LKAS12 re-sent to the car: status values {sorted(collections.Counter(d[5] & 7 for d in tx).items())}, warning-bit frames {sum((d[5] >> 4) & 1 for d in tx)}")
print("panda:", dict(P), dict(faults), "| carState faults:", dict(ev))
