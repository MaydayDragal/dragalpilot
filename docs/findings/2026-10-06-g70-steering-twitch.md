# G70 2024: steering-wheel "twitchiness" on straight roads (2026-10-06, session 10)

**Status:** log and video analysis done (offline).
- The twitch is a hold-and-jump wheel motion that the video confirms. The controller's P and friction-ramp terms generate most of it.
- It got worse at highway speed after the torqued restore.
- Mechanism (stick-slip) is a hypothesis.
- No change proposed yet; options in §7.
- QA: not applicable (analysis only).

**Complaint (user, 2026-10-06, after riding along):** the primary lateral complaint is twitchiness of the steering wheel, more precisely than "weaving" (which also happens). Even on a straight road with a straight lane and clear lane lines, the wheel seems to be constantly correcting or overcorrecting in small amounts.
- The user bookmarked moments on the device.
- The user filmed the wheel at those times (phone videos, filed with routes `0x22` and `0x23`).

**Scope:** offline analysis of existing rlogs and videos. No device access, no code change. Earlier work (sessions 4b–7) studied the 0.3–0.6 Hz weave. This study adds the faster, small corrections.

Evidence labels:
- **Source fact:** file + revision `c027a92857`. The lateral path is identical to `82f58a9a8c`; `c027a92857` changed only soundd/micd/selfdrived audio files.
- **Observation:** rlog / video, with route and time.
- **Hypothesis.**

## 1. Inputs

| Item | Detail |
|---|---|
| Routes, era E4 (restored torqued) | `0x1e`–`0x25`, 2026-10-06, `c027a92857`. torqued valid; applied laf 3.55–3.69, friction 0.081–0.085, offset −0.02…−0.07 |
| Routes, era E3 (post-wipe) | `0x18`–`0x1d`, 2026-10-05, `82f58a9a8c`. torqued not valid, so the offline 4.0 / 0.07 / 0 |
| Routes, era E2 (tune, torqued learning) | `8`–`0x16` |
| Routes, era E1 (original port tune 2.7 / 0.11) | `3`–`7` |
| Bookmarks (`userBookmark`) | route `0x22` at 553.4 s (18:17:36) and 629.7 s (18:18:52); route `0x23` at 209.3 s (19:23:01) and 261.7 s (19:23:53) |
| Wheel videos | Phone, 3840×2160, 30 fps, iPhone `creationdate` (EDT, 1 s resolution). They are copied with sha256 into `videos/user-phone-wheel/` of their route; the originals stay in `C:\Videos`. |

The videos, with their approximate route times (before the alignment in §4):

| Video | Times | Route | Route time |
|---|---|---|---|
| `1815 first` | 18:15:13, 7.8 s | `0x22` | 410–418 s |
| `1815 second` | 18:15:27, 17.2 s | `0x22` | 424–441 s |
| `1817` | 18:17:33, 17.6 s | `0x22` | 550–568 s |
| `1922` | 19:22:59, 30.1 s | `0x23` | 208–238 s |
| `1923` | 19:23:54, 30.7 s | `0x23` | 263–293 s |

## 2. The lateral path on this car (source facts, `c027a92857`)

1. **Model → plan:** the desired curvature comes from `modeld` (default model) through controlsd.
2. **Controller:** `LatControlTorqueV0` (`openpilot/sunnypilot/selfdrive/controls/lib/latcontrol_torque_v0.py`), 100 Hz, in lateral-accel units.
   - **Setpoint:** `lat_delay · desired_lateral_jerk + expected_lateral_accel` (L91). `expected` is the request from `lat_delay` ago, and the jerk is (current request − expected)/`lat_delay`. So with that delay definition the setpoint equals the *current* request desired_curvature·v².
   - **Measurement:** the steering angle converted to lateral accel through the vehicle model (L74, L87).
   - **Error** = setpoint − measurement (L92).
   - **Feedforward** `f` = request − roll·g − latAccelOffset + `get_friction(error)` (L96–100).
   - **P** = KP(v)·error, with KP 1.0 at ≥ 30 m/s, 2.0 at 15 m/s, 3.5 at 10 m/s (L25–29). **I** uses KI 0.3. **D** = 0.
   - **Output torque** = (P + I + f) / latAccelFactor (L108; `interfaces.py` L215–220).
