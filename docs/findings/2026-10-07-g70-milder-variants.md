# G70 2024: weave modelling and milder twitch fixes after the first on-car D2C4 A/B (2026-10-07, session 12mv)

Started from the [milder-variants kickoff](../sessions/2026-10-07-s11-milder-variants-kickoff.md) (updated after session 11r). Offline only: no device access, no change to `sunnypilot/` or the WSL clone.

**Why this session exists.** On the car, D2C4 cut the twitch and cost transients about as the model predicted, but weave got worse (angle W +18%, lane-centre offset 0.2–0.7 Hz +41%), which the model did not predict ([on-road A/B findings](2026-10-07-g70-d2c4-ab-onroad.md) §4). Weave has to be modelled before milder variants can be ranked on it.

Evidence labels: **source fact** (file + revision `89bbe60ab1`), **observation** (rlogs, route IDs), **model result**, **hypothesis**, **exploratory** (computed before a pre-registration, used only to design it).

**Data independence.** Route `0x28` (the only D2C4 drive) and its same-road A drives (`0x26`, `0x1e`, `0x20`, `0x22`, `0x24`) are used here for model checking. They are no longer an independent test. No logged era is untouched by candidate selection. The next on-car A/B with a chosen variant is the independent test.

## 0. Session start (2026-10-07 ~16:05 EDT)

