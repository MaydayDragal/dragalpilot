# G70 2024: first drives back on our branch, the look-ahead test, curves in three phases

Covers 2026-11-25 about 08:10 to 15:40 local time (US Eastern). Drives `00000018` (13:31, 22 segments) and `00000019` (14:10, 18 segments) on our branch `g70-fingerprint` @ `1064526`, daylight. Continues [2026-11-25-g70-sunnypilot-settings-tests-steering-identification-return.md](2026-11-25-g70-sunnypilot-settings-tests-steering-identification-return.md). Device identifiers and GPS are kept out of this repo.

Statements are marked as observations (measured from logs), inferences, or plans.

## 1. Summary

- **Observation:** the two message options turned on that morning worked: SCC14 went out with a valid counter and checksum on every frame, MDPS12 to the camera as "steering assist unavailable" with a valid checksum and no counter skips, no fault, no new warning.
- **Observation:** the look-ahead raised to 0.3 s above 56 mph made the steering worse: fast wobble 13.0-13.6 per minute above 60 mph against 2.0-2.7, lane movement on the same road 3.34-3.55 cm against 2.21-2.30, and no gain in slow sway.
- **Inference:** looking further ahead than the smoothing filter lags is a lead: it raises the planner's reaction at 0.45-1 Hz. The measured request-to-vehicle delay (0.40-0.45 s) is how the car responds, not something to cancel with look-ahead. The recommendation of section 9b of the previous findings was wrong.
- **Observation:** every highway curve has the same shape on every setup: the car turns in toward the inside, holds 16-20 cm inside, and sits about 12 cm to the outside just after the exit. The delay setting on sunnypilot's branch (0.21 against 0.33 s) did not change it.
- **Device:** the look-ahead is still `0.2 20 25 0.3`; putting back `0.2 20 25` is approved and not yet done (the comma was unreachable).

## 2. Message options (observations, `msg_check.py`, cruise-engaged segments)

| | `00000018` | `00000019` |
|---|---|---|
| SCC14 sent: nibble checksum valid | 33,002 of 33,002 | 30,001 of 30,001 |
| SCC14 counter | 0 to 14, one step on every frame | the same |
| MDPS12 to the camera: CRC valid | 63,892 of 63,892 | 58,900 of 58,900 |
| MDPS12 counter steps | all of one | all of one |
| Share of the steering unit's frames relayed | 96.8 % | 98.2 % |
| Camera LKAS12 status values | 3, 4, 5; no warning frames | 4, 5; no warning frames |
| Car faults (steering, cruise) | none | none |

