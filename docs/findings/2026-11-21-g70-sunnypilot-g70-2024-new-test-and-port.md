# G70 2024: sunnypilot's `g70-2024-new` branch tested, two of its message changes ported

Covers 2026-11-21 from about 09:00 to 18:30 local time (US Eastern). Drive `00000003` (16:35, 20 segments) on sunnypilot `g70-2024-new` @ `ffb5a06`. Continues [2026-11-21-g70-close-stop-creep-soft-stop-ramp.md](2026-11-21-g70-close-stop-creep-soft-stop-ramp.md). Device identifiers and GPS are kept out of this repo.

Statements are marked as observations (measured from logs, code or tests), inferences, or plans.

## 1. Summary

- sunnypilot published a branch for this car and asked for a test of three things: the grasp warning with stock longitudinal, cluster faults with Alpha Longitudinal, and steering above 40 mph.
- **Observation:** on one 20-minute drive, no fault and no grasp or attention warning. Steering was far worse than ours: about 190 torque reversals a minute above 70 mph against under 10.
- **Observation:** the same set-speed error (cluster 1.45 mph above the set speed) and the same creep at a stop (to 0.7 m behind a car, driver braked) that this repo fixed on its own branch.
- **Ported to our branch (`2a81f61`):** its way of stopping the grasp warning at the camera (MDPS12 re-sent to the camera) and a counter and checksum on SCC14. Both behind option files, both off. Panda firmware rebuilt; safety tests 9232 OK.
- **State:** our branch is back on the comma at `2a81f61` with the option files and settings restored. Not driven.

## 2. The branch against ours (observations, from the code)

| | Our branch | `g70-2024-new` |
|---|---|---|
| Firmware fingerprint (camera, radar, steering unit) | three strings | the same three strings |
| Lateral acceleration factor / friction / max | 4.0 in code (4.5, then 4.2 by override) / 0.07 / 2.7 | 3.45 / 0.09 / 2.7 |
| Steering ratio | 14.1 | 15.0 |
| Steering actuator delay | not set per car; published delay fixed at 0.33 s | 0.24 s |
| Extra steering term | none | feed-forward on the rate of the requested curvature: 0 at 20 m/s to 26 CAN counts per deg/s at 33 m/s, 0.06 s filter, capped at 60 counts |
| Grasp warning | camera's HDA11_MFC (`0x484`) blocked | steering unit's MDPS12 (`0x251`) blocked towards the camera and re-sent as "steering assist unavailable" |
| SCC14 with openpilot longitudinal | no counter or checksum | rolling counter and checksum for this car |
| Take-a-break, standstill prompt, lead-departure filters; four gaps; cluster set speed; main-button engage; stop and restart handling | present | absent |

- Its factor and friction are close to what the car's own estimator settled at in our logs (3.42–3.55, 0.077–0.085).
- The steering ratio is above anything measured (section 5).

## 3. The drive on `g70-2024-new` (observations)

### Steering (`sway.py`, hands off)

| Above 60 mph | Ours, same road | `g70-2024-new` |
|---|---|---|
| Fast wobble per minute | 2.3–7.7 | 92–101 |
| Wheel reversals per minute | 22–46 | 116 |
| Wheel movement 0.2–4 Hz | 0.18–0.25° | 0.52° |
| Ping-pong per minute | 2.0–2.6 | 2.5–3.3 |

| Speed band | Torque-command reversals per minute (≥ 0.05, 1–6 Hz): ours `e1` | `g70-2024-new` |
|---|---|---|
| 20–45 mph | 14 | 134 (0.7 min) |
| 45–60 mph | 2 | 156 |
| above 70 mph | 1 | 192, peak near 1.4 Hz |

- The lateral controller's own output oscillates at every speed, including below 45 mph where the feed-forward is zero. Above 70 mph the car controller adds about ±26 counts rms on top (ours: 6–9 from rate limiting).
- **Inference:** the factor of 3.45 asks about 30 % more torque per request than the 4.5 we ran, with the stock friction ramp and no request smoothing; on our branch a wider friction ramp and smoothing removed this kind of wobble. Not tested on that branch.
- Events: one `steerSaturated` (on-ramp), no faults. Driver: no unexpected messages.

### Speed control

- **Set speed:** holding 78 for 204 s, cluster 78.0 mph, set speed 76.6 mph (+1.45 mph). Ours with the cluster correction: +0.33.
- **Stop:** 2:48 into the drive the car held 1.6–2.0 mph for about 2 s against a request of −0.31 m/s², the gap went from 2.3 m to 0.7 m, no stop was requested, and the driver braked. The creep described in the morning findings.
- **Following:** median time gap 1.68 s above 34 mph. Acceleration-command swings of 0.1 m/s² or more: 12 per minute (ours at 0.69 s: 14). One request at −3.5 m/s² for under a second.

### The camera's messages

| | Ours (`e1`) | `g70-2024-new` |
|---|---|---|
| Camera LKAS12, low three bits of byte 0 | 1 on 20 % of frames, 3 on 80 % | 1 on every frame |
| Camera SCC11 standstill prompt bit | 2,642 frames | 0 (no cruise-held stop) |

