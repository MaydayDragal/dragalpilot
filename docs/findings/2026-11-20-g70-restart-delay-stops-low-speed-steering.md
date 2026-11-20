# G70 2024: restart delay behind a lead, firm stops, 0.69 s gap driven, low-speed steering

Covers 2026-11-20 from about 08:00 to 17:30 local time (US Eastern). Drives `000000df` (13:20), `000000e0` (13:55) and `000000e1` (16:06). Continues [2026-11-20-g70-gap-verification-fan-readout-pc-logs.md](2026-11-20-g70-gap-verification-fan-readout-pc-logs.md). Device identifiers and GPS are kept out of this repo.

Statements are marked as observations (measured from logs or tests), inferences, or plans.

## 1. Summary

- **Observation:** the car first moves 1.5–2.1 s after a lead pulls away from a standstill. About 1.0–1.2 s of that is the car letting go of its standstill hold after openpilot asks for acceleration, and a stronger request does not shorten it (`e1`).
- **Observation:** the 0.69 s gap shortened the following distance as its setting predicts, within about 1.5 m from 55 to 75 mph.
- **Observation:** with the stop request at 2.2 mph, stops behind a car end 3.2–5.5 m back (0.7–0.8 m before), and the last 2 s run at −0.6 to −1.0 m/s² (about −0.2 before). Driver: firm, with a lot of distance left.
- **Observation:** highway steering on `e1` is the best since `d4` with no steering change since the morning drives, which were worse. The difference is the route, not a setting.
- **Withdrawn:** the suspicion raised mid-day that openpilot longitudinal makes steering worse. `e1` has it on and matches `d4`.
- **Observation:** at 20–45 mph the steering wheel swings 1° or more 9–14 times a minute (1–2 above 60 mph). Driver: low-speed hunting still bad.
- **State:** `g70-fingerprint` @ `e3f7ac8`; fan readout off; stop speed 0.6 m/s; two-stage restart `1.2 0.3`; low-speed look-ahead `0.12 13 18`. The last three are not driven.

## 2. Restart from a standstill (observations, `restart_delay.py`)

Times after the lead reaches 0.3 m/s (and stays above it for 0.5 s), restarts without gas.

| | Stop request off | Car moves (0.1 m/s) | 1 m/s | Lead's head start at 1 m/s |
|---|---|---|---|---|
| `d6`, `df` before any change (3 restarts) | 0.4–0.95 s | 1.5–2.15 s | 2.4–3.2 s | 5–6 m |
| `e1` with the full request at once (5 restarts) | 0.4–0.9 s | 1.6–2.05 s | 2.25–2.8 s | 2.4–5.9 m |

- **Stock behaviour:** the planner keeps its stop request until its own plan asks for 0.1 m/s², then the request ramps from about 0.3 to 0.9 m/s² over a second. The controller goes from `stopping` straight to `pid`; this branch has no `starting` state.
- **`bb68347`, driven on `e1`:** `QuickStart` asked for 1.2 m/s² from the moment the lead was faster than 0.7 m/s and accelerating by more than 0.5 m/s². The request went out as designed (1.20 on every trace) and the car still took 1.0–1.2 s to move. It also began 0.2–0.5 s later than the stock release because of its thresholds, so it gained nothing.
- **Inference:** the remaining delay is the car releasing its standstill hold. With the gas pedal the car rolled about 0.25 s after the pedal (`df`).
- **`e3f7ac8`, not driven:** an early stage. As soon as the lead is faster than 0.3 m/s and accelerating by more than 0.15 m/s² for three planner cycles, the stop request is dropped with a small request (0.3 m/s²), and the full one follows as before. Replayed over ten drives (`replay_quick_start.py`) it begins 0.2–0.8 s before the logged stop release on the real restarts.
- **Known side effect:** 4 of 19 replayed starts are behind a lead that crept and stopped again (speed 3 s later under 1 m/s). The car would roll a little before the plan stops it. The replay uses the logged car response, so it shows when the logic starts and ends, not how far the car would roll.

