# G70 2024: standard-value steering tests on sunnypilot's branch, a borrowed neural-network model, and its third tune

Covers 2026-11-22 about 19:40 to 2026-11-23 morning (local time, US Eastern). Drives on sunnypilot `g70-2024-new`: `00000007`, `00000008` (2026-11-22 19:39 and 20:02, `4e6c248` as published), `00000009`, `0000000a` (20:55, 21:03), `0000000b` (21:34), `0000000c` (21:53). All after dark. Continues [2026-11-22-g70-mdps12-relay-driven-sunnypilot-retest-install.md](2026-11-22-g70-mdps12-relay-driven-sunnypilot-retest-install.md). Device identifiers and GPS are kept out of this repo.

Statements are marked as observations (measured from logs or code), inferences, or plans.

## 1. Summary

- **Observation:** removing the damping feed-forward (`4e6c248`) cut the highway wobble on sunnypilot's branch from about 100 to 12 per minute. The torque command still reversed about 100 times a minute above 70 mph, and 20–45 mph did not change.
- **Observation:** with only the standard per-car values edited locally, friction sets the chatter and the lateral acceleration factor sets how tightly the lane is held. 4.0 / 0.04 was the best of four setups and near our branch on the highway.
- **Observation:** no standard-value setup improved 20–45 mph, and the two speed ranges want opposite factors.
- **Observation:** the neural-network controller with the older G70's model was the worst setup: about 230 torque reversals a minute and a take-over every 26 s.
- **Device:** sunnypilot's third tune, `9dd31d0`, is installed unmodified: factor 2.5, friction 0.055, and the car moved to the 270-count torque limit with slower rate limits. Not driven.

## 2. The setups (observations)

The branch's ramp width is fixed at 0.2 (`FRICTION_THRESHOLD`), its maximum torque was 384 counts until `9dd31d0`. Edits were made in the working copy on the comma only (`torque_data/override.toml`, `values.py`), never committed.

| Drives | Factor / friction / steer ratio | Other |
|---|---|---|
| `00000007`, `00000008` | 3.45 / 0.09 / 15.0 | as published at `4e6c248` |
| `00000009`, `0000000a` | 4.5 / 0.04 / 14.1 | |
| `0000000b` | 4.5 / 0.04 / 14.1 | `NeuralNetworkLateralControl` on; model `GENESIS_G70` (not an exact match) |
| `0000000c` | 4.0 / 0.04 / 14.1 | |
| not driven | 4.0 / 0.05 / 14.1 | discarded at the update to `9dd31d0` |

- The on-board torque learner was allowed (`useParams` 1) but not calibrated (55–81 %), so the edited values were the ones in force on every drive.

## 3. Results (observations)

### Above 60 mph, straights, hands off (`sway.py`)

| | 3.45 / 0.09 | 4.5 / 0.04 | 4.5 / 0.04 + NN | 4.0 / 0.04 | ours `e1` (afternoon) |
|---|---|---|---|---|---|
| Minutes | 6.7 | 3.4 | 1.3 | 3.6 | 5.4 |
| Wobble per minute | 12.0 | 3.4 | 16.3 | 2.0 | 2.7 |
| Ping-pong per minute | 4.3 | 5.7 | 6.8 | 4.4 | 2.4 |
| Swings of 15 cm or more per minute | 1.34 | 2.09 | 3.79 | 0.27 | 0.37 |
| 90th-percentile swing (cm) | 15.2 | 17.7 | 23.4 | 11.5 | 9.5 |
| Trains per 10 min | 1.5 | 0 | 0 | 0 | 0 |
| Wheel reversals per minute | 42 | 21 | 58 | 23 | 22 |

### By speed, curves included

Torque-command reversals of 0.05 or more per minute (1–6 Hz) / steering-wheel swings of 1° or more per minute.

| | 20–45 mph | 45–60 mph | above 60 mph |
|---|---|---|---|
| 3.45 / 0.09 | 128 / 37 | 65 / 8 | 76 / 2.2 |
| 4.5 / 0.04 | 82 / 43 | 63 / 17 | 23 / 2.3 |
| 4.5 / 0.04 + NN | 309 / 70 | 327 / 70 | 167 / 3.0 |
| 4.0 / 0.04 | 135 / 59 | 70 / 22 | 31 / 1.9 |
| ours `e1` | 14 / 17 | 2 / 7 | 1 / 1.4 |

### Same road, above 35 mph

| Pair | Shared min | Lane movement 0.2–0.7 Hz (cm) | Wobble per minute |
|---|---|---|---|
| 3.45 / 0.09 against 4.5 / 0.04 | 6.0 | 3.02 against 4.30 | 6.2 against 4.8 |
| 3.45 / 0.09 against 4.0 / 0.04 | 5.0 | 2.92 against 3.19 | 7.3 against 1.4 |
| 4.5 / 0.04 against 4.0 / 0.04 | 5.0 | 4.16 against 3.48 | 5.0 against 3.8 |

### Steering active above 45 mph

| | Take-overs per 10 min | Tracking error rms (m/s²) |
|---|---|---|
| 3.45 / 0.09 | 10.4 | 0.38 |
| 4.5 / 0.04 | 4.7 | 0.51 |
| 4.5 / 0.04 + NN | 23.1 | 0.73 |
| 4.0 / 0.04 | 3.5 | 0.48 |

