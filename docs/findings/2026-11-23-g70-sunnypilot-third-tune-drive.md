# G70 2024: first drive on sunnypilot's third tune (`9dd31d0`)

Covers 2026-11-23 about 06:30 to 08:00 local time (US Eastern). Drive `0000000d` (06:32, 22 segments, 21 min) on sunnypilot `g70-2024-new` @ `9dd31d0`, unmodified, its default steering settings. Continues [2026-11-23-g70-sunnypilot-branch-standard-value-tests.md](2026-11-23-g70-sunnypilot-branch-standard-value-tests.md). Device identifiers and GPS are kept out of this repo.

Statements are marked as observations (measured from logs), inferences, or plans.

## 1. Summary

- **Observation:** the slow side-to-side movement above 60 mph is the lowest of any setup on that branch (2.2 ping-pong swings per minute; ours 2.4), and lane movement is 3.5 cm (ours 3.0).
- **Observation:** fast wobble is 7.9 per minute: better than its second tune (12.0), worse than the local 4.0 / 0.04 test (2.0) and ours (2.7). The loop still over-answers fast requests (gain 1.19 at 0.7–1 Hz, as on the second tune).
- **Observation:** 20–45 mph: 30 wheel swings of 1° or more per minute and 118 torque reversals, better than its second tune (37 and 199), short of ours (17 and 33).
- **Observation:** the new 270-count torque limit was never approached (99th percentile of the command 37 %).
- **Observation:** both driver bookmarks are in the log: highway hunting at 7:17, and the camera's lead-departure flag at 14:25–14:30, which that branch passes to the cluster.
- This drive shares no road with the evening tests, so setups are compared across roads here.

## 2. Steering (observations)

### Above 60 mph, straights, hands off (`sway.py`)

| | 2nd tune (3.45 / 0.09, 384) | local test (4.0 / 0.04, 384) | 3rd tune (2.5 / 0.055, 270) | ours `e1` |
|---|---|---|---|---|
| Minutes | 6.7 | 3.6 | 6.9 | 5.4 |
| Wander per minute | 4.9 | 4.7 | 8.6 | 6.2 |
| Ping-pong per minute | 4.3 | 4.4 | 2.2 | 2.4 |
| Swings of 15 cm or more per minute | 1.34 | 0.27 | 0.72 | 0.37 |
| 90th-percentile swing (cm) | 15.2 | 11.5 | 15.0 | 9.5 |
| Wobble per minute | 12.0 | 2.0 | 7.9 | 2.7 |
| Wheel reversals per minute | 42 | 23 | 41 | 22 |

Loop reading for the third tune: follow delay 0.52 s, follow gain 1.19 at 0.7–1 Hz, largest amplification 1.96.

### By speed, curves included, in torque counts

Torque-command reversals of 13 counts or more per minute (1–6 Hz) / wheel swings of 1° or more per minute / lane movement 0.2–0.7 Hz (cm).

| | 20–45 mph | above 60 mph |
|---|---|---|
| 2nd tune | 199 / 37 / 7.9 | 139 / 2.2 / 4.9 |
| local test 4.0 / 0.04 | 200 / 59 / 5.8 | 75 / 1.9 / 4.5 |
| 3rd tune | 118 / 30 / 6.1 | 113 / 3.3 / 3.5 |
| ours `e1` | 33 / 17 / 3.7 | 7 / 1.4 / 3.0 |

- Above 45 mph: 3.5 take-overs per 10 minutes, tracking error 0.50 m/s² rms.
- Torque command while hands off above 45 mph: 99th percentile 37 % of the 270 limit, no time above 90 %.
- Events: two `steerSaturated`, two `ldw`; no faults.

## 3. Bookmarks (observations)

| Time | Driver's note | Log |
|---|---|---|
| 7:17 | hunting at highway speed | 71 mph, hands off; lane position ranged over 44 cm in the 40 s before, largest single swing 23 cm, wheel angle range 3.7° |
| 14:29 | lead-departure message with openpilot longitudinal; start of a 45 mph stretch | camera LKAS12 bit 32 set on 41 frames (4.1 s), from 3.3 s before the bookmark to 0.8 s after; the only episode in the drive; the car was at a standstill 30 % of the preceding 30 s |

- That bit is the one our branch clears in the re-sent LKAS12 when `/data/g70_long_no_lead_alert` exists. sunnypilot's branch forwards the camera's LKAS12 unchanged.

## 4. Reading (inferences)

- In torque counts the third tune kept the steering strength (108 counts per m/s², 111 before) and cut the friction snap (74, 173 before). The unchanged strength matches the unchanged over-answering at 0.7–1 Hz; the smaller snap and slower rate limits match the calmer slow movement.
- The local 4.0 / 0.04 test ran at 96 counts per m/s² and had the least fast wobble. At the 270 limit that strength is a factor of about 2.8.
- Low speed again improved least; no standard value is speed-dependent.

## 5. Plan

- Suggested next standard-value step on that branch: factor 2.5 → about 2.8, friction and limits unchanged; watch whether the ping-pong stays low.
- Feedback for sunnypilot drafted for the driver.

Current device state is unchanged: sunnypilot `g70-2024-new` @ `9dd31d0`, unmodified; our branch at `/data/openpilot_ours` @ `1064526`.