## 3. Stops behind a car (observations)

| Drive | Stop requested at | Final gap | Last 2 s, mean / strongest | Strongest braking on the approach |
|---|---|---|---|---|
| `d6` (stock 0.7 mph) | 0.7 mph, 3.4 m | 3.2 m | −0.19 / −0.37 m/s² | −2.49 at 22 mph, 37 m |
| `df` (2.2 mph), 3 stops | 2.1–2.2 mph, 5.0–5.8 m | 4.0–5.0 m | −0.66 / −0.99 | −1.95 to −3.75 |
| `e1` (2.2 mph), 4 stops | 2.2 mph, 4.0–6.3 m | 3.2–5.5 m | −0.60 to −0.70 / −1.04 | −1.6 to −2.4 at 8–17 mph, 12–26 m |

- The earlier stop request cured the 0.7 m stops and overshot: in `stopping` the command ramps to −2.0 m/s² at 1 m/s³ while the car still rolls at 2 mph.
- **Device:** `/data/g70_long_stop_speed` `1.0` → `0.6` (1.3 mph). **Plan:** expect a gentler end about 3.5–4.5 m back; an estimate, not driven.
- The mid-approach braking is partly the 0.69 s gap, which brakes later. Not changed.

## 4. Following distance at 0.69 s (observations, `df`, `e0`)

| mph | 55–60 | 60–65 | 65–70 | 70–75 | 75–80 |
|---|---|---|---|---|---|
| 0.75 s + 2 m (m) | | 32.2 | 30.6 | 32.8 | 36.4 |
| 0.69 s + 2 m (m) | 25.5 | 25.7 | 28.8 | 32.0 | 45.6 |
| 0.69 s expected (m) | 25.8 | 27.3 | 28.8 | 30.4 | 31.9 |

- 75–80 mph (171 s) is following at the set speed of 78 behind a faster lead, not at the gap.
- Following above 34 mph for 15.7 min: time gap p1 0.52 s, p5 0.85 s, median 1.19 s; 1.67 % of the time under 0.6 s; shortest time to collision 4.4 s.
- One slowdown reached the −3.5 m/s² limit: 50 → 34 mph in 3.0 s behind a braking lead, smallest gap 1.66 s / 29 m. Others −1.7 to −2.6 m/s².
- Set speed: cluster 78.0 mph against 77.7 mph set, over 464 s.

## 5. Steering

### Above 60 mph (`sway.py`, straights, hands off)

| | `d4` (best) | `dd`, `de` | `df`, `e0` | `e1` |
|---|---|---|---|---|
| Minutes | 4.2 | 7.2 | 13.1 | 5.4 |
| Ping-pong per minute | 3.5 | 3.0 | 3.7 | 2.4 |
| Swings of 15 cm or more per minute | 0.47 | 0.55 | 1.15 | 0.37 |
| Wobble per minute | 2.0 | 8.4 | 6.6 | 2.7 |
| Same road as `d4`: ping-pong, ref | | | 4.8, 3.2 (9.4 min) | 3.4, 2.5 (11.3 min) |
| Same road as `d4`: lane movement 0.2–0.7 Hz (cm), ref | | | 3.79, 2.23 | 2.29, 2.08 |

- Steering settings above 40 mph were identical on `dd`–`e1`. Driver: `df` / `e0` "doesn't seem very good anymore", `e1` "much better".
- **Checked and ruled out as causes of the morning result** (`lat_state.py`, `sway_vs_lead.py`): params identical; learned torque values not used (fixed values are) and steady (factor 3.42–3.55, friction 0.077–0.085); steer ratio 13.75–14.4; model time 30–33 ms, no dropped frames; carControl interval p99 14 ms; LKAS11 interval 9.8 ms median, p99 13 ms; processor 52–55 %; no relation between lane movement and lead distance; the later drives do not accelerate or brake more than `d4`.
- **Withdrawn:** on road shared with `d4`, the first four openpilot-longitudinal groups showed 1.5–2.4 times `d4`'s ping-pong and the stock-cruise group matched it. `e1`, with openpilot longitudinal on, is within the spread of `d4`. With curves included, whole-drive lane movement above 60 mph ranges from 2.3 cm (`d5`) to 9.1 cm (`da`) across drives with no relation to setup.
- **Inference:** `d4`, `d5` and `e1` are afternoon drives and the weaker ones are mornings: route and direction, as earlier findings said of the wobble count. Compare only like with like.

