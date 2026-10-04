# G70 2024: video check of the lane-position findings (2026-10-04, session 5)

**Question:** do the road videos, measured with a method independent of the driving model, confirm what [the lane-drift
findings](2026-10-04-g70-lane-drift.md) derived from `modelV2.laneLines`?

- A static left bias of the device of ~0.15–0.19 m.
- A shift toward the inside of curves of ~0.25–0.4 m per 1/1000 m of curvature.
- That the slow lane-position variation is real motion.

Also: what is the visual context of the short engaged low-speed windows?

**Evidence types:**

- Observations from existing recordings: routes 6, 7 (`7e9d0755d9`) and 8 (`82f58a9a8c`) for the highway comparison; routes 4, 6–9 for the low-speed windows.
- Confirmed source facts (file + `dragal/custom` @ `82f58a9a8c`).
- An offline measurement whose error is stated below.

No device access this session. Roads and conditions weren't controlled.

## Summary

- **The video confirms the model's lane-position numbers on the highway.**
  - Lane-centre position at 12 m: video − model = **+0.4 to +0.7 cm** on all three routes (block SE 0.2 cm).
  - On near-straight road the device is **0.14–0.20 m left of the lane centre** by both methods.
- **It confirms the curve-inside shift, with an independent curvature reference.**
  - Device position vs curvature from Kalman yaw rate / v, at x = 0: video 0.40 / 0.39 / 0.23 m vs model 0.40 / 0.37 / 0.24 m per 1/1000 m (routes 6 / 7 / 8).
  - With the model's own road curvature the numbers are the same within 0.02.
- **The slow variation is seen by both methods.** After a 20 s detrend: correlation 0.90–0.97, video/model slope 0.94–0.96, peak at lag 0.
  - So the variation is not an artefact of the model's perception (confirmed observation; the camera and calibration are shared, see Limitations).
- **The model draws its lane lines 6–7 cm inside the left paint centre and 7–9 cm inside the right one.**
  - Its lane is 0.14–0.16 m narrower than the paint centre-to-centre width.
  - The two sides nearly cancel in the centre (+0.4–0.7 cm). This does not explain the left bias.
- **Low-speed windows (≤ 17 s each, 24 windows):**
  - Almost all are at or next to intersections and turns, or on unmarked residential streets.
  - Both lane lines are confident less than half the time in 11 of 24 windows.
  - 6 windows have a lead vehicle at 10–25 m. In those with weak lines, the model's lane lines visibly bend toward the lead vehicle (observation, 4 frames per window, not quantified).
  - None is stop-and-go; none is a sustained steady stretch.

## Inputs and frame alignment

- **Videos:** narrow road camera `fcamera.hevc`, 1344×760, HEVC.
  - Routes 5–7 were pulled in session 3.
  - Routes 3, 4, 8, 9 were pulled by session 4b (`device-pull-20261004d`, all sha256 MATCH) and promoted to `recordings/2026/10/04/`.
  - Route 4 segment 9 and route 9 segment 4 are 0-byte files on the device, kept as received; neither is used here.
- **Camera model** (source fact):
  - `mici` + `os04c10` → `DEVICE_CAMERAS` narrow road = `CameraConfig(1344, 760, 1522·3/4 = 1141.5)`, principal point at the image centre (`openpilot/common/transformations/camera.py` L49–71).
  - Device and sensor are logged in `deviceState` and `narrowRoadCameraState` on every route (observation).
  - Projection as used by the UI and modeld: `K · view_from_device · rot(rpyCalib) · p` (`camera.py` L74–97; `transformations.py` L141–155, Z-Y-X; `selfdrive/ui/mici/onroad/augmented_road_view.py` L282–314).
