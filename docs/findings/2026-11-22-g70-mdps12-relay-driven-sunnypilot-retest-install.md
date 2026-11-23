# G70 2024: MDPS12 relay driven, soft stop and factor 4.2 measured, sunnypilot's updated branch installed for a retest

Covers 2026-11-21 about 18:55 to 2026-11-22 (local time, US Eastern). Drives `00000005` (2026-11-21 18:56, 13 segments) and `00000006` (19:37, 15 segments) on our branch `2a81f61`; `00000004` is a single segment and was not used. Continues [2026-11-21-g70-sunnypilot-g70-2024-new-test-and-port.md](2026-11-21-g70-sunnypilot-g70-2024-new-test-and-port.md). Device identifiers and GPS are kept out of this repo.

Statements are marked as observations (measured from logs or tests), inferences, or plans.

## 1. Summary

- **Observation:** the MDPS12 relay to the camera worked on its first two drives: every frame valid, no relay fault, no new alerts, camera behaviour as before. Its counter skipped a step on about 4 % of frames; fixed in `1064526`.
- **Observation:** the soft stop ramp holds the command at −0.8 m/s² while the car rolls, as designed. The stops are a little gentler (three stops).
- **Observation:** restarts behind a lead: first movement 1.5 and 1.8 s after the lead (1.6–2.05 s before). Marginal.
- **Observation:** steering with the factor at 4.2 was worse than at 4.5 on shared road, and 30–45 mph with the low-speed look-ahead was worse than without. Both drives were in the dark.
- **Device:** sunnypilot's updated `g70-2024-new` @ `4e6c248` (damping feed-forward removed) is installed unmodified for a retest, with the steering settings at its defaults. Our branch is kept beside it at `1064526`.
- **For the return to our branch:** factor back to 4.5; the low-speed look-ahead file is already removed.

## 2. MDPS12 relay (observations, both options off)

| | `00000005` | `00000006` |
|---|---|---|
| Steering unit's frames (bus 0) | 72,702 | 86,770 |
| Sent to the camera | 68,428 | 83,388 |
| Checksum valid | 100 % | 100 % |
| Interval median / p99 / max | 9.9 / 20.5 / 23 ms | 9.9 / 19.5 / 23 ms |
| Gaps over 50 ms | 0 | 0 |
| Counter steps of 1 / of 2 | 64,966 / 3,461 | 80,831 / 2,556 |
| `ToiActive` / `ToiUnavail` differing from the car's latest frame | 3 / 0 | 0 / 0 |

- About 94–96 % of the steering unit's frames are relayed: when two arrive within one control cycle only the newer is sent.
- Panda: no relay malfunction, no invalid RX. Events and alerts: nothing new (`cruiseMismatch`, overrides, lane changes, gear and door events).
- Camera LKAS12 status as on earlier drives on our branch (levels 1 and 3); no warning. **Corrected 2026-11-23:** this reading used the wrong field (the attention status is bits 40-42) and is withdrawn; see [2026-11-23-g70-sunnypilot-fourth-tune-drive-daw.md](2026-11-23-g70-sunnypilot-fourth-tune-drive-daw.md) section 5. No cruise-held stop with the standstill prompt.
- **Counter:** it was the control frame number, so it stepped by two whenever a control frame had nothing new to send. **`1064526`:** the car controller keeps its own counter, one step per frame sent. Not driven.

## 3. Stops, restarts, speed control (observations)

| Final stop behind a car | Stock ramp, request at 2.2 mph (`df`, `e1`; 8 stops) | Soft ramp −0.8 (3 stops) |
|---|---|---|
| Gap at standstill | 3.2–5.5 m | 4.2–6.5 m |
| Last 2 s, mean deceleration | −0.60 to −0.70 m/s² | −0.50 to −0.62 |
| Last 2 s, strongest | −0.87 to −1.04 | −0.83 to −1.04 |
| Lowest command while rolling | −1.61 to −1.95 | −0.80 |
| Command when the car stopped | −2.0 | −1.31 to −1.34 |

