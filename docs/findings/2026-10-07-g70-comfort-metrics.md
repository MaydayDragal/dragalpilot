# G70 2024: comfort and twitch measures that match the driver's experience (2026-10-07/08, session 15cm)

**Status:** in progress. Offline only; no device access, no change to `dragal/custom` or the WSL clone.

**Goal (user):** "Ultimately it's driving comfort that we're trying to improve." Build and validate measures of:
- **(a)** the weave (0.2–0.7 Hz);
- **(b)** the faster twitch: the steering wheel visibly stepping by itself while the comma drives, and the comfort upset that comes with it.

Only then re-score D2C4 and the earlier candidates.

**Why** ([weave-twitch findings](2026-10-07-g70-weave-twitch-sim.md) §12.1): the project's twitch metrics (jumps/min, T, hold-steps) fire as often in manual and stock-LKA driving as under the comma. Twitch conclusions from sessions 10–13ws are provisional.

Evidence labels:
- **source fact** (file + revision);
- **observation** (rlog, route, time);
- **model result**;
- **hypothesis**.

## 0. Session start (2026-10-07 ~22:24 EDT)

- Outer `main` @ `606c36b` + uncommitted docs (sessions 8–13ws, 14lv).
- `dragal/custom` @ `89bbe60ab1`, clean. WSL clone @ `89bbe60ab1`, clean.
- `E:` UniqueId matches (`\\?\Volume{daa460f7-…}\`), write probe OK, 226.7 GB free.
- **A parallel session is running:** session 14lv (the log viewer). It has its own `claude` process since 21:01, and its Node tests read recordings in `scratch/wsl/rlogviewer`. Its work is in `tools/log-viewer/`, so there is no overlap with this analysis. This session does not touch its files.
- No device access, no SSH.

## 1. Input facts found before any comparison (source facts and observations)

**Extraction.** `scratch/wsl/cm/cm_extract.py`, checkout venv, read-only. It reads all 500 segments of the 39 dated routes in one pass into `analysis/g70-comfort-metrics-20261007/extract/seg/`.
- One row per `carState` event (100 Hz), holding the latest value of every other stream. That includes the raw LKAS11 (ours and the stock camera's), MDPS12, ESP12 and ADRV_0x51, plus controlsState, modelV2 lanes, vehicleParameters, lateralTorqueParameters and GPS.
- The raw IMU, calibration and bookmarks are kept at their own rates.
- Errors: only the usual capnp end-of-file in routes' final segments. `sunnypilot/` porcelain is 0 after the run.
- Time base: seconds from the first non-initData event after sorting by logMonoTime, the `drive_extract.py` convention (`cm_t0.py`). Check: the `0x22`/`0x23` bookmarks come out at 553.43 / 629.71 / 209.26 / 261.72 s, matching session 10's 553.4 / 629.7 / 209.3 / 261.7.

**ESP12 carries the car's own yaw rate and lateral acceleration** (correction to session 13ws).
- **Source fact** (`opendbc/dbc/generator/hyundai/hyundai_can.dbc` L1228–1242, checkout @ `89bbe60ab1`): ESP12 (0x220) has YAW_RATE (13 bits, 0.01, −40.95; deg/s) and LAT_ACCEL (11 bits, 0.01, −10.23; m/s²). The Hyundai `carstate.py` does not read them, so `carState.yawRate` is 0.
- **Observation** (`cm_checks.py`, all routes with motion; `checks/checks.json`, `logs/s15cm-checks-*`):
  - ESP12 is present at 100 Hz on bus 0 on every route.
  - Its yaw rate matches the calibrated device gyro with r −0.996…−0.9998 and a scale of 1.00–1.01 (route `0x08`: 0.96). It is 30–40 ms behind the gyro and positive for a left turn, like the steering angle (r with the angle +0.92…+0.98).
  - ADRV_0x51's yaw rate is ESP12's relayed 30 ms later (r 0.9995–0.9998).
  - So **the 13ws statement "ADRV_0x51 is the only car-side yaw-rate source" is wrong**: ESP12 is the source, ADRV relays it. The fingerprint findings get a correction note.
- LAT_ACCEL tracks v × yaw rate with r 0.85–0.97.

**Steering torques** (observation, all routes):
- MDPS12 `CR_Mdps_StrTq` (Nm, 0.01) equals `CR_Mdps_StrColTq` (= `carState.steeringTorque`) × **0.00781 Nm per raw unit** on every route (0.007805–0.007809). So the column torque has about 0.008 Nm resolution. STEER_THRESHOLD 150 ≈ 1.17 Nm.
- `CR_Mdps_OutTq` (= `steeringTorqueEps`, 0.1 units) follows our LKAS11 command 20 ms later at 0.041–0.056 units per count (r 0.67–0.93 while openpilot steers). So full scale (384) ≈ 16–21 units.

**Bookmarks** (all routes): `0x22` 553.4 and 629.7 s; `0x23` 209.3 and 261.7 s (session 10); `0x1a` 92.5 s (the session 8 grasp warning in stop-and-go traffic, not a twitch); **`0x28` 238.0 s, during the D2C4 drive. Not explained; to ask the user.**

**Stock-LKA steering is route `0x0e` (step 5 of the kickoff, inventory only).**
- Stock source = panda in `elm327`, the camera's LKAS11 with ActToi = 1, the EPS reporting ToiActive = 1, and no openpilot LKAS11 within 0.1 s.
- **369 s** (6.2 min) of the 377 s total are in route `0x0e`. The rest: `0x17` (8 s at standstill, MOCK fingerprint) and `0x18` (0.4 s).
- **Why:** `0x0e` was driven with `OpenpilotEnabledToggle = 0`, which is dashcam mode ([low-speed findings](2026-10-04-g70-lowspeed-drives.md); `card.py` L133–138). `pandaStates` reports `elm327` for the whole route. The camera's LKAS11 reached the EPS (ToiActive = 1 while it requested, with no openpilot LKAS11), so the car's own lane keeping steered whenever it was on.
- **Where:** `0x0e` is the session 4b low-speed loop. The user drove it on 2026-10-04 14:28, after:
  - `0x0a` (13:51, engaged on parts);
  - `0x0b` (14:04, engaged on the full loop);
  - `0x0c` (14:16, manual, openpilot on).

  All are the same road in the same direction (session 4b: 0b and 0e follow 0c's track for 94% / 92%).
- The stock runs are 9–28 m/s (median about 15 m/s), up to 39 s long; cruise is on in most of them.
- **So a same-road, same-day, same-driver comparison of the car's own lane keeping, the comma (E2 tune, `82f58a9a8c`) and manual driving exists in the logs.** It is the stock reference for this session.
- Its limits:
  - one lap;
  - 25–65 mph only;
  - the E2 tune (laf 4.0, friction 0.07), not E4 or D2C4;
  - no wheel video;
  - whether the driver's hands were on the wheel is not known yet. It is measured below as a covariate.

## 2. Brainstorm (written before computing any comparison)

### 2.1 What the complaint needs from a measure

- **"The wheel visibly steps by itself"** has three parts:
  - **visible wheel motion**: angle steps;
  - **by itself**: the actuator, not the driver's hands, loads the wheel;
  - **steps**: holds, then quick breakaways, i.e. stick-slip.

  Angle alone cannot see the second part. In manual driving the same angle pattern comes from the driver's hands, which the driver does not perceive as twitch. That is the likely reason §12.1's metrics fire in manual driving.
- **The comfort upset** is the vehicle motion that a wheel step causes: yaw and lateral acceleration and jerk.
  - The device IMU's lateral acceleration at 0.7–4 Hz is road-dominated (d2c4 validation §2.1.1: coherence with steering 0.06–0.33).
  - The yaw rate is much less sensitive to road input than lateral acceleration, and ESP12 now gives it at 0.01 deg/s, 100 Hz, from the car's own sensor.
- **Confounders:**
  - **Driver's hands** (hypothesis H-hands). The stock LKA is a hands-on system, so the user's experience of it is mostly with hands on the wheel. The complaint about the comma comes from riding along (session 10) and from hands-off driving. Hands damp and preload the column, so they may suppress visible stick-slip and change who loads the wheel. The column torque (0.008 Nm resolution) can show this.
  - **Viewing position:** a passenger watching the wheel vs a driver. Not measurable in logs.
  - **Road, speed, light:** handled by same-road matching and speed bands.

### 2.2 Candidate measures (each is computed the same way for every source)

| Code | Measure | Construct | Notes |
|---|---|---|---|
| W_ar | RMS of a_r = v·r (ESP12 yaw rate) in 0.2–0.7 Hz | weave, felt lateral acceleration | yaw-based, so road-robust |
| W_lane | lane-centre offset 0.2–0.7 Hz RMS (modelV2) | weave, lane position | existing measure |
| W_ang | angle 0.2–0.7 Hz RMS | weave, wheel | existing (reference) |
| J_r | RMS of v·dr/dt with r band-passed 0.7–4 Hz | twitch-band lateral jerk felt from yaw | per window |
| J_coh | the part of J_r coherent with the steering angle (pooled cross-spectra) | steering-caused twitch-band jerk | per group only |
| A_wd | ISO 2631-1 W_d-weighted RMS of a_r | standard comfort weighting | secondary |
| T | angle 0.7–4 Hz RMS | twitch, wheel (existing; not validated) | reference |
| E_step | angle ≥ 0.3° within 150 ms, per min | existing jumps (not validated) | reference |
| E_hs | hold-steps: 0.3 s within 0.1°, then ≥ 0.3° within 150 ms, per min | stick-slip by angle (not validated) | reference |
| **S_act** | hold-steps during whose hold the EPS output torque built up toward the step while the driver's column torque did not | **the wheel stepping by itself (actuator-loaded stick-slip)** | new; torque-based |
| S_drv | hold-steps with a driver column-torque build-up toward the step | driver-made steps | new |
| Δa_step, U | the lateral-acceleration change caused per hold-step (event-locked), and U = E_hs/min × mean Δa_step | comfort upset per step and per minute | new |
| hands | column torque 0.05–2 Hz RMS and the fraction of time with \|τ_c\| ≥ 0.3 Nm | covariate, not a measure | |

**Not chosen:**
- The raw IMU lateral acceleration at 0.7–4 Hz: road-dominated (§2.1.1 of the validation doc). It is reported only as ESP12 LAT_ACCEL, for reference.
- A video-based wheel measure: only 5 phone clips exist, all under the comma.
- GPS position-aligned road-input cancellation by subtraction: positions are good to only a few metres, which is too coarse for 0.7–4 Hz alignment at highway speed. Same-road matching is used for comparisons instead.

## 3. Amendment 13: pre-registration (written 2026-10-07 ~22:45 EDT, before any measure was computed on any source, window or comparison)

### 3.1 Signals (`cm_lib.py`, `~/venvs/vid`)

- r = ESP12 YAW_RATE (deg/s → rad/s), positive left. a_r = v·r; j_r = v·dr/dt (central difference).
- θ = `carState.steeringAngleDeg` (0.1°).
- τ_e = MDPS12 OutTq (0.1 units); τ_c = column torque × 0.00781 Nm.
- Lane-centre offset c = (y₁ + y₂)/2 of modelV2 lane lines 1 and 2 at their first point, where both probabilities are > 0.5 (zero-order held at 100 Hz).
- **Filters:** zero-phase 4th-order Butterworth (`sosfiltfilt`) over each contiguous data block (gaps > 50 ms split blocks). Statistics are computed over the selected samples.
- **W_d** (secondary): as Amendment 5 (a'), applied to a_r.

### 3.2 Sources and selections (per 100 Hz sample)

- **OP:** safety `hyundai`, `latActive`, our LKAS11 ActToi = 1, EPS ToiActive = 1.
- **STOCK:** safety `elm327`, the camera's LKAS11 ActToi = 1, EPS ToiActive = 1, no openpilot LKAS11 within 0.1 s.
- **MAN:** lateral not active, EPS ToiActive = 0.
- **Common exclusions:**
  - v < 9 m/s;
  - within ±3 s of a blinker;
  - OP and STOCK only: within ±1 s of `steeringPressed`.
- **Runs:** contiguous ≥ 8 s within a block, 2 s trimmed at each end for RMS statistics. Events need the whole event window inside the run.
- **Speed bands** by run median: L 9–15.6, M 15.6–24.6, H ≥ 24.6 m/s.
- **Straight:** |κ| < 2.5e-4 1/m, κ = 4 s centred mean of r/v (the car's own yaw rate now, not the steering-derived curvature). "All" = no curvature filter.

### 3.3 Event definitions

- **E_step:** `s11_plant.jumps_hold` logic (≥ 0.3° change over 15 samples; re-armed 30 samples later).
- **E_hs:** `s16_ws_holdstep.holdsteps` logic: range ≤ 0.1° over the 31 samples ending at the onset k, then |θ[k+15] − θ[k]| ≥ 0.3°; re-armed 30 samples later. The step sign is s = sign(θ[k+15] − θ[k]).
- **S_act:** E_hs events with:
  - ΔE = s·(τ_e[k] − τ_e[k−30]) ≥ **1.0** units, i.e. the EPS torque built up toward the step during the hold;
  - Δc = s·(τ_c[k] − τ_c[k−30]) < **0.1 Nm**, i.e. the driver did not.

  Sensitivity: ΔE* ∈ {0.5, 1.0, 2.0} × Δc* ∈ {0.05, 0.1, 0.2}. The conclusion must hold at all nine to count.
- **S_drv:** E_hs events with Δc ≥ 0.1 Nm.
- **Δa_step:** s·(mean a_r[k+25 … k+45] − mean a_r[k−10 … k]), the lateral acceleration 0.25–0.45 s after the onset relative to just before.
  - **Nulls:** the same at random times (uniform over the selected samples, 2,000 per group, seed 0). Two variants:
    - (i) random sign: the noise SD;
    - (ii) sign = the sign of the 0.2–0.7 Hz band of a_r's slope at that time: the bias from slow reversals, since jumps follow slow request reversals (13ws §6.4).
  - The step effect is reported as Δa_step minus null (ii).
- **U** = E_hs/min × (mean Δa_step − null (ii) mean), in m/s² per minute.
- **Event-locked averages** (ETA) of s·a_r and s·j_r over −1…+2 s are plotted per source (reported).

### 3.4 Validation (the criteria for "valid")

**V-label: the user's labelled twitchy moments, under the comma.**
- **Episodes:** the bookmarks (−15/+5 s) merged with the filmed clips:
  - `0x22`: [410.0, 441.1], [538.4, 568.0], [614.7, 634.7];
  - `0x23`: [194.3, 238.7], [246.7, 293.9].

  OP samples with v ≥ 24.6 m/s, all-road (no straight filter).
- **Reference:** the E4 routes `0x1e`–`0x25`, OP, ≥ 24.6 m/s, all-road, outside the episodes. They are cut into consecutive 30 s chunks within runs; chunks with ≥ 20 s are kept.
- **Statistic:** each episode's percentile in the reference distribution. Higher means more twitchy for twitch and comfort measures.
- **Pass:** the median of the 5 percentiles is ≥ 75 **and** ≥ 4 of 5 are ≥ 50. Under a measure unrelated to the labels, this has a chance of roughly 10%. The `0x23` episodes are kept, even though the old metrics rated them calm.

**V-stock: comma vs the car's own LKA, the same road, the same day.**
- **Data:** STOCK = `0x0e`; OP = `0x0a` + `0x0b`.
- **Restriction:** both are restricted to the road they share. A sample counts if a sample of the other source lies within 30 m with heading within 45° (GPS with a fix).
- **Pooling:** all speed bands ≥ 9 m/s, with OP reweighted to STOCK's L/M/H time shares.
- **Statistic:** the ratio OP/STOCK, with a 10 s block bootstrap 95% CI (2,000 resamples, seed 0, blocks resampled within each source).
- **Verdicts:**
  - **pass** if the CI lies above 1 (the comma higher, as the user's experience says);
  - **fail** if the point estimate is ≤ 1;
  - otherwise **not separated**.
- MAN (`0x0c` + `0x0e` without stock steering) on the same shared road is reported, with no criterion.
- For the event measures the per-minute rate is the statistic; for RMS measures, the pooled RMS.

**Verdict per measure:**
- **valid** = V-label pass and V-stock pass;
- **partly supported** = one passes and the other is not separated;
- **not valid** = either fails.

V-label and V-stock apply to the twitch and comfort measures (J_r, A_wd, T, E_step, E_hs, S_act, U). The weave measures (W_ar, W_lane, W_ang) have no twitch labels. Their check is that W_ar and W_lane agree: Spearman ρ ≥ 0.5 across the E4 OP H 30 s chunks with lane data. This is reported as consistency, not as validation against perception.

**Mechanism check (reported):** the event-locked Δa_step − null (ii) > 3 SE in the pooled OP H sample, i.e. a hold-step causes a measurable lateral motion.

### 3.5 Then (step 4), in order

1. **D2C4 re-score:**
   - B = `0x28` vs A-primary (`0x26`, `0x1e`, `0x20`, `0x22`, `0x24`), on B's road, ≥ 55 mph, straight and all, as the A/B §3.1 arms (the same road mask rule: 30 m, 45°);
   - every measure, labelled valid or not; 60 s block bootstrap CIs.
2. **Bicycle check:**
   - **Model:** opendbc's dynamic bicycle model with this car's CarParams (1905 kg, 3579 kg·m², 1.132 / 1.698 m, cF / cR 250,373 / 263,859 × stiffnessFactor) and vehicleParameters' steerRatio and angle offset, driven by the logged θ (Euler, 1 ms).
   - **Comparison** with r on E4 OP H straight runs, per band 0.2–0.7 / 0.7–1.5 / 1.5–4 Hz (8 s Welch cross-spectra): the gain and phase of measured vs modelled θ → r, and W_ar and J_r of the model's r vs the measured W_ar and J_coh.
   - **"Reproduces"** if:
     - the gain is within ±20% and the phase within ±20° in every band where the coherence is ≥ 0.5;
     - both measures are within ±25%.
3. **Candidates:** if 2 reproduces **and** a twitch or comfort measure is valid, re-rank A0, D2C4, F7d, S1, S2, MV2 and MV3 on simulated measures. The simulated θ goes through the bicycle model, which gives J_r and W_ar; the hold-steps come from the simulated angle. This step gets its own amendment before it runs.

### 3.6 Exploratory (reported as such)

- The hands covariate per source, and the measures split by hands state within OP.
- The LKAS11 non-torque fields, stock vs ours.
- The torque command's spectra, stock vs ours, on the shared road.

## 4. Results (observations from logs unless marked; focused review done, §6)

Tools in `E:\DragalPilot\scratch\wsl\cm\`:
- `cm_route.py` (per-route inputs);
- `cm_eval.py` (§3.4);
- `cm_bike.py` (§3.5.2);
- `cm_ab.py` (§3.5.1);
- exploratory `cm_eta.py`, `cm_explore.py`;
- self-tests `cm_selftest.py`: all pass. They cover hold-step, torque build-up and Δa logic on synthetic steps, the J_r scale on a sine, W_d vs ISO 2631-1 Table 3, and the run splitting.

Outputs: `analysis/g70-comfort-metrics-20261007/eval/{eval,bike_check,ab_d2c4,eta_exploratory,explore}.json`. Logs: `logs/s15cm-*`. Runner `run_cm_vid.sh` (`~/venvs/vid`: Python 3.12, numpy 2.5, scipy 1.18, numba 0.68).

### 4.1 Mechanism check: a wheel hold-step causes a measurable lateral jolt (PASS)

| OP, ≥ 55 mph | Hold-steps | Mean Δa_step (m/s²) | Null (ii) (slow-trend bias) | Null (i) SD | Effect | z |
|---|---|---|---|---|---|---|
| E2 | 584 | 0.205 | 0.059 | 0.125 | **0.146** | 26.6 |
| E3 | 560 | 0.210 | 0.059 | 0.130 | **0.151** | 26.6 |
| E4 | 906 | 0.205 | 0.061 | 0.131 | **0.145** | 30.8 |
| all eras | 3,319 | 0.217 | 0.062 | 0.139 | **0.155** | 44.1 |

- At highway speed, each comma-driven wheel step of ≥ 0.3° is followed within 0.25–0.45 s by a lateral-acceleration change of about **0.15 m/s²** (net of the slow-trend bias).
- That is the size of Amendment 5's step-event threshold (0.1 m/s² in 0.2 s). So the twitch is not only visual: it moves the car.

### 4.2 V-label: the user's labelled moments

**One of the five episodes cannot be scored.**
- `0x22` 614.7–634.7 s, around the 629.7 s bookmark, was **manual driving at low speed** (0.3–13 m/s, latActive 0 throughout, the wheel pressed; confirmed by the review, F2).
- So **V-label is not evaluable as pre-registered** (5 episodes) for any measure.

**Percentile of each scoreable episode** within 67 E4 OP ≥ 55 mph 30 s chunks:

| Measure | `0x22` 410–441 s | `0x22` 538–568 s | `0x23` 194–239 s | `0x23` 247–294 s | Median | Rule adapted to 4 (median ≥ 75, ≤ 1 below 50) |
|---|---|---|---|---|---|---|
| W_ar | 90 | 46 | 55 | 25 | 51 | (weave; not a criterion) |
| W_lane | 68 | 47 | 86 | 15 | 58 | (weave) |
| W_ang | 88 | 63 | 46 | 6 | 54 | (weave) |
| T | 97 | 97 | 51 | 6 | 74 | fail |
| **J_r** | 87 | 99 | **90** | 42 | **89** | **pass** |
| **A_wd** | 97 | 97 | 66 | 30 | **81** | **pass** |
| E_step | 84 | 81 | 45 | 3 | 63 | fail |
| E_hs | 78 | 79 | 43 | 4 | 60 | fail |
| S_act | 84 | 54 | 22 | 15 | 38 | fail |
| U | 97 | 90 | 57 | 9 | 73 | fail |

- **The adaptation to four episodes was chosen after the percentiles were seen.** Its verdicts are therefore **exploratory**, not a pre-registered validation.
- The `0x22` episodes are twitchy by every measure.
- The first `0x23` episode, which the wheel-angle measures rate as average, is in the top 10% by the yaw-derived jerk J_r.
- The second `0x23` episode is calm by everything.
- **The wheel-angle measures and the new torque-based detector (S_act) do not rank the labelled moments high.**

### 4.3 V-stock: comma vs the car's own LKA, on the same road, the same day, the same driver

**Data.** Shared road = route `0x0e` (stock) ∩ `0x0a`/`0x0b` (comma, E2 tune).
- STOCK: 4.4 min (L 1.9, M 2.2, H 0.4).
- OP: 6.4 min.
- MAN (`0x0c` + `0x0e`): 4.7 min.

OP is reweighted to STOCK's speed-band shares. CIs are from a 10 s block bootstrap.

| Measure | STOCK | OP | MAN | **OP/STOCK** [95% CI] | Verdict | MAN/STOCK | OP/MAN |
|---|---|---|---|---|---|---|---|
| **W_ar** (m/s²) | 0.042 | 0.080 | 0.043 | **1.88 [1.58, 2.30]** | **pass** | 1.02 [0.82, 1.26] | **1.84 [1.53, 2.26]** |
| W_lane (m) | 0.022 | 0.027 | 0.022 | 1.24 [0.91, 1.53] | not separated | 1.04 | 1.19 |
| W_ang (°) | 0.34 | 0.66 | 0.57 | **1.92 [1.44, 2.55]** | pass | 1.65 | 1.16 |
| T (°) | 0.105 | 0.110 | 0.155 | 1.04 [0.81, 1.37] | not separated | 1.47 | 0.71 |
| **J_r** (m/s³) | 0.296 | 0.311 | 0.269 | 1.05 [0.91, 1.23] | not separated | 0.91 | 1.16 |
| A_wd (m/s²) | 0.036 | 0.051 | 0.034 | 1.42 [1.22, 1.71] | pass | 0.94 | 1.51 |
| E_step (/min) | 54.5 | 70.3 | 82.7 | 1.29 [1.06, 1.63] | pass | 1.52 | 0.85 |
| E_hs (/min) | 19.2 | 24.5 | 34.7 | 1.28 [1.06, 1.62] | pass | 1.81 | 0.71 |
| S_act (/min; 1.0 / 0.1) | 4.5 | 6.4 | 0.9 | 1.43 [0.94, 2.64] | not separated (3 of 9 grid points pass) | 0.19 | 7.5 |
| U (m/s² per min) | | | | 1.24 [0.93, 1.76] | not separated | | |
| S_drv (/min) | 1.4 | 0.6 | 20.5 | 0.43 | fail (expected: not a twitch measure) | 15.2 | 0.03 |

**Hands (covariate).** The driver's column torque was **as low under the stock LKA as under the comma**:
- E2 OP: 0.10 Nm RMS in 0.05–2 Hz, |τ_c| ≥ 0.3 Nm 4.7% of the time;
- STOCK: 0.14 Nm, 4.8%;
- manual: 1.06 Nm, 83%.

So hypothesis H-hands (the stock system was experienced with hands on the wheel) is **not supported for this sample**. The comparison is fair on that point.

**Robustness** (review F8):
- STOCK has only 3 ten-second blocks at ≥ 55 mph, so the bootstrap CIs are probably too narrow for the **borderline passes**:
  - E_step and E_hs, lower bounds 1.055;
  - S_act at ΔE* 0.5, lower bounds 1.13–1.16.
- Treat those as fragile.
- **W_ar's separation** (lower bound 1.58) and the not-separated twitch-band jerk ratios **are not borderline**.

### 4.4 Verdicts (pre-registered rule; V-label only with the post-hoc four-episode adaptation)

| Measure | V-label (adapted) | V-stock | Verdict |
|---|---|---|---|
| A_wd (W_d-weighted yaw-derived lateral acceleration) | pass | pass | **valid with the adaptation**: a broad comfort measure; its comma–stock separation comes largely from the weave band |
| J_r (0.7–4 Hz yaw-derived lateral jerk) | pass | not separated | **partly supported** |
| T, E_step, E_hs (wheel angle) | fail | not separated / pass | **not valid** (confirms §12.1 of the weave-twitch findings) |
| S_act (actuator-loaded hold-steps) | fail | not separated | **not valid** |
| U (step upset per minute) | fail (73) | not separated | **not valid** |
| W_ar (weave) | n/a | pass (1.9×) | **consistent with the lane-offset weave** (Spearman ρ 0.71 over 72 E4 chunks; criterion ≥ 0.5): **the recommended weave comfort measure** |

**Strictly as pre-registered, no twitch measure is validated:** V-label cannot be evaluated with one episode unscoreable.

### 4.5 The steering-caused part of the twitch-band jerk (J_coh, per group)

| Group | J_r (spectral) | J_coh | Coherent share | Coherence 0.7–1.5 Hz | 1.5–4 Hz |
|---|---|---|---|---|---|
| E4 OP H straight | 0.650 | 0.299 | 46% | 0.60 | 0.10 |
| E2 OP H straight | 0.619 | 0.246 | 40% | 0.49 | 0.08 |
| E4 MAN M all | 0.685 | 0.384 | 56% | 0.69 | 0.21 |
| E2 STOCK M all | 0.259 | 0.107 | 41% | 0.53 | 0.11 |

- About half of the twitch-band yaw jerk is steering-caused, almost all of it at 0.7–1.5 Hz. Above 1.5 Hz it is road input.

### 4.6 Bicycle check (§3.5.2): does NOT reproduce

E4 OP H straight, 23.8 min:

| Band | Measured/model gain | Measured − model phase | Coherence | |
|---|---|---|---|---|
| 0.2–0.7 Hz | 1.35 | +29° | 0.76 | fail |
| 0.7–1.5 Hz | 1.96 | +37° | 0.60 | fail |
| 1.5–4 Hz | 2.23 | +12° | 0.10 | n/a |

- W_ar of the model / measured: 0.69. The model's J_r / measured J_coh: 0.57.
- **Under the comma at highway speed, the car yaws more, and earlier, in response to the measured wheel angle than the bicycle model predicts.** By the pre-registered rule, **no candidate is re-ranked on simulated comfort**.

**The mismatch depends on who steers** (review finding F1; reproduced by the coordinator, `cm_verify_review.py`, `logs/s15cm-verify-review-*`). The values are the measured/model gain and phase at 0.2–0.7 Hz | 0.7–1.5 Hz:

| Selection | 0.2–0.7 Hz | 0.7–1.5 Hz |
|---|---|---|
| comma E4 H straight | 1.35, +29° | 1.96, +37° |
| comma E4 M | 1.27, +18° | 1.24, +29° |
| comma E2 M | 1.14, +7° | 1.13, +2° |
| **stock E2 L+M** | 1.20, **+14°** | 1.36, +2° |
| **manual E2 M** | **1.05, −5°** | **1.00, −14°** |
| **manual E4 M** | **1.02, −5°** | **1.08, −17°** |
| manual E4 H (27 segments) | 0.69, −11° | 0.78, −14° |

- **The bicycle model matches manual driving at medium speed within 2–8%.** Its remaining phase lag is what the ESP12 delay of about 30–35 ms produces at those frequencies.
- **Under actuator control the yaw leads the wheel angle:** the comma by up to +37°, the stock LKA by +14° at 0.2–0.7 Hz.
- A vehicle's own response can't depend on who turns the wheel. So the "does not reproduce" verdict does not show that the model is wrong. **Under actuator control, the steering-wheel angle is not a faithful input for the vehicle's response.**
- **Two explanations, not separable with these data:**
  - the rack leads the wheel (H-col, §4.7);
  - closed-loop estimation bias: the input is generated by a feedback loop.
- Either way, the simulator's wheel angle can't be turned into vehicle motion with the bicycle model. The candidates stay unranked on comfort.
- The 13ws outer-loop twin, which uses the same model on the simulated wheel angle, is affected in the same way.

### 4.7 Exploratory: the car starts turning before the wheel steps (`cm_eta.py`; hypothesis H-col, stated before the run)

Event-locked averages around hold-step onsets. The values are the change over the 0.3 s before the onset, sign-aligned to the step (a positive value means it moved toward the step before the wheel did):

| Group | Steps | Wheel angle | Yaw rate (ESP12) | Bicycle-model yaw (from the wheel) | Column torque | Torque command |
|---|---|---|---|---|---|---|
| OP E4 H | 861 | −0.007° | **+0.098 ± 0.007 °/s** | −0.012 °/s | −0.087 Nm | +19.8 counts |
| OP E2 loop L/M | 218 | +0.005° | **+0.112 ± 0.014** | +0.017 | −0.089 | +17.8 |
| STOCK `0x0e` L/M | 70 | +0.014° | **+0.060 ± 0.016** | +0.016 | −0.069 | +14.9 (camera's) |
| MAN E4+E2 H/M | 713 | 0.000° | −0.009 ± 0.010 | +0.004 | **+0.206** | — |
| MAN loop L/M | 288 | 0.000° | −0.004 ± 0.011 | 0.000 | +0.180 | — |

**Reading** (hypothesis, consistent with the bicycle mismatch in §4.6):
- Under actuator control (the comma, and the stock LKA to a lesser degree), the motor torque ramps toward the step while the steering-wheel angle holds. Over the same time the car **already turns** (yaw rate rising), and the column torque moves the other way, as if the pinion were pulling on a stuck wheel. Then the wheel steps.
- In manual driving the driver's torque leads, and the car does not turn before the wheel moves.
- So on this rack-type EPS the visible wheel step looks like the steering wheel **catching up** with a rack that has already started moving, through friction in the column above the torque sensor. It does not look like the whole steering system sticking.
- **Caveats:**
  - sub-0.1° creep of the wheel within one angle quantum, amplified by the car's yaw gain (§4.6), could explain part of the pre-rise;
  - the 0.09 Nm column-torque wind-up corresponds to only about 0.05° of torsion-bar twist.

  Not established.

**The review checked for artifacts** (item 7 of the review; not repeated by the coordinator):
- **ESP12's delay:** it would push a yaw rise later, not earlier.
- **Angle creep inside the hold:** about 0.01°, too small (about 0.2° would be needed).
- **Control groups:**

  | Hold followed by | Measured yaw beyond the model's prediction | Torques |
  |---|---|---|
  | a step back | about +0.14 °/s toward the step | column against it, EPS toward it |
  | a step in the same direction | about +0.05 °/s toward the step | the same |
  | no step | no rise | |

  In manual driving the yaw follows the model within about 0.02 °/s.
- **So the pre-step yaw rise is tied to the coming step and occurs only under actuator control.**
- **Not ruled out:**
  - a closed-loop cause;
  - a steering-sensor delay that manual driving masks.

  For the closed-loop cause, a correction by the driving model would steer *against* a disturbance-driven yaw. That would predict the opposite sign; it was not tested here.
- It agrees with the source dependence in §4.6.

### 4.8 Exploratory: the shared-road steering-caused jerk, and finer V-label views (`cm_explore.py`)

- **On the shared loop:**
  - the steering-coherent twitch-band jerk is OP/STOCK **1.12 [0.82, 1.56]** (MAN/STOCK 0.87);
  - the 0.7–1.5 Hz yaw jerk is OP/STOCK 0.97 [0.66, 1.43].
  - **The comma's fast, steering-caused lateral motion is not distinguishable from the stock system's** on this road and tune.
- **Labelled episodes** (percentiles as §4.2):

  | Measure | `0x22` 410–441 s | `0x22` 538–568 s | `0x23` 194–239 s | `0x23` 247–294 s |
  |---|---|---|---|---|
  | J_r1, 0.7–1.5 Hz yaw jerk | 98.5 | 98.5 | 94 | 27 |
  | J_r2, 1.5–4 Hz | 69 | 96 | 88 | 43 |
  | J_b, the bicycle model's steering-caused jerk | 98.5 | 98.5 | 61 | 4.5 |

  - The first `0x23` episode's high yaw jerk is only partly explained by the wheel angle.
  - J_r1 is the best-ranking single measure here, but it was defined after the results and needs new labels to be tested.

### 4.9 D2C4 re-scored on the car (B `0x28` vs A-primary on B's road, OP ≥ 55 mph; 60 s block bootstrap; one B drive)

| Measure | Validity | All-road: B vs A [95% CI] | Straight: B vs A [95% CI] |
|---|---|---|---|
| **W_ar** (felt weave) | weave measure | **+28.6% [+11.8, +48.5]** | **+22.3% [+4.7, +42.7]** |
| W_lane | weave | +48.8% [+20.2, +84.2] | +31.1% [+9.6, +57.5] |
| W_ang | weave | +34.0% [+10.3, +62.4] | +28.2% [+1.3, +59.4] |
| **J_r** (felt twitch-band jerk) | partly supported | **−4.3% [−16.7, +8.5]** | −6.9% [−19.6, +7.5] |
| A_wd | valid (adapted) | −3.2% [−11.9, +6.9] | −10.5% [−19.0, −0.3] |
| T | not valid | −25.8% [−35.2, −14.6] | −32.3% [−42.9, −19.4] |
| E_step | not valid | −20.9% [−36.1, −0.4] | −38.8% [−54.4, −16.4] |
| E_hs | not valid | −25.8% [−40.9, −5.5] | −39.7% [−54.7, −18.4] |
| S_act | not valid | −12.0% [−40.8, +27.6] | −29.1% [−58.5, +7.8] |
| U | not valid | −19.4% [−37.6, +7.0] | −39.1% [−55.0, −13.7] |

- B: 10.5 min (6.9 straight). A: 24.9 min (16.7 straight), from 5 routes.
- **D2C4 makes the felt weave worse by about a quarter. It does not change the felt twitch-band jerk. It reduces only the wheel-step counts, which do not track the user's labels.**
- Same caveats as the session 11r A/B: one B drive, A mostly in the dark, different days.

### 4.10 Exploratory: what the EPS receives from the stock camera vs from the comma (`cm_lkas.py`; §3.6)

**Torque command shape** (shared loop, counts):

| | 0.2–0.7 Hz RMS | 0.7–1.5 Hz | 1.5–4 Hz | 4–10 Hz | 10–50 Hz | 10 ms steps: 0 | 1–2 | exactly 3 | ≥ 4 |
|---|---|---|---|---|---|---|---|---|---|
| Stock camera | 11.3 | 5.2 | 3.3 | 1.6 | 1.1 | 27% | 65% | 4.5% | 3.6% |
| Comma (E2) | **15.3** | 3.8 | 3.8 | 2.1 | 1.6 | **50%** | 21% | **19%** | 9.7% |

- The stock request changes almost every 10 ms in 1–2-count steps.
- The comma's is held flat half the time, then moves at the +3 rate limit or in larger down-steps: a staircase. This fits P plus the friction ramp acting on the 0.1°-quantized angle.
- The comma also has a third more slow (weave-band) torque.

**LKAS11 status fields:**
- The EPS receives LdwsSysState 3/4, LdwsOpt_USM 2 and FcwOpt_USM 2 from the comma. The camera sends 0 / 0 / 0.
- Source fact (`hyundaican.py` `create_lkas11`, checkout @ `89bbe60ab1`): these set the cluster icons for this car's group, which includes `GENESIS_G70_2024`.
- All other fields match, including ActToi = 1 and ToiFlt = 0.
- **Whether the EPS treats the torque differently with these status values is untested.** Hypothesis, low prior.

## 5. Reading and options (offline evidence; for the user)

**What the measures say:**
1. **Weave is the clearest comfort difference between the comma and the car's own lane keeping.**
   - On the same road, the same day, with the same driver and the same (light) hands, the comma's felt weave (yaw-derived lateral acceleration 0.2–0.7 Hz) is **1.9× the stock system's and 1.8× the driver's**. The wheel's own weave is also 1.9×.
   - That was with the E2 tune at 25–65 mph. D2C4 adds about 25–30% on top at highway speed.
2. **The fast, steering-caused lateral motion is about the same** for the comma, the stock system and the driver on that road (ratios 0.9–1.1, not separated).
   - The wheel steps under the comma are slightly more frequent than under the stock system (1.28×). Both are fewer than in manual driving.
   - Each step moves the car (about 0.15 m/s²). Both actuator systems show the car turning before the wheel steps (§4.7).
3. **No twitch measure is validated as pre-registered.**
   - Only two labelled events with comma data exist (four episodes).
   - The yaw-derived measures (J_r, A_wd, and exploratory J_r1) rank them best. The wheel-angle and torque-based step measures do not.
   - **Hypothesis**, to test with labels: what the user sees as "constant twitching" is the wheel following the comma's larger weave in visible steps. Jumps follow slow request reversals (13ws §6.4), and the comma reverses with about twice the stock system's slow amplitude. If so, the twitch is a symptom of the weave, and fixing the stick-slip alone will not remove it.
4. **D2C4** trades a large weave increase for fewer wheel steps, with no change in the felt twitch-band jerk.
   - On the comfort measures it makes the car worse on the weave and no better on the twitch.
   - Keep or roll back is the user's decision. **No `dragal/custom` or device change without asking.**
5. **Candidates F7d / S1 / S2 / MV2 / MV3** were selected on jumps and T, which are not valid. They cannot be ranked on comfort now.
   - Under actuator control the wheel angle does not predict the car's yaw the way the bicycle model assumes (§4.6).
   - The bicycle model itself fits manual driving.
   - What is missing is a model of how the comma's torque moves the rack and the car, not only the wheel.

**Options (the user decides):**
- **(a) The decisive recording:** a same-road comparison at highway speed of the stock LKA (openpilot switched off by the user in the device settings, i.e. dashcam mode as on `0x0e`) and the comma, with:
  - the phone filming the wheel;
  - the passenger bookmarking twitchy moments **and calm ones**;
  - a note of the hands state.

  This gives highway-speed stock data (only 0.4 min exist), labels for both sources, and a direct visual comparison. It needs the user's consent. The settings change is the user's own action in the UI; any step by this project on the device needs authorization.
- **(b) More labels from existing drives:** for example, tell us what the `0x28` bookmark (238 s, during the D2C4 drive) was for; and whether the twitch was seen at the `0x23` filmed moments.
- **(c) D2C4:** keep, or return to A (`c027a92857`), on the weave evidence above.
- **(d) Next analysis:** target the weave, the clearest difference, with W_ar as the outcome.
  - The driving model in the loop (M4(c)) is the tool for that.
  - It needs a vehicle response driven by the comma's torque rather than the wheel angle (§4.6). The closed-loop estimation bias has to be handled in its identification.

## 6. QA: focused adversarial review (one independent agent, 2026-10-07)

**Scope and setup:**
- Scope:
  - the `cm_*` code against §1–3 (requirements only: no handoffs or changelog);
  - the unreviewed 13ws read-only scripts (`s16_ws_bus1`, `lkas_adrv`, `adrv_decode`, `adrv_scale`, `dup`, `nnlc_*`, `stock_lka`, `stock_sticks`, `holdstep`, `eps_events`, `srcprobe`);
  - a skim of the twin code.
- `s13ws_model/*` was not reviewed.
- Report: `E:\DragalPilot\scratch\wsl\cm\review\review.md`, with the reviewer's checks `rv_*.py`.
- The reviewer changed no files. `sunnypilot/` was clean after its runs.

**No blocker.** These match the DBC, opendbc and Amendment 13:
- CAN decoding, units and signs;
- the source masks;
- the event logic;
- the filters;
- the V-label and V-stock mechanics;
- the bicycle equations: steady state equal to opendbc's formula to 1e-15, and the CarParams equal to the rlogs'.

**Findings and dispositions.** The coordinator verified F1, F2, S1 and F10 independently (`cm_verify_review.py`, `logs/s15cm-verify-review-*`).

| ID | Severity | Finding | Disposition |
|---|---|---|---|
| F1 | major | The bicycle-check mismatch depends on who steers, so it doesn't show the model is wrong | **Agreed, reproduced.** The verdict stands as computed; the reading is revised in §4.6 and §5 |
| F2 | major | V-label can't pass as pre-registered (one episode has no comma data) | **Agreed.** Already reported as not evaluable; the episode's description is corrected (low speed, 0.3–13 m/s) |
| S1 | major (13ws) | The FFT band-pass in `s16_ws_stock_sticks.py` / `s16_ws_holdstep.py` has no detrending and inflates the 0.7–4 Hz angle RMS: ×1.15 (comma H), ×1.29 (comma M), ×1.33 (stock L), ×1.48 (manual M), ×2.53 (manual H) | **Agreed, reproduced** with the same factors. Erratum added to the weave-twitch findings §12. The counts (jumps, hold-steps) are not affected; the cm pipeline is not affected |
| F3 | minor | The extractor resets held values at each segment. OP and stock runs split every ~60 s; about 7% of RMS samples lost; no bias | Noted, not fixed (needs a re-extraction; no bias) |
| F4 | minor | Event rates include run edges where no event can be detected: rates 1–3% low, ratios < 1% | Noted |
| F5 | minor | File-order holding: 4–5% of rows have CAN values 10–27 ms newer than the angle | Noted |
| F6 | minor | J_r differentiates against jittered timestamps: +0.7–0.9% for every source | Noted |
| F7 | latent | U is missing, not 0, in a window with no hold-steps (0 of 67 chunks today) | Noted |
| F8 | minor | V-stock: the U null is held fixed; zero-denominator replicates are dropped; the stock ≥ 55 mph sample is 3 blocks, so the CIs are too narrow for the borderline passes | **Agreed.** Caveat added in §4.3 |
| F10 | minor | `cm_ab.py`: B is not restricted to road that A also covers | Checked: B on A-covered road is 10.4 of 10.5 min; W_ar +28.5% either way, J_r −4.1 vs −4.2%. No effect |
| S2 | note | `s16_ws_eps_events.py`: the 15–25 ms "gaps" are batching jitter (equal 0–5 ms count) | Agrees with the 13ws text (§12.1, "log timestamp batching"). No change |
| S3 | minor | `s16_ws_adrv_decode.py` assumes 20 Hz rows (ADRV is 100 Hz). Its lag search is ±0.2 s, not ±1 s, in 10 ms units | The documented lags (ADRV about 0.03 s after carState, about 0.07 s after the gyro) agree with this session's independent measurement (ESP12 30–40 ms after the gyro, ADRV 30 ms after ESP12). No change |
| S4 | note | An ADRV "angle changes" statistic ignores the 30 ms lag | No documented conclusion depends on it (the fingerprint findings say no finer resolution) |
| item 7 | — | The pre-step yaw rise is not an artifact of ESP12 delay, angle creep, or hold selection (controls) | Recorded in §4.7. It remains a hypothesis |

- The other review notes (F9, F11, F12, S5–S7) affect no result.
- **QA status:** focused review **done**. The `s13ws_model/*` probe code and the twin code remain unreviewed. The twin was not used for any result.
