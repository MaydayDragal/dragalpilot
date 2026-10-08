# G70 2024: root cause of the steering twitch: stick-slip model, ablations, candidates (2026-10-07, session 10)

**User request (2026-10-07):** "Even pre-restore settings were twitchy. I want to find the root cause. Do #1 [offline closed-loop model with steering stick-slip] and expand the data you test to earlier routes as well."

Follows the [twitch characterisation](2026-10-06-g70-steering-twitch.md):
- the twitch is a hold-and-jump wheel motion, confirmed on video;
- P and the friction ramp carry most of the fast command;
- it is worse at higher loop gain.

**Offline only. No device access, no code change in `sunnypilot/`.**

Evidence labels:
- **Source fact:** file + revision `c027a92857`; the lateral path is identical to `82f58a9a8c` and to `7e9d0755d9` except for the tune values.
- **Observation:** rlog, with route and time.
- **Model result.**
- **Hypothesis.**

## 0. New observation that widens the question (made before this plan; exploratory)

- **20 Hz pulse.** While lateral control is active, the EPS output torque (`steeringTorqueEps`) has sharp spectral lines at **20 Hz and 40 Hz**. They are absent in manual driving and at standstill, in every era (E1, E3, E4).
  - In the raw samples, a pulse of about 2–3.5 units appears every 5th carState sample (50 ms). Between pulses the output is about −1…+1.
  - The pulse is **not locked to modelV2 arrivals**: its phase after the last model message is spread over the whole 50 ms.
  - Its period (50.14–50.18 ms) equals 5 carState periods (5 × 10.05 ms).
  - Script: `s10_eps_pulse.py`. Its sign test was invalid (the detector also flags the neighbours), so no sign claim is made.
- **Wheel vibration.** The column torque sensor (`steeringTorque`) shows a broad **12–20 Hz hump** plus the 20 Hz line while engaged: about 9 raw units RMS at 8–20 Hz, against 0.2–1 when stopped. The steering-override threshold is 150. Output: `eps_spectra.png`, `eps_spectra.json`.
- **Hypotheses for the source:**
  - (i) something we send every 5 frames: Hyundai `LFAHDA_MFC` at 20 Hz when `SEND_LFA` is set (`hyundai/carcontroller.py` L186; set when 0x485 is seen on bus 2 at fingerprint, `interface.py` L95–96);
  - (ii) the EPS's own LKAS processing at 20 Hz;
  - (iii) something else on the 100 Hz loop.
- **Questions for this phase:**
  - Is the 20 Hz pulse / 12–20 Hz vibration part of the felt twitch? It is too fast to show in 30 fps video.
  - Does it interact with the hold-and-jump?

## 1. Questions

- **RC1 (root cause of the hold-and-jump):** which ingredients are *necessary* for it? Candidates:
  - (a) static friction / stick-slip in the steering;
  - (b) the error-driven friction-compensation ramp;
  - (c) P gain;
  - (d) small fast jitter in the model's request (setpoint);
  - (e) 0.1° angle quantization feeding the error;
  - (f) the 20 Hz staircase of the request;
  - (g) the 20 Hz EPS pulse.
- **RC2:** what produces the 20 Hz EPS pulse and the 12–20 Hz wheel vibration: us (a periodic TX), the EPS, or the loop?
- **RC3:** which car-scoped change, if any, would remove the twitch without hurting tracking, the weave or curves (offline)?

## 2. Data (all engaged-capable routes on record)

Eras by the parameters the controller actually applied (verified in the [twitch findings](2026-10-06-g70-steering-twitch.md) §5.2):

| Era | Routes | laf / friction applied |
|---|---|---|
| **E1** (original port) | `3` (re-extracted), `4`, `6`, `7` | 2.7 / 0.11 |
| **E2** | `8`, `9`, `a`, `b`, `10`, `12`, `15` | 4.0 / 0.07; torqued values from `0x12` on (3.75–3.87 / 0.076–0.079) |
| **E3** | `18`, `1a`–`1d` | 4.0 / 0.07 |
| **E4** | `1e`–`25` | torqued 3.55–3.69 / 0.081–0.085 |

