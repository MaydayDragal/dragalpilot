# G70 2024: three more drives, October findings review, and the "take a break" warning (2026-11-13)

**Status:** `g70-fingerprint` @ `4525e88` is on the device (installed 2026-11-13 12:24Z). The Driver Attention Warning fix is **not yet confirmed in the car**.

Follows [2026-11-12-g70-fingerprint-update-drives.md](2026-11-12-g70-fingerprint-update-drives.md). Device identifiers, addresses and GPS are kept out of this repo.

Evidence labels: **source fact**, **observation** (rlog), **hypothesis**.

## 1. Recordings

Extraction as on 11-12 (on the device while offroad, compact per-segment files, analysis on the PC).

| Route | UTC | Length | Settings (initData params) |
|---|---|---|---|
| `000000a7` | 11-12 21:06 | 1585 s | override 4.0 / 0.07, `EnforceTorqueControl=1`, `LateralJerkTorqueController=0`; bookmark at 1111.1 s |
| `000000a8`, `a9` | 11-13 11:19, 11:30 | parked | not analysed |
| `000000aa` | 11-13 11:32 | 447 s | 4.0 / 0.07, Enforce 1, **Jerk 1** |
| `000000ab` | 11-13 11:40 | 639 s | **Enforce 0**, Jerk param still 1, override params still stored; `lateralTorqueParameters.useParams` true, raw 3.76–3.77 / 0.072–0.074 |

Not determined: which controller class runs with `EnforceTorqueControl=0` on this revision, and whether the jerk toggle has any effect then.

All routes: `GENESIS_G70_2024`, no `steerFaultTemporary`/`Permanent` samples. pandaStates `faultStatus = faultTemp` again in `a7`, `aa`, `ab` (not investigated).

## 2. Tracking by configuration (observations)

Hands off, lat active, no blinker, runs ≥ 8 s with 1 s trimmed at each end. Error = desired − actual lateral acceleration. Band values are FFT-band RMS per run, length-weighted.

**> 60 mph**

| Config | Routes | s | RMS error (m/s²) | angle 0.2–0.7 Hz (°) | angle 0.7–4 Hz (°) | lane centre 0.2–0.7 Hz (m) | torque rate RMS (1/s) |
|---|---|---|---|---|---|---|---|
| 5.0 / 0.04, Enforce 1 | a3, a5, a6 | 110–548 | 0.071–0.088 | 0.145–0.209 | 0.048–0.087 | 0.035–0.037 | 0.38–0.40 |
| 5.0 / 0.04, Enforce 1, Jerk 1 | a4 | 128 | 0.085 | 0.237 | 0.086 | 0.045 | 0.46 |
| 4.0 / 0.07, Enforce 1 | a7 | 388 | 0.067 | 0.186 | 0.071 | 0.027 | 0.50 |
| 4.0 / 0.07, Enforce 1, Jerk 1 | aa | 298 | 0.064 | 0.187 | 0.129 | 0.026 | 0.62 |
| Enforce 0 | ab | 278 | 0.058 | 0.178 | 0.092 | 0.029 | 0.60 |

**35–60 mph**

| Config | Route | s | RMS error | angle 0.7–4 Hz (°) | torque rate RMS (1/s) |
|---|---|---|---|---|---|
| 5.0 / 0.04, Enforce 1 | a3, a5, a6 | 29–94 | 0.107–0.168 | 0.22–0.42 | 0.43–0.55 |
| 4.0 / 0.07, Enforce 1 | a7 | 209 | 0.092 | 0.38 | **0.88** |
| 4.0 / 0.07, Enforce 1, Jerk 1 | aa | 36 | 0.095 | 0.36 | 0.68 |
| Enforce 0 | ab | 110 | 0.062 | 0.13 | 0.53 |

**Curve events** (peak \|desired\| ≥ 1.0 m/s², > 35 mph, hands off; medians per route):

| Config | Route | n | shortfall / peak | overshoot (m/s²) |
|---|---|---|---|---|
| 5.0 / 0.04 | a3, a5, a6 | 3–5 | 0.16–0.21 | 0.31–0.34 |
| 5.0 / 0.04 + Jerk | a4 | 1 | 0.30 | 0.30 |
| 4.0 / 0.07 | a7 | 6 | 0.15 | 0.27 |
| 4.0 / 0.07 + Jerk | aa | 5 | 0.16 | 0.23 |
| Enforce 0 | ab | 7 | 0.14 | 0.18 |