- Driver: `00000007` / `00000008` highway much better than the first test; the NN drive "pretty bad"; `0000000c` "probably best yet tonight".
- Bookmarks on `00000007` at 10:50 (77 mph, 117 torque reversals per minute in the 20 s before), 13:54 (70 mph, steering calm), 17:15 (62 mph), and on `00000008` at 4:22 (67 mph, braking to −1.6 m/s²).
- `00000007` / `00000008`: no faults or unexpected messages; camera LKAS12 at its lowest level throughout (**corrected 2026-11-23:** wrong field, withdrawn; see the fourth-tune drive findings, section 5); cluster 1.5–1.7 mph above the set speed; median time gap 1.83 s.

## 4. Reading (inferences)

- **Friction over the ramp width sets the chatter.** The snap near zero error is friction ÷ ramp width in torque units: 0.45 published, 0.20 at 0.04; our branch 0.175 above 40 mph (0.07 over 0.40).
- **The factor sets how tightly the lane is held.** At 4.5 the car moved about 40 % more in the lane than at 3.45; at 4.0 about 15 % less than at 4.5.
- **Standard values cannot serve both speed ranges.** At 20–45 mph the torque reversals were 82 at 4.5 and 135 at 4.0: low speed wants the higher factor, the highway the lower.
- **The borrowed model does not transfer.** `GENESIS_G70.json` (2023, the older steering unit) asks 15–25 % less steady torque than factor 4.5, which looked mild; its reaction to fast changes was not sampled before the drive and that is where it failed.
- A lower friction number is not equivalent to a wider ramp: it also lowers the full push for a real error (0.04 against our 0.07).

## 5. sunnypilot's third tune (`9dd31d0`; observations from the code)

`g70-2024-new` @ `9dd31d0` = a merge of its master (GPS fuser replacing its locationd, a panda change that resets heartbeat mismatches on engage) and opendbc `7d150890` "Hyundai: lower G70 2024 steering torque limits".

| | Previous | New | Ours |
|---|---|---|---|
| Factor / friction | 3.45 / 0.09 | 2.5 / 0.055 | 4.5 / 0.07 |
| Maximum torque (counts) | 384 | 270 (`ALT_LIMITS`) | 384 |
| Rate limit up / down per 10 ms | 3 / 7 | 2 / 3 | 3 / 7 |
| Steer ratio | 15.0 | 15.0 | 14.1 |

In torque counts, since factor and friction are fractions of the maximum:

| | Previous | New | 4.0 / 0.04 test | Ours |
|---|---|---|---|---|
| Counts per m/s² of lateral acceleration | 111 | 108 | 96 | 85 |
| Full friction push (counts) | 35 | 15 | 15 | 27 |
| Friction snap near zero (counts per m/s² of error) | 173 | 74 | 77 | 67 above 40 mph |

- **Inference:** the steering strength is about unchanged and the friction snap is cut to where the best test sat. Expect the chatter largely gone; low speed least improved; the lower ceiling may bring the "hands on wheel" prompt sooner on tight ramps.

## 6. Other things looked up (observations)

- **Per-car steering hooks in the code:** `torque_from_lateral_accel` (only GM uses it, a sigmoid-plus-linear curve) takes the lateral acceleration and the torque parameters, not speed. Friction is added before it, in lateral-acceleration space. The car controller can do anything (the removed feed-forward lived there). The neural-network controller takes speed, lateral acceleration, jerk and roll, and needs a model file per car: 114 ship, none for `GENESIS_G70_2024`; name similarity picks `GENESIS_G70`.
- **Public routes for this car:** the only ones referenced are the two in commaai/opendbc 1134 (February 2024), credited there to this car's owner. The firmware lists hold one set of versions.
- **A lateral error dead zone** (`steeringAngleDeadzoneDeg`) grows with speed squared, so it acts on the highway, not at 20–45 mph.

## 7. Device record (local time)

| When | Change |
|---|---|
| 2026-11-22 about 20:40 | in the working copy of `g70-2024-new` @ `4e6c248`: factor 4.5, friction 0.04, steer ratio 14.1 (not committed) |
| 2026-11-22 about 21:25 | `NeuralNetworkLateralControl` on; off again about 21:50 |
| 2026-11-22 about 21:50 | factor 4.0 |
| 2026-11-22 about 22:20 | friction 0.05 (never driven) |
| 2026-11-23 morning | local edits discarded; `g70-2024-new` fetched to `9dd31d0`, rebuilt in place at two parallel jobs, reboot, panda flashed (expected signature `a3aa95a94181e7ef`) |

Current: **sunnypilot `g70-2024-new` @ `9dd31d0`, unmodified, its default steering settings.** Our branch is at `/data/openpilot_ours` @ `1064526`; the steps to return are in the 2026-11-22 findings, section 6.

- A `Params.put_bool` read back in the same process returned the old value; the write had landed (the file showed it). Read the file, or wait, before concluding a write failed.
- The first boot on `9dd31d0` took about 100 s before the manager's processes appeared.

## 8. Open

- Drive `9dd31d0`: chatter, lane holding, 20–45 mph, tight ramps at the 270-count limit; then feedback to sunnypilot.
- A neural-network model trained on this car is the route that could cover both speed ranges; ask sunnypilot.
- On our branch: the continuous relay counter, `/data/g70_cam_mdps12`, the 0.85 s gap on one bar, a daylight comparison at 4.5.
