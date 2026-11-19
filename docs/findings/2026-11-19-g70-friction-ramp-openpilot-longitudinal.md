# G70 2024: friction ramp against the wobble, stock-cruise baseline, first drive with openpilot longitudinal

Covers 2026-11-19 02:30Z to 23:50Z. Drives `000000d1`–`000000d5`. Continues [2026-11-19-g70-sway-tool-controller-delay.md](2026-11-19-g70-sway-tool-controller-delay.md). Device identifiers and GPS are kept out of this repo.

Statements are marked as observations (measured from logs), inferences, or plans.

## 1. Summary

- **Observation:** lowering the V1 feedback gain to 0.6 did not reduce the wobble at a 0.10 s controller delay (15.7 against 15.2 fast swings per minute) and made the wheel busier at 45–56 mph. **Driver: worse.** Reverted.
- **Observation:** a 0.20 s controller delay lands between 0.33 s and 0.10 s on both faults (ping-pong 3.0, wobble 11.3 per minute above 60 mph).
- **Observation:** widening the friction ramp from 0.24 to 0.40 at that delay removed the wobble without bringing the ping-pong back: on 9.5 shared minutes, wobble 11.4 → 2.2 per minute, ping-pong 3.6 → 3.5. **Driver: highway pretty good, low speed still hunts.** This is the first change that broke the trade between the two faults.
- **Observation:** a speed-dependent ramp (0.24 below 20 m/s, 0.40 above 25 m/s) was worse than a flat 0.40 at 45–60 mph and on shared road. **Driver: hunting a little worse across the board.** Back to a flat 0.40.
- **Observation:** every setup hunts at 20–45 mph at a 3–4 s period; there the car follows the request 0.7–0.9 s late. Not solved, and there is little hands-off data at those speeds.
- **Observation:** openpilot longitudinal (alpha) works on this car: no faults, lead from the car's own object 98 % of lead time, commanded and measured acceleration correlate 0.95 with a 0.3 s lag. Problems on the first drive: one stop 0.8 m behind a lead, engagement refused from the accelerate toggle, three gap settings instead of four, and 8.7 acceleration swings per minute with a lead against 1.8 for the car's own cruise.
- **State:** `g70-fingerprint` @ `87e6a9e`, openpilot longitudinal on, with four new optional settings for it (section 7). Not driven in this state.

## 2. Steering drives (observations)

Common to all: `TorqueControlTune` 1.0 (V1), Lateral Jerk on, Enforce on, override 4.5 / 0.07, published delay fixed 0.33 s, smoothing `0.2 20 25`. Measures are from `tools/drive-eval/sway.py`, hands off, on straights.

Above 60 mph:

| Drives | Controller delay | Gain kp | Friction ramp | Straights (min) | Ping-pong /min | Swings ≥ 15 cm /min | Wobble /min | Wheel reversals /min |
|---|---|---|---|---|---|---|---|---|
| `ca`–`cc` | 0.33 | 0.8 | 0.24 | 11.3 | 5.0 | 1.06 | 5.7 | 31 |
| `cd`–`d0` | 0.10 | 0.8 | 0.24 | 5.8 | 1.0 | 0.17 | 15.2 | 48 |
| `d1` | 0.10 | 0.6 | 0.24 | 7.5 | 1.2 | 0.40 | 15.7 | 53 |
| `d2`, `d3` | 0.20 | 0.8 | 0.24 | 14.2 | 3.0 | 0.98 | 11.3 | 38 |
| `d4` | 0.20 | 0.8 | 0.40 | 4.2 | 3.5 | 0.47 | 2.0 | 23 |
| `d5` | 0.20 | 0.8 | 0.24 → 0.40 over 20–25 m/s | 4.0 | 4.3 | 1.51 | 5.6 | 35 |

Same-road pairs (cells both drove, above 35 mph):