- **Inference:** with the steering unit reported as unavailable, the camera's attention state did not move off its lowest level. One drive; the field position is taken from earlier notes.

## 4. What was ported (`87ae226`, `cf0e989`, `2a81f61`)

### MDPS12 to the camera

- **Panda:** `{0x251, bus 2}` in both camera-SCC TX lists. That also stops the car's MDPS12 from being forwarded to the camera, so openpilot has to send it in every case.
- **Car code:** each new MDPS12 frame is sent to the camera once with a new counter and checksum, and not at all once the steering unit's frame is older than 0.1 s. Unchanged, unless `/data/g70_cam_mdps12` exists: then `CF_Mdps_ToiActive` 0, `CF_Mdps_ToiUnavail` 1.
- The existing `0x484` block stays; the two stack.
- **Found while checking:** the steering unit always sets bits 32–34, which no upstream signal covers; `g70-2024-new` sends them as 0. A new signal `CF_Mdps_Rsv32` carries them, so the unchanged re-send is exact, and the "unavailable" mode zeroes them to match what was driven.

### SCC14

- `AliveCounter` (48|4) and `Checksum` (52|4) added to the message definition; filled for this car with openpilot longitudinal when `/data/g70_long_scc14_counter` exists.

### Checks

| Check | Result |
|---|---|
| CRC8 (J1850, as `hyundai_checksum`) over the frame without byte 3, against the steering unit's own frames (`mdps12_check.py`) | 72,179 of 72,179; counter +1 on 99.99 % |
| Unchanged re-send through the real `CANPacker`, against the car's frames | identical on 72,179 of 72,179 |
| "Unavailable" output against what `g70-2024-new` sent | identical on 31,376 of 35,010; the rest differ only in torque fields from a neighbouring frame |
| `opendbc.safety.tests.test_hyundai` on the comma | 1,906 OK after adding `0x251` to the shared-message exception in `tests/common.py` (3 bookkeeping failures before) |
| Full safety suite on the comma | 9,232 OK |
| Firmware | `build_fw.sh` reproduces the previous firmware byte for byte from `ac2bdcb`; new sha256 `cb6201ae…`, signature `9209954232d5bbba`, +32 bytes |

### Not ported

- The torque numbers, the steering ratio of 15.0 and the damping feed-forward.

## 5. Steering ratio (observations)

The G70 has a variable-ratio rack. Estimated from this car's logs as steering angle against GPS heading rate at steady cornering, corrected for speed (27,595 samples; spread about ±2 within a row).

| Wheel angle | Typical speed | Ratio |
|---|---|---|
| near centre, highway (the live estimator) | 60–75 mph | 13.75–14.4 |
| 25–90° | 18–25 mph | 12.9–13.1 |
| 90–150° | 15 mph | 12.6 |
| 150–250° | 10 mph | 11.4 |
| 250–400° | 8 mph | 10.9 (96 samples) |

- openpilot assumes one ratio. **Inference, not tested:** in tight low-speed turns the car steers about 20 % more per degree than the model expects, which may be part of why low-speed steering is harder to settle.
- `carState.yawRate` is not populated on this car; the GPS heading was used.

## 6. Device record (local time)

| When | Change |
|---|---|
| 2026-11-21 about 11:45 | driver: fresh install of sunnypilot `g70-2024-new` @ `ffb5a06` (built on the device). A full reset: drive logs, `/data/g70_*` files, settings and the SSH host key gone |
| 2026-11-21 about 18:10 | our branch `2a81f61` cloned from this repo's `sunnypilot/g70-scc11-filter`, swapped in, reboot; panda flashed ("Done flashing", expected signature `9209954232d5bbba`) |
| same | option files written back as of the morning; settings written back: torque override on (4.2 / 0.07), `TorqueControlTune` 1.0, `CustomTorqueParams`, `EnforceTorqueControl`, `LateralJerkTorqueController`, `TorqueBar`, `AlphaLongitudinalEnabled`, `DisableUpdates` |

Current: `g70-fingerprint` @ `2a81f61`, rollback branch `g70-fingerprint-prev` = `ac2bdcb`; `/data/g70_cam_mdps12` and `/data/g70_long_scc14_counter` absent. The other install is kept at `/data/openpilot_g70new`.

### What went wrong on the way

- An attempt to build `g70-2024-new` in a side folder over SSH ran out of memory at six parallel jobs (one compile killed); cancelled at the driver's request and cleaned up. The comma's own first-boot build completed.
- Twice a cleanup command killed itself: `pkill -f <pattern>` matches the SSH shell whose command line contains the pattern. Run such cleanups from a script file.
- After the reset the comma's SSH host key changed. It was confirmed by reading the key over the USB debug link before connecting, and kept in a separate known-hosts file.

## 7. Open

- First drive on `2a81f61` with both options off: the camera with openpilot relaying MDPS12. Then `/data/g70_cam_mdps12`.
- Whether "unavailable" changes anything else the camera shows (lane or highway-assist icons).
- Still not driven from the morning: the soft stop ramp, the 0.85 s gap on one bar, the early restart release, the low-speed look-ahead; factor 4.2 road for road.