- **Calibration:** the latest `extrinsicsCalibration` (rpyCalib, height) at each frame. Routes 6–8: `calibrated`, pitch 1.21–1.33°, yaw −1.04° to −1.15°, height 1.20 m (session 4).
- **Frame ↔ log mapping:**
  - Source fact: `modelV2.frameId` = vipc frame id of the narrow camera (`selfdrive/modeld/fill_model_msg.py` L83, `modeld.py` L276).
  - `narrowRoadEncodeIdx` gives `segmentNum` and `segmentId` (index in the segment's file, presentation order; `cereal/log.capnp` EncodeIndex).
  - Verified on route 6 segment 2: 1200 encode-index entries, `segmentId` 0–1199 contiguous, 1200 decoded frames, encodeIdx and camera SOF identical. `modelV2.frameId` was found in the encode index for 1199/1200 frames (the last is at the segment boundary).
  - On routes 4 and 6–9, every `modelV2` frame maps to an encode-index entry (0 missing).
  - So each measured frame is the exact frame the model saw.
  - Visual check: the model's lines projected onto the decoded frames land on the paint (`overlays/`).
  - Lag check in the comparison: correlation peaks at lag 0 at 0.2 s resolution.

## Measurement method (independent of the model)

Script `vid_detect.py` (v2). It uses only the image, the intrinsics and the logged calibration; no model output is used for detection or selection.

1. **Bird's-eye view** of the flat road plane z = h in the calibrated frame: x 6–30 m, y ±4 m, 0.1 × 0.02 m cells. Grey plus a yellow channel ((R+G)/2 − B).
2. **Ridge filter** per row: centre (±0.06 m) minus the brighter of the two side bands (0.14–0.30 m).
   - Bright stripes respond; edges and shadows don't.
   - v2 subtracts a seam level of 8: concrete seams reach 4–9, paint 10–40 (`vid_seam_probe.py`).
3. **Line search** for curves y = a + b(x−12) + c(x−12)² over 6.5–25 m (|b| ≤ 0.04, |c| ≤ 0.001).
   - Lane pairs of 2.6–4.4 m width, ranked by summed response.
   - Each line needs ≥ 1.0 m of paint rows.
4. **Joint parallel-line fit** (shared heading and curvature) with per-side residual rejection. A single dash still fixes its line's offset.
   - Output: the centre of each painted stripe at x = 0 (extrapolated), 6.75, 9.19, 12, 15.19 and 18.75 m. These are the model's `X_IDXS` 6–10, so both are compared at the same distances.
5. **Frames:** the eligible highway frames of the lane-drift analysis (identical criteria: lateral active, no steering press, no blinker within 3 s, v > 15 m/s, both line probs > 0.7, stretches ≥ 30 s), every 4th frame (5 Hz).
   - Route 6: 2712 frames; route 7: 3113; route 8: 5964.
   - Detector success: 93.1 / 93.3 / 94.7%.
   - "Strict" subset (paint within 8–15 m on both sides, fit RMS < 3 cm): 55–60%.

**Detector history:** v1 (no seam suppression) was run first. A random hand check found it put a dashed line on a continuous concrete seam (R6 t = 230.1 s, 0.42 m off), so v2 was made and everything was re-run. The v1 conclusions (routes 6–7) were the same within ~1 cm (v1 video − model: +1.1 to +1.5 cm). This tuning was done after seeing results, so it is exploratory, not held-out.

## Measurement error

- **Hand check:** 15 frames picked at random (seed 20261004; per route 3 strict, 1 ok-only and 1 failed). For each line, the 12 m image row profile was read by hand.
  - Record: `E:\DragalPilot\analysis\g70-video-lane-20261004\validation_handcheck_v2.md`.
  - 14 line instances had paint in that row. Detector − hand: **mean +0.2 px, RMS 1.2 px (≈ 1.3 cm), max 2.6 cm.**
  - Where both lines were checkable (3 frames), the centre error was ≤ 0.1 px.
  - 10 instances fell in a dash gap at 12 m (value from the joint fit, not hand-checkable at that row).
  - All 3 failed frames inspected were conservative rejections (faint or worn dashes), not wrong lines.
- **Per-frame noise:** the lane-width variation (10 s detrend) implies ≤ 3–5 cm centre noise per frame. This is an upper bound, since real width changes are included.
  - Video − model at 12 m: sd 2.6–3.1 cm on the strict set, 2.9–4.9 cm on all.
  - Outliers: |line difference| > 0.2 m in ≤ 2.4% of frames; |centre difference| > 0.1 m in 0.5–2.9%.
- **Systematic:**
  - The lane centre is insensitive to scale errors (flat-road assumption, height) to first order: a 5% scale error moves a 0.19 m offset by 1 cm.
  - Lane widths and the curve slopes scale with it; the camera height was not independently verified.
  - Roll (−0.005°) is negligible.

## Results (eligible highway frames, all detector-ok frames; strict subset in brackets where it differs)

Positions: y right-positive. Lane centre c(x) = (left + right)/2. Device position relative to the lane centre p = −c (negative = device left of centre). Uncertainty: SE from 10 s block means. Curvature sign as `desiredCurvature` (positive = right turn).

| | Route 6 | Route 7 | Route 8 |
|---|---|---|---|
| Eligible measured time (ok) | 505 s | 581 s | 1130 s |
| Lane centre at 12 m: video / model | +0.173 / +0.169 m | +0.190 / +0.185 m | +0.128 / +0.121 m |
| Video − model at 12 m (SE) | +0.004 (0.002) [+0.004] | +0.005 (0.002) [+0.006] | +0.007 (0.002) [+0.007] |
| Video − model at 9.19 / 15.19 m | +0.004 / +0.005 | +0.006 / +0.004 | +0.007 / +0.007 |
| Near-straight: device left of centre at 12 m, video / model | 0.195 / 0.192 m | 0.183 / 0.178 m | 0.147 / 0.138 m |
| Near-straight: at x = 0 (extrapolated), video / model | 0.196 / 0.201 m | 0.194 / 0.187 m | 0.153 / 0.145 m |
| Curve slope of p at 12 m vs Kalman curvature, video / model (m per 1e-3) | 0.32 / 0.34 | 0.30 / 0.31 | 0.17 / 0.17 |
| Same at x = 0 | 0.40 / 0.40 | 0.39 / 0.37 | 0.23 / 0.24 |
| Same at x = 0 vs the model's road curvature | 0.39 / 0.38 | 0.37 / 0.35 | 0.24 / 0.24 |
| Slow variation at 12 m (20 s detrend): corr, slope video/model | 0.95, 0.94 [0.99, 0.95] | 0.97, 0.96 [0.99, 0.96] | 0.90, 0.96 [0.97, 0.97] |
| Left line: video − model at 12 m | −0.065 m | −0.063 m | −0.072 m |
| Right line: video − model at 12 m | +0.073 m | +0.074 m | +0.086 m |
| Lane width at 12 m: video / model | 3.17 / 3.03 m | 3.35 / 3.22 m | 3.42 / 3.26 m |

Notes on the table:

- **Near-straight** = both curvature references < 5e-4 1/m (route 6: 1726 frames; route 7: 1978; route 8: 3914).
- **Curvature references:**
  - "Kalman" = `liveLocationKalman` yaw rate / v, 2 s mean. It is independent of the lane model, though it is the curvature the car drove.
  - The model's road curvature = the lane centre at 15–60 m, as in the lane-drift analysis.
  - They correlate 0.965–0.969.
- **Curve-slope geometry:** the slope at 12 m is lower than at x = 0 by 0.05–0.07. That matches the geometry: the lane centre 12 m ahead in a curve is displaced by κx²/2 = 0.072 m per 1e-3 toward the inside.
- **By curvature bin** (p at 12 m, sharpest bins |κ| > 1e-3, model road curvature), video vs model:
  - route 6: −0.455 / −0.483 (left) and +0.218 / +0.238 (right);
  - route 7: −0.574 / −0.583 and +0.121 / +0.157;
  - route 8: −0.272 / −0.277 and +0.085 / +0.090.
- **Yaw calibration:** the mean heading relative to the lane in the calibrated frame is ≈ 0 on straights. Video c(12) − c(0) is −0.001 / −0.011 / −0.006 m, so any yaw-calibration offset relative to lane-parallel travel is ≲ 0.05°. The left bias is not a heading artefact.

Logs: `E:\DragalPilot\logs\vid-compare-v2-*.log`, `vid-summary-v2-*.log`; JSON `E:\DragalPilot\analysis\g70-video-lane-20261004\vid_compare.json`. v1 outputs: `analysis\...\v1\`.

## Interpretation

- **The left bias is real relative to the paint** (confirmed observation in the calibrated frame, ±1 cm).
  - On these highway stretches the device runs 0.14–0.20 m left of the lane centre.
  - With the device mounted at the windshield centre (user, ±3 mm), the car does as well. This assumes the camera is centred in the device and the windshield centre is on the car's centreline; neither was verified.
- **The model doesn't mis-perceive the lane centre.** Its lines sit inboard of the paint by nearly equal amounts. That looks like a line-definition convention (lines placed near the inner edge of the paint) rather than an error. The resulting centre offset (+0.4–0.7 cm) is two orders of magnitude smaller than the bias.
  - So the bias and the curve-inside shift are **the model's path choice** (hypothesis from session 4, now with the perception step independently checked).
  - Session 4 had already shown that the controller executes that plan.
- **The curve-inside shift is real** and of the size reported earlier (0.23–0.40 m per 1/1000 m at the device). Route 8 (new tune, different roads) is smaller, as before.
- **Not established:** whether a human drives the same way on these roads. Session 4b's same-loop comparison (low-speed roads) found the human 5–8 cm left of centre, and engaged −4…+1 cm, where lines are confident ([low-speed findings](2026-10-04-g70-lowspeed-drives.md)). No manual highway reference exists for routes 6–8.

## Low-speed engaged windows: visual context (observation)

- **Source:** the 24 engaged 9–16 m/s windows of `E:\DragalPilot\logs\lowspeed-windows-20261004.log` (routes 4, 6–9).
  - For each, 4 frames (start, 1/3, 2/3, end) with the model's lane lines (thickness by probability) and its lead are in `E:\DragalPilot\analysis\g70-video-lane-20261004\lowspeed_windows\`.
  - Window statistics are in `logs\vid-windows-20261004-152107.log`.
  - Time origin verified: the window mean speeds match the listed ones on all 24.
- **Frames:** exact by frame id. The descriptions are from 4 frames per window, so brief events between them can be missed.

| Route, local time (EDT) | Length | Scene | Lane lines (both > 0.7) | Lead (p > 0.5) | Steer pressed |
|---|---|---|---|---|---|
| R4 00:37:25 | 15.8 s | Night, residential street, no markings | 0% | none | 0% |
| R4 00:37:53 | 5.1 s | Night, two-lane road, double yellow + edge line, accelerating | 99% | none | 16% |
| R4 00:39:13 | 3.1 s | Night, approaching an intersection: yellow cross-hatched median, construction barrels, crosswalk at the end | 85% | none | 0% |
| R4 00:43:37 | 4.3 s | Night, slowing toward a signal; white chevron hatching on the right, turn arrow | 93% | 38%, ~63 m | 0% |
| R4 00:43:51 | 4.4 s | Night, leaving an intersection (no markings inside it), then a left curve | 53% | none | 10% |
| R4 00:44:16 | 6.1 s | Night, approaching an intersection: hatching, pavement text, lines vanish; driver input at the end | 27% | none | 4% |
| R4 00:44:27 | 4.0 s | Night, just after the turn: lines lost, then a confident double yellow | 40% | none | 0% |
| R6 10:02:14 | 3.4 s | Pulling away from a green light across a crosswalk, divided arterial | 59% | 100%, ~58 m | 0% |
| R6 10:03:34 | 4.2 s | Crossing an intersection close behind a pickup; lines bend toward the lead | 0% | 100%, ~13 m | 0% |
| R7 10:06:39 | 3.8 s | Slowing toward a signal; a left-turn bay with hatching opens on the left | 75% | 100%, ~52 m | 0% |
| R7 10:07:14 | 7.1 s | Pulling away from a signal behind an SUV, pickup alongside; lines bend toward the lead early | 54% | 100%, ~14 m | 0% |
| R7 10:08:50 | 3.9 s | Pulling away from a green light, crosswalk, divided road | 76% | none | 0% |
| R7 10:09:10 | 6.9 s | Lane split/taper on the right, then slowing toward a signal | 46% | none | 33% |
| R7 10:10:36 | 6.2 s | Tight left turn (desired curvature up to 0.035), no lines in the turn, then a work-zone road | 35% | none | 0% |
| R7 10:23:12 | 9.5 s | Two-lane road with double yellow + yellow hatching, left curve, following an SUV | 65% | 100%, ~17 m | 3% |
| R7 10:23:36 | 8.9 s | Following into a curving junction/roundabout; lines drop at the end | 65% | 100%, ~23 m | 0% |
| R8 11:41:48 | 14.1 s | Residential street, curbs, no markings | 0% | none | 0% |
| R8 11:42:14 | 4.4 s | After a turn onto a rural two-lane road; gore on the right at first, then double yellow | 79% | 64%, ~60 m | 7% |
| R8 11:42:51 | 5.9 s | Finishing a right turn onto a rural road (lateral active from the 2nd frame), then confident lines | 38% | 31%, ~52 m | 0% |
| R8 11:57:39 | 14.0 s | Wet multi-lane arterial, slowing for a signal behind traffic; left-turn bay opens; weak lines through the intersection | 66% | 100%, ~36 m | 0% |
| R8 12:01:29 | 14.5 s | Arterial, following an SUV through a signalized intersection; left-turn bay with hatching opens | 60% | 100%, ~18 m | 0% |
| R9 12:21:39 | 10.3 s | Pulling away from a signal behind an SUV onto a two-lane road with yellow hatching; weak lines | 17% | 100%, ~14 m | 0% |
| R9 12:22:42 | 4.6 s | Slowing to turn left at an intersection (blinker on); lines vanish inside it | 26% | none | 0% |
| R9 12:22:55 | 17.4 s | Residential street, no markings | 0% | none | 0% |

Takeaways:

- None of these windows is the steady low-speed driving or stop-and-go the complaint is about. They are transitions: intersections, turns, turn-bay openings, and unmarked streets.
- Where a close lead and weak lines coincide (R6 10:03:34, R7 10:07:14, R9 12:21:39), the model's lane lines bend toward the lead vehicle. That fits a plan that follows the lead when the lines are weak. It's a hypothesis from video only, not quantified.
- Left-turn bays opening on the left recur (R7 10:06:39, R8 11:57:39, R8 12:01:29). Session 4b found its largest engaged-vs-human difference at such a place.

## Limitations

- **Shared camera and calibration.** The video measurement uses the same camera, intrinsics and calibration as the model. It checks the model's **perception of the paint**, not the calibration or the camera's lateral position in the car.
  - The heading test above bounds a yaw-calibration offset to ≲ 0.05°.
  - The camera's lateral position within the device and the device's position relative to the car's centreline are not measured.
- **Flat-road plane.** Lane widths and curve slopes inherit any height/scale error (unverified). The centre is robust to it.
- **Highway comparison only:** daytime, routes 6–8, the eligible frames where the model's lines are confident. Low-speed and night roads were described visually, not measured.
- **Detector tuning.** The v2 detector was tuned after a hand check on the same data (exploratory). The conclusions did not change between v1 and v2.
- **Hand check.** One reader (Claude), 14 instances with paint in the row; dash-gap values can't be checked at 12 m.
- **x = 0 values** are extrapolated from ≥ 6.5 m in both methods.

## Scripts and outputs

- Scripts: `E:\DragalPilot\scratch\wsl\vid\` — `vid_probe.py`, `vid_log_extract.py`, `vid_common.py`, `vid_detect.py` (v2; v1 kept as `vid_detect.v1.py.bak`), `vid_measure.py`, `vid_compare.py`, `vid_summary.py`, `vid_overlay.py`, `vid_debug.py`, `vid_validate_pick.py`, `vid_seam_probe.py`, `vid_rstats.py`, `vid_prof.py`, `vid_windows.py`; runners `run_py.sh` (checkout venv), `run_vid.sh`, `run_measure_hw.sh`, `setup_vid_venv.sh`.
- Environment: a separate WSL venv `~/venvs/vid` (Python 3.12.13, opencv-python-headless 5.0.0.93, numpy 2.5.3, scipy 1.18.1, matplotlib 3.11.2; installed with uv; log `logs\vid-venv-setup-*.log`). The checkout's `.venv` was not changed. ffmpeg 6.1.1 (apt).
- Log extraction used the WSL clone at `82f58a9a8c`.
- Outputs: `E:\DragalPilot\analysis\g70-video-lane-20261004\` (`*.log.npz`, `*.hw.vid.npz`, `vid_compare.json`, `overlays/`, `debug/`, `lowspeed_windows/`, `validation_*`). Logs: `E:\DragalPilot\logs\vid-*.log`.

## Follow-up (session 7, 2026-10-04): the weave band in the video

The comparison above uses a 20 s moving-average detrend, which passes everything above ~0.05 Hz. It is dominated by the motion below 0.2 Hz and does not isolate the ~3 s weave. This band-limited check reuses the outputs above, read-only.

**Method** (`E:\DragalPilot\scratch\wsl\vid\vid_weave_band.py`; log `logs\vid-weave-band-20261004-165245.log`; output `analysis\g70-video-weave-band-20261004\weave_band.json`):
- detector-ok eligible highway frames (5 Hz), routes 6, 7 and 8;
- gaps ≤ 1 s interpolated, runs ≥ 30 s;
- lane centre at 12 m; 4th-order zero-phase band-pass 0.2–0.6 Hz;
- Welch cross-spectra with 12.8 s segments;
- noise floor = band-passed lane-width std / 2 (an upper bound).

An earlier run in this check had an un-normalised spectral RMS and was rerun; coherence, gain and phase were unaffected.

| Band | Coherence video–model | Gain video/model | Phase | RMS video / model (cm) |
|---|---|---|---|---|
| 0.2–0.3 Hz | 0.88–0.96 | 0.96–1.00 | ≤ 1.5° | 2.2–2.6 / 2.2–2.5 |
| 0.3–0.4 Hz | 0.72–0.87 | 1.00–1.07 | ≤ 4° | 1.6–2.2 / 1.3–1.9 |
| 0.4–0.6 Hz | 0.40–0.75 | 0.91–1.09 | 5–15° | 1.0–1.2 / 0.7–0.9 |

- **The 0.2–0.4 Hz lane-position motion at highway speed (~33 m/s) is confirmed independently of the model's perception** (observation). The 0.2–0.6 Hz band std is 2.5–3.2 cm in both methods, and the 90th-percentile envelope 5–7 cm. Above 0.4 Hz the agreement falls toward the video noise floor (≤ 1.7–2.0 cm).
- **Limits:**
  - daytime highway only;
  - shared camera and calibration;
  - this confirms the motion, not its cause.
- Extrapolating to x = 0 adds noise (route 8 coherence drops sharply), so 12 m is used.