Routes without engagement (`5`, `c`, `e`, `f`, `11`, `13`, `14`, `16`, `19`) give only manual baselines.

## 3. Step 1: characterisation (observational, all eras)

- **Hold/jump statistics**, per era × speed band, on the straight-clean engaged selection of the twitch findings §3:
  - hold durations;
  - jump sizes;
  - command change during a hold until breakaway (the "breakaway Δcommand", counts);
  - EPS output torque during holds vs at breakaway;
  - dependence on speed.
- **20 Hz pulse source (RC2)**, from raw rlog CAN timing on a few segments:
  - MDPS12 (0x251) arrival times and `CR_Mdps_OutTq` values;
  - our sent LKAS11 (0x340) and any 20 Hz TX (0x485 `LFAHDA_MFC` if present) from `sendcan`.
  - Decision rule:
    - the pulse is **ours** if it keeps a fixed phase (IQR < 10 ms over ≥ 60 s) with a 20 Hz TX;
    - it is **EPS-internal** if it keeps a fixed phase with the MDPS12 frame sequence and drifts against all our 20 Hz TX.
  - Also: is the pulse present with the LKAS steer request on but at zero command, and does its size depend on the command?

## 4. Step 2: stick-slip plant model

- **Structure** (steering-wheel angle domain, deg):
  - EPS torque = g_eps · (command delayed by τ_d and first-order lag τ_e);
  - rack/wheel: m θ̈ = T_eps − k_a(v)·(θ − θ_0) − c·θ̇ − F_f;
  - **Karnopp stick-slip friction:** stuck while |θ̇| < ε and |net force| ≤ F_s; otherwise F_f = F_c·sign(θ̇);
  - θ_0 is a slow bias (road crown/roll, trim);
  - the sensor quantizes θ to 0.1°.
- **Controller measurement:** the logged per-sample vehicle-model map from angle to lateral accel (opendbc `VehicleModel.calc_curvature` with the logged steerRatio, stiffness factor, angle offset and roll), exactly as V0 computes it.
- **Controller and output stage:** the session 6 fast V0 (`s5_fast.Ctrl`, equivalence-checked against the source), with the logged timing (command k → carOutput k+1) and each era's applied laf/friction.
- **Identification:** output-error on 20 s chunks of straight-clean engaged runs, open loop (driven by the logged command). The parameters per speed band (M, H) are g_eps, k_a, c, F_s, F_c, τ_d, τ_e, bias.
  - **Fit set:** E2 and E3 routes (gain level 0.74–0.75 setpoint path).
  - **Held out:** all of E1 (gain 1.11) and E4 (0.84), and route `3`.
- **Adequacy criteria (fixed now)**, closed loop (V0 + plant, logged requests, speed, roll, delay; the clean mode of session 6), on the held-out eras at H and at M when ≥ 60 s exist. Simulated vs logged:
  - hold fraction within ±0.10 (absolute);
  - jumps ≥ 0.3°/min within ±35%;
  - angle T-band (0.7–4 Hz) RMS within ±35%;
  - the logged ordering E3 < E4 < E1 is reproduced for both jumps/min and angle T RMS;
  - weave band (0.2–0.7 Hz) angle RMS within ±40% (so that the model is not twitch-only).
  - **If the criteria fail, ablations are reported as exploratory and no candidate is ranked.**

## 5. Step 3: ablations for the root cause (on the adequate model only, held-out eras first)

| Variant | What is removed or changed |
|---|---|
| A0 | baseline (as driven) |
| A1 | plant without static friction: F_s = F_c (Coulomb only) |
| A2 | plant without any dry friction: F_s = F_c = 0 |
| A3 | controller friction term off (friction = 0) |
| A4 | KP halved at all speeds (diagnostic) |
| A5 | request smoothed: 1 Hz zero-phase low-pass of desiredCurvature (removes model jitter) |
| A6 | request linearly interpolated between model updates (removes the 20 Hz staircase) |
| A7 | perfect angle sensor (no 0.1° quantization) |

- **Necessity rule:** an ingredient is a **root-cause component** if removing it reduces simulated jumps/min **and** angle T RMS by ≥ 50% against A0, in both held-out eras at H.
- It is **contributing** at a 20–50% reduction, and not implicated below 20%.