Reading:
- 4.0 / 0.07 tracks slightly better than 5.0 / 0.04 (less overshoot, less lane motion in the weave band) at the cost of a faster-moving torque command at 35–60 mph.
- The jerk controller tracks about the same and moves the wheel more in the fast band above 60 mph.
- Enforce 0 was best on error and overshoot.
- **Limits:** different roads, times and traffic; the 11-13 routes are short; none passes the turn bookmarked on 11-12 (GPS match within 40 m, same heading: only `a5`). These are leads, not an A/B.

Other events in `a7`:
- `espDisabled` at 6.8 s and 156.5–157.1 s → "TAKE CONTROL IMMEDIATELY / Electronic Stability Control Disabled" at about 50 mph. `a6` also had `espDisabled` at 117 s. Cause not established (user input or car).
- Full torque (−1.00) at 1424 s, 21 mph, wheel −57°: 2.0 of 2.6 m/s² delivered, no `steerSaturated` event.

## 3. October findings, read against the current setup

Digests of all 27 October documents were made by three parallel readers on 2026-11-12; the points below are the ones that bear on the current state.

- **Controller differs.** Every October measurement ran `LatControlTorqueV0` with `EnforceTorqueControl` absent and no override ([drives-tune](2026-10-04-g70-drives-tune.md)). The 11-12/11-13 drives with Enforce 1 and the override are not comparable with October baselines.
- **Tune.** 4.0 / 0.07 gave curve actual/desired 1.007 on V0 ([tune-0x484-first-drive](2026-10-04-g70-tune-0x484-first-drive.md)). torqued, when valid, learned 3.5–3.7 / 0.081–0.085. No October measurement supports 5.0. The weave simulation found plant gain 1.21–1.29× what 4.0 assumes at 35+ mph ([weave-sim](2026-10-04-g70-weave-sim.md)), and modelled a ×1.1–1.29 factor as reducing jumps, so 5.0 may trade turn-in for a calmer wheel (hypothesis).
- **Audio gate removed.** Without it, soundd/micd crashed on 5 of 21 cold starts ([device-errors](2026-10-05-g70-device-errors.md)). The user reports no crash on the new base so far; the logs have not been checked for it.
- **Quick re-enable.** Re-enabling sunnypilot about 2 s after disabling gave a MOCK fingerprint and dropped learned state; wait about 10 s.
- **`0x484`.** Unproven against a real hands-off escalation; the first one with the change active coincided with a reported "grasp not detected". The proposed test (deselect Highway Driving Assist in the car) was never run.
- **Weave / twitch.** 0.2–0.4 Hz weave about 1.9× the stock LKA; every offline tuning fix was rejected; D2C4 worsened the weave on the car. No twitch measure was validated.
- **Lane position.** Static left bias 0.15–0.19 m and a shift toward the inside of curves, attributed to the model's path. In `a7` before the bookmark the car sat 0.28 m (mean) off the lane centre through a 70 mph curve.
- **`maxLateralAccel` 2.7** is the upstream port value, never measured on this car.
- Not in any October document: `faultTemp` panda status.

## 4. "Take a break": Driver Attention Warning in LKAS12

**User report:** the `a7` bookmark (1111.1 s) marks the cluster message telling the driver to take a break. The car has no menu option to turn it off.

**Observation (`a7`, bus 2, `0x53E`):**

| t (s) | payload | `CF_LkasDawStatus` (byte 5 & 7) |
|---|---|---|
| start | `0100000008051400` | 5 |
| 396.0 | `03002d2d08043700` | 4 |
| 546.3 | `01002d2d08053700` | 5 |
| 915.3 → 1090.7 | … | 4 → 3 → 2 → 1 |
| **1107.2** | **`0300414108164b00`** | **6, with bit 44 set** |
| **1111.2** | `0300414108014b00` | 1 |
| 1321.3 → 1581.1 | … | 2 → 3 → 4 |

