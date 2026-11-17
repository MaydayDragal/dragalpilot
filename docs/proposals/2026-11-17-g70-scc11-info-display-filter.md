# Proposal: hide "Use switch or pedal to accelerate" by filtering SCC11 (2026-11-17)

**Status (2026-11-17 23:40Z): stages 0 and 1 passed. Branch `sunnypilot/g70-scc11-filter` @ `5aeff4e` holds the car and safety code and the rebuilt firmware. Nothing installed; stage 2 (pass-through drive) is next and needs the user's go-ahead.**

Evidence labels: **source fact** (`466c14c` on the device), **observation** (route `000000c4`), **inference**, **unknown**.

## 1. What raises the message (observations)

- The cluster shows "Use switch or pedal to accelerate" when the camera's SCC11 (`0x420`, bus 2, 50 Hz, 8 bytes) carries `SCCInfoDisplay` = 4. The field is bits 1–3 of byte 0; 0 → 4 flips **byte 0 bit 3**.
- Route `000000c4`: the value is 0 except for five periods of 4 (166.2–173.9, 243.5–253.8, 308.2–343.2, 376.8–397.1, 435.3–462.2 s; 5006 of 73,817 frames). Each starts with the car at standstill and cruise enabled, about 3 s after the standstill bits elsewhere change, and ends when the car moves off. No other value occurs.
- The user bookmarked the message three times just after it appeared: bookmarks at 309.7, 378.6 and 436.5 s, i.e. 1.2–1.8 s after the change to 4.
- Bit scan (`tools/drive-eval/bookmark_bits.py`, segments 4–7): ten bits change before all three bookmarks with five or fewer changes elsewhere. Nine of them flip 3–6 s before the bookmark (standstill indications on `0x394`, `0x410`, `0x47F`, `0x48A`, bus 1 `0x210`, and SCC12 `0x421` byte 1 bit 7). `0x420` byte 0 bit 3 is the only one in the last 2 s.

## 2. What else uses the field (source facts, unknowns)

- `hyundai_can.dbc` (the generator source of `hyundai_can_generated`): `SCCInfoDisplay : 1|3`, receivers **CLU, ESC**. Other SCC11 signals go to CLU, ESC, EMS, TCU and ABS (`AliveCounterACC`, `VSetDis`, `ObjValid`, `ACC_ObjStatus`, `ACC_ObjDist`, `ACC_ObjRelSpd`). SCC11 is part of the stock cruise chain, not a display-only message like LKAS12.
- `carstate.py`: `cruiseState.standstill = SCC11.SCCInfoDisplay == 4` and `nonAdaptive = … == 2`, read from the camera's copy on bus 2. openpilot uses `standstill` to send RES when the lead moves. This is unaffected by the filter, which only changes what reaches bus 0.
- `hyundaican.create_acc_commands`: when openpilot does the longitudinal control on CAN Hyundais it sends SCC11 without `SCCInfoDisplay` (always 0), also when stopped. **Inference:** the car accepts 0 at standstill.
- **Unknown:** whether the ESC acts on `SCCInfoDisplay` = 4 (for example for the standstill hold) in stock longitudinal mode. The DBC lists it as a receiver; nothing in the source or the logs settles it. This is the main open risk and is what stage 3 below tests.

## 3. Design

Same pattern as the `0x484` and LKAS12 changes, G70 2024 only, stock longitudinal only.

**Panda (`safety/modes/hyundai.h`)**

- Add `{0x420, 0, 8, .check_relay = true}` to `HYUNDAI_CAMERA_SCC_TX_MSGS`. The panda then stops forwarding the camera's SCC11 from bus 2 to bus 0, lets openpilot send it on bus 0, and raises relay malfunction if another SCC11 appears on bus 0.
- **Source fact:** the TX hook already handles `0x420` in every Hyundai mode: it copies bit 0 (`MainMode_ACC`) into `acc_main_on_tx` and calls `hyundai_common_acc_main_on_sync()`, which drops `acc_main_on` and exits MADS after three consecutive frames where the camera says main on and our frame says off. A faithful re-send keeps bit 0 equal to the camera's, one frame late at an edge, so at most one or two mismatches. A re-send that stalls does not count mismatches (the hook only runs on TX).
- The RX check for `0x420` on bus 2 (50 Hz) is unchanged.
- Firmware rebuild and flash, as for the two earlier entries. Expected diff: `HYUNDAI_CAMERA_SCC_TX_MSGS` grows from 5 to 6 entries, nothing else.

**opendbc car code**

- `carstate.py`: keep a copy of the camera's `SCC11` values and the timestamp of its last frame (as for LKAS12).
- `hyundaican.py`: `scc11_info_filter(values)` returns the values with `SCCInfoDisplay` 4 → 0 and everything else untouched (2, "Cruise Control", passes through); `create_scc11_passthrough(packer, values)` packs them for bus 0.
- `carcontroller.py`: send **one frame per new camera frame** (when the camera timestamp changes), not on a fixed divider, so `AliveCounterACC` stays in sequence and nothing is repeated or skipped. Stop sending when the camera's frame is older than 0.1 s.
- A file switch like the other G70 settings: `/data/g70_scc11_filter` absent → re-send unchanged; present → apply the filter. The panda blocks the camera's copy either way, so this separates "does the re-send itself work" from "does zeroing the field work".
- SCC11 has no checksum. The DBC signals cover all 64 bits exactly once (1+3+4+8+1+2+3+2+9+11+12+2+2+2+2), so the message can be rebuilt bit for bit; this must be proven on logged payloads (stage 0) because three signals use a 0.1 scale.