- Outer `main` @ `606c36b` with the uncommitted session 8–11r docs (32 paths).
- `sunnypilot/` `dragal/custom` @ `89bbe60ab127…`, clean. WSL clone `~/src/sunnypilot` @ `89bbe60ab1`, clean. No WSL jobs.
- `E:` UniqueId `daa460f7…` matches; write probe OK; 228.8 GB free.
- Outputs: `E:\DragalPilot\analysis\g70-milder-variants-20261007\`. New scripts: `E:\DragalPilot\scratch\wsl\sng\s15_mv_*.py` and `run_s15_mv_*.sh` (shared `s11_*`–`s14_*` scripts are imported, never edited). Logs: `E:\DragalPilot\logs\s12mv-*`.

## 1. Exploratory semantics checks (before the pre-registration; no B-vs-A metric)

Done to design step 2. They use only fit-set routes (E2, E3 and the E4 opposite-direction routes `0x1f`/`0x21`/`0x23`/`0x25`), never the B-road arms.

1. **Signal semantics** (`s15_mv_semantics.py`, routes `0x20`, `0x28`):
   - modelV2 runs at 20.0 Hz. Lane lines use y to the right: left line median −1.5 m, right +1.8 m. Lane-centre offset c = (ly + ry)/2.
   - The model's `action.desiredCurvature` reaches `controlsState.desiredCurvature` 1–2 controls cycles later, unchanged (98–100% of active samples within 1e-7 at lag 1–2). So the logged request is the model's output.
2. **What the lane offset measures** (`s15_mv_lane_semantics.py`, `explore/lane_semantics_fixed.json`, 2,883 s straight-clean ≥ 55 mph; Welch 20 s, model-time series). A first run summed auto-spectra once per pair (a bug in the exploratory script, fixed and re-run; the first output was discarded).

   | Band (Hz) | request → a_s: coherence, gain, phase | a_s → gyro v·ω: coh, gain, phase | gyro v·ω → c″: coh, gain, phase | c → request: coh, gain (m/s² per m), phase |
   |---|---|---|---|---|
   | 0.1–0.2 | 0.81, 1.05, −18° | 0.51, 0.65, +2° | 0.23, 0.37, 158° | 0.39, 0.42, +50° |
   | 0.2–0.4 | 0.77, 1.10, −48° | 0.77, 1.25, +29° | 0.49, 0.86, 162° | 0.50, 1.00, +50° |
   | 0.4–0.7 | 0.82, 1.19, −73° | 0.88, 1.72, +42° | 0.40, 1.13, 170° | 0.45, 1.56, +45° |
   | 0.7–1.5 | 0.44, 0.65, −82° | 0.52, 1.86, +45° | 0.12, 2.22, 142° | 0.13, 1.00, +89° |

   - a_s = V0's measurement map of the steering angle; v·ω = speed × gyro yaw rate (IMU); c″ = second derivative of the lane-centre offset.
   - **Reading (exploratory):**
     - About half of the lane offset's 0.2–0.7 Hz motion is the car's own motion (c″ ≈ −v·ω, gain ≈ 1, coherence 0.4–0.5); the rest is perception noise or motion the gyro doesn't see.
     - The model's request responds to the lane offset with a phase lead of about 45–50° (a P+D-like policy), coherence about 0.5. **So an outer loop exists in the weave band.**
     - These are closed-loop H1 estimates, biased by feedback (e.g. the gyro "leads" the steering because road disturbances move the car before the model corrects them). They are not causal transfer functions; step 2b identifies the parts with methods that handle this.

## 2. Pre-registration of steps 2 and 3 (written 2026-10-07 before any of these metrics was computed)

Common definitions:
- **Arms** exactly as the on-road A/B findings §3.1: B = `0x28` on its own road (`onA_same_dir_all`); A-primary = `0x26`, `0x1e`, `0x20`, `0x22`, `0x24` on B's road (`onB`); A-day = `0x20` + `0x22`; A-same-day = `0x26`; per-route A values.
- **Speed** H = v ≥ 24.6 m/s. **Straight-clean** = `s11_holdjump.select`; **all-engaged** = `s11_eval.select_all`.
- **Signals:** request r = `desiredCurvature`·v² (logged, unfiltered in both arms); a_s = V0's measurement map of the logged angle; lane-centre offset c from modelV2 (both lane probabilities > 0.5).
- **Bootstrap:** 60 s blocks of the selected runs, 2,000 resamples, `default_rng(0)`, B and A resampled independently, as `s14_ab_metrics.py`.

### 2.1 Step 2a: does B's request weave more? (log check, no model)

Straight-clean H on B's road.
- **M1** request 0.2–0.7 Hz RMS; **M2** a_s 0.2–0.7 Hz RMS. Amendment 5 masks (runs ≥ 8 s, 2 s trimmed) and whole-route zero-phase 4th-order Butterworth band-pass at 100 Hz.
- **M3** lane-centre offset 0.2–0.7 Hz RMS (`s12_comfort.lane_offset_runs`; recomputed, must equal session 11r).
- **M4** request → a_s transfer in the weave band, and **M5** lane offset → request transfer, each with coherence. 20 Hz model-time series, straight-clean H with both lanes ok, contiguous runs ≥ 10 s, Welch 10 s Hann segments with 50% overlap, cross-spectra pooled over runs; band value = |ΣS_xy| / ΣS_xx and angle(ΣS_xy) over the bins in [0.2, 0.7) Hz; also 0.2–0.4 and 0.4–0.7 Hz.
- Also reported: request 0.05–0.7 Hz and 0.7–4 Hz RMS.
- Bootstrap CIs for M1, M2 (% change) and for the M4 phase difference (B − A, degrees) and gain ratio.

**Decision rules:**
- **(a) Request:** "B's request weaves more" if M1 is up > 15% **and** its CI excludes 0. "Not more" if the CI's upper end is ≤ +15%. Otherwise "inconclusive". The A-day arm and the per-route A range are reported next to it; if B lies inside the per-route A range, the change is called not distinguishable from day-to-day variation.
- **(b) Inner loop:** "B's wheel lags the request more in the weave band" if the M4 phase difference is negative (more lag) with a CI excluding 0. Its size is compared with the model's D2C4 prediction on the same estimator (step 3).
- **(c) Reading:**
  - request more **and** lag more → consistent with the outer-loop hypothesis (C4's lag → more lane error → more correction);
  - request not more, lane more → the extra lane weave is not driven by a larger request; it comes from the inner loop's response or from perception (light);
  - request more, lag not more → an exogenous request change (road, light, traffic), not attributable to D2C4.

### 2.2 Step 3: `0x28` as a plant check (engaged D2C4 data)

- `0x28` straight-clean H runs ≥ 12 s (the `s11_eval` statistics rule), whole route.
- Logged requests replayed through the harness with **D2C4** (E4-identified plant primary, E2+E3 plant secondary; `s11_eval.simulate` unchanged; the C4 filter starts at the route's first sample, as on the device).
- **Adequacy criteria** (Amendment 6, unchanged): sim vs logged hold within ±0.10, jumps/min within ±35%, T RMS within ±35%, W RMS within ±40%. Reported too: reversals, steering-proxy comfort (a_s 0.5–4 Hz RMS, jerk, steps), tracking on all-engaged H (mean error), the M4 weave-band phase (sim vs log).
- **A0 on the same requests** (sim) is reported, giving the model's within-drive D2C4 effect on B's own requests.
- **The same adequacy check for A0 on the A-primary drives** (sim A0 vs logged, B's road): it tells whether the plant is adequate on this road before any outer loop is added.

### 2.3 Step 2b: outer-loop model

**Structure (deviation form).** The simulation keeps the logged request and adds the model's predicted response to the simulated deviation from the logged motion:
- r_sim(t) = r_log(t) + Δr(t);
- Δθ = θ_sim − θ_log (both 0.1°-quantized) → road-wheel angle Δδ = Δθ·π/180 / sR (paramsd's sR, as V0's map);
- **vehicle:** opendbc's dynamic bicycle model (source fact: `opendbc/car/vehicle_model.py` `create_dyn_state_matrices`; mass, wheelbase, centerToFront, tyre stiffness × paramsd's stiffness factor, rotationalInertia by `scale_rot_inertia`, from `0x28`'s CarParams), integrated at 100 Hz, giving the lateral deviation Δy and heading Δψ;
- **lane offset:** Δc(t) = −(Δy + l·Δψ)(t − L_img), in the a_s sign convention (c″ ≈ −v·ω, §1). Primary l = 0 (CG), L_img = 0.05 s; sensitivity l = centerToFront, L_img = 0 and 0.1 s;
- **policy:** an ARX model at the 20 Hz model rate, A(q)·r = B(q)·c + e, na = 10 (r lags 1–10), nb = 20 (c lags 0–19), applied to the deviations: Δr(t) = Σ a_i Δr(t−i) + Σ b_k Δc(t−k), updated every 5th controls cycle and held in between;
- **inside the loop:** Δr is added to the request before V0, so a candidate's request filter acts on r_log + Δr. For linear filters, filter(r_log + Δr) = filter(r_log) + filter(Δr): the log part is pre-filtered as now, the Δ part filtered in the loop.

**Identification of the policy:** ordinary least squares on r and c (both 0.05 Hz zero-phase 2nd-order high-pass, per run) on straight-clean H runs ≥ 20 s with both lanes ok. **Fit set:** E1, E2, E3 and the E4 opposite-direction routes (`0x1f`, `0x21`, `0x23`, `0x25`). Not used for the fit: the A-primary drives, `0x26`–`0x28`.
- **ARX adequacy:** A(z) stable, and on the held-out A-primary drives the free-run (c-driven, no r feedback) prediction explains ≥ 20% of the request's 0.2–0.7 Hz variance.

**Harness check before any result:** with the outer loop off (Δr ≡ 0) the new loop must be bit-identical to `s11_fastloop.closed_loop` for A0, D2, C4 and D2C4 on at least 10 runs from 4 eras.

**Validation (on the A-primary drives, B's road; E4 plant primary, E2+E3 plant secondary):**
- **V1 adequacy of A0 with the outer loop** (sim vs logged): hold ±0.10, jumps ±35%, T ±35%, W ±40%, lane 0.2–0.7 Hz RMS ±40% (lane: c_sim = c_log + Δc); and no divergence (|Δc| p99 < 0.5 m).
- **V2 reproduction** of the on-car D2C4 effect: D2C4 vs A0, both with the outer loop, on the same drives. "Reproduces" if **all** of:
  - jumps/min change within the on-car 95% CI (−55.8…−25.2%);
  - T RMS change within −48.0…−27.7%;
  - W change > 0 and within −9.6…+44.8%;
  - lane-offset 0.2–0.7 Hz change within +20.5…+65.4%;
  - mean tracking error (all-engaged H) change within +16.2…+39.2%;
  - curve entry/exit lag change within +0.046…+0.137 s (`s12_curves` events and lag on all-engaged H runs ≥ 12 s).
  - The same comparison without the outer loop is reported, to show what the outer loop adds.
- **V3** (descriptive): D2C4 vs A0 with the outer loop on `0x28`'s own requests.
- If V1 and V2 pass on the primary plant, the outer-loop model is used to rank candidates in step 5. Otherwise step 2c.

### 2.4 Step 2c: fallback weave proxy (used only if 2b does not reproduce)

**This is a proxy, not a weave model.**
- Weave-band phase and gain of the request → a_s transfer (the M4 estimator) on simulated runs with logged requests replayed (no outer loop), straight-clean H, per candidate vs A0, same plant and era.
- **"Weave not up (proxy)"**: simulated W not up, **and** added phase lag ≤ 25% of D2C4's added lag on the same plant and era, **and** the band gain within ±10% of A0.
- Rationale (hypothesis): if the on-car lane-weave increase scales with the added weave-band lag, ≤ 25% of D2C4's lag predicts ≤ about +10% lane weave (25% of +41%).

## 3. Results

### 3.1 Step 2a: B's request weaves more (observation; `2a/request_weave.json`, `s15_mv_2a.py`, log `logs/s12mv-2a-20261007-162641.log`)

Straight-clean ≥ 55 mph on B's road. B = 399 s (401 s for the transfer estimates), A-primary = 1,006 s (1,065 s).

| Metric | A-primary | B | Change (95% CI) | vs A-day | Per-route A range |
|---|---|---|---|---|---|
| M1 request 0.2–0.7 Hz RMS (m/s²) | 0.0319 | 0.0423 | **+32% (+13…+51%)** | +25% (+7…+48%) | 0.0300…0.0347 (B above) |
| M2 a_s 0.2–0.7 Hz RMS (m/s²) | 0.0448 | 0.0569 | +27% (+5…+49%) | +27% | 0.0380…0.0495 (B above) |
| M3 lane-centre offset 0.2–0.7 Hz RMS (m) | 0.0167 | 0.0235 | +41% (+21…+66%) | +24% | 0.0152…0.0201 (B above) |
| request 0.05–0.7 Hz RMS | 0.0676 | 0.0763 | +13% (−9…+41%) | −5% | 0.0551…0.0837 |
| request 0.7–4 Hz RMS (jitter band) | 0.0237 | 0.0189 | **−20% (−28…−9%)** | −21% | 0.0194…0.0271 (B below) |
| M4 request → a_s, 0.2–0.7 Hz: gain / phase | 1.19 / −54.4° | 1.17 / −61.3° | phase −6.9° (−17.9…+1.0°); gain −1% | −11.2° (−23.5…−1.0°) | −47.7…−60.8° |
| M4, 0.2–0.4 Hz phase | −35.2° | −53.1° | −17.9° (−29.4…−8.4°) | | −29.9…−42.6° |
| M4, 0.4–0.7 Hz phase | −66.5° | −71.0° | −4.5° (−15.5…+2.9°) | | −60.8…−70.7° |
| M5 lane → request, 0.2–0.7 Hz: gain / phase / coherence | 0.98 / +55° / 0.38 | 1.49 / +51° / 0.71 | gain +52% (+17…+117%) | gain +78% | 0.64…1.33 / coh 0.21…0.60 |

M3 equals session 11r's value, as required.

**Verdicts by the pre-registered rules:**
- **(a) B's request weaves more:** +32%, CI excludes 0, and above every A drive.
- **(b) Not "more lag":** the full-band phase difference's CI includes 0.
- **(c) Reading by the rule:** request more, lag not more → **an exogenous request change (road, light, traffic), not attributable to D2C4 on this data.**

**Observations outside the rule (not used for a verdict):**
- In the 0.2–0.4 Hz sub-band B's wheel lags the request 18° more (CI excludes 0); in 0.4–0.7 Hz, where C4's lag is largest, only 4.5° (CI includes 0). C4 alone would add about 8.5° at 0.3 Hz and 15° at 0.55 Hz. So the sub-band pattern does not match C4's lag.
- On B the request follows the lane offset with a 52% higher gain and much higher coherence (0.71 vs 0.38). The midday A drive `0x20` (same time of day as B) is closest to B (gain 1.33, coherence 0.60). That fits either a stronger outer-loop oscillation on B or cleaner daylight lane perception; this data cannot separate them.
- **The request's own jitter band (0.7–4 Hz) is 20% lower on B.** Part of the on-car twitch reduction (jumps −42%) therefore came with a calmer request, not only from D2C4 (see §3.2).

### 3.2 Step 3: `0x28` plant check (model result vs observation; `3/plant_check.json`, `s15_mv_3.py`, log `logs/s12mv-3-20261007-162817.log`)

No outer loop; logged requests replayed. Straight-clean ≥ 55 mph runs ≥ 12 s; tracking and curve lag on all-engaged ≥ 55 mph runs ≥ 12 s.

| Source | Jumps/min | Hold | T RMS (°) | W RMS (°) | Reversals/min | a_s jerk RMS | M4 phase full / lo / hi | Mean \|error\| | Curve lag (s) |
|---|---|---|---|---|---|---|---|---|---|
| **B `0x28` logged (D2C4)** | 22.0 | 0.615 | 0.057 | 0.175 | 21.7 | 0.179 | −61.2 / −53.2 / −71.0° | 0.0641 | 0.282 (9 events) |
| sim D2C4, E4 plant | 16.1 (−27%) | 0.732 (**+0.117**) | 0.047 (−18%) | 0.155 (−12%) | 19.9 | 0.161 | −58.8 / −50.4 / −69.9° | 0.0599 | 0.322 |
| sim D2C4, E2+E3 plant | 18.4 (−16%) | 0.756 (**+0.141**) | 0.044 (−22%) | 0.149 (−15%) | 17.7 | 0.152 | −59.1 / −50.9 / −70.6° | 0.0598 | 0.294 |
| sim A0 on B's requests, E4 plant | 28.3 | 0.571 | 0.065 | 0.184 | 35.7 | 0.191 | −36.3 / −30.8 / −43.5° | 0.0487 | 0.198 |
| **A-primary logged (A0)** | 37.9 | 0.504 | 0.093 | 0.148 | 33.5 | 0.232 | −54.6 / −35.6 / −66.5° | 0.0505 | 0.188 (31 events) |
| sim A0, E4 plant | 32.8 (−14%) | 0.580 (+0.075) | 0.085 (−8%) | 0.143 (−4%) | 36.7 | 0.224 | −41.5 / −27.8 / −51.6° | 0.0460 | 0.215 |
| sim A0, E2+E3 plant | 30.5 (−20%) | 0.628 (**+0.124**) | 0.078 (−16%) | 0.136 (−8%) | 30.6 | 0.206 | −41.7 / −27.2 / −52.8° | 0.0449 | 0.201 |
| sim D2C4 on A-primary, E4 plant | 15.3 | 0.772 | 0.057 | 0.120 | 16.4 | 0.169 | −63.2 / −45.1 / −79.6° | 0.0542 | 0.297 |

**Verdicts by the pre-registered adequacy criteria:**
- **`0x28` with D2C4: fails on both plants**, on hold only (+0.117 and +0.141 vs ±0.10). Jumps, T and W are inside their limits. The model makes the wheel sit still more than it did on the car: the real D2C4 drive twitched more than predicted (22.0 vs 16.1 jumps/min).
- **A0 on the A-primary drives: passes with the E4 plant** (jumps −14%, hold +0.075, T −8%, W −4%); fails on hold with the E2+E3 plant (+0.124).

**Readings (model results; hypotheses where marked):**
- **The model's D2C4 effect on B's own requests** (E4 plant): jumps 28.3 → 16.1 (−43%), T −28%, W −16%, tracking +23%, curve lag +0.12 s. Against the on-car comparison (jumps −42% vs other days' A drives), the logged B jumps (22.0) are only 22% below what the model's A0 would do with B's requests (28.3). Since the model's A0 underestimates the A drives' jumps by 14%, the true within-drive reduction is probably between −22% and −42% (*hypothesis*).
- **Weave-band phase:** the model reproduces the logged D2C4 phase well (−59° vs −61°), but its A0 lags the real A drives 13° less (−41.5° vs −54.6°). So it **over-predicts D2C4's added weave-band lag** (+22° in the model vs +7° observed, §3.1). Relative phase predictions between variants are the usable part.
- **W:** with B's requests, the model's A0 gives W 0.184°, about B's logged 0.175°. In the model, B's higher W comes from B's request content (§3.1), not from D2C4's inner loop. D2C4 on the same requests lowers W (0.155°).

### 3.3 Step 2b: outer-loop policy model not adequate (model result; `2b/arx.json`, `s15_mv_arx.py`, log `logs/s12mv-arx-20261007-163015.log`)

- **ARX(10, 20) on 3,544 s** of the fit set: stable (max |pole| 0.94), one-step R² 0.91 (mostly the request's own autoregression).
- **Held-out free-run (lane-offset-driven) 0.2–0.7 Hz variance explained: A-primary 14.9%** (criterion ≥ 20%), B 24.6%, fit set 18.9%.
- **Verdict: not adequate by the pre-registered rule.** The closed-loop simulation with this policy was not built, and V1–V3 were not run. **Step 2c (the declared proxy) applies.**
- Observation about the fit: its lane → request response (gain 0.56 → 0.25, phase +109° → 0° over 0.2–0.6 Hz) disagrees with the closed-loop H1 estimate (§1: gain 1.0–1.6, phase about +50°). Plausible reasons (*hypotheses*, not tested): the same image produces both the lane estimate and the request (errors in variables), the model's temporal memory needs a different structure, and much of the lane offset's band content is perception noise (§1).
- **Possible next steps** (not done; each would need its own pre-registration): instrumental-variable identification (e.g. the steering-predicted lateral motion as instrument), lane lags ≥ 1 frame only, or a model with the policy's heading input from the full lane-line geometry (only the first x point is extracted now).

### 3.4 Candidate set and Amendment 8

- **User decision (2026-10-07):** all 9 proposed candidates (MV1–MV9), with red flags **reported only**: they rank candidates but don't fail them.
- Pre-registered as **Amendment 8** in the [D2C4 validation findings](2026-10-07-g70-d2c4-validation.md) §4 before any run. It holds the candidate table, the decision rule and the ranking.

**Harness** (`s15_mv_var.py`):
- `closed_loop_fp` is the shared numba loop copied line by line, plus a separate friction-path request (MV9).
- `simulate_mv` re-implements `s11_eval.simulate` on it, plus the shelf filter (MV8).
- `install()` points the shared per-file functions at it without editing them.
- θ0 (the whole-route convolution) is cached per route. It is the identical computation, so results stay bit-identical; check 1 and the reproduction check below confirm this.

**Checks** (logs `s12mv-check-*`, `s12mv-a8-*`):
1. **Checks 1+2:** `simulate_mv` vs the original `s11_eval.simulate` for A0, D2, D3, C4 and D2C4 on 12 runs (3 per era, straight-clean and all-engaged): **max difference 0**. Run before any candidate result.
2. **Check 3:**
   - MV8 with g = 0 equals D2C4 exactly;
   - g = 1 gives the raw request within 1.4e-17;
   - MV9 with the controller friction off equals D2 with friction off exactly (and MV9 differs from D2 with friction on).
   - Run before any candidate result.
3. **Check 4a:** the new transient runner reproduces all 144 stored Amendment 7 A0/D2C4 entries identically.
   - It was needed because `s12_transient.run()` passes `fr_dz_shift = False` for every variant.
4. **Check 4b:** the curve runner reproduces all 21 stored A0/D2C4 keys identically.
   - 4a and 4b were evaluated in the same runs that produced the candidate transient and curve results, not before them. Both passed, so no result depends on a failed check.

### 3.5 Amendment 8 transients (model results, E4 plant primary; `a8/transient_2a.json`, `a8/curves_2b.json`)

| Variant | Red flags (E4 plant; reported only) | Curve window, E2+E3: peak / mean error / lag / jumps |
|---|---|---|
| D2C4 (ref.) | R5 (0.6 Hz, all speeds), R3 (0.3 m/s² at 75 mph), C3 | +16% / **+28%** / +0.089 s / −20% |
| MV1 dz 0.5 | R3 (30 and 33.5 m/s, both step sizes) | +10% / +18% / +0.034 s / −15% |
| MV2 dz 0.6 | R3 (as MV1) | +13% / +22% / +0.044 s / −19% |
| MV3 shifted 0.4 | R3 (33.5 m/s) | +13% / +23% / +0.048 s / −21% |
| MV4 shifted 0.3 | R3 (33.5 m/s) | +11% / +19% / +0.042 s / −19% |
| MV5 D2 + 4 Hz | R3 (33.5 m/s, 0.3 step) | +10% / +19% / +0.050 s / −14% |
| MV6 D2 + 3 Hz | R3 (33.5 m/s, 0.3 step) | +12% / +23% / +0.064 s / −15% |
| MV7 shifted 0.3 + 4 Hz | R3, **R5 (0.6 Hz at 33.5 m/s)**, C3 | +15% / **+26%** / +0.071 s / −21% |
| MV8 D2 + shelf | R3 (33.5 m/s) | +10% / +20% / +0.052 s / −16% |
| MV9 D2 + friction-path filter | R3 (30 and 33.5 m/s) | +10% / +18% / +0.041 s / −13% |

- **Every candidate except MV7 has fewer red flags than D2C4.** All lose R5 except MV7, and none trips C1 or C2.
- R3 (slower settling of small steps at 75 mph) comes from any deadzone ≥ 0.3°, as it did for D2. It is not a pass/fail criterion here (user decision).

### 3.6 Amendment 8 grid and verdict (model results; `a8/grid.json`, `a8/summary.json`; logs `s12mv-a8-grid-20261007-164207.log`, `s12mv-a8-summary-*`)

- **Reproduction check:** A0 and D2C4 with the E4 plant equal the stored Amendment 6 outputs on all 12 twitch and 28 tracking keys (identical).
- E4 plant, change vs A0 of the same era. "Lag" is the added request → a_s weave-band (0.2–0.7 Hz) phase lag, in degrees. The proxy bound is ≤ 25% of D2C4's lag, i.e. ≤ 5.5°.

| Variant | Jumps E2 / E3 | T E2 / E3 | W E2 / E3 | Lag E2 / E3 (fraction of D2C4) | Gain E2 / E3 | Tracking E2 / E3 | Steering-proxy jerk / steps (E2) | Verdict: criteria missed |
|---|---|---|---|---|---|---|---|---|
| D2C4 (ref.) | −45 / −52% | −33 / −41% | −20 / −25% | +22.1 / +22.1° (1.00) | −19 / −23% | +21.0 / +19.6% | −23 / −29% | (reference) weave proxy; E2 tracking |
| MV1 dz 0.5 | −46 / −47% | −25 / −32% | −19 / −21% | +16.5 / +16.0° (0.75 / 0.72) | −16 / −18% | +15.3 / +14.6% | −18 / −34% | E2 twitch (T); weave proxy |
| MV2 dz 0.6 | −56 / −61% | −31 / −37% | −20 / −21% | +18.2 / +17.6° (0.83 / 0.80) | −16 / −18% | +17.8 / +18.0% | −20 / −50% | weave proxy only |
| MV3 shifted 0.4 | −54 / −58% | −32 / −39% | −20 / −22% | +17.5 / +17.4° (0.80 / 0.79) | −15 / −17% | +18.4 / +17.4% | −21 / −53% | weave proxy only |
| MV4 shifted 0.3 | −47 / −49% | −28 / −34% | −18 / −20% | +15.4 / +14.8° (0.70 / 0.67) | −15 / −16% | +15.1 / +14.1% | −18 / −42% | E2 twitch (T); weave proxy |
| MV5 D2 + 4 Hz | −29 / −37% | −24 / −29% | −17 / −18% | +17.2 / +16.4° (0.78 / 0.74) | −17 / −17% | +15.7 / +14.8% | −18 / −15% | twitch both eras; weave proxy |
| MV6 D2 + 3 Hz | −38 / −41% | −28 / −33% | −18 / −20% | +18.9 / +18.4° (0.86 / 0.83) | −17 / −19% | +18.2 / +16.3% | −20 / −23% | E2 twitch; weave proxy |
| MV7 shifted 0.3 + 4 Hz | −51 / −55% | −33 / −39% | −19 / −21% | +19.1 / +18.7° (0.87 / 0.85) | −16 / −18% | +19.4 / +18.7% | −22 / −48% | weave proxy only |
| MV8 D2 + shelf | −37 / −46% | −29 / −34% | −19 / −22% | +17.7 / +16.9° (0.80 / 0.76) | −18 / −19% | +15.7 / +14.6% | −20 / −26% | E2 twitch; weave proxy |
| MV9 D2 + friction-path filter | −39 / −48% | −26 / −32% | −19 / −21% | +16.1 / +14.9° (0.73 / 0.67) | −17 / −18% | +14.7 / +14.6% | −18 / −30% | E2 twitch; weave proxy |

**Verdict by the pre-registered rule: no candidate passes.**
- **Every candidate fails the weave proxy.** Each adds 15–19° of weave-band lag (67–87% of D2C4's), against a bound of 25%, and cuts the weave-band gain by 15–19% (bound ±10%). Simulated W is down for all of them.
- **On twitch and tracking, MV2, MV3 and MV7 pass on both primary eras;** the others miss the T or jumps threshold on E2.
- The secondary eras (E1/E4) and the E2+E3 plant give the same picture: every candidate's lag is 0.58–0.90 of D2C4's, and no candidate passes the weave proxy (full tables in `summary.json` and the summary log).

**Exploratory split** (after the verdict; `a8/split_exploratory.json`, `s15_mv_split.py`; changes no verdict). In-context weave-band lag vs A0, E4 plant:

| Variant | E2 | E3 |
|---|---|---|
| D2 alone | +13.0°, gain −16% | +12.3°, gain −16% |
| C4 alone | +10.0°, gain −5% | +9.6°, gain −5% |
| D2C4 | +22.1°, gain −19% | +22.1°, gain −23% |

**Reading (model results; hypotheses where marked):**
- **With realistic small-amplitude requests, the deadzone causes at least as much weave-band lag as the 2 Hz filter, plus most of the gain loss.**
  - The Amendment 7 sines (0.3 m/s², about 3× the deadzone) hid this: there D2 added only 1–2°.
  - In this model every mechanism that cuts the twitch does so by making the wheel ignore small errors. Lane-keeping corrections on a straight road are also small errors, so they are followed later and more weakly.
  - *Hypothesis:* in this model, a twitch reduction of about 40–60% comes with roughly 15–20° of added weave-band lag, whichever mechanism produces it. The candidates trace one frontier: no filter-free variant escapes it.
- **Where the candidates do differ is transient cost** (§3.5): the no-filter deadzone variants (MV2, MV3) match D2C4's twitch reduction with about half its curve lag (+0.04–0.05 s vs +0.09 s), curve-window error +22–23% vs +28%, and no R5 or C3.
- **How much the proxy matters for the car is uncertain:**
  - the model over-predicted D2C4's added weave-band lag on the car (+22° vs +7°, §3.2);
  - the step 2a log check's pre-registered reading attributes B's extra weave to an exogenous request change;
  - the outer-loop model was not adequate (§3.3).
  - So "weave proxy fail" means "no better than D2C4 on weave-band lag in this model". It does not mean the variants would weave more on the car.

## 4. Recommendation (offline evidence only; for the user's decision)

1. **Keep D2C4 installed while more on-car data come in (recommended).**
   - No candidate meets the pre-registered weave proxy, so none is shown to fix weave better than D2C4.
   - The one on-car D2C4 drive's weave increase is not attributable to D2C4 by this session's pre-registered log check.
   - Its twitch reduction is partly confounded by a calmer request (§3.1–3.2).
   - The A/B follow-up session (more same-road daylight B drives, the road video, the driver's assessment) is what can settle whether D2C4 causes weave.
2. **If more B drives confirm that weave is worse on D2C4:** the model offers no lag-free twitch fix.
   - The best-supported alternative to test on the car would be **MV3** (continuous 0.4° friction deadzone, no filter) or **MV2** (existing 0.6° deadzone, a car-table value only). Either keeps D2C4's twitch reduction in the model with about half its transient cost.
   - But their weave-band lag is about 80% of D2C4's. They should be expected to weave about as D2C4 does, not less.
   - Rolling back to `c027a92857` is the other option.
   - Either way, the next on-car A/B must use the lane-offset 0.2–0.7 Hz band and the request's own weave band (step 2a's M1) as weave criteria, so that a request change can be told apart from a response change.
3. **Not recommended now:** replacing D2C4 with any MV variant. It would need code, tests, two-round QA, new artifacts and an on-car A/B, for a change the model predicts is no better on weave.

**What would change this:** an adequate outer-loop model (§3.3 next steps), or on-car evidence that the weave increase tracks the added lag.

## 5. Focused review of this session's analysis (one independent adversarial agent; 2026-10-07)

**Scope:**
- `s15_mv_2a/3/arx/var/grid/transient/curves/summary/check.py`, against §2 of this doc and Amendment 8 (plus Amendment 7's definitions) only.
- The agent was read-only on project files, used ≤ 2 processes, and was told not to read the changelog, handoffs or results.
- Its scripts and logs are in `E:\DragalPilot\scratch\review-s12mv\`.

**Result:** no blocker or major. Every finding was verified by the coordinator against the code and the reviewer's logs, and all are agreed. **No verdict changes.**

| # | Severity | Finding | Verification | Disposition |
|---|---|---|---|---|
| 1 | minor | The θ0 cache was keyed on `id(X)` without holding a reference. A freed route's id could be reused, giving a stale θ0. | The reviewer re-ran the full grid with θ0 always recomputed: 7,854 calls, 0 stale; all 456 grid keys identical to `a8/grid.json`. | **Fixed:** the cache now holds X and compares identity. Check 1–3 re-run: bit-exact, PASS (`logs/s12mv-check-20261007-165208.log`). No result changes. |
| 2 | minor | 2a's M4/M5 estimator splits runs into ≤ 60 s pieces (the bootstrap units) before Welch. The pre-registration said pooled over runs. | Whole-run estimator: B −60.7°, A −55.1°, so the difference is **−5.6°** (reported −6.9°). | **Recorded as a deviation.** The rule (b) verdict ("not more lag", CI includes 0) is unchanged. |
| 3 | minor | Step 3 pools T/W as the square root of the weighted mean square. Amendment 6's adequacy used the linear weighted mean of per-run RMS. | Linear pooling moves W by ≤ 3 points (e.g. E4/A0 +5% → +8%) and T by ≤ 1 point. | Recorded. The adequacy verdicts (fail on hold) are unchanged. |
| 4 | note | Step 3 applied B's road mask to `0x28` ("whole route" pre-registered). | Identical without the mask. | Recorded. |
| 5 | note | The 2a lane CI (+20.7…+66.2%) differs slightly from session 11r's (+20.5…+65.4%), because the bootstrap stream is consumed in a different order. | Point values identical. | The on-car reference CI stays session 11r's. |
| 6 | note | The ranking counts distinct flag types. | No candidate passes, so the ranking is empty. | Recorded. |
| 7 | note | a_s is point-sampled at 20 Hz without an anti-alias filter. | Affects coherence only. | Recorded. |

**Independent reproductions:**
- 2a M1 +32.5%.
- Weave-proxy lag (E4 plant): D2C4 +22.6 / +22.2°, MV2 +18.6 / +17.5°, MV9 +16.6 / +15.0° (E2 / E3), against the reported +22.1 / +22.1, +18.2 / +17.6, +16.1 / +14.9°. Lag fractions 0.68–0.82, so the c2 failures stand.

**Also checked and found correct:**
- `closed_loop_fp` equivalence; MV8 and MV9 as specified;
- the monkeypatch chain (transients, curves, tracking);
- the decision rule;
- ARX fit/held-out separation and the VAF definition;
- selections and the bootstrap.

**QA stage:** focused review done (analysis only, no product change). Two-round QA does not apply.

## 6. Follow-up: is B's extra weave really not attributable to D2C4? (exploratory, post hoc; user question 2026-10-07)

**User:** "An increase of 32% being caused by the same exact model on the same stretch of roadway on a clear day is illogical. Are we sure this is the case?"

**Exploratory check** (`s15_mv_2a_followup.py`, log `logs/s12mv-2a-followup-20261007-173651.log`; not pre-registered; the recorded §3.1 verdict text stands as what the rule gave):
- **Speed is not the explanation.** The request is curvature × v², so a faster drive would show more request weave. But B averaged 32.6 m/s on straight-clean ≥ 55 mph, inside the A drives' 29.4–34.4 m/s. In curvature units B is 0.43 vs 0.30–0.39 (×10⁻⁴ /m).
- **Pairwise on exactly the same road samples** (B restricted to each A drive's road, that drive restricted to B's), B vs each A drive, 0.2–0.7 Hz RMS:

  | A drive | Request weave | Curvature units | Wheel (a_s) | Lane offset | Request jitter 0.7–4 Hz |
  |---|---|---|---|---|---|
  | `0x26` (dark) | +41% | +43% | +33% | +40% | −20% |
  | `0x1e` (dark) | +32% | +30% | +27% | +53% | −25% |
  | `0x20` (midday, same time of day as B) | **+9%** | +16% | +21% | **+30%** | **−1%** |
  | `0x22` (low sun) | +42% | +73% | +37% | +22% | −31% |
  | `0x24` (dark) | +48% | +29% | +36% | +56% | −9% |

**Revised reading (coordinator; supersedes the "exogenous" reading of §3.1 as an interpretation):**
- **The §3.1 rule was too blunt.** In closed loop the request is not an exogenous input. The model re-plans from the car's lane position, so a less-damped lane-keeping loop raises the request's own weave. The rule assumed that would also show as a significantly larger measured wheel lag.
  - The lag measured on the car is in that direction (−5.6…−6.9°; −18° in 0.2–0.4 Hz, CI excludes 0), but smaller than the model predicts.
  - The lane → request coherence rose from 0.38 to 0.71. That is what a loop-dominated oscillation looks like; added perception or road noise would lower it, not raise it.
- B is above every same-road A drive on every weave metric, at matched speed, and the A drives agree closely with each other. **D2C4 is the most likely cause of the weave increase** (*hypothesis*, one B drive).
- **Not excluded:**
  - the date (B is 2026-10-07; four of the A drives are from 2026-10-06);
  - traffic (no video yet);
  - pure chance with a single B drive.
- **Against the light-matched midday drive `0x20`** (121 s), the request difference shrinks to +9%, but the lane-offset (+30%) and wheel (+21%) weave increases remain.
  - The twitch-band request jitter is the same as `0x20`'s (−1%). So B's "calmer request" (§3.1) is probably a daylight effect, not D2C4's.
  - The jitter reduction then belongs to D2C4 only as far as the wheel itself is calmer: the logged jumps were 22.0/min on B vs 19.3/min on `0x20`.
- **Consequence for §4:**
  - "Keep D2C4 while collecting data" rested partly on the weave not being attributable to D2C4. That support is withdrawn.
  - The Amendment 8 result becomes more important: in the model, every candidate twitch fix adds 67–87% of D2C4's small-signal weave-band lag. If D2C4's weave increase is real, MV2/MV3 would be expected to weave too.

## 7. Root cause of D2C4's on-car weave: pre-registration (written 2026-10-07 before any of these metrics was computed)

**User:** "I'd rather find a logical defensible root cause for the weave in D2C4 because it seems to have addressed a lot of the other concerns."

**Hypotheses:**
- **H1, filter lag:** C4 delays the request (first-order 2 Hz: atan(f/2), i.e. 8.5° at 0.3 Hz and 15° at 0.55 Hz). The lane-keeping loop loses phase margin. Linear: the same at every amplitude, and entirely in the request → setpoint step.
- **H2, deadzone backlash:** inside ±0.4° (≈ 0.1 m/s² at 75 mph), V0's friction term is zero (`apply_center_deadzone`) and only P (≈ 1×error) and a slow I act. Static friction then holds the wheel until the error leaves the band, and the friction term switches on in a step.
  - In the lane-keeping loop (lane position is a double integral of the response) that is a relay with a deadband: a classic cause of a slow limit cycle (hunting).
  - It predicts: lag **and** gain loss concentrated at **small** correction amplitudes; more and longer wheel holds that end with |error| near the band edge; lane drift during holds.
- **H0, not D2C4:** date, traffic, or chance (one B drive). No inner-loop change would then be visible.

**Source/log facts used:**
- On B, `torqueState.desiredLateralAccel` (dataset `des`) is the setpoint after C4. With lat_delay ≥ dt, V0's setpoint equals the current (filtered) request.
- On A, `des` equals the raw request. So on B, request → `des` is C4 alone, and `des` → measurement is the rest of the inner loop (D2, controller, steering).

**Data:**
- Arms as §2: B = `0x28` on its own road; A-primary = 5 drives on B's road; the light-matched `0x20` reported alongside.
- Straight-clean ≥ 55 mph, Amendment 5 masks (runs ≥ 8 s, 2 s trimmed).
- Signals at 100 Hz: request r = desiredCurvature·v², setpoint `des`, measurement a_s = V0's map of the logged angle, error e = des − a_s. Lane offset from modelV2 at 20 Hz.

**Tests:**
- **T1, decomposition** (runs ≥ 10 s, Welch 10 s Hann 50%, cross-spectra pooled over 60 s pieces as in §3.1; bands 0.2–0.7, 0.2–0.4, 0.4–0.7 Hz):
  - transfers r → des, des → a_s and r → a_s, gain and phase per arm;
  - bootstrap (60 s units, 2,000, `default_rng(0)`) of B − A for the des → a_s phase and gain;
  - also: B's r → des against the theoretical 2 Hz first-order filter.
- **T2, amplitude dependence:**
  - non-overlapping 10 s windows inside the runs;
  - per window, the des → a_s 0.2–0.7 Hz transfer (single-window cross-spectra) and the window's des 0.2–0.7 Hz RMS;
  - windows binned by des RMS terciles, with the bin edges from the pooled A-primary windows;
  - per arm and bin: pooled gain and phase.
- **T3, holds:**
  - a hold is a stretch of ≥ 1.0 s where the logged angle stays within a 0.1° range;
  - per arm: holds/min, mean duration, fraction of time in holds;
  - |e| at hold end, as a mean and as a fraction ≥ 0.08 m/s²;
  - |lane-offset change| across the hold (20 Hz, lanes ok).
- **T4, error weave:** e 0.2–0.7 Hz RMS per arm, and the coherence of e with the lane offset (20 Hz model times, as §3.1).

**Decision rules (per test, reported separately):**
- **H1 supported** if B's r → des lag matches the theoretical filter within 3° in both sub-bands, and C4's lag is a substantial share of B's total extra r → a_s lag.
- **H2 supported** if all of:
  - (a) T1 des → a_s on B shows more lag (B − A phase CI below 0) **or** a gain loss (gain-change CI below −10%);
  - (b) T2 B's gain deficit vs A is larger in the smallest-amplitude bin than in the largest;
  - (c) T3 B has longer holds **and** a larger mean |e| at hold end than A.
- **H0 favoured** if T1 des → a_s shows no change (CI includes 0, gain within ±10%) **and** T3 shows no hold difference.
- H1 and H2 can both be supported. The light-matched `0x20` comparison is reported for every metric; one B drive limits every verdict.

## 8. Root cause of D2C4's on-car weave: results (observation; `rc/weave_root_cause.json`, `s15_mv_rc.py`, log `logs/s12mv-rc-20261007-174614.log`)

Straight-clean ≥ 55 mph on B's road: B 5.9 min, A-primary 15.7 min, `0x20` 1.7 min. Phase is response minus input (negative = lag). Δ = B − A-primary with 95% bootstrap CI.

**T1 decomposition of the request → wheel path:**

| Path | Band | B gain / phase | A-primary gain / phase | Δ phase (CI) | Δ gain (CI) |
|---|---|---|---|---|---|
| request → setpoint (= C4 on B; identity on A) | 0.2–0.4 Hz | 0.99 / −7.8° | 1.00 / 0° | −7.8° (−8.3…−7.4) | −1% |
| | 0.4–0.7 Hz | 0.98 / −12.1° | 1.00 / 0° | −12.1° (−13.0…−11.5) | −3% |
| setpoint → wheel (D2, controller, steering) | 0.2–0.4 Hz | 1.14 / −45.8° | 1.11 / −36.1° | **−9.7° (−19.4…−1.9)** | +3% (−9…+15%) |
| | 0.4–0.7 Hz | 1.35 / −56.5° | 1.35 / −65.8° | +9.3° (−1.7…+15.9) | 0% (−7…+6%) |
| | 0.2–0.7 Hz | 1.23 / −51.1° | 1.22 / −55.4° | +4.3° (−5.6…+11.0) | +1% (−7…+8%) |
| request → wheel (total) | 0.2–0.4 Hz | 1.13 / −54.1° | 1.11 / −36.1° | **−18.0° (−27.8…−10.5)** | +2% |
| | 0.4–0.7 Hz | 1.31 / −68.5° | 1.35 / −65.8° | −2.7° (−14.2…+4.1) | −3% |

- **C4 works exactly as designed.** B's request → setpoint lag is 7.8° and 12.1°, against the theoretical first-order 2 Hz filter's ≈ 7° and 14° over those bins (within 3°).
- `0x20` (light-matched) setpoint → wheel at 0.2–0.4 Hz: −37.8°. B's −45.8° is 8° beyond it too.

**T2 setpoint → wheel by amplitude** (10 s windows; tercile edges 0.025 / 0.032 m/s² from A-primary):

| Bin | B windows | B gain / phase | A-primary windows | A gain / phase |
|---|---|---|---|---|
| small | 3 | 0.91 / −89° | 25 | 1.23 / −62° |
| middle | 6 | 1.20 / −59° | 25 | 1.23 / −56° |
| large | 19 | 1.31 / −48° | 25 | 1.22 / −54° |

B's small-amplitude response is weaker (−26%) and later (−27°); its large-amplitude response is not. Only 3 of B's windows are small-amplitude: B spends most of its time at larger weave amplitudes.

**T3 wheel holds (≥ 1 s within 0.1°):**

| Arm | Holds/min | Mean / p90 duration (s) | Time in holds | Mean \|error\| at hold end (m/s²) | ≥ 0.08 at end | Mean \|lane change\| during a hold (m) |
|---|---|---|---|---|---|---|
| B | 18.6 | 1.92 / 3.29 | 59% | 0.062 | 29% | 0.039 |
| A-primary | 14.5 | 1.68 / 2.75 | 40% | 0.054 | 27% | 0.032 |
| `0x20` (midday) | 18.9 | 1.86 / 2.77 | 59% | 0.050 | 24% | 0.039 |

**T4 tracking error e = setpoint − wheel**, 0.2–0.7 Hz: RMS 0.048 vs 0.041 m/s², **+18% (CI +6…+34%)**. Coherence of e with the lane offset 0.50 vs 0.23 (`0x20`: 0.32).

**Verdicts by the pre-registered rules:**
- **H1 (filter lag): supported.** C4's lag matches theory, and it is a substantial share of B's extra lag: all of it over 0.2–0.7 Hz, 43% of it at 0.2–0.4 Hz.
- **H2 (deadzone backlash): not supported by the strict rule.** Criterion (a) fails on the full band (the CI includes 0) and holds only in the 0.2–0.4 Hz sub-band. (b) is met, but on 3 windows. (c) is met against A-primary but not against the light-matched `0x20`. **Partial support, concentrated at 0.2–0.4 Hz and small amplitudes.**
- **H0 (not D2C4): not favoured.** Holds and tracking error differ, and the request → wheel lag at 0.2–0.4 Hz is 18° larger (CI excludes 0), 8° beyond the light-matched drive.

**Reading:**
- **The car and the model agree in the lane-keeping band.** At 0.2–0.4 Hz (2.5–5 s periods, where this car's weave has always been: session 4b's ~3 s weave), D2C4 adds **18° of lag on the car**: 8° from C4 and 10° after it.
- The stick-slip model (Amendment 8 grid and exploratory split, E2/E3, same estimator) predicts **17–18° for D2C4 at 0.2–0.4 Hz: 7° from C4 alone and 9–10° from D2 alone.**
- In the 0.4–0.7 Hz sub-band the model over-predicts the lag (D2C4 +27–29°, the car about +3°). That is why the full-band proxy over-predicted (§3.2).
- **Mechanism (hypothesis, well supported in this band; one B drive):**
  - the twitch fix removes the friction term's push for small errors (D2) and delays the request (C4);
  - together they cost about 18° of phase in the lane-keeping loop at its weave frequency;
  - the model's lane-keeping (outer) loop is then less damped. So the car drifts further before each correction (tracking-error weave +18%, now twice as coherent with the lane offset), the model corrects harder (request weave +32%, lane → request coherence 0.38 → 0.71), and the lane offset weaves more (+41%).
  - Physically: the wheel is held by static friction longer at small errors (time in holds 40% → 59%), so small lane corrections start later.
- **The deadzone part is the small-signal part.** The data are consistent with D2 slowing exactly the small corrections lane-keeping needs on a straight road (T2 small bin), not large ones.
- **Weave-band lag at 0.2–0.4 Hz by variant** (model, E2 / E3; from `a8/grid.json`, exploratory):
  - D2C4 +16.5 / +17.6°;
  - MV1 +12.7 / +13.6°; MV2 +14.2 / +15.3°; MV3 +13.7 / +15.2°; MV4 +11.3 / +13.0°;
  - MV5 +12.6 / +13.6°; MV6 +14.4 / +15.2°; MV7 +14.5 / +16.1°;
  - MV8 +13.4 / +13.9°; MV9 +11.9 / +12.2°.
  - None recovers more than about 5° of D2C4's 17°, because each keeps a deadzone ≥ 0.3°.

**What would make it decisive:** an on-car isolation of the two halves (a D2-only and a C4-only build on the same road in daylight). The model and the car's decomposition predict about 10° and 8° respectively at 0.2–0.4 Hz.