| Later against earlier | Shared (min) | Ping-pong /min (earlier / later) | Wobble /min (earlier / later) |
|---|---|---|---|
| `d1` against `cd`–`d0` | 4.2 | 2.2 / 2.6 | 25.8 / 19.6 |
| `d2`, `d3` against `ca`–`cc` | 20.1 | 5.1 / 3.3 | 5.5 / 12.6 |
| `d4` against `d2`, `d3` | 9.5 | 3.6 / 3.5 | 11.4 / 2.2 |
| `d5` against `d4` | 3.9 | 3.1 / 7.8 | 1.0 / 3.8 |

- **Observation:** within one setup the wobble count per drive ranges from 1.5 (`cf`) to 25.8 (`cd`) per minute. It depends on the road; only the same-road pairs are reliable.
- **Observation (code, `latcontrol_torque.py`):** the feed-forward uses the undelayed request at every controller delay. The delay sets the setpoint the error is taken from and the point where the request's jerk is read; with a delay of 0.20 s or less the jerk is read at the newest request. On straights the proportional term is about a tenth of the feed-forward (mean |p| 0.007 against |f| 0.06).
- **Inference:** at a short controller delay the wobble comes from the friction compensation, which is driven by the gap between request and car and by the request's jerk. A wider ramp lowers its slope (0.07 / 0.24 → 0.07 / 0.40). The feedback gain does not scale it, which is why 0.6 changed nothing.

### 45–60 mph and below (thin data)

| Speed | Drives | Hands-off (s) | Ping-pong /min | Swings ≥ 15 cm /min | Lane 0.2–0.7 Hz (cm) |
|---|---|---|---|---|---|
| 20–35 mph | `ca`–`cc` (0.33, ramp 0.24) | 42 | 5.7 | 0.0 | 2.03 |
| 20–35 mph | `d4` (0.20, ramp 0.40) | 97 | 3.7 | 1.8 | 3.81 |
| 45–60 mph | `d4` (flat 0.40) | 185 | 3.6 | 0.0 | 1.63 |
| 45–60 mph | `d5` (0.24 → 0.40) | 123 | 5.4 | 3.4 | 2.45 |

- **Observation:** in 20–45 mph straight windows the request-to-acceleration delay is 0.56–0.89 s at 0.1–0.45 Hz on every setup with data, against 0.4–0.65 s above 60 mph on the short-delay setups, and the estimated loop gain is near 1 at 0.1–0.3 Hz with a negative phase margin.
- **Open:** `d5` has no hands-off data below 45 mph, so the low end of the speed-dependent ramp is unmeasured.

## 3. Stock cruise baseline (observations, `long_baseline.py`)

17 drives `c4`–`d4`, 295 min, 121 min cruising (cruise engaged, no pedals), 84 min with a lead, lead from the car's object 97 % of lead time.

| Area | Result |
|---|---|
| Following gap | Setting 1: 1.11 s median (35 m at 72 mph, 41 min). Setting 2: 1.39 s (6 min). |
| Comfort above 60 mph | Acceleration 0.22 m/s² RMS, braking harder than 1.5 m/s² 0.10 % of the time |
| Comfort below 35 mph (7 min) | Acceleration 0.90 m/s² RMS, braking harder than 1.5 m/s² 8.1 % of the time |
| Hard braking | 16 events below −2.0 m/s² for 0.3 s or more, strongest −3.4 m/s² |
| Speed see-saw | 1.8 acceleration swings of 0.4 m/s² or more per minute with a lead, 0.3 without |
| Set speed | 1.2 mph under the set speed with no lead |
| Stops | 13 held by cruise; 3.1 m to the lead (median), 1.4 m minimum; strongest braking −2.2 m/s² median |
| Restarts | 6 by cruise alone, 1.7 s after the lead moved; 7 with the gas pedal first |
| Take-overs | 18 gas overrides, 16 brake presses (1.4 and 1.2 per 10 min); cruise already braking harder than 0.5 m/s² in 1 of 16 |
| Warnings | 1 stock forward-collision warning, no automatic braking |

openpilot's planner, running in the background on the same drives (its requests, not its driving):