3. **Friction term:** `get_friction` (`opendbc_repo/opendbc/car/lateral.py` L204–212) is a linear ramp from −friction·laf to +friction·laf over an error of ±0.3 m/s² (`FRICTION_THRESHOLD`). For this car the deadzone is 0 (`configure_torque_tune` default `steering_angle_deadzone_deg=0.0`, `interfaces.py` L256).
   - In torque units its slope near zero error is friction/0.3: 0.27 per m/s² with the restored friction 0.081, 0.23 before.
   - The P slope at highway speed is 1/laf: 0.27–0.28 now, 0.25 before.
   - **So near zero error, the friction term about doubles the controller's proportional torque gain at highway speed.**
4. **Output stage (Hyundai CAN):** `torque · STEER_MAX` with STEER_MAX 384, rate-limited to +3 / −7 counts per 10 ms, plus driver-torque limits (`hyundai/carcontroller.py` L87–88; `values.py` L21–23, L57). Sent as `CR_Lkas_StrToqReq` in LKAS11 at 100 Hz. The EPS executes it.

## 3. Analysis plan (written before computing any twitch metric)

### Questions

- **Q1:** On straight, clean, engaged driving, how much small, fast steering motion is there? Is it more than in manual driving on comparable roads and speeds?
- **Q2:** Which layer creates it? Model plan (setpoint), controller feedback (P, friction term), integrator, or actuator/EPS/road (angle motion without matching command)?
- **Q3:** Did it change between parameter eras, in particular E3 → E4 (the restore raised friction and lowered laf)? This is observational only; roads, speeds and conditions are not controlled.
- **Q4:** Do the logged signals reproduce what the video shows (video agent, §4)?

### Definitions