## 4. Risks

| Risk | Why | Mitigation |
|---|---|---|
| SCC11 missing on bus 0 while openpilot is stalled, restarting or crashed | the panda blocks the camera's copy as long as the Hyundai safety mode is active; the stock path only returns when the panda drops to no-output and releases the relay | stop-condition on stale camera frames; accept that a `card` crash while driving now also interrupts stock cruise, not only steering. On 11-16 controlsd crashed in this project; `card` did not |
| Added latency and jitter on a 50 Hz control-chain message | re-sent from a 100 Hz Python loop, so up to about 10 ms later and less regular | stage 2 measures the bus-0 timing and looks for cruise faults before any field is changed |
| ESC uses `SCCInfoDisplay` = 4 | listed receiver; unknown function | stage 3: standstill tests in a safe place before any road use |
| MADS / `acc_main_on` desync | TX hook compares our bit 0 with the camera's | faithful re-send; stage 2 checks `acc_main_on` mismatches stay at 0–1 |
| Startup gap | between the safety mode being set and the first re-sent frame | same as LKAS12 today; observe in stage 2 |
| Firmware | a wrong build bricks nothing (bootstub untouched) but can leave the panda refusing to send | reproduce the shipped binary byte for byte from unchanged source before building the change |

The message also has a purpose: it tells the driver the car will stay stopped until they act. With openpilot sending RES when the lead moves that is usually moot, but when RES is not sent (lead gone, long stop) the car will stay put with no prompt.

## 5. Stages

0. **Offline, no car.** Rebuild every logged SCC11 payload from the DBC (routes `ba`–`c4`) and require exact equality; require that the filter changes only byte 0 bit 3 and only when the field is 4.
1. **Firmware.** Set up the build on this PC or the 11-12 PC (Arm GNU Toolchain 13.2.Rel1, flags from the pinned `SConscript`, the re-implemented signer; see the 11-12 findings §3). Reproduce the shipped `panda_h7.bin.signed` exactly from unchanged source, then build with the one new entry and compare symbols.
2. **Pass-through drive** (no file switch): install, check pandad flashes with no signature mismatch, drive with stock cruise. Require: no cluster or SCC warnings, `SCC11` on bus 0 at 50 Hz with an unbroken counter, no `relayMalfunction`, `acc_main_on` behaviour unchanged, stop-and-go and RES working, the cluster message still appearing as before.
3. **Filter on**, parked-lot tests first: stop behind a stationary car with cruise holding; confirm the car holds, no creep, no warnings, RES and pedal both resume; repeat a few times and after a long hold. Then a normal drive.
4. Roll back at any failure: `g70-fingerprint-prev` plus reboot (pandad re-flashes the previous firmware by signature).

## 6. Not validated

No opendbc car or safety tests can be run on the PC used on 2026-11-17 (no Linux environment). The safety-test lists for camera SCC would need the new address, as for `0x53E`.

## 7. Stage 0 result (2026-11-17, offline result)

`tools/drive-eval/scc11_roundtrip.py` on the parked device, routes `c1`–`c4` (100 segments):

- 294,043 camera SCC11 frames, 105,794 distinct payloads. The 15 DBC signals cover 64 of 64 bits without overlap.
- Decode and re-pack: **0 mismatches**.
- `SCCInfoDisplay`: 0 on 288,537 frames, 4 on 5,506; no other value.
- Filter: 344 distinct payloads carry 4; exactly those change, each only in byte 0 bit 3.
- Camera stream as logged: counter step 1 on 293,936 frame pairs and 2 on 8; spacing median 20.0 ms, 1st–99th percentile 10.3–29.8 ms, maximum 44.6 ms.

The car controller keeps only the camera's latest frame per 10 ms cycle, so two camera frames inside one cycle would be re-sent as one (a counter step of 2 on bus 0). The 10.3 ms first percentile says this will be rare; stage 2 has to count it.

## 8. Stage 1 result (2026-11-17, offline result)

Built on the second PC with `tools/panda-fw/build_fw.sh` (Git Bash): sources taken with `git archive` (LF), Arm GNU Toolchain 13.2.Rel1 for Windows (zip sha256 `51d933f0…`, equal to Arm's published value) on a short path, flags from the pinned `sunnyhaibin/panda` `SConscript` @ `8a16e089b885`, DEBUG build, committed `gitversion.h` and `cert.h`, signed with the tree's `board/crypto/sign.py` (`SETLEN=1`, debug key).

- **Reproduction:** `df21ce2` builds to `main.bin` sha256 `471ab450…` and `panda_h7.bin.signed` `f99ab974…`, byte for byte the files shipped in the tree.
- **With the entry (`5aeff4e`):** `main.bin` `351ba34c…`, `panda_h7.bin.signed` `8213b0c4…`, signature starts `1a059f84405a5733`, +16 bytes. The only symbol whose size changed is `HYUNDAI_CAMERA_SCC_TX_MSGS` (80 → 96 bytes, 5 → 6 entries); the sixth entry decodes as `0x420`, bus 0, len 8, relay check, in the same layout as the `0x484` and `0x53E` entries. Bootstub not rebuilt.