- on 30 episodes closing on a lead faster than 2 m/s it asked for braking a median 3.0 s before the stock cruise, earlier in 26, later in none;
- in steady following at the stock gap it asked for −0.20 m/s² on average;
- with a lead its requests were 0.53 m/s² RMS against 0.38 for the stock cruise, correlation 0.88.

## 4. Code check for openpilot longitudinal on this car (observations)

- `alphaLongitudinalAvailable` is true for the port (camera SCC, not legacy). `AlphaLongitudinalEnabled` selects it; the panda limits are −3.5 to +2.0 m/s².
- The G70 re-sends of SCC11 and LKAS12 were conditional on stock longitudinal. With openpilot longitudinal the car controller builds SCC11 / SCC12 / SCC14 itself.
- The panda's camera-SCC longitudinal TX list did not contain HDA11_MFC (`0x484`) or LKAS12 (`0x53E`), so the camera's copies would have been forwarded again ("grasp not detected", "take a break"). Added in `cca8ce7`, with the LKAS12 re-send enabled in both modes.
- FCA11 is not sent by openpilot on camera-SCC cars and is not in that TX list, so the camera's FCA11 is forwarded unchanged; the panda blocks any openpilot SCC12 or FCA11 that commands emergency braking. **Not confirmed on the car:** whether the cluster shows an AEB or collision-system warning in this mode (asked, not yet answered).
- The lead comes from the camera's SCC11 (`ACC_ObjDist`, `ACC_ObjRelSpd`) through sunnypilot's radar extension: one track. In `d5` the camera kept reporting it while openpilot controlled speed.
- The planner in this sunnypilot version always takes the lowest of the lead plan, the cruise plan and the model's own desired acceleration, also with experimental mode off; `longitudinalPlanSource` reads `e2e` much of the time.
- `STOP_DISTANCE` (6 m) is compiled into the solver; the following time and the obstacle position are run-time parameters.

## 5. First drive with openpilot longitudinal (`d5`, observations)

22 min, 14.3 min engaged, 11.8 min cruising, lead present 87 % of the active time. Gap setting changed four times by the driver.

| Area | `d5` (openpilot) | Baseline (stock cruise) |
|---|---|---|
| Steady following gap | 1.47 s median (5.3 min) | 1.11 s on setting 1 |
| Acceleration RMS, all cruising | 0.45 m/s² | 0.34 m/s² |
| Acceleration swings ≥ 0.4 m/s² per minute, with a lead | 8.7 | 1.8 |
| The same, no lead (2 min) | 4.1 | 0.3 |
| Hard-braking events | 4 in 12 min | 16 in 121 min |
| Gas overrides per 10 min | 4.2 | 1.4 |
| Command against measured acceleration | error 0.14 m/s² RMS, correlation 0.95, lag 0.30 s | |

- **Stop at 662 s:** 0.8 m to the lead by the logged distance. The car was 4.0 m behind at 2.5 mph with a target of −0.7 m/s², then rolled at 1–2 mph for about 5 s with targets of −0.2 to −0.4 m/s² until `shouldStop` came at 0.4 mph. Strongest braking in the approach was −1.9 m/s². The second stop (1141 s) was an engagement while already standing, 3.3 m. **One real stop.**
- **Engagement:** two presses of the accelerate toggle gave `resumeBlocked` ("Press Set to Engage"); the decelerate toggle engaged at the current speed. `selfdrived` refuses accelerate / resume while no set speed is stored (`vCruise` above 250).
- **Gap settings:** openpilot has three personalities (1.25 / 1.45 / 1.75 s); the cluster's bars are personality + 1.
- **Events:** `cruiseMismatch` on 856 frames while engaged (the car reports cruise engaged while openpilot is the one controlling; no alert is attached to it). No stock FCW, no automatic braking, no planner FCW.
- **Driver:** longitudinal "seems alright"; stops too close; wants the car's engagement behaviour and four gap settings with shorter distances.

## 6. Code and builds (sunnypilot branch `sunnypilot/g70-scc11-filter`)

