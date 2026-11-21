# G70 2024: a 1.0 m stop from the lower stop speed, the car's creep, a gentler final ramp, factor 4.5 → 4.2

Covers 2026-11-21 from about 07:25 to 08:10 local time (US Eastern). Drives `000000e2` (07:26, 8 min) and `000000e3` (07:34, 9 min). Continues [2026-11-20-g70-hard-braking-behind-a-lead.md](2026-11-20-g70-hard-braking-behind-a-lead.md). Device identifiers and GPS are kept out of this repo.

Statements are marked as observations (measured from logs or tests), inferences, or plans.

## 1. Summary

- **Observation:** with the stop request lowered to 0.6 m/s the car stopped 1.0 m behind a lead (`e3`). The setting was mine, from the day before, meant to soften the stop.
- **Observation:** the car creeps at about 0.9 m/s (2 mph) against a weak braking request. A stop request below that speed comes too late; 1.0 m/s is above it.
- **Device:** stop speed back to 1.0 m/s; `ac2bdcb` installed with a gentler final ramp (`/data/g70_long_stop_soft` = `-0.8`). Not driven.
- **Driver:** changed the lateral acceleration factor from 4.5 to 4.2 between the two drives; the first part felt worse than before.
- **Observation:** the two drives share no road and have 3.8 and 2.4 minutes hands off above 60 mph; the factor cannot be judged from them. On the road `e2` shares with the previous morning it was about the same as then.
- **Not tested on these drives:** the 0.85 s gap (the distance setting was on two bars), the two-stage restart (blocked by the close stop), the low-speed steering look-ahead (no hands-off driving under 45 mph).

## 2. The 1.0 m stop (observations, `e3`, about 5:45 into the drive)

| Seconds before standstill | Speed (mph) | Measured accel (m/s²) | Request (m/s²) | Gap (m) |
|---|---|---|---|---|
| −7.0 | 4.6 | −0.74 | −1.05 | 6.9 |
| −6.0 | 2.6 | −0.86 | −0.83 | 5.1 |
| −5.5 | 1.9 | −0.52 | −0.59 | 4.6 |
| −5.0 to −3.0 | 1.9–2.0 | about 0 | −0.41 to −0.35 | 4.2 → 2.2 |
| −2.0 | 1.4 | −0.23 | −0.31 | 1.5 |
| −1.5 | 1.1 | −0.32 | stop requested, command −0.70 | 1.2 |
| 0 | 0 | | command −2.0 | 1.0 |

- From −5.5 s to −2.5 s the car held 1.9–2.0 mph against a request of about −0.35 m/s² and closed 2.8 m.
- With the stop request at 1.0 m/s (the setting on 2026-11-20) it would have come at about −5.5 s with 4.6 m in hand; the stops then ended 3.2–5.5 m back.
- The same creep is in the 0.7 and 0.8 m stops of `d5` and `db` that led to the earlier stop request in the first place.
- **Inference:** the stop-request speed has to stay above the creep speed. Softening the stop has to be done in how the final braking is applied, not by requesting it later.

## 3. Gentler final ramp (`ac2bdcb`, not driven)

- **Stock:** in `stopping` the command ramps to −2.0 m/s² at 1 m/s³ from the moment the stop is requested, whatever the speed.
- **Change:** `g70_long.soft_stop_accel`, used in `longcontrol.py`. With `/data/g70_long_stop_soft` holding a value (range −1.5 to −0.4, set to `-0.8`), the command goes no lower than it until the car is below 0.15 m/s, then ramps to the hold value as stock.
- **Guards:** never less braking than the plan asks or than is already commanded; stock ramp again after 2.5 s in `stopping`.
- **Check on the 13 logged stops of 2026-11-20** (request at 2.2 mph): the plan asked −0.60 to −0.86 just before the stop request, the command reached −2.0 while still rolling, and the strongest measured deceleration was −0.82 to −1.04. With the floor the command stays at −0.8 while rolling.
- **Expectation, not measured:** peak about −0.5 to −0.8 without the final tightening, a few tenths of a metre more roll. It does not change the braking earlier in the approach (−1.6 to −2.4 m/s² at 9–17 mph on 2026-11-20).

## 4. Steering (observations)

The driver set `TorqueParamsOverrideLatAccelFactor` from 4.5 to 4.2 between `e2` and `e3` (friction override 0.07 unchanged). A lower factor is about 7 % more torque for the same lateral-acceleration request.

| Above 60 mph, straights, hands off | `e1` (4.5, afternoon route) | `e2` (4.5) | `e3` (4.2) |
|---|---|---|---|
| Minutes | 5.4 | 3.8 | 2.4 |
| Ping-pong per minute | 2.4 | 3.9 | 3.8 |
| Swings of 15 cm or more per minute | 0.37 | 1.04 | 0.84 |
| Wobble per minute | 2.7 | 14.5 | 6.0 |
| Wheel reversals per minute | 22 | 46 | 34 |

- `e2` and `e3` share no road. `e2` ran at 76 mph throughout.
- Same road as `e2`, against `df` / `e0` of the morning before (5.2 min shared): ping-pong 3.2 against 2.8 per minute, lane movement at 0.2–0.7 Hz 3.05 against 3.43 cm, wobble 13.5 against 11.3. About the same.
- **Inference:** "worse than before" compares with the afternoon drive `e1`; the morning route steers worse with the same settings (2026-11-20 findings).
- Loop reading for `e2`: follow gain 1.09 at 0.7–1 Hz, the car over-answers fast requests. A lower factor raises that gain; `e3` is too short to show whether it did.
- No hands-off driving under 45 mph on either drive: the low-speed look-ahead installed on 2026-11-20 is still unjudged.

## 5. Speed control (observations)

- Steady following was on two bars: 48.5 m at 73 mph (setting 1.25 s + 2 m predicts 48.7 m). No steady following on one bar.
- Following above 34 mph for 3.9 min: strongest request −1.23 m/s², no substantial braking event.
- Set speed: cluster 78.0 mph against 77.7 mph set over 342 s.
- **Restart after the close stop:** the lead left hard (to 3 m/s² within a second). The early release needs 3.0 m of gap and the car stood 1.4 m back, so it did not start; the plan's own release came about 0.5 s after the lead moved, the full 1.2 m/s² request 0.5 s later, and the driver pressed the gas about 1.0 s after the release, before the car had moved.

## 6. Device record (user-authorized, local time)

| When | Change |
|---|---|
| 2026-11-21, between `e2` and `e3` | driver: lateral acceleration factor override 4.5 → 4.2 in the settings |
| 2026-11-21 about 07:55 | `/data/g70_long_stop_speed` `0.6` → `1.0` |
| 2026-11-21 about 08:00 | `ac2bdcb` installed; `/data/g70_long_stop_soft` = `-0.8`; no reboot (read at the next ignition) |

Current: `g70-fingerprint` @ `ac2bdcb`, rollback branch `g70-fingerprint-prev` = `e3f7ac8`.

## 7. Open

- A stop behind a lead with the soft ramp: final gap and the last 2 s.
- The 0.85 s gap needs one bar on the distance setting; rerun `brake_events.py` / `brake_plot.py` after it.
- Factor 4.2: keep it for a round trip and compare road for road with `sway.py`.
- The early restart release needs a normal stop gap; low-speed look-ahead needs hands-off minutes at 20–45 mph.