- **Straight-clean engaged sample** (100 Hz controlsState grid):
  - lateral control active;
  - no steering override within ±1 s;
  - no blinker within ±3 s;
  - not saturated;
  - both lane lines with probability > 0.5 (modelV2, zero-order hold);
  - road curvature |κ| < 2.5e-4 1/m (radius > 4 km), where κ = carState yawRate / v smoothed with a centred 4 s moving average (from the car's yaw sensor, not from the model);
  - inside a contiguous qualifying run ≥ 8 s, with 2 s trimmed at each end after band filtering.
- **Straight-clean manual sample:** the same, but lateral control not active and the vehicle moving under the driver. A human-input baseline, not a target.
- **Speed bands:** L 9–15.6 m/s (20–35 mph), M 15.6–24.6 m/s (35–55 mph), H > 24.6 m/s (55+ mph).
- **Frequency bands** (zero-phase 4th-order Butterworth band-pass on the whole route, then statistics over the selected samples):
  - **T (twitch) 0.7–4 Hz** (chosen before looking, from the complaint: small, frequent corrections, faster than the weave);
  - **W (weave) 0.2–0.7 Hz**, for continuity with sessions 4b–7.
  - Spectra (Welch, 8 s segments) are reported too, so that the band choice can be checked.

### Metrics, per era × speed band × mode (engaged / manual)

1. Steering angle (`carState.steeringAngleDeg`): T-band and W-band RMS (deg).
2. Micro-reversals: local extremes of the 4 Hz low-passed angle that differ from the previous extreme by ≥ 0.3°, per minute.
3. Steering rate (`steeringRateDeg`): RMS (deg/s).
4. Torque command (`carOutput.actuatorsOutput.torque`): T-band RMS, and sign changes of its T-band component per minute (engaged only).
5. Vehicle lateral response: yawRate·v, T-band RMS (m/s²): what occupants feel.
6. **Attribution (engaged)**, all in torque units (component / laf).
   - The output is split as P + I + f_model + f_friction:
     - f_friction is recomputed from the logged error with `get_friction` and the applied laf/friction;
     - f_model = logged f − f_friction.
     - Reconstruction residual vs the logged output is reported.
   - For each component: its share of the T-band variance of the sum, var_T(c)/var_T(sum), and its correlation with the sum.
   - The error's T-band content is split between setpoint and measurement: var_T(setpoint), var_T(measurement), and their correlation.
7. Command → angle coherence in the T band (engaged): is the angle motion driven by the command?

### Attribution criteria (fixed now)

- **Model/plan layer (H1):** the setpoint carries most of the error's T-band variance (var_T(setpoint) > var_T(measurement)), **and** f_model + P-from-setpoint is the largest share of the command's T-band variance.
- **Controller feedback (H2):** var_T(measurement) ≥ var_T(setpoint) **and** P + f_friction carry > 50% of the command's T-band variance. Friction is named the main contributor if f_friction alone has the largest share.
- **Actuator/EPS/road (H3):** command → angle coherence in the T band < 0.5 while the angle's T-band RMS is above the manual baseline.
- If none applies, the result is reported as mixed or undetermined.
- These criteria diagnose. They do not justify a change by themselves; any change gets its own pre-registered offline test (as in session 7) and then the user's approval.

## 4. Video: wheel angle measured from the phone clips (observation)

A background agent did this; the coordinator checked `summary.json` and the `1815_second` plot. Scripts: `E:\DragalPilot\scratch\wsl\vidwheel\`. Outputs and method README: `E:\DragalPilot\analysis\g70-twitch-20261006\wheel-video\`. Logs: `logs\s10-vidwheel-*.log`.

- **Method:**
  - Frames at 1920×1080.
  - Phone motion is removed by tracking points on the cluster, hood and centre stack (wheel masked) and stabilising with a homography.
  - Wheel angle = the hub's rotation against a mid-clip reference (dense image alignment).
  - Frames with low match quality are rejected: arm over the hub at the start of `1817` and `1922`, an overpass in `1815 second`.
- **Accuracy:**
  - Synthetic rotations of 0.1–3° are recovered with 0.008–0.018° RMS error (worst 0.11°).
  - High-frequency noise is 0.02–0.06°.
  - The image-plane angle is a projection, so its scale is calibrated against the log: 1.2–1.6 video-deg per logged deg in the fast band.
- **Alignment:** `creationdate` is the clip start. Offsets are −0.11 to +1.02 s, consistent with 1 s truncation plus the ±1 s route-start uncertainty. The "clip end" hypothesis has no peak.

| Clip | Aligned t0 (route s) | r overall | r fast (0.7–4 Hz) | r slow | Note |
|---|---|---|---|---|---|
| `1815 first` | 410.02 | 0.91 | 0.75 | 0.91 | short clip |
| `1815 second` | 423.89 | 0.90 | **0.90** | 0.86 | video fast motion 0.14° RMS (log units) vs 0.13° logged |
| `1817` | 550.28 | 0.85 | 0.49 | 0.83 | from 3.9 s (arm over the hub before) |
| `1922` | 208.58 | 0.71 | failed | 0.83 | dark, large phone motion: the fast band is unusable |
| `1923` | 263.18 | 0.78 | 0.30 | 0.82 | logged fast motion 0.027° RMS ≈ measurement noise: inconclusive |

- **Q4: where measurable (the three route `0x22` clips), the visible small fast wheel motions are in the logged steering angle at about the same size.**
  - The video shows the same **hold-and-jump** motion as the log (`1815_second_wheel_vs_log.png`, zoom 433.5–438.5 s): the wheel holds, then moves 0.3–0.6° within about 0.1–0.2 s.
  - So the logged angle is an adequate measure of the twitch, and the jumps are real wheel motion, not a sensor artifact.
  - The video shows no sign of extra fast wheel motion that the sensor misses. It cannot resolve motion below about 0.05°.
- The route `0x23` clips can't confirm or rule out fast motion: logged motion is near the video noise floor in `1923`, and `1922` failed. The logs rate both as calm (§5.6).
- **Limitation:** slow-band and overall scales vary (1.5–3.3), probably from phone sway and parallax that correlate with the car's motion. Slow-band video amplitudes are not physical wheel angles.

## 5. Results (logs)

Tools in `E:\DragalPilot\scratch\wsl\sng\`: `s10_twitch.py` (§3 metrics), `s10_twitch_table.py`, `s10_spectra_plot.py`, `s10_window_plot.py`, `s10_jumps.py` (exploratory), `s10_check_yaw.py` (input checks). Run with `run_s10_vid.sh` (~/venvs/vid: Python 3.12.13, numpy 2.5.3, scipy 1.18.1). Outputs: `E:\DragalPilot\analysis\g70-twitch-20261006\logs\`; logs: `E:\DragalPilot\logs\s10-twitch-*.log`.

### 5.1 Deviations from the plan (found while checking inputs, before reading results)

- **No yaw rate:** `carState.yawRate` is 0 on every sample on this car (`s10_check_yaw.py`).
  - Road curvature therefore uses `controlsState.curvature`, smoothed with a centred 4 s moving average. That is the measured curvature from the steering angle through the vehicle model, not the model plan.
  - The yawRate·v response metric (§3, metric 5) is dropped.
- **Micro-reversal counter:** the first version returned 0. It was fixed and tested (0.5 Hz sine → 60 reversals in 60 s) before any reading.
- **Steering rate:** `steeringRateDeg` RMS is about 4 deg/s in every case. This car's rate signal is coarsely quantized (about 4 deg/s steps), so metric 3 is uninformative and not used.
- **Added after the plan:** a by-source split. Because |error| < 0.3 m/s² in 98–100% of samples, the friction ramp is linear and the command splits exactly into a setpoint path, a measurement path and I. Its reconstruction residual is ≤ 0.1% of the variance.
  - setpoint path = (KP + s_f + 1)/laf × setpoint, where s_f = friction·laf/0.3;
  - measurement path = (KP + s_f)/laf × measurement.

### 5.2 Decomposition check (observation)

- The friction term rebuilt from the logged error with the applied laf/friction matches the logged `f` minus the model feedforward on every engaged route (median |Δ| ≈ 1e-8, p99 ≤ 0.007 m/s²).
- The rebuilt output P + I + f equals the logged output to ≤ 1e-7 on all E3/E4 routes. A few E1/E2 routes have larger p99 residuals (≤ 0.44, at limits/saturation, which the selection excludes).
- So the V0 reading in §2 is confirmed on this car, and the applied parameters per era are as stated (`decomposition_check.json`).

### 5.3 Metrics, straight-clean engaged vs manual (`twitch_table.txt`)

| Era/band | Straight s | Angle RMS T (°) | Angle RMS W (°) | Reversals ≥ 0.3°/min | Jumps ≥ 0.3° in 150 ms /min | Wheel still | Torque RMS T | Cmd→angle coherence T |
|---|---|---|---|---|---|---|---|---|
| E1 / H (port 2.7 / 0.11) | 729 | **0.134** | 0.107 | 42 | 48 | 46% | 0.0348 | 0.59 |
| E2 / H (4.0 / 0.07) | 1,138 | 0.055 | 0.129 | 16 | 16 | 68% | 0.0156 | 0.44 |
| E3 / H (4.0 / 0.07) | 1,154 | 0.054 | 0.121 | 16 | 19 | 66% | 0.0157 | 0.43 |
| **E4 / H (restored 3.63 / 0.083)** | 1,364 | **0.080** | 0.141 | **27** | **30** | 57% | **0.0204** | 0.49 |
| E3 / M | 150 | 0.055 | 0.189 | 15 | 20 | 70% | 0.0100 | 0.47 |
| E4 / M | 270 | 0.050 | 0.173 | 18 | 24 | 62% | 0.0112 | 0.46 |
| Manual / H (E2–E4, 6–82 s each) | — | 0.15–0.24 | 0.46–1.45 | 29–48 | 69–91 | 20–36% | — | — |

- **Q1:**
  - On straight highway, the engaged wheel makes small, fast moves. With the restored parameters it reverses by ≥ 0.3° about every 2 s (27/min) and jumps ≥ 0.3° within 150 ms about 30 times a minute.
  - The amplitudes are small: 0.08° RMS in 0.7–4 Hz, with individual jumps of 0.3–0.6°.
  - Manual driving has *more* fast angle motion: that is the driver's own hand input, which the driver does not perceive as twitch. So "more than manual" is **not** what distinguishes the complaint. What distinguishes it is that the wheel moves by itself, in hold-and-jump steps (5.4).
- **Q3 (observational):** at highway speed, E3 → E4 shows:
  - angle T-band RMS +48%;
  - reversals +64%;
  - jumps +59%;
  - torque T-band RMS +30%.

  The proportional torque gain rose by 13% (setpoint path 0.74 → 0.84, measurement path 0.49 → 0.56 per m/s²), and E1, with the highest gain (1.11 / 0.74), is about twice E3.
  - At 35–55 mph the change is small (angle −9%, reversals +18%, jumps +16%).
  - Roads, days and possibly drivers differ between eras.

### 5.4 Spectra and the hold-and-jump pattern (`spectra_H.png`, `spectra_M.png`, `window_1815_second_428.png`)

- **Setpoint (model request) spectra are the same in E2, E3 and E4**: the excitation from the model did not change.
- **Measurement and steering-angle spectra rise at 0.7–2 Hz with the loop gain:** E3 < E4 < E1, and E1 has a clear resonance hump at 1–2 Hz. So the extra fast motion in E4 and E1 is generated in the feedback loop, not in the model input.
- **Time series, `1815 second` window** (route `0x22`, 428–438 s, 77 mph, straight, engaged, no override):
  - The steering angle holds still for 0.5–1.5 s, then jumps 0.3–0.6° within about 100 ms, then holds again.
  - The torque command ramps up during each hold until the wheel breaks free, and reverses right after the jump. The cycle repeats every 1.5–2 s.
  - The P term and the friction term are nearly identical traces of the same size (about ±15–25 counts of 384 each). Together they carry the fast part of the command; the model feedforward is smoother.
  - **Hypothesis:** this is a stick-slip hunting cycle between static friction in the steering system and the controller's error-proportional torque. It is P plus the friction ramp, which near zero error doubles the proportional gain at highway speed (§2). Each break-free jump overshoots the setpoint and flips the error, so the next ramp starts in the other direction. That would be the visible twitch.

### 5.5 Attribution against the pre-registered criteria (engaged, straight-clean)

| Era/band | Term shares of torque T variance P / I / f_model / f_friction | By source: setpoint / measurement | var_T setpoint vs measurement (m²/s⁴) | Criterion met |
|---|---|---|---|---|
| E1 / H | 0.42 / 0.00 / 0.16 / 0.41 | 0.47 / 0.54 | 7.4e-4 < 1.8e-3 | **H2** (controller feedback) |
| E2 / H | 0.39 / 0.00 / 0.25 / 0.36 | 0.74 / 0.26 | 4.0e-4 > 3.2e-4 | **H1** (model/plan) |
| E3 / H | 0.39 / 0.00 / 0.25 / 0.36 | 0.74 / 0.26 | 3.8e-4 > 2.9e-4 | **H1** |
| E4 / H | 0.39 / 0.00 / 0.22 / 0.39 | 0.66 / 0.34 | 5.0e-4 < 5.8e-4 | **H2** |
| E3 / M | 0.50 / 0.00 / 0.21 / 0.29 | 0.73 / 0.27 | 1.1e-4 > 8.7e-5 | H1 |
| E4 / M | 0.48 / 0.00 / 0.20 / 0.32 | 0.71 / 0.29 | 9.9e-5 > 7.5e-5 | H1 |

- **H3** (actuator/road, with the angle above the manual baseline) is met nowhere: the engaged angle is below manual everywhere.
- **Reading (mixed, by the pre-registered rule):**
  - In every era the **P term and the friction term carry 75–83% of the command's fast variance**, in about equal halves at highway speed.
  - The model setpoint's small fast jitter is the main *input* at moderate gain (E2/E3, and E4 at 35–55 mph).
  - At the higher gains (E4 at highway, E1) the measurement's own fast motion exceeds the setpoint's: the loop generates it (H2).
  - The input did not change between eras (5.4); the loop gain did. The evidence therefore points at the **controller's proportional path, P plus the error-driven friction ramp, interacting with steering friction**, as the layer that turns small model jitter into visible twitch. The higher torqued friction and lower laf since the restore made it worse at highway speed.
  - Status: a supported hypothesis, not a verified cause. There is no closed-loop test yet (§7).

### 5.6 Video windows (approximate alignment; `video_windows.json`)

| Clip | Route time | v (mph) | Angle RMS T (°) | Reversals/min | Torque RMS T | Setpoint/measurement var_T |
|---|---|---|---|---|---|---|
| `1815 first` | `0x22` 410–418 s | 78 | 0.110 | 23 | 0.021 | 0.93 |
| `1815 second` | `0x22` 424–441 s | 77 | 0.156 | 52 | 0.032 | 0.53 |
| `1817` | `0x22` 550–568 s | 77 | 0.143 | 44 | 0.026 | 0.40 |
| `1922` | `0x23` 208–238 s | 75 | 0.047 | 12 | 0.021 | 2.58 |
| `1923` | `0x23` 263–293 s | 74 | 0.028 | 8 | 0.015 | 2.83 |

- Route `0x22` clips are among the twitchiest stretches on record: 2× the E4 highway average, and loop-dominated (setpoint/measurement < 1).
- Route `0x23` clips are calmer than average by these metrics, and setpoint-dominated.
- The windows above use the approximate starts. The video alignment (§4) moved them by ≤ 1.02 s, which does not change the picture.
- Video check (§4): the `0x22` motion is visible on camera and matches the log.

## 6. Conclusions (status: supported hypothesis; no closed-loop or on-car test yet)

1. **The twitch is real wheel motion and the logs capture it.** It is a hold-and-jump pattern: holds of 0.5–1.5 s, jumps of 0.3–0.6° within about 0.1–0.2 s, repeating every 1.5–2 s on straight highway. Video confirms it.
2. **Layer:** the controller's proportional path generates most of it. P and the error-driven friction ramp carry 75–83% of the command's fast variance, about equally at highway speed. The model's request supplies a small, unchanged excitation.
   - **Hypothesis for the mechanism:** stick-slip between static friction in the steering and that proportional torque. The friction ramp (±friction·laf over only ±0.3 m/s² of error, deadzone 0) about doubles the proportional gain near zero error at highway speed.
3. **The restore made it worse at highway speed (observational):** angle jumps +59%, reversals +64%, fast angle RMS +48%. The proportional gain rose 13% (friction 0.070 → 0.083, laf 4.0 → 3.63). The original port tune (2.7 / 0.11, gain +50%) was about twice as twitchy as E3. The three eras form a gain-ordered series, consistent with (2).
4. **The weave (0.2–0.7 Hz) and the twitch share a loop.** The torque spectrum peaks at 0.4–0.5 Hz. The twitch is the fast edge of the same hunting cycle (jumps) plus the 1–2 Hz hump that grows with gain.

## 7. Options (none is authorized; each needs a pre-registered offline test, then the user's approval for any device change)

- **(a) Offline closed-loop model with steering stick-slip.**
  - The session 6 plant is linear and overdamped, so it cannot reproduce hold-and-jump.
  - Identify a steering friction model (static/Coulomb friction, breakaway torque, jump size) from these logs.
  - Validate it on the three-era gain series: it must reproduce the jump rate and the 0.7–2 Hz hump ordering E3 < E4 < E1.
  - Then test candidate changes offline. **Prerequisite for (c)–(e).**
- **(b) Quick on-car A/B, with no code change.** sunnypilot's existing override params (`EnforceTorqueControl` + `TorqueParamsOverrideEnabled`, `TorqueParamsOverrideLatAccelFactor` / `TorqueParamsOverrideFriction`; `latcontrol_torque_ext_override.py`) set laf/friction instead of torqued's.
  - For example, return to the E3 values (4.0 / 0.07) and compare the twitch on the same road.
  - This is a device param change plus a restart (`EnforceTorqueControl` is read at init). It needs §6 authorization and measurement on the same road in both settings.
- **(c) Car-scoped friction-term change:** a non-zero `steering_angle_deadzone_deg` for GENESIS_G70_2024 (an existing `configure_torque_tune` argument; no other car in this checkout uses it), or a wider ramp. This needs (a) first.
- **(d) Lower friction alone** (cap torqued's friction, or override it). This needs (a) or (b).
- **(e) Lower highway KP:** session 7 tested KP schedules for the weave and none passed. It would need re-testing against twitch criteria with (a).

## 8. Limitations

- **The era comparison is observational:** different days, roads and possibly drivers, and only the straight filter is matched.
- **Small samples:** few straight-clean samples at 20–35 mph (26–68 s) and small manual baselines (6–106 s per cell).
- **Straightness** is judged from steering-angle curvature: the car reports no yaw rate.
- **Sensors:** the steering angle has 0.1° resolution, and the rate signal is unusable.
- **No closed-loop evidence:** the stick-slip mechanism is a hypothesis.
- **Perception:** "twitchy" is a perception. These metrics measure wheel motion and command, not what occupants feel.