- **Restarts** (two clean): first movement 1.50 and 1.76 s after the lead, 1 m/s at 2.17 and 2.60 s. On one the stop request was already off 2 s before the lead passed 0.3 m/s (the early stage); the car still took about 1.5 s.
- Braking events: three, strongest −2.07 m/s². Following above 34 mph for 4.5 min, strongest request −1.72.
- Set speed: cluster 77.0 mph, set 77.7 mph over 354 s.
- The 0.85 s gap: 0.5 min of steady following on one bar, behind a faster lead at the set speed. Still not measured.

## 4. Steering (observations)

Factor override 4.2, low-speed look-ahead `0.12 13 18`, both drives after dark.

| Above 60 mph, straights, hands off | `e1` (4.5) | `00000005`, `00000006` (4.2) |
|---|---|---|
| Minutes | 5.4 | 6.0 |
| Ping-pong per minute | 2.4 | 5.1 |
| Swings of 15 cm or more per minute | 0.37 | 1.32 |
| Trains per 10 min | 0 | 1.7 |
| Wobble per minute | 2.7 | 5.7 |

| Same road as the new drives, above 35 mph | shared min | ping-pong: other / new | lane 0.2–0.7 Hz (cm): other / new | wobble: other / new |
|---|---|---|---|---|
| `d4` (4.5) | 4.3 | 3.7 / 4.0 | 2.30 / 3.70 | 0.9 / 7.5 |
| `e1` (4.5) | 3.9 | 3.4 / 4.1 | 2.65 / 3.45 | 1.2 / 7.0 |
| `df`, `e0` (4.5, morning route) | 8.6 | 4.6 / 4.4 | 3.53 / 3.44 | 7.6 / 6.6 |

- At 30–45 mph (1.6 min, curves included): 31 wheel swings of 1° or more per minute, against 14 on `e1` and 10 on `d4`.
- **Inference:** 4.2 is worse than 4.5 on the two afternoon-route comparisons and equal on the morning-route one; darkness is a confound. The look-ahead did not help low speed.
- **Plan:** factor back to 4.5 at the return to our branch. `/data/g70_lat_lookahead_low` removed (2026-11-22).

## 5. sunnypilot's updated branch

- sunnypilot replied to the feedback: an update for the steering, longitudinal later once the car is merged.
- `g70-2024-new` moved from `ffb5a06` to `4e6c248`: one change, its opendbc at `4fe29c54` "Hyundai: remove G70 2024 damping feedforward".
- **Installed unmodified** (driver: change nothing on his branch): the copy kept on the comma was fetched to `4e6c248`, rebuilt in place at two parallel jobs (no memory failure), swapped in, panda flashed.
- **Steering settings set to that branch's defaults** for the test, as on its first drive: `TorqueControlTune` 0.0, torque override off (2.5 / 0.1), `LateralJerkTorqueController` 0, `TorqueBar` 0, `CustomTorqueParams` and `EnforceTorqueControl` removed. Left: `AlphaLongitudinalEnabled` 1, `DisableUpdates` 1. Our `/data/g70_*` files remain; that branch does not read them.

## 6. Device record (local time)

| When | Change |
|---|---|
| 2026-11-22 | `g70-2024-new` @ `4e6c248` swapped in, steering settings to its defaults, reboot, panda flashed to its firmware (signature `28783c291d318164`) |
| 2026-11-22 | kept copy of our branch (`/data/openpilot_ours`) fast-forwarded to `1064526`, rollback branch there `2a81f61`; `/data/g70_lat_lookahead_low` removed |

Current: **sunnypilot `g70-2024-new` @ `4e6c248` is running.** Ours is at `/data/openpilot_ours` @ `1064526`.

### Returning to our branch

1. Parked: move `/data/openpilot` to `/data/openpilot_g70new` and `/data/openpilot_ours` to `/data/openpilot`.
2. Settings: `TorqueControlTune` 1.0, `CustomTorqueParams` 1, `EnforceTorqueControl` 1, `LateralJerkTorqueController` 1, `TorqueBar` 1, `TorqueParamsOverrideEnabled` 1, `TorqueParamsOverrideFriction` 0.07, **`TorqueParamsOverrideLatAccelFactor` 4.5**.
3. Reboot; the panda flashes to `cb6201ae…` (signature `9209954232d5bbba`).

## 7. Open

- The retest drive on `4e6c248`: steering above 40 mph, then feedback to sunnypilot.
- On our branch: the continuous counter, then `/data/g70_cam_mdps12`; the 0.85 s gap on one bar; a daylight comparison at 4.5.
