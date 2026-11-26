# G70 2024: two long drives, drive-to-drive noise, and under-delivery in firmer curves

Covers drives `0000001c` (2026-11-26 about 11:35, 89 segments) and `0000001d` (about 15:57, 90 segments), plus the short `0000001b`, on our branch `1064526` with the settings of `d4` / `e1` and both message options on. Both were driven before the view shift was installed. Analysed the same evening. Continues [2026-11-26-g70-left-lean-model-replay-view-shift.md](2026-11-26-g70-left-lean-model-replay-view-shift.md). Device identifiers and GPS are kept out of this repo.

Statements are marked as observations (measured from logs), inferences, or plans.

## 1. Summary

- **Observation:** on about 10 minutes of road shared with `d4` and `e1`, with identical logged settings and camera calibration, `0000001d` had about twice the slow swings and 40 % more lane movement. Drive-to-drive variation is as large as most effects tested in the last week.
- **Observation:** on straights the controller follows its request closely (tracking error 0.010-0.014 m/s2); above 60 mph the car's own movement explains 10-37 % of the lane movement; the extra torque activity on these drives comes from the model's request, not the feedback.
- **Observation:** in firmer curves at 45-60 mph the car delivers 0.90 of the request mid-turn and trails it by 0.41 s on entry (highway sweepers: 0.96 and 0.07 s).
- **Plan:** after a drive with the view shift alone, test factor 4.2 over a long drive.

## 2. Drive-to-drive noise (observations, `sway.py` same-road section, above 35 mph, hands off)

| Other drive / `0000001d` | Shared min | Ping-pong per min | Lane 0.2-0.7 Hz (cm) | Wheel 0.2-4 Hz (deg) | Wobble per min |
|---|---|---|---|---|---|
| `d4` | 9.9 | 3.2 / 6.6 | 2.17 / 3.27 | 0.187 / 0.234 | 1.6 / 3.5 |
| `e1` | 10.0 | 3.0 / 5.4 | 2.29 / 3.16 | 0.178 / 0.180 | 1.4 / 3.5 |
| `0000001a` | 11.0 | 4.3 / 6.3 | 2.75 / 3.39 | 0.233 / 0.228 | 3.9 / 3.2 |

- Logged settings compared (`initData` params for torque, delay, jerk and controller version; `carParams` lateral tuning, steer ratio, delay): identical apart from bookkeeping keys. Camera calibration at mid-drive: pitch 1.05-1.10 degrees, yaw -1.00 to -1.17 degrees, height 1.197-1.210 m on every drive since `d4`.
- **Inference:** traffic, light, road surface and the model's reading of the day vary more than expected. Verdicts from one drive of about 10 shared minutes (for example factor 4.2 on 2026-11-21, several tests on sunnypilot's branch) are weaker than they were presented. Judge tuning on long drives or repeated routes.

## 3. Straights (observations)

`drive_quality.py`: above 60 mph `0000001c` 19.6 min, lane movement 3.3 cm, slow swings 8.0 per minute; `0000001d` 3.16 cm and 5.2 (baseline `d4` / `e1` 2.41 cm and 3.1).

| Torque about its 5 s mean, rms counts (hands off, gentle road) | Output | Feedback p | Feed-forward f |
|---|---|---|---|
| `d4` + `e1`, above 60 mph | 9.3 | 3.1 | 6.6 |
| `0000001c`, above 60 mph | 12.8 | 4.2 | 8.8 |
| `0000001d`, above 60 mph | 12.7 | 4.1 | 9.0 |

- `torqueState` output equals -(p + i + f) exactly on these drives, so p, i, f are the whole command.
- Loop above 60 mph: car follows 0.79-0.82 s late, gain 0.67-0.70 at 0.7-1 Hz, largest amplification 1.55-1.91 (`d4` / `e1` 0.81-0.94 s, 0.42-0.61, 1.54-1.76).

## 4. Curves (observations, `curve_phases.py`, 54 curves)

| | Above 60 mph (40) | 45-60 mph (14) | Earlier drives above 60 mph (25) |
|---|---|---|---|
| Plateau (m/s2) | 0.96 | 1.48 | 0.96 |
| Entry shortfall (m/s2) | 0.04 | 0.17 | 0.03 |
| Car trails the request on entry (s) | 0.07 | 0.41 | -0.06 |
| Delivered mid-turn | 0.96 | 0.90 | 0.95 |
| Position mid-turn toward the inside (cm) | 17 | 34 | 16 |
| Peak torque (share of 384) | 0.26 | 0.43 | 0.20 |

- **Inference:** the shortfall grows with the curve's force, the sign of a factor a little high for larger lateral acceleration. The steady-state fit of 2026-11-25 gives 88-112 counts per m/s2 at 30-60 mph against 85 at factor 4.5; 4.2 gives 91.

## 5. Plan

1. Next drive: the view shift alone (`/data/g70_view_shift` = 0.10, installed), judged on highway position.
2. Then: `TorqueParamsOverrideLatAccelFactor` 4.5 -> 4.2, everything else unchanged, over a long drive with 45-60 mph curves. Judge on curve entry shortfall, delay and mid-turn delivery, and on straights over shared road with `0000001c` / `0000001d`.
3. Not before those: request smoothing 0.3 s with a 0.3 s look-ahead above 56 mph (best in the 2026-11-18 open-loop comparison, never driven).
