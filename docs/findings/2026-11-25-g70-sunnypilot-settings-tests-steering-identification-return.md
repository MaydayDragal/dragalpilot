# G70 2024: settings-only tuning on sunnypilot's branch, the steering identified from logs, and the return to our branch

Covers 2026-11-24 about 06:20 to 2026-11-25 about 07:20 local time (US Eastern). Drives on sunnypilot `g70-2024-new` @ `f239548`: `00000010` (2026-11-24 06:22), `00000011` (14:13), `00000012` (16:32), `00000013` to `00000016` (evening, about 18:35 to 19:55), `00000017` (2026-11-25 06:16). Continues [2026-11-23-g70-sunnypilot-fourth-tune-drive-daw.md](2026-11-23-g70-sunnypilot-fourth-tune-drive-daw.md). Device identifiers and GPS are kept out of this repo.

Statements are marked as observations (measured from logs or code), inferences, or plans.

## 1. Summary

- **Observation:** on sunnypilot's branch, with settings only, the best setup found was the v1 controller, factor 2.5, friction 0.055, a fixed 0.33 s delay. Factors 2.3, 2.7 and 3.1 all swayed more. It stays behind our branch on the same road.
- **Observation:** that branch's live torque learner reached 100 % and began moving the values from 2.7 / 0.055 toward about 3.1 / 0.09. It was turned off after about 98 s of engaged driving under learned values.
- **Observation:** the steering identified from logs has a delay of 0.18–0.28 s, friction of 5–7 torque counts on highway straights, and a stiffness that is about half as large near the centre as in turns.
- **Observation:** on the highway our branch's controller follows its request about six times more closely than that branch's best setup (error 0.011–0.012 m/s² rms against 0.068–0.073).
- **Not achieved:** a tune that is stable by calculation. A loop model built from the identified steering did not reproduce the measured response.
- **Built, not installed:** a G70-only torque curve and a steering-wheel movement bar, both behind option files, on our branch (`74ef2dc`).
- **Device:** back on our branch `1064526` with its best highway settings; `/data/g70_cam_mdps12` on for the first time. Not driven in this state.
- **Withdrawn in this document:** three readings made during the session (section 8).

## 2. Drives on `g70-2024-new` (observations, `sway.py`, hands off)

### Setups

| Drive | Controller | Factor / friction | Delay | Route, light |
|---|---|---|---|---|
| `00000010` | v0 | 2.7 / 0.055 | live, about 0.21 s | morning route, dawn |
| `00000012` | v0, learner off | 2.7 / 0.055 | live | afternoon route, dusk |
| `00000013` | v1 | 2.7 / 0.055 | live | morning route, dark |
| `00000014` | v1 | 2.5 / 0.055 (override) | live | afternoon route, dark |
| `00000015` | v1 | 2.5 / 0.055 | fixed 0.33 s | morning route, dark |
| `00000016` | v1 | 3.1 / 0.055 | fixed 0.33 s | afternoon route, dark |
| `00000017` | v1 | 2.3 / 0.055 | fixed 0.33 s | morning route, dawn |

`00000011` was almost all hands-on with steering off and was not used.

### Above 60 mph, straights

| | min | Ping-pong per min | Swings of 15 cm or more per min | 90th-percentile swing (cm) | % of time in a train | Wobble per min | Largest loop amplification |
|---|---|---|---|---|---|---|---|
| ours `d4` | 4.2 | 3.5 | 0.47 | 10.5 | 0 | 2.0 | 1.54 |
| ours `e1` | 5.4 | 2.4 | 0.37 | 9.5 | 0 | 2.7 | 1.76 |
| `0000000d` (2.5, v0, earlier) | 6.9 | 2.2 | 0.72 | 15.0 | 0 | 7.9 | 1.96 |
| `00000010` | 6.7 | 3.6 | 0.60 | 11.6 | 0 | 6.9 | 2.96 |
| `00000012` | 5.2 | 5.0 | 1.14 | 13.8 | 0 | 4.2 | 1.96 |
| `00000013` | 7.6 | 5.2 | 1.05 | 13.8 | 1.4 | 2.5 | 4.23 |
| `00000014` | 7.0 | 3.8 | 1.28 | 18.5 | 1.7 | 3.3 | 3.10 |
| `00000015` | 7.5 | 3.9 | 0.80 | 12.7 | 0 | 4.0 | 3.73 |
| `00000016` | 7.3 | 5.7 | 2.59 | 20.9 | 2.7 | 2.5 | 2.25 |
| `00000017` | 7.2 | 6.1 | 1.11 | 14.7 | 1.8 | 5.8 | 3.34 |