| Commit | Change | Installed (UTC) |
|---|---|---|
| `a9b83b1` | `/data/g70_friction_threshold` may hold `low high v_lo v_hi`; used per update by the V1 controller and the jerk-aware extension | 2026-11-19 22:15 |
| `cca8ce7` | Camera-SCC longitudinal TX list gains `0x484` and `0x53E`; LKAS12 re-send in both modes; safety test expectations updated | with `6658738` |
| `4d4ddab`, `6658738` | Panda firmware rebuilt: sha256 `5277014d…`, signature `a47d97cd238a20e0` (32 bytes larger; the previous revision rebuilds to the shipped `8213b0c4…` byte for byte) | 2026-11-19 22:50 |
| `87e6a9e` | `g70_long.py` and its use in `long_mpc.py`, `selfdrived.py`, `controlsd.py`: optional following times, fourth gap setting, extra lead distance, engage with either toggle | 2026-11-19 23:45 |

`87e6a9e` settings (each off unless its file exists):

| File | Meaning | Set to |
|---|---|---|
| `/data/g70_long_follow` | Following time per gap setting, 3 or 4 numbers, each clamped to 1.0–2.5 s, non-decreasing. With four, the distance button cycles four settings, the cluster shows one to four bars, and settings 3 and 4 share the relaxed personality for everything except distance. | `1.05 1.25 1.45 1.75` |
| `/data/g70_long_stop_extra` | Metres taken off the lead's position before planning (0–4), so the car keeps that much more distance at every speed | `2.0` |
| `/data/g70_long_engage_any` | Present: accelerate / resume engages at the current speed when no set speed is stored | present |
| `/data/g70_long_gap` | Current gap setting 0–3, written by `selfdrived`, read by the planner and `controlsd` at most every 0.5 s; ignored whenever it disagrees with the personality | written by the device |

Checks: 16 and 42 assertions on the two helper modules on the PC; all changed modules import on the device; the planner's solver ran on the device with the four following times and the shifted obstacle. **Not run:** the panda safety tests, and anything in `selfdrived` or `controlsd` that needs the car (button handling, cluster bars). The gap-file design avoids a fourth value in `LongitudinalPersonality`, which other code assumes has three.

## 7. Device record (user-authorized)

| When (UTC, 2026-11-19) | Change |
|---|---|
| about 02:15 | `/data/g70_v1_gains` = `0.6 0.15` |
| about 12:10 | `/data/g70_v1_gains` removed; `/data/g70_lat_ctrl_delay` 0.10 → 0.20 |
| about 19:35 | `/data/g70_friction_threshold` 0.24 → 0.40 |
| about 22:15 | `a9b83b1` installed; `/data/g70_friction_threshold` = `0.24 0.40 20 25`; reboot |
| about 22:50 | `6658738` installed; panda reflashed; reboot |
| about 23:00 | `AlphaLongitudinalEnabled` = 1 |
| about 23:45 | `87e6a9e` installed; `/data/g70_friction_threshold` = `0.40`; the three `g70_long_*` files written; reboot |

Current: `g70-fingerprint` @ `87e6a9e`, rollback branch `g70-fingerprint-prev` = `6658738`. No tracebacks from controlsd, modeld, lagd, card, pandad, plannerd, radard or selfdrived on `d1`–`d5`.

## 8. Open

- Drive `87e6a9e`: stops (distance to the lead, target 3 m or more), engagement from either toggle, the four gap settings and the cluster's bars, and whether the flat 0.40 ramp restores `d4`'s steering.
- Whether the cluster shows an AEB or collision-system warning with openpilot longitudinal.
- Speed see-saw with openpilot longitudinal (8.7 swings per minute with a lead).
- Low-speed creep before a stop: the request of −0.2 to −0.4 m/s² does not hold the car at 1–2 mph.
- Low-speed steering hunt (20–45 mph), and making the cruise button itself engage (it shares the button with steering on / off).
- `cruiseMismatch` while engaged; `interruptRateCan2` / `faultTemp`; LKAS11 chime filter untested; cluster speed-limit issue; `adb` not installed permanently.