- The status went to 6 exactly 4.0 s before the bookmark and back at the bookmark.
- Bit scan of segments 17–18 (all buses, bits with ≤ 6 transitions): on buses 0 and 2 the only bits that turn on and off in that window are `0x53E` byte 5 bits 0, 1, 2, 4 and the camera's own `0x340` byte 1 bit 7 (already blocked by the panda).
- Over six routes (50,208 frames on bus 2): 10 Hz (mean gap 100.0 ms), 8 bytes, 51 distinct payloads, no counter or checksum. Byte 5 takes `01`–`05` and `16`; `16` occurs in 40 frames only (this event).
- The panda forwards the camera's frame to bus 0 (seen as `src 128`). sunnypilot only reads `CF_Lkas_TsrSpeed_Display_Clu` from it (`carstate_ext.py`).
- **Source fact:** `hyundai_can.dbc` defines LKAS12 as 6 bytes with `CF_LkasDawStatus` at bit 40; the CAN-FD DBC documents the equivalent signal ("Rest Recommend Warning").

One event. The meaning of levels 1–5 and of bit 44 is inferred from this sequence.

## 5. Fix: `4525e88` on `sunnypilot/g70-fingerprint`

- `safety/modes/hyundai.h`: `{0x53E, 0, 8, .check_relay = true}` in `HYUNDAI_CAMERA_SCC_TX_MSGS`. The panda stops forwarding the camera's copy to bus 0 and openpilot may send it; a `0x53E` seen on bus 0 from elsewhere sets relay malfunction. Applies to every non-long camera-SCC Hyundai in this safety mode; **only the G70 2024 re-sends the message, so this build is for that car only.**
- `hyundai_can.dbc`: LKAS12 → 8 bytes, with filler signals (`CF_Lkas12_Raw0/1/2/3/6/7`, `CF_Lkas12_DawWarning` at 43\|5) so the message can be rebuilt exactly.
- `carstate.py`: copies the camera's LKAS12 and its timestamp (G70 2024).
- `hyundaican.py` / `carcontroller.py`: `lkas12_daw_filter` replaces status 6 or non-zero warning bits with the last normal level; LKAS12 is sent on bus 0 at 10 Hz when not openpilot-longitudinal and the camera's frame is younger than 0.5 s.
- Safety tests: camera-SCC TX / relay / forwarding lists include `0x53E` (not run).
- Firmware: same build as 11-12 (the previous build still equals the committed file). Only `HYUNDAI_CAMERA_SCC_TX_MSGS` changed size (4 → 5 entries); the new entry decodes as `0x53E`, bus 0, len 8, relay check. sha256 `f99ab974…`, signature `64fe5bf2ce4bba2d`.

**Offline check (independent decoder, no repo code run):** the 14 LKAS12 signals cover all 64 bits once; all 51 logged payloads round-trip exactly; over 279 logged payload changes the filter alters only `0300414108164b00` → `0300414108014b00`.

**Not validated:** opendbc car and safety tests; the cluster's reaction to the re-sent message; whether the warning has another path; behaviour of the speed-limit sign display.

**Behaviour to expect:** active only while sunnypilot runs (in `noOutput`/offroad the relay passes the camera through). The warning fired once in 84 min, after about 12 min of draining, so confirmation needs a long drive.

## 6. Device record (2026-11-13)

- 11:57Z, read-only: offroad, `c4776c4`, clean.
- 12:24Z: bundle of `c4776c4..4525e88` (sha256 `cbbf5978…`, verified on the device); guards passed; rollback branch `g70-fingerprint-prev` → `c4776c4`; fast-forward to `4525e88`; guarded reboot.
- After the restart (uptime 637 s): `4525e88`, clean, offroad, `DisableUpdates=1`, no offroad alerts, pandad log "Done flashing" with no mismatch and `./pandad` running since boot. The signature line for this boot was not captured.
- Settings left by the user: override 4.0 / 0.07, `EnforceTorqueControl=0`, `LateralJerkTorqueController=1`.

## 7. Open

- Confirm the DAW fix on a long drive; check the speed-limit sign and for new cluster warnings.
- `espDisabled` events; `faultTemp` panda status.
- Controller in use with Enforce 0; a same-road comparison of the three configurations.
- opendbc tests on `be9fe0d`..`4525e88`.
- Grasp warning: not checked in any November drive.