### Same road, above 35 mph (other / newer drive)

| Pair | Shared min | Ping-pong per min | % in a train | Lane 0.2–0.7 Hz (cm) | Wobble per min |
|---|---|---|---|---|---|
| `0000000d` (2.5, v0) / `00000010` (2.7, v0) | 10.6 | 3.1 / 5.0 | 0 / 3.9 | 3.19 / 3.34 | 8.5 / 6.9 |
| ours `d4` / `00000012` | 9.9 | 2.1 / 5.1 | 0 / 0 | 2.05 / 2.79 | 1.2 / 2.7 |
| ours `e1` / `00000012` | 10.1 | 2.4 / 5.1 | 0 / 0 | 2.18 / 2.84 | 1.5 / 2.9 |
| `00000010` (v0) / `00000013` (v1) | 9.6 | 4.2 / 5.3 | 0 / 1.3 | 3.27 / 3.27 | 6.8 / 2.3 |
| ours `d4` / `00000014` | 9.6 | 3.4 / 4.3 | 0 / 0 | 2.20 / 3.23 | 1.9 / 4.3 |
| ours `e1` / `00000014` | 10.1 | 3.1 / 4.2 | 0 / 2.1 | 2.45 / 3.21 | 1.8 / 4.6 |
| `00000013` (2.7) / `00000015` (2.5, delay 0.33) | 9.8 | 5.2 / 3.6 | 2.6 / 0 | 2.85 / 3.45 | 2.5 / 3.7 |
| `00000014` (2.5) / `00000016` (3.1) | 10.4 | 4.3 / 4.7 | 0 / 2.7 | 3.37 / 3.43 | 3.7 / 3.5 |
| `00000015` (2.5) / `00000017` (2.3) | 9.7 | 3.9 / 4.8 | 0 / 2.0 | 3.40 / 3.75 | 4.4 / 6.1 |

