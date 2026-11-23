# G70 2024: sunnypilot's fourth tune (2.7) driven, a live watch over the hotspot, the take-a-break warning, and a correction

Covers 2026-11-23 about 16:20 to 17:10 local time (US Eastern). Drive `0000000f` (16:23, 30 segments, 29 min) on sunnypilot `g70-2024-new` @ `f239548`, unmodified, its default steering settings. Continues [2026-11-23-g70-factor-2.8-test-sunnypilot-fourth-tune.md](2026-11-23-g70-factor-2.8-test-sunnypilot-fourth-tune.md). Device identifiers and GPS are kept out of this repo.

Statements are marked as observations (measured from logs), inferences, or plans.

## 1. Summary

- **Observation:** on about 11 minutes of road shared with each of our two best drives, the 2.7 tune has about twice the ping-pong (6.9–7.2 against 3.2–3.4 per minute), 45 % more lane movement (3.2–3.3 against 2.2–2.3 cm) and three times the fast wobble. This is the first solid same-road comparison of that branch with ours.
- **Observation:** below 60 mph it is the calmest that branch has been, level with ours or better on the by-speed measures (about three minutes per band).
- **Observation:** above 60 mph the fast wobble fell again (4.2 per minute) and the slow sway is the highest of its tunes (ping-pong 6.9, large swings 2.1 per minute).
- **Observation:** the camera raised its take-a-break warning for 3.9 s at the driver's bookmark, and that branch forwards it to the cluster.
- **Correction:** an earlier reading in these notes, that the camera's attention state stayed at its lowest level on that branch, came from the wrong field of LKAS12 and is withdrawn (section 5).
- **New capability:** with the PC on a hotspot that travels with the car, the comma can be watched live while driving.

## 2. Steering (observations)

### Same road, above 35 mph, hands off (`sway.py`)

| Against | Shared min | Ping-pong per min: other / 2.7 | Lane movement 0.2–0.7 Hz (cm) | Wheel 0.2–4 Hz (deg) | Wobble per min |
|---|---|---|---|---|---|
| ours `d4` | 11.4 | 3.2 / 7.2 | 2.23 / 3.22 | 0.184 / 0.296 | 1.1 / 3.4 |
| ours `e1` | 11.5 | 3.4 / 6.9 | 2.27 / 3.25 | 0.187 / 0.289 | 1.2 / 3.1 |
| its 2.8 local test | 2.0 | 5.0 / 5.9 | 5.26 / 4.53 | 0.413 / 0.385 | 6.0 / 3.4 |

### Above 60 mph, straights, hands off

| | 2.5 (`0000000d`) | 2.8 local (`0000000e`) | 2.7 (`0000000f`) | ours `e1` |
|---|---|---|---|---|
| Minutes | 6.9 | 2.4 | 5.2 | 5.4 |
| Ping-pong per minute | 2.2 | 4.9 | 6.9 | 2.4 |
| Swings of 15 cm or more per minute | 0.72 | 1.24 | 2.12 | 0.37 |
| 90th-percentile swing (cm) | 15.0 | 14.2 | 16.2 | 9.5 |
| Wobble per minute | 7.9 | 5.5 | 4.2 | 2.7 |
| Wheel reversals per minute | 41 | 22 | 28 | 22 |

Loop reading for 2.7: follow delay 0.59 s, follow gain 0.52 at 0.7–1 Hz (1.19 at 2.5), largest amplification 2.90 (1.96 at 2.5).

### By speed, curves included

Torque reversals of 13 counts or more per minute / wheel swings of 1° or more per minute / lane movement (cm) / lane swings of 15 cm or more per minute.

| | 20–45 mph | 45–60 mph | above 60 mph |
|---|---|---|---|
| ours `e1` | 33 / 17 / 3.7 / 3.1 | 12 / 6.6 / 6.5 / 2.9 | 7 / 1.4 / 3.0 / 1.7 |
| 2.5 | 118 / 30 / 6.1 / 10.8 | | 113 / 3.3 / 3.5 / 3.3 |
| 2.7 | 30 / 8.5 / 2.9 / 1.0 | 45 / 3.6 / 3.0 / 1.2 | 98 / 4.7 / 3.5 / 3.1 |

- 2.7 at 20–45 mph on straights only (1.9 min): ping-pong 6.4 per minute with 5.3 trains per 10 minutes (11 % of the time in a train); ours has none.
- Above 45 mph: 5.9 take-overs per 10 minutes, tracking error 0.54 m/s² rms.
- **Inference:** the over-answering of fast requests is gone at 2.7 (gain 0.52), and the slow loop is now amplified more. The low-speed result is better than expected from the evening tests; it is one drive.

## 3. Live watch over the hotspot (observations)

- With the PC on a hotspot that travels with the car, SSH to the comma works while driving.
- A read-only script on the comma (lowest priority; conflated reads of `carState` and `carControl` at 20 Hz, `modelV2` and `selfdriveState` at 4 Hz) printed one line per minute for 12 minutes during the start of `0000000f` and stopped by itself.
- In its five fully engaged, hands-off minutes (38–59 mph): 1–2 wheel swings of 1° per minute, 24–72 torque reversals per minute. The log analysis of the whole drive gives 30–45 below 60 mph, so the live figures were in the right range; they run lower than the 100 Hz analysis and the lane range they print includes lane changes and curves.
- Processor load during the watch 41–53 %, as without it.
- **Kept small on purpose:** device load while it controls the car is safety-sensitive (CLAUDE.md §4). A log pull over the hotspot is about 200–300 MB.

## 4. The take-a-break warning (observations)

- Driver: the bookmark at 23:12 was the take-a-break message.
- Camera LKAS12 (`0x53E`, bus 2): `CF_LkasDawStatus` (bits 40–42) = 6 with bit 44 set, byte 5 = `0x16`, for 40 frames (3.9 s), from 3.5 s before the bookmark to 0.5 s after. The only episode in the drive.
- That branch sends the camera's LKAS12 on to the car unchanged (17,452 frames on the panda's bus-0 echo). Our branch blocks the camera's copy and re-sends it with the warning replaced by the last normal level, and clears the chime bit in LKAS11.
- With the lead-departure flag on `0000000d`, that is two cluster messages seen on that branch that ours hides.

## 5. Correction

The 2026-11-21 findings compared "the low three bits of byte 0" of the camera's LKAS12 between branches and inferred that, with MDPS12 sent as "steering assist unavailable", the camera's attention state did not move off its lowest level. The 2026-11-22 and 2026-11-23 findings repeated the reading.

- The attention status is `CF_LkasDawStatus` at bits 40–42. The low bits of byte 0 are a different field.
- On `0000000f` the status moved through its levels (bits 40, 41 and 42 each differ from the commonest payload on thousands of frames) and the warning fired.
- **Withdrawn:** that the MDPS12 spoof keeps the camera's attention state quiet. It does not stop the take-a-break warning.
- **Still unknown:** whether the spoof prevents the grasp-warning sequence. No drive has shown that sequence starting or being prevented.

The three earlier documents are marked at the affected lines.

## 6. Open

- Feedback to sunnypilot: the 2.7 drive, and the take-a-break and lead-departure messages reaching the cluster.
- On that branch with standard values: 2.5 held the highway best, 2.7 the low and mid speeds; no value has done both.
- Whether the MDPS12 spoof does anything for the grasp sequence: needs a long hands-off highway stretch with stock cruise, on either branch.

Current device state is unchanged: sunnypilot `g70-2024-new` @ `f239548`, unmodified; our branch at `/data/openpilot_ours` @ `1064526`.
