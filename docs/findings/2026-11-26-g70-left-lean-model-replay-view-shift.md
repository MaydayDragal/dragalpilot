# G70 2024: the left lean, an offline replay of the driving model, and a view-shift option

Covers 2026-11-26 local time (US Eastern). Continues [2026-11-25-g70-first-drives-back-lookahead-curves.md](2026-11-25-g70-first-drives-back-lookahead-curves.md). Device identifiers and GPS are kept out of this repo.

Statements are marked as observations (measured from logs or code), inferences, or plans.

## 1. Summary

- **Observation:** on the highway the car sits left of the lane centre on every logged drive, on both branches: ours 14-29 cm (median of drives about 19), sunnypilot's 1-23 cm (about 11). This was in our data and not reported until a comparison from another project pointed at it.
- **Observation:** an offline replay of the driving model this build runs, on recorded road video, reproduces the logged model: lane lines within 1.2-1.3 cm, the car's position in the lane identical (15.0 cm left), desiredCurvature at r 0.9998.
- **Observation:** the model plans to stay there: 3.4 s ahead its planned path is only 1.8 cm right of the car. The lean is the model's own line, not the steering or the calibration.
- **Observation:** shifting the model's view so it sees the car further left makes it plan and steer right, close to one for one.
- **Device:** our branch `8c1c374` with `/data/g70_view_shift` = `0.10` (move the car 10 cm right). Not driven.

## 2. Where it came from

A USB drive from another project (a sunnypilot fork on a different car) carried a comparison of our `d4` with sunnypilot's `00000010` and an analysis toolkit. The comparison reported our build 27 cm left of centre against 7 cm; across all drives the gap between branches is about 5-8 cm, and both lean. The toolkit's model replay was the useful part; nothing from the drive was copied into this repo.

## 3. The replay (observations)

- **Model:** this build runs `driving_supercombo.onnx` from sunnypilot master `066c0e2` (compiled on the device to `driving_tinygrad.pkl`); downloaded from sunnypilot's large-file store and checked against the pointer's sha256 (`65a08adc...`, 60,918,562 bytes). One model with its frame, desire and feature queues as inputs and outputs (`new_img` 2x6x128x256 for the road and wide cameras, `desire`, `traffic_convention`, `action_t`), unlike the toolkit's two-model version, so the model call was rewritten.
- **Kept from the toolkit:** the nearest-neighbour warp and 6-channel packing (identical to tinygrad's `compile_warp.py` at `92b742f`, which this build compiled) and the view-shift matrix.
- **Inputs from the log:** `extrinsicsCalibration` (rpy and camera height), `narrowRoadEncodeIdx` / `wideRoadEncodeIdx` to find each frame in `fcamera.hevc` / `ecamera.hevc`, `lateralDelay`, the smoothing look-ahead, `carParams.longitudinalActuatorDelay`. Onnxruntime on the PC CPU, about 40 ms per frame.
- **Data:** route `0000001a` segments 15-17 (66 mph, our branch, 3,500 frames after 100 warm-up); road and wide video pulled from the comma for those segments (6 files, sha256 verified).

| Replay against the log | |
|---|---|
| Inner lane lines at the car / 31 m / 60 m (rms) | 1.3 / 1.6 / 3.0 cm |
| Car's position in the lane (median) | +15.0 cm both (car left of centre) |
| Planned position 0.6 / 1.6 / 3.4 s ahead (corr) | 0.999 / 1.000 / 1.000 |
| desiredCurvature | corr 0.9998, rms difference 0.010 m/s2 |

## 4. View shift (observations, open loop)

Against the unshifted replay, same frames. "Seen" = where the model sees the lane centre relative to the car.

| Shift (car moved in the model's view) | Seen position change | Planned position change 1.0 / 1.65 / 2.8 s | Steering request change |
|---|---|---|---|
| 10 cm right | car seen 9.8 cm further left | +1.3 / +3.4 / +5.9 cm (right) | +0.048 m/s2 |
| 10 cm left | car seen 9.5 cm further right | -1.2 / -3.1 / -5.4 cm | -0.043 m/s2 |
| 20 cm left | car seen 19.1 cm further right | -2.3 / -6.2 / -10.6 cm | -0.083 m/s2 |

- **Inference:** in closed loop the model steers until it sees itself at its preferred spot again, so the car should settle about the shift further right. Not tested on the road.
- The toolkit's comment says a positive shift "moves the car left"; with this camera geometry its positive shift makes the model see the car further right. The option below is named by the effect on the car.

## 5. The option (`8c1c374`, pushed)

- `/data/g70_view_shift` = metres, + = the car sits further right; limited to ±0.30; no file or an unreadable one = none. Read once when modeld starts.
- Applied in `selfdrive/modeld/modeld.py` to both camera warps whenever the calibration updates, at the calibrated camera height (1.21 m on these drives). sunnypilot's `CameraOffset` acts only in the Model Manager runner (`modeld_v2`), not in this one.
- **Checked:** the branch function gives the same warp as the replay's shift for both cameras and several values; file parsing and limits; on the comma after install, modeld imports with `VIEW_SHIFT = 0.1` and the warp changes, and the car interface imports.

## 6. Device record (local time)

| When | Change |
|---|---|
| 2026-11-26 about 18:28 | our branch fast-forwarded `1064526` -> `8c1c374` (adds the torque curve, the steering-wheel bar and the view shift, the first two off without their files); rollback branch `g70-fingerprint-prev` = `1064526`; `/data/g70_view_shift` = `0.10`; reboot |

## 6a. First drives with the shift (observations, added 2026-11-27)

Drives `0000001e` to `00000023` (2026-11-26 evening to 2026-11-27), all on `8c1c374` with `/data/g70_view_shift` = 0.10; 77 logs, sha256 verified. Road and wide video pulled for `00000022` segments 2-3 and `00000023` segments 16-18 (10 files, verified).

The logged lane lines come from the shifted view, so the true position was measured with the replay run with and without the shift:

| Highway straights | `00000022` (1.9 min, 76 mph) | `00000023` (2.9 min, 70 mph) |
|---|---|---|
| Replay with the 10 cm shift against the log | +0.3 cm, rms 0.8 cm, corr 0.999 | +0.1 cm, rms 0.7 cm, corr 0.995 |
| Replay without the shift against the log | -9.4 cm | -9.2 cm |
| **True position** (replay without the shift) | **10.3 cm left of centre** | **10.1 cm left** |
| Time more than 30 cm off centre | 2 % left, 2 % right | 0 % |

- The shift was in force, and the car moved about 9 cm right (typical before: 15-29 cm left, about 19). The model still holds its own preferred spot in what it sees (logged 19.1-19.6 cm).
- `drive_quality.py` above 60 mph: `00000022` lane movement 2.53 cm, slow swings 2.6 per minute, wheel 0.152 degrees; `00000023` 3.04, 4.7, 0.181 (`d4` / `e1` 2.41, 3.1, 0.12).
- **Inference:** about 0.19 would centre the car; 0.15 about 5 cm left.

| When | Change |
|---|---|
| 2026-11-27 about 18:30 | `TorqueParamsOverrideLatAccelFactor` 4.5 -> 4.2 (the planned curve test; view shift kept at 0.10) |

## 7. Open

- Factor 4.2 over a long drive (curve entry, delivery, straights on shared road with `0000001c` / `0000001d`).
- Then the shift: 0.15 to 0.19.
- The replay scripts live outside the repo (`Documents\\DragalPilot\\external\\model-replay-g70`); bring them in if the method is kept.