- **v1** cut the fast wobble to about a third and did not reduce the slow sway.
- **The fixed 0.33 s delay** (that branch's live-delay switch off, software delay 0.09 s on its 0.24 s) made the swings smaller and removed the trains; lane movement on the same road went up. The actual curvature trailed the request by 0.12 s against 0.23 s before.
- **Factor:** 2.5 is the best of 2.3, 2.5, 2.7 and 3.1 on v1. At 3.1 the car answered requests with 0.84–1.21 times the requested lateral acceleration (1.0–1.45 at 2.5) and swayed more: over-answering was not the main cause.
- **20–45 mph:** almost no data on v1. `00000017` had 1.1 min on straights: ping-pong 14.2 per minute, 10.5 % of the time in a train (ours 4.3–5.0, none). The driver reports long slow oscillations at low speed on 2.7 / v0.
- **Events:** `steerSaturated` once on `00000014` (on-ramp, 24–36 mph, wheel to 44°, torque at the 270-count limit). Bookmarks: `00000012` at 21:24 (15–32 mph: lane swings of 15 cm or more with periods of 5–20 s, 6.5 per minute; largest −23 to +25 cm), `00000016` at 9:17 (77 mph: +17 to −23 to +19 cm in 30 s), `00000017` at 16:50 (the take-a-break warning, section 6).
- **Darkness** is a confound on `00000013` to `00000016`.

## 3. That branch's settings (observations from its code)

- **Torque learner:** `LiveTorqueParamsToggle` is honoured only when `EnforceTorqueControl` is on (`torqued_ext.py`). With both at their defaults the learner is used. On `00000010` it reached 100 % at segment 15 and the applied values moved 2.70 / 0.055 → 2.83 / 0.063 during the last 98 s of engaged driving (raw estimate 3.1–3.3 / 0.078–0.091 all drive). Turned off with `EnforceTorqueControl` 1 and `LiveTorqueParamsToggle` 0; the stored `LiveTorqueParameters` was removed (a copy is kept on the comma). With Enforce on, the car's table values are reloaded (2.7 / 0.055) and `TorqueControlTune` selects the controller.
- **Controller:** `TorqueControlTune` 0.0 = `LatControlTorqueV0`, 1.0 = the upstream controller (`torqueState.version` 1 in the log). v1 already feeds the request's rate into the friction term; the Lateral Jerk setting adds nothing to it.
- **Values without editing the branch:** `TorqueParamsOverrideEnabled` with `TorqueParamsOverrideLatAccelFactor` and `TorqueParamsOverrideFriction`, read by both controllers every 300 frames when Enforce is on.
- **Delay:** `LagdToggle` off makes modeld and controlsd use `steerActuatorDelay` + `LagdToggleDelay` (written to `LagdValueCache` by lagd).
- **Since our port** (`ffb5a06`) that branch's opendbc changed: the damping feed-forward removed, the torque numbers, three EV signals in the DBC, and a reset of the panda's heartbeat-mismatch counters on engage. No new message blocking.

## 4. The steering identified from logs (observations)

### Steady cornering (about 48,000 samples above 30 mph, wheel not moving, road tilt removed as the controller does)

| Lateral acceleration (m/s²) | −0.75 | −0.45 | −0.25 | −0.05 | +0.15 | +0.25 | +0.35 | +0.55 | +0.75 |
|---|---|---|---|---|---|---|---|---|---|
| Torque (counts) | −55 | −25 | −7 | 0 | 14 | 14 | 18 | 48 | 63 |

- Two-slope fit: slope near the centre 0.45 of the slope beyond 0.25 m/s²; outer slope 94 counts per m/s² (factor 2.87 at a 270 limit, 4.09 at 384); rms error 3.0 counts against 5.0 for a straight line.
- **By speed** (beyond 0.4 m/s², 10 mph bins): 94, 88, 93, 83, 92 counts per m/s² from 35–45 to 75–85 mph, no trend. 15–25 mph: 179 on 203 samples with a poor fit. A factor that changes with speed fits no better than one factor (r² 0.740 both).

### With the wheel moving (torque = stiffness × lateral acceleration + damping × its rate + friction × direction, best delay)

| | Delay (s) | Stiffness (counts per m/s²) | Damping (counts per m/s³) | Friction (counts) |
|---|---|---|---|---|
| Straights, 45 mph and up (both branches) | 0.18–0.26 | 44–52 | 14–27 | 5.4–7.4 |
| Turns, 60 mph and up | 0.22–0.28 | 75–80 | 28–40 | 6.7–10.2 |
| Turns, 45–60 mph (ours) | 0.28 | 88 | 15 | 20.7 |

- On highway straights the request varies by 0.046 m/s² rms about its 5 s mean and the torque by 9.3 counts, against friction of 5–7 counts. **Inference:** the car steers inside its friction band much of the time; friction of that size left unserved for half a 3–4 s swing is 10–14 cm, the size of the measured swings.
- **Inference, open:** whether the flat centre in the steady data is a softer response or the friction band seen at rest. The two measurements above both give about half the stiffness near the centre; a wheel held by stiction would look the same.

### What was tried on it

- **A linear loop model** (identified plant, the v1 control law): predicts a gain of 1.2–1.4 and a lag of 30–50° at 0.2–0.45 Hz where `sway.py` measures 0.84–0.90 and 81–92° on our branch. It does not validate and was not used to choose settings.
- **Friction pushed in the direction of travel** (a play operator on the request): the request reverses by 0.02 m/s² or more 84–90 times a minute on our branch and 223 on that branch; with a 0.05 threshold the push would flip 50–52 times a minute. Not built.
- **A damping feed-forward:** on our branch the feedback's output follows the request's rate with only 3–4 counts per m/s³. The 0.20 s controller delay against the undelayed feed-forward already acts as one.

### How closely the controller follows its request (highway, hands off)

| | ours `d4`, `e1` | `00000014`, `00000015` (2.5, v1) |
|---|---|---|
| Error rms, all highway (m/s²) | 0.011–0.012 | 0.068–0.073 |
| Error rms entering and leaving turns | 0.017–0.019 | 0.083–0.085 |
| 95th percentile in turn entry and exit | 0.03–0.04 | 0.17 |
| Feedback output rms (counts) | 1.6–2.2 | 7.6–10.2 |

- On our branch 6–44 % of the lane-offset movement above 60 mph is explained by the car's own movement; the rest is the lane lines moving (road shape and perception).

### Sway by speed (straights, hands off, slow swings of 8 cm or more per minute)

| mph | 20–30 | 30–40 | 40–50 | 50–60 | 60–65 | 65–70 | 70–75 | 75–80 |
|---|---|---|---|---|---|---|---|---|
| ours (`d4`, `e1`, `df`, `e0`) | 11.0 | 5.7 | 3.1 | 2.7 | 5.0 | 3.2 | 2.1 | 2.7 |
| that branch, v0 | 13.2 | 11.9 | 9.8 | 3.6 | 3.2 | 8.1 | 4.1 | 3.2 |
| that branch, v1 | | | | | 4.4 | 4.5 | 3.9 | 5.0 |

## 5. Other cars with a non-linear torque curve (observations from the code)

- `opendbc/car/gm/interface.py`: Chevrolet Bolt EUV, GMC Acadia, Chevrolet Silverado (upstream) and two Bolt variants without ACC (sunnypilot), each with four numbers for a sigmoid-plus-linear curve of torque against lateral acceleration, looked up in both directions. It takes no speed input. Those curves are steep at the centre and flatten; the G70's measured shape is the other way round.
- The neural-network controller is the other non-linear route (114 models, none for this car).

## 6. The take-a-break warning again (observation)

- `00000017`, bookmark at 16:50 into the route: camera LKAS12 status 6 with the warning bit for 40 frames (3.9 s), from 2.7 s before the bookmark to 1.2 s after; all 1,799 camera frames in those three segments appear on the car's bus. That branch forwards it.
- Our branch blocks the camera's LKAS12 in the panda and re-sends it with the warning replaced by the last normal level (in place since 2026-11-13).

## 7. Built on our branch, not installed (`g70-scc11-filter` @ `74ef2dc`)

- **Torque curve** (`opendbc/car/hyundai/g70_torque_curve.py`, hooked in `interface.py` for `GENESIS_G70_2024` only): the request is remapped (slope `centre_gain` inside `knee`, 1 outside, blended) and then divided by the factor. On only while `/data/g70_lat_torque_curve` exists (`centre_gain knee [width]`, fitted 0.45 0.25). Checked on the PC: identical to the line at gain 1.0, increasing, odd, inverts to 0.001 m/s²; through the real `CarInterface` class off without the file and off for other cars. On `00000015` the request is inside the knee 71 % of the engaged time. **Not driven. Inference:** inside the knee it cuts everything the controller asks for, the friction push included; factor 3.1 on that branch wandered.
- **Steering-wheel movement bar** (`selfdrive/ui/mici/onroad/torque_bar.py`): with `/data/g70_ui_steer_bar` (`span [seconds]`, default 2° and 8 s) the bar shows the wheel angle about its own recent average and stays thin and white. Wheel movement from its 8 s average on straights above 60 mph: median 0.12–0.28°, 90th percentile 1.1–1.5°. It ran on the comma as a local edit to `g70-2024-new` for one drive (`00000013`) and was removed.

## 8. Withdrawn during the session

- "Low speed hunting is mostly gone" on the 2.7 tune (from wheel swings and torque reversals on `0000000f`). The driver reports long slow oscillations; on straights that drive spent 11 % of the time in a train at 20–45 mph.
- "The car needs about 38 % more torque at low speed" (from 15–30 mph against the highway in wide bands). In 10 mph bins the need is flat from 35 mph up; only 15–25 mph is higher, on thin data.
- The bookmark on `00000017` was first described as a steering bookmark. It was the take-a-break warning.
- The prediction that factor 3.1 would reduce the sway (the car over-answering requests) was wrong: it swayed more.

## 9. Device record (local time)

| When | Change |
|---|---|
| 2026-11-24 about 14:07 | on `g70-2024-new`: `EnforceTorqueControl` 1, `LiveTorqueParamsToggle` 0, `LiveTorqueParameters` removed (copy kept in `/data`), reboot |
| about 18:15 | `TorqueControlTune` 1.0 |
| about 18:29 | local edit of `torque_bar.py`, `/data/g70_ui_steer_bar` = `2`, reboot |
| about 18:55 | that file restored from git, option file removed; `TorqueParamsOverrideEnabled` 1 with 2.5 / 0.055; reboot |
| about 19:15 | `LagdToggle` 0, `LagdToggleDelay` 0.09 (delay 0.33 s) |
| about 19:40 | factor override 3.1 |
| about 20:05 | factor override 2.3 |
| 2026-11-25 about 07:17 | `/data/openpilot` moved to `/data/openpilot_g70new`, `/data/openpilot_ours` to `/data/openpilot`; `TorqueControlTune` 1.0, `CustomTorqueParams`, `EnforceTorqueControl`, `LateralJerkTorqueController`, `TorqueBar`, `TorqueParamsOverrideEnabled` on with 4.5 / 0.07, `LagdToggle` 1, `LagdToggleDelay` 0.2; `/data/g70_cam_mdps12` created; reboot |
| 2026-11-25 about 07:40 | `/data/g70_long_scc14_counter` created, reboot |

Current: **our branch `g70-fingerprint` @ `1064526`**, no local edits; the panda reports no faults after the reboot (its firmware signature was not read). Option files as before the excursion plus `/data/g70_cam_mdps12` and `/data/g70_long_scc14_counter`, both on for the first time on our branch, and `/data/g70_lat_smooth` = `0.2 20 25 0.3` (section 9b). sunnypilot's install is kept at `/data/openpilot_g70new` (@ `f239548`, unmodified).

- A log pull was held while the comma was still onroad (load average 9 against about 1.5 parked) and done after the ignition was off.

## 9a. Checksums and counters of what our branch sends (observations, drive `00000006`, four segments)

| Message | Checksum | Counter |
|---|---|---|
| MDPS12 to the camera | CRC8 valid on 23,511 of 23,511 (the steering unit's own: 23,999 of 23,999) | one step per frame since `1064526` |
| LKAS11 | CRC8 valid on 24,000 of 24,000 | |
| SCC12 | nibble checksum valid on 12,000 of 12,000 | |
| FCA11 | CRC8 valid on 11,994 of 11,994 | |
| SCC11 | none in the message (no byte matches a CRC8 or a sum of the rest) | steps by one on every frame |
| LKAS12 re-sent | none in the message; no counter; every payload sent is one the camera also sends | |
| SCC14 | **zero; valid on 90 of 12,000** | **zero** |

- The camera's own SCC14 has a counter running 0 to 14 and a nibble checksum valid on all 11,994 frames. Our branch sent both as zero because `/data/g70_long_scc14_counter` was off; no fault was seen from it on any drive.
- The option (sunnypilot's formula, ported on 2026-11-21) was turned on 2026-11-25 about 07:40. Not driven.
- A first pass of this check reported every CRC as invalid, the car's own frames included: the test's CRC started from the wrong register value (the routine starts from init XOR xor-out). Check a checksum test against the car's own frames before reading it.

## 9b. The delay the car needs (observations, 2026-11-25 morning)

Measured as the phase delay from the request (`controlsState.desiredCurvature` x v^2) to the vehicle's yaw rate x v, 0.1-0.6 Hz, hands off (`delay_extract.py`, `delay_measure.py`). The yaw rate is the raw gyroscope combined to match the calibrated yaw of the drives that log it (main axis 2 degrees from vertical).

| Speed | Ours `e1` / `d4` | sunnypilot's branch (`00000012`, `00000014`, `00000015`) |
|---|---|---|
| 30-45 mph | - / 0.28 s | |
| 45-60 mph | 0.34 / 0.33 s | |
| 60-70 mph | 0.33 / 0.39 s | 0.19 s (one drive) |
| above 70 mph | 0.45 / 0.46 s | 0.22, 0.28, 0.28 s |

- The delay rises with speed on both branches and is shorter at 0.6-1.2 Hz (0.22-0.28 s on ours, 0.13-0.19 s on that branch): a lag more than dead time.
- It did not change with the published delay on that branch (0.28 s at 0.21 and at 0.33 published).
- lagd's own estimate: 0.227-0.268 s on ours, 0.204-0.212 s on that branch.
- **Against our settings:** the planner's delay is the published 0.33 s plus 0.025 s; the smoothing's look-ahead only cancels the filter's own lag. That matches the measurement at 45-70 mph and is about 0.1 s short above 70 mph.
- The steering-angle-based curvature trails the request by 0.44-0.64 s and trails the yaw rate by 0.1-0.25 s. Cause not known; the gyroscope's tilt was checked and is not it.
- **Curves** (position toward the inside while the request builds / is steady / unwinds): ours +14 / +15 to +18 / +8 to +11 cm; that branch +18 to +31 / +16 to +30 / +14 to +23 cm. Every setup sits inside; the differences between delay settings are within the spread and on different roads.
- **Withdrawn while measuring:** that the 0.1 degree steps of the angle sensor explain the lag (the logged angle moves in finer steps).
- **Device, 2026-11-25 about 08:05:** `/data/g70_lat_smooth` `0.2 20 25` -> `0.2 20 25 0.3` (look-ahead 0.3 s with the 0.2 s filter: planner delay 0.33 s up to 45 mph, 0.43 s from 56 mph). The previous file is kept beside it. Not driven.

## 10. Open

- First drive back on our branch: the highway in daylight on the usual route, whether `/data/g70_cam_mdps12` changes anything on the cluster, and SCC14 with its counter and checksum (any cruise fault).
- 20–45 mph on any setup; a measurement of the centre that separates stiffness from stiction.
- For sunnypilot: the learner pulling tunes back toward the measured values, the torque limit reached on an on-ramp, the take-a-break and lead-departure messages reaching the cluster.
- Still not driven on our branch: the 0.85 s gap on one bar, the continuous relay counter (it runs from this drive on).