## 6. Step 4: candidate changes (defined after step 3, pre-registered in an amendment before any run)

- Car-scoped only (GENESIS_G70_2024). Evaluated on the held-out eras with the twitch metrics.
- Also with the session 6/7 criteria:
  - 0.2–0.7 Hz band gain/lag;
  - curve actual/desired 0.95–1.04;
  - mean |error| not up > 20%;
  - step overshoot.
- Nothing is proposed for the device without the user's approval, and any on-car check follows CLAUDE.md §6.

## 7. Results

Data: `E:\DragalPilot\analysis\g70-twitch-rc-20261007\`. Scripts: `E:\DragalPilot\scratch\wsl\sng\s11_*.py`. Logs: `E:\DragalPilot\logs\s10-s11-*.log`.
- Python: the checkout venv for the dataset (opendbc VehicleModel); `~/venvs/vid` for the rest (numpy 2.5.3, scipy 1.18.1, **numba 0.68.0 installed this session**, `logs/s10-install-numba-20261007.log`).

### 7.0 Dataset and harness checks (observation)

- **Route `3`** has no lateral-active samples, so it adds nothing to the engaged analysis (its re-extraction is in `drives/`).
- **Measurement map:** the per-sample map (opendbc `VehicleModel` from each route's own carParams, updated with the logged stiffness factor and steer ratio) reproduces V0's logged measurement on every route E1–E4: median |Δ| ≈ 1e-9 m/s², p99 ≤ 0.004 m/s² (`dataset/dataset_summary.json`).
- **Numba closed loop:** `s11_fastloop.py` (V0 + Hyundai output stage + plant) is **bit-exact** against the Python reference (`s5_fast.Ctrl` + `s11_closed.plant_step`). Max |Δ| is 0 for angle and command on 12 runs from 3 routes, with the friction term on and off (`s11_fastloop_check.py`).

### 7.1 Step 1: hold/jump characterisation (`s11_holdjump.py`, `step1/holdjump_summary.json`)

Straight-clean engaged, 55+ mph (medians, with p10–p90):

| Era | Straight s | Jumps/min | Hold before jump (s) | Command rise during the hold until breakaway (counts of 384) | Ramp toward the jump | Gap to setpoint angle before jump (°) | After jump (°) | Overshoot |
|---|---|---|---|---|---|---|---|---|
| E1 | 729 | 47 | 0.35 (0.15–1.16) | 35 (12–54) | 97% | 0.32 (0.16–0.51) | −0.13 | 74% |
| E2 | 1,138 | 16 | 0.60 (0.16–1.43) | 32 (5–53) | 92% | 0.40 (0.18–0.60) | +0.05 | 41% |
| E3 | 1,155 | 19 | 0.54 (0.16–1.97) | 27 (0–46) | 89% | 0.39 (0.20–0.58) | +0.03 | 46% |
| E4 | 1,364 | 30 | 0.52 (0.18–1.15) | 31 (11–48) | 98% | 0.39 (0.20–0.57) | −0.01 | 52% |

- **Every era, including the original port tune, has the same stick-slip.**
  - The wheel sits about 0.4° short of the angle the controller wants. The controller's torque rises by about 30 counts (about 8% of STEER_MAX) toward the target.
  - Then the wheel breaks free and jumps 0.3–0.4°, landing on the target on average. Higher loop gain lands past it more often (E1 74%).
- **Erratum (session 11, 2026-10-07):** the conversion in the next line used a plain bicycle model without the understeer factor. V0's own vehicle-model map (the logged A, E4 medians) gives 0.020 / 0.025 / 0.029 m/s² per 0.1° at 25 / 30 / 33.5 m/s, so a 0.3–0.4° jump at 75 mph is about 0.09–0.11 m/s². The 0.4° deadzone is about 0.10–0.115 m/s² at 30–33.5 m/s, not 0.18 (also in §7.8). The simulations were not affected: they always used the logged map. Details: [D2C4 validation](2026-10-07-g70-d2c4-validation.md) §3.1.
- At 55+ mph, 0.1° of steering is about 0.045 m/s² of lateral acceleration. So each 0.3–0.4° jump is a lateral step of about 0.13–0.18 m/s², which occupants can feel.
- **Mechanical, not EPS-side (`s11_eps_hold.py`, `step1/eps_hold.json`):**
  - During holds, the EPS output torque (`steeringTorqueEps`, low-passed 4 Hz) tracks the command's ramp with the same slope as while moving: within-hold 0.058–0.069 EPS units per count, correlation 0.87–0.91; moving 0.056–0.069, correlation 0.92–0.97 (all eras, H and M).
  - So the EPS applies the requested torque and the steering does not move until the torque change exceeds a breakaway level. That is **static friction in the steering mechanism / tyres**, not an EPS deadband on LKAS requests.

### 7.2 RC2 status: the 20 Hz EPS-output pulse (timeboxed; open)

- **Raw CAN** (`s10_canpulse.py`, route `0x22` segments 7–8):
  - MDPS12 arrives at 99.8 Hz with no dropped counters;
  - we send LKAS11 at 99.5 Hz and `LFAHDA_MFC` (0x485) at 19.9 Hz (`SEND_LFA` is set on this car);
  - `CF_Lkas_ActToi` = 1 throughout.
- **Folding:** the pulse does not hold a fixed slot in the MDPS12 frame sequence, in our send sequence, or relative to 0x485 (contrast ≤ 1.4× per 10 s block, and the slot changes).
- **Frequency:** high-resolution DFT 19.92 Hz. That is closest to our send rate / 5 (19.90) and differs from modelV2 and MDPS12/5 (both 19.97). The peak is weak (10× median) and the frame times are approximate.
- **Not resolved.** It is a 20 Hz component, too fast for the visible twitch. It may contribute to the felt "buzz" (column torque 8–20 Hz about 9 units RMS while engaged, ≤ 1 stopped).
- **Next test if pursued:** the logs cannot separate the remaining sources. A decisive test needs a code variant (e.g. a different 0x485 phase or rate) and an engaged device test. Not proposed.

### 7.3 Amendments

- **Amendment 1 (2026-10-07, before any closed-loop result):** the first plant fit (`plant/plant_fit.json`) hit the upper bounds of `a` (400) and `td` (0.12 s).
  - Bounds widened to a ≤ 5000, b ≤ 500, c ≤ 500, fs/fc ≤ 300, td ≤ 0.25 s, te ≤ 0.3 s, and the fit re-run (`plant2/`).
  - Fit set and objective unchanged.
  - The M band has only 100 s (5 chunks) of fit data, so M results are low-confidence.
- **Adequacy of the refit plant (pre-registered §4 check; `step2/adequacy_plant2.json`): FAIL.** Closed loop, logged requests, 55+ mph (sim vs log):

  | Era | Role | Jumps/min | Hold | Angle T RMS (°) | Angle W RMS (°) |
  |---|---|---|---|---|---|
  | E1 | held out | 111 vs 50 (✗) | 0.24 vs 0.45 (✗) | 0.33 vs 0.12 (✗) | 0.12 vs 0.10 |
  | E2 | fit | 21.2 vs 18.1 | 0.70 vs 0.65 | 0.075 vs 0.050 | 0.13 vs 0.11 |
  | E3 | fit | 20.1 vs 20.6 | 0.71 vs 0.64 | 0.068 vs 0.047 | 0.12 vs 0.11 |
  | E4 | held out | 37.1 vs 32.1 (✓) | 0.58 vs 0.55 (✓) | 0.109 vs 0.072 (✗ +51%) | 0.14 vs 0.13 (✓) |

  - The ordering E3 < E4 < E1 is reproduced for jumps/min and T RMS.
  - At 35–55 mph (held-out E4, 286 s): jumps +39% (✗), hold ✓, T +24% ✓, W +33% ✓.
  - **Reading:** the model reproduces the stick-slip rate and hold fraction at moderate gain from the logged requests alone. It overstates jump size (T RMS +44–51%, even on the fit eras) and goes near-unstable at E1's gain.
  - The open-loop fit objective does not constrain the closed-loop jump size or stability margin.
  - A preview with the first (bound-limited) fit behaved the same way (`temporary\s11-smoke\eval_preview_v1.json`, exploratory).
- **Amendment 2 (2026-10-07, before running it):** identify the same plant structure **in closed loop on the fit eras only** (E2, E3; `s11_plant_cl.py`).
  - **Objective:** pooled relative errors of jumps/min, hold, T RMS and 0.5·W RMS against the fit-era logs, plus 0.5 × the 1 Hz low-passed angle error / 0.3°.
  - **Held out:** E1 and E4 stay untouched, and the §4 adequacy criteria are applied to them unchanged.
  - **Limitation:** this tunes the model to reproduce the fit eras' statistics, so its in-sample (E2/E3) agreement is not evidence; only E1/E4 are.

### 7.4 Step 2 result: the closed-loop-identified plant passes the held-out check at 55+ mph (`plant_cl/plant_fit.json`, `step2/adequacy_plant_cl.json`)

- **Plant (H band):**
  - a 4524, b 248, c 105;
  - **f_s 223, f_c 75 (static ≈ 3× kinetic)**;
  - td 0.031 s, te 0.022 s;
  - 4,270 evaluations, 57 min.
  - a, b and the friction levels scale together, so only their ratios matter: a/b = 18.2, f_s/a = 0.049, f_c/a = 0.017. `a` near its bound is a scaling degeneracy, not a constraint.

| Era (55+ mph) | Role | Jumps/min sim vs log | Hold | Angle T RMS | Angle W RMS | Criteria |
|---|---|---|---|---|---|---|
| **E1** | **held out** | 56.8 vs 49.8 (+14%) | 0.457 vs 0.450 | 0.116 vs 0.121 (−4%) | 0.108 vs 0.101 (+7%) | **all pass** |
| E2 | fit | 19.4 vs 18.1 | 0.71 vs 0.65 | 0.053 vs 0.050 | 0.123 vs 0.114 | (in-sample) |
| E3 | fit | 18.3 vs 20.6 | 0.71 vs 0.64 | 0.050 vs 0.047 | 0.115 vs 0.111 | (in-sample) |
| **E4** | **held out** | 29.1 vs 32.1 (−9%) | 0.630 vs 0.550 (+0.08) | 0.069 vs 0.072 (−5%) | 0.132 vs 0.133 | **all pass** |

- The ordering E3 < E4 < E1 is reproduced for jumps and T RMS.
- **So one plant, fitted only on the 4.0 / 0.07 eras, predicts the stick-slip statistics of both the original port tune (2.7 / 0.11) and the restored-torqued tune from their logged requests.**
- **Not covered:** the M band (35–55 mph) was not identified in closed loop; conclusions below are for 55+ mph only.

### 7.5 Step 3: ablations on the adequate model (`step3/ablation_plant_cl.json`; change vs A0 of the same era, held-out E1 / E4)

| Variant | E1 jumps | E1 T RMS | E4 jumps | E4 T RMS | Verdict by the §5 rule |
|---|---|---|---|---|---|
| A1 static = kinetic friction | −16% | −4% | −29% | −4% | not implicated in T |
| A2 no dry friction | +22% | +14% | +25% | +30% | **removing it makes it worse** (continuous oscillation instead of hold-and-jump) |
| A3 controller friction term off | −55% | −39% | −57% | −39% | **contributing (largest controller ingredient)** |
| A4 KP × 0.5 | −26% | −17% | −29% | −21% | contributing (weak) |
| A5 request smoothed 1 Hz (zero-phase) | −68% | −52% | −55% | −40% | **contributing (largest overall; meets the root rule in E1 only)** |
| A6 request interpolated (no 20 Hz staircase) | +5% | +3% | +5% | +3% | not implicated |
| A7 no 0.1° quantization | −41% | −2% | −57% | −2% | not implicated in motion (T unchanged; the jump count changes because the simulated angle is no longer stepped) |

- **No single ingredient is necessary by the pre-registered rule.**
- The model points to a **combination**:
  - the model request's small fast jitter is the excitation;
  - the error-driven friction-compensation ramp, and to a lesser degree P, amplify it;
  - the steering's static friction (about 3× kinetic) shapes the motion into hold-and-jump.
- Removing the steering friction does not help: the loop then oscillates continuously.
- **Amendment 3** (written before running any of the following):
  - **Combined ablations (diagnostic):** A8 = A3 + A5 (friction term off and request smoothed); A9 = A3 + A4.
  - **Candidates (car-scoped, causal, implementable), Step 4:**
    - **C1** friction ramp threshold 0.3 → 1.0 m/s²;
    - **C2** friction coefficient × 0.5;
    - **C3** friction coefficient 0 (= A3 as a candidate);
    - **C4** causal first-order low-pass of desiredCurvature at 2 Hz;
    - **C5** KP at ≥ 30 m/s 1.0 → 0.7;
    - **C6** C1 + C4.
  - **Pass criteria** at 55+ mph, on held-out E1 **and** E4, against A0 of the same era:
    1. **Twitch:** jumps/min ≥ 40% lower **and** angle T RMS ≥ 30% lower.
    2. **No harm on straight runs:** W RMS not up > 10%.
    3. **No harm on all engaged 55+ mph runs, curves included** (press/blinker/saturation filters only): mean |request − measurement| not up > 20%, and curve ratio (Σmeas/Σrequest where |request| > 0.5 m/s²) within 0.95–1.04 and within ±0.02 of A0.
  - A candidate passes only if it meets all three. Passing is offline model evidence only; any device use needs the user's approval and a new on-car check.

### 7.6 Step 4: combined ablations and candidates (`step4/candidates_twitch.json`, `step4/candidates_tracking.json`)

Change vs A0 of the same era at 55+ mph. Held-out E1 / E4. Tracking uses all engaged 55+ mph runs, curves included (E1 1,305 s, E4 2,445 s).

| Variant | Jumps E1 / E4 | T RMS E1 / E4 | W RMS E1 / E4 | Mean \|error\| E1 / E4 | Curve ratio E1 / E4 (A0 1.066 / 1.028) | Criteria |
|---|---|---|---|---|---|---|
| A8 friction off + request smoothed (diag.) | −81% / −75% | −68% / −59% | −10% / −21% | +12% / +22% | 1.058 / 1.034 | (diagnostic) |
| A9 friction off + KP × 0.5 (diag.) | −76% / −73% | −62% / −58% | −11% / −28% | +43% / +45% | 1.077 / 1.042 | (diagnostic) |
| C1 friction ramp 0.3 → 1.0 | −36% / −42% | −24% / −28% | 0% / −11% | +14% / +16% | 1.072 / 1.032 | fail (1) |
| C2 friction × 0.5 | −25% / −29% | −16% / −20% | +1% / −6% | +10% / +10% | 1.071 / 1.031 | fail (1) |
| C3 friction 0 | −55% / −57% | −39% / −39% | −5% / −16% | **+23% / +23%** | 1.074 / 1.034 | fail (3: error) |
| C4 causal 2 Hz request low-pass | −27% / −26% | −22% / −22% | −5% / −7% | +1% / +10% | 1.054 / 1.025 | fail (1) |
| C5 KP(≥30 m/s) 0.7 | −14% / −15% | −10% / −10% | 0% / −3% | +5% / +6% | 1.069 / 1.030 | fail (1) |
| **C6 = C1 + C4** | **−57% / −58%** | **−43% / −41%** | −6% / −14% | +14% / **+23%** | **1.057** / 1.030 | fail (3: E4 error; E1 curve band) |

- **No candidate passes the pre-registered criteria.** The closest is C6 (both twitch criteria met in both eras; fails E4's error limit by 3 points and E1's curve band).
  - E1's own baseline (1.066) is already outside 0.95–1.04, so E1 cannot pass that band for any candidate that doesn't also fix the old tune's curve overshoot.
- **Trade-off (model result):** every variant that cuts the twitch raises the mean tracking error. Absolute numbers are small: A0 0.046 m/s² → C6 0.056 m/s² on E4, which is about 0.02° of steering at 75 mph.
  - The hunting is the loop's way of holding the angle near the request through stiction. Less hunting means the wheel sits slightly further from the request inside the stiction band.

### 7.7 Conclusion on the root cause (model-supported, 55+ mph; status: hypothesis supported by a held-out-validated model, not by an on-car test)

The twitch is a **stick-slip limit cycle**. It needs three things together:

1. **Static friction in the steering mechanism / tyres.**
   - Observed: the EPS applies the ramping torque while the wheel stays put, breakaway at about +30 counts.
   - Model: static ≈ 3 × kinetic friction.
2. **A high error-proportional torque gain near zero error.**
   - At highway speed it is dominated by V0's friction-compensation term, which is driven by the error, has deadzone 0 and ramps fully over ±0.3 m/s². P adds the rest.
   - It keeps ramping torque while the wheel is stuck, and the release overshoots.
3. **Small fast jitter in the model's curvature request** keeps re-triggering the cycle.

- Removing the controller's friction term or smoothing the request each halves the twitch in the model; together they cut it by 75–81%.
- Removing the steering's dry friction makes it worse (continuous oscillation).
- The 20 Hz request staircase and the 0.1° sensor quantization are not implicated.
- **Why "even pre-restore settings were twitchy":** ingredients 1–3 are present in every era.
  - The parameters only set the loop gain: E1 (friction 0.11, laf 2.7) highest, E4 next, E2/E3 lowest.
  - The validated model reproduces exactly that ordering, from the logged requests.

### 7.8 Amendment 4: mechanism-targeted candidates (user chose option 2, 2026-10-07; written before any run)

**Idea:** keep friction compensation for real request changes, but stop it hunting on small errors inside the stiction band (about 0.4° of steering ≈ 0.18 m/s² at 75 mph; **erratum, session 11:** ≈ 0.115 m/s² by V0's own vehicle-model map, see §7.1).

**Source fact:** V0's deadzone path is `get_friction(err, lateral_accel_deadzone, ...)` with `lateral_accel_deadzone = |calc_curvature(radians(steeringAngleDeadzoneDeg), v, 0)|·v²` (`latcontrol_torque_v0.py` L76–77, L100). `apply_center_deadzone` zeroes the error inside the band and passes it unchanged outside (`opendbc/car/lateral.py` L198–201), so the friction term steps at the band edge. `steeringAngleDeadzoneDeg` is set per car (`configure_torque_tune`, `interfaces.py` L256; 0 for this car).

| ID | Change (car-scoped) | Code needed |
|---|---|---|
| D1 | `steeringAngleDeadzoneDeg` 0.2° | car port only (existing mechanism) |
| D2 | `steeringAngleDeadzoneDeg` 0.4° | car port only (existing mechanism) |
| D3 | 0.4° deadzone, continuous (shifted: friction input = sign(e)·max(\|e\| − dz, 0)) | controller |
| J1 | friction input = the request change over the delay (`desired_lateral_jerk · lat_delay` = request − delayed request) instead of the error; threshold 0.3 | controller |
| J2 | as J1, threshold 0.1 | controller |
| H1 | friction input = D2-deadzoned error + request change over the delay | controller |
| P1 | D3 + the same shifted 0.2° deadzone on P's error (I unchanged) | controller |
| D2C4 | D2 + causal 2 Hz request low-pass (C4) | car port + controller |

**Criteria:** as Amendment 3 (§7.5), with one clarification that applies to these candidates only. Where A0's own curve ratio is outside 0.95–1.04 (E1: 1.066), the candidate must be within ±0.02 of A0 and not further from the band than A0.
- This clarification would not change any Amendment 3 verdict: C6 still fails on E4's error.

**Harness:** the numba loop gains these options. With them off it must stay bit-exact against the Python reference (re-checked before use).

**Harness checks (before any candidate result):**
- Defaults are still bit-exact against the Python reference (`s11_fastloop_check.py`, log `s10-s11-fastcheck2-*`).
- Limit cases reproduce their references exactly (`s11_amend4_check.py`):
  - 100° deadzone ≡ friction off (plain and shifted);
  - J1 with friction 0 ≡ friction off;
  - H1 with a 100° deadzone ≡ J1;
  - 100° P deadzone ≡ KP 0;
  - D2 differs from V0.

**Results** (`step4/amend4_twitch.json`, `step4/amend4_tracking.json`; change vs A0 of the same era, held-out E1 / E4, 55+ mph):

| ID | Jumps | T RMS | W RMS | Mean \|error\| | Curve ratio (A0 1.066 / 1.028) | Verdict |
|---|---|---|---|---|---|---|
| D1 (0.2°) | −8% / −8% | −4% / −4% | 0% / −4% | +3% / +2% | 1.068 / 1.029 | fail (1) |
| D2 (0.4°, existing mechanism) | −41% / −37% | −23% / −21% | −6% / −15% | +13% / +10% | 1.074 / 1.028 | fail (1) |
| D3 (0.4°, shifted) | −52% / −54% | −35% / −35% | −7% / −18% | +19.5% / +18.6% | 1.077 / 1.032 | fail (E1 curve further from band than A0) |
| J1 (request change) | −7% / −19% | +2% / −12% | +11% / −3% | +29% / +17% | 1.085 / 1.036 | fail (1, 2, 3) |
| J2 (J1, threshold 0.1) | +66% / +93% | +69% / +59% | | | | fail (worse) |
| H1 (D2 error + request change) | +2% / −3% | +12% / +3% | | | | fail (1) |
| P1 (D3 + P deadzone 0.2°) | −72% / −70% | −55% / −52% | −18% / −31% | **+37% / +32%** | 1.087 / 1.037 | fail (3) |
| **D2C4** (0.4° + causal 2 Hz request low-pass) | **−57% / −52%** | **−42% / −39%** | −9% / −22% | **+14% / +19.4%** | **1.061** / 1.027 | **pass** (all criteria; E4 error margin 0.6 points) |

- **Mechanism reading:** friction keyed to the request change alone (J1/J2/H1) does not help in this model. The stick-slip needs the error-driven breakaway torque, and the request change over 0.1–0.2 s is mostly the jitter itself.
- What helps is not responding with friction torque to errors inside the stiction band (D2/D3), together with less request jitter (C4).

**Exploratory robustness check** (not pre-registered; `s11_robust.py`, `step4/robust_d2c4.json`). A0 vs D2C4 on plants with f_s, f_c ×0.7/×1.3, td ×0.5/×1.5, b ×0.8/×1.2, te ×2:
- **D2C4's twitch reduction is robust:** jumps −47…−62%, T RMS −37…−44% in every case and both eras.
- **Its tracking cost is +10…+24%.** On E4 it exceeds the 20% limit in 4 of 10 perturbed plants (f_s ×0.7 +24%, f_c ×0.7 +21%, td ×0.5 +21%, b ×1.2 +21%).
- So the pass on tracking is **marginal**: about +0.009 m/s² mean on E4 (≈ 0.02° of steering), before the outer loop (model re-planning), which is not simulated.

**Implementation notes (not a proposal):**
- D2 is a car-port value: `configure_torque_tune(..., steering_angle_deadzone_deg=0.4)` for GENESIS_G70_2024.
  - Source fact: torqued's restore key is (carFingerprint, lateral tuning type, friction, latAccelFactor, version) (`torqued.py` L137–142). The deadzone is not in it, so D2 alone would keep torqued's learned state.
  - paramsd/lagd keys are not checked yet.
- C4 needs a car-scoped causal low-pass of desiredCurvature in the lateral controller (new code + tests).

### 7.9 Limitations

- **Speed band:** 55+ mph only. The M band was not identified in closed loop (100 s of fit data), and L has almost no straight-clean data.
- **Plant:** single-input, with a slow offset taken from the log (θ0). No tyre/vehicle dynamics beyond the vehicle-model measurement map; the plant structure is assumed (Karnopp friction, first-order EPS).
- **Identification method:** the closed-loop identification (Amendment 2) tuned the plant to reproduce the fit eras' statistics. Only E1/E4 agreement is evidence. Both pass with margin, but the jump-size and hold criteria were part of the fit objective on E2/E3.
- **Not simulated:** the outer loop (the model re-planning against the car's motion). Logged requests are replayed.
- **20 Hz EPS pulse:** source unresolved (§7.2).
- **Candidates:** tested on logged straights and highway curves only. No synthetic steps, no low-speed, no stop-and-go.