- In the spoofed MDPS12, byte 1 and byte 4 differ from the steering unit's own frame (the assist-status bits and the three always-set bits), as intended.
- Events: `cruiseMismatch` as on earlier drives, one `driverDistracted1` ("Pay Attention", openpilot's own monitor), lane changes; `ldw` and `speedTooHigh` only on hand-driven stretches.
- **Not new, found while checking:** the panda reports `faultTemp` with `interruptRateCan2` on every sample of these drives and equally on `d4`, `e1` and `00000006`; `safetyTxBlocked` rises by one per second on drives with openpilot longitudinal (`e1`, `00000006`, these two) and is 0 on `d4`. Neither is investigated.

## 3. The look-ahead test (observations, `sway.py`, hands off)

`/data/g70_lat_smooth` = `0.2 20 25 0.3`: filter 0.2 s, look-ahead 0.3 s, fading in from 45 to 56 mph. Everything else as on `d4` and `e1`.

| Above 60 mph, straights | `d4` | `e1` | `00000018` | `00000019` |
|---|---|---|---|---|
| Minutes | 4.2 | 5.4 | 6.4 | 5.7 |
| Wobble per minute | 2.0 | 2.7 | 13.0 | 13.6 |
| Ping-pong per minute | 3.5 | 2.4 | 4.2 | 2.6 |
| Swings of 15 cm or more per minute | 0.47 | 0.37 | 1.25 | 0.70 |
| 90th-percentile swing (cm) | 10.5 | 9.5 | 16.6 | 14.7 |
| Wheel reversals per minute | 23 | 22 | 44 | 41 |
| Plan's reaction at 0.45-0.7 Hz (m/s2 per m) | 2.31 | 2.35 | 3.64 | 4.50 |
| Car's answer at 0.7-1 Hz (share of the request) | 0.61 | 0.42 | 0.82 | 0.88 |

| Same road as `00000018`, above 35 mph | Shared min | Ping-pong per min | Lane 0.2-0.7 Hz (cm) | Wheel 0.2-4 Hz (deg) | Wobble per min |
|---|---|---|---|---|---|
| `d4` / `00000018` | 9.0 | 3.3 / 4.5 | 2.21 / 3.55 | 0.178 / 0.280 | 1.0 / 14.9 |
| `e1` / `00000018` | 9.1 | 3.2 / 3.4 | 2.30 / 3.34 | 0.192 / 0.265 | 1.2 / 14.5 |

- Request to vehicle yaw, 0.1-0.6 Hz above 60 mph: 0.40-0.45 s, as before the change.
- lagd's own estimate: 0.218 and 0.238 s.

## 4. Curves in three phases (observations, `curve_phases.py`)

A curve: the request above 0.5 m/s2 with one sign for 3 s or more, above 45 mph, hands off, lanes seen. All curves found are highway sweepers at 70-76 mph with a plateau near 1 m/s2 lasting about 10 s. Position is toward the inside of the turn, relative to the car's position on straights of the same drive (cm, medians).

| Setup | Curves | Before | Entry | Mid-turn | Exit | 1.5 s after |
|---|---|---|---|---|---|---|
| ours (`d4`, `e1`, `df`, `e0`) | 25 | -2 | +13 | +16 | +10 | -12 |
| sunnypilot's branch, v0, delay 0.20 | 11 | -4 | +8 | +17 | +14 | -13 |
| sunnypilot's branch, v1, delay 0.21 | 15 | +1 | +18 | +19 | +13 | -11 |
| sunnypilot's branch, v1, delay 0.33 | 22 | 0 | +19 | +20 | +12 | -12 |
| ours with look-ahead 0.3 (`00000018`, `00000019`) | 14 | -5 | +21 | +21 | +7 | -18 |

- **Entry** (2.5-3.0 s): the widest point is within 1 cm of the straight-road position on ours; the request is followed to within 0.03 m/s2.
- **Mid-turn:** steering-wheel movement about 0.07-0.09 degrees rms, no torque reversals of 13 counts on any setup; lane position moves over 23-32 cm within a curve. Lane movement about its 4 s average is 2.9 cm mid-turn against 2.0 cm on straights for ours, and 2.7-2.9 against 2.4-2.5 cm on that branch: our advantage is on straights.
- **Exit** (5-8 s): the car crosses from the inside to about 12 cm outside.
- Peak torque 20 % of the limit on ours (384 counts), 32-41 % on that branch (270).
- The curves on `00000018` / `00000019` are firmer (plateau 1.06 against 0.96 m/s2); against the firm curves of the earlier drives (+22 / +18 / -14) the difference is smaller.
- **Not usable:** per-curve timing from the 50 % points (scatter of half a second); the share of the request delivered mid-turn (0.93-0.98; the yaw scale is good to about 5 %).

## 5. Device record (local time)

| When | Change |
|---|---|
| 2026-11-25 about 08:05 | `/data/g70_lat_smooth` `0.2 20 25` -> `0.2 20 25 0.3` (recorded in the previous findings) |
| not yet done | back to `0.2 20 25` (approved about 15:30; the comma was not reachable) |

## 6. Open

- Put `/data/g70_lat_smooth` back to `0.2 20 25`.
- The panda's `interruptRateCan2` flag and the one blocked message per second: which message, and whether sunnypilot's branch shows the same.
- The exit of curves: whether the drift to the outside is the model's line or can be reduced.