### 20–45 mph

Steering active, hands off, no blinker, stretches of 6 s or more, curves included (lane lines not required).

| | 20–30 mph: min, wheel swings ≥ 1° per min | 30–45 mph | 45–60 mph | > 60 mph |
|---|---|---|---|---|
| `d4` (friction ramp flat 0.40) | 1.7, 10.2 | 3.8, 10.4 | 4.6, 5.4 | 6.7, 0.7 |
| `dc`–`de` (flat 0.40) | | 3.8, 20.5 | 1.4, 12.3 | 10.4, 2.0 |
| `df`, `e0` (0.24 below 29 mph) | 0.7, 22.2 | 2.1, 18.2 | 2.6, 14.8 | 20.5, 1.6 |
| `e1` (0.24 below 29 mph) | 1.2, 8.8 | 3.5, 14.1 | 3.1, 6.6 | 7.7, 1.4 |

- The wheel movement peaks at 0.35–0.41 Hz in every band: the same loop as on the highway, larger at the wheel because the same correction needs more angle at low speed.
- The narrower friction ramp below 40 mph has neither clearly helped nor hurt on 1–4 minutes per drive.
- **Loop on low-speed straights (`d4`, 7 windows):** at 0.1–0.3 Hz the model's request leads lane position by about 20° (65–95° above 60 mph), the car answers 45–59° late, and the loop gain is 1.35 / 0.76 with negative margin: it magnifies that band 1.6 times.
- **`e3f7ac8`, not driven:** modeld aims further ahead at low speed, `/data/g70_lat_lookahead_low` = `seconds v_lo v_hi`; set to `0.12 13 18` (0.12 s below 29 mph, none from 40 mph). controlsd keeps its own 0.20 s delay.
- **Caution:** offline on route `c1`, aiming further ahead made the request 10–15 % larger at 0.3–0.7 Hz. This is a test on one drive's evidence.

## 6. Device record (user-authorized, local time)

| When | Change |
|---|---|
| 2026-11-20 about 08:10 | `/data/g70_ui_fan` removed (fan readout off). Stopping the screen process did not bring it back; rebooted |
| 2026-11-20 about 14:50 | `bb68347` installed; `/data/g70_long_start` = `1.2`; reboot |
| 2026-11-20 about 17:05 | `/data/g70_long_stop_speed` `1.0` → `0.6` |
| 2026-11-20 about 17:20 | `e3f7ac8` installed; `/data/g70_long_start` = `1.2 0.3`; `/data/g70_lat_lookahead_low` = `0.12 13 18`; reboot; checked over USB afterwards |

Current: `g70-fingerprint` @ `e3f7ac8`, rollback branch `g70-fingerprint-prev` = `bb68347`.

- The manager does not restart a killed process: stopping `ui` leaves the screen dark until a reboot.
- After two of three reboots today the comma did not reappear over USB for several minutes; restarting the adb server and waiting brought it back once.

## 7. Open

- Drive the two-stage restart, the 0.6 m/s stop speed and the low-speed look-ahead; a few minutes hands off at 20–45 mph.
- If low-speed steering is worse, delete `/data/g70_lat_lookahead_low`.
- Braking on the approach at the 0.69 s gap.
- Still open from before: AEB or collision warning on the cluster with openpilot longitudinal; four bars against the lane-change arrow; the settings menu with three names.
