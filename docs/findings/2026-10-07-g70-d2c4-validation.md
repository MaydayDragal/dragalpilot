# G70 2024: validation of twitch candidate D2C4 (2026-10-07, session 11)

Continues the [root-cause findings](2026-10-07-g70-twitch-root-cause.md) (§7.8: D2C4 = `steeringAngleDeadzoneDeg` 0.4° + causal 2 Hz desiredCurvature low-pass) and follows the 4 steps of the [s10b handoff](../sessions/2026-10-07-s10b-d2c4-validation-handoff.md) §9.

Every evaluation reports three outcome groups together: **wheel jitter** (hold-and-jump), **weaving** (0.2–0.7 Hz, lane position) and **overall comfort** (§2.1).

**Offline only until step 4.** No device access without the user's explicit per-action authorization.

Evidence labels: **source fact** (file + revision `c027a92857`), **observation** (rlog, route, time), **model result**, **hypothesis**.

## 1. Step 1: focused adversarial review of the session 10 model/harness

**Status: done** (focused review, CLAUDE.md §5; not two-round QA).

**Reviewer:** one new agent, given only the code, the source, data paths, neutral questions and the pre-registered criteria, with no results or conclusions from the findings or handoff. Isolation was instructional (it was told not to read `docs/`, the changelog or memory), not enforced; for a focused review CLAUDE.md §5 does not require enforced isolation. Its scratch scripts and outputs are in `E:\DragalPilot\analysis\g70-d2c4-20261007\qa\review-s11-harness\` (`r1`–`r9`; moved from `temporary\s11-review`). The round 1/2 QA material for step 3 is in the sibling folders `qa1-cooperative\` and `qa2-package.txt`. It first reproduced the stored step 4 numbers exactly, so its sensitivity tests share the session 10 baseline.

**Findings and coordinator verification** (every finding checked against code, source or a reproduction; all agreed, so no tiebreaker was needed):

| # | Severity | Finding | Coordinator verification | Disposition |
|---|---|---|---|---|
| 1 | major | Criterion 3 for D2C4 on E4 is fragile. θ0 (10 s centred average of logged angle − a/b·logged command, `s11_eval.py`) carries the curve regime, which the plant (fit on straights only) never identified. With a 10/30/60 s θ0 window, E4's tracking change is +19.4/**+20.6**/+15.1%. E1's A0 curve ratio (1.066 → 1.049 → 1.031), which motivated the Amendment 4 clarification, is largely a θ0 artefact. | Confirmed: the reviewer's `r6_track_theta0.py` calls the harness loop unchanged with only θ0 swapped, and its 10 s row equals the stored results. | **Agreed.** Not fixable by a code change. Criterion 3 for D2C4 is reported as **not robustly met**; carried into step 2 (§2.3). |
| 2 | major (method) | Held-out reuse. E1/E4 informed both the design of the Amendment 4 candidates (after the Amendment 3 results) and the choice among about 17 candidates. So D2C4's pass is not an independent held-out confirmation, and no untouched validation set remains. | Confirmed by the record: root-cause findings §7.6 → §7.8, run logs 07:42 → 09:07. | **Agreed.** Carried into step 2 (§2.3). |
| 3 | major (interpretation) | With A7 (no quantization), the metrics were computed on the unquantized angle, so A7's −41/−57% jump change is a metric artefact. | Confirmed (`s11_fastloop.py` L51/138). The root-cause findings §7.5 already said the jump count changes "because the simulated angle is no longer stepped" and called A7 not implicated, but gave no corrected number. | **Fixed:** A7 metrics now use the 0.1° reported angle. A7 is −3/+1% jumps, −1/0% T: not implicated, verdict unchanged. |
| 4 | minor | The controller port omits `latAccelOffset` (`ff -= latAccelOffset`, `latcontrol_torque_v0.py` L98). It is non-zero on all E4 routes and E2 `0x12`/`0x15` (−0.02…−0.08 m/s²). | Confirmed in code. **Open-loop replay against the logged controller** (`s11_replay_check.py`): route `0x12` torque residual p50 6.4e-3 → 8.6e-5 with the fix; zero-offset routes unchanged (~1e-4). | **Fixed** in both loops (`pl.roll_ff`). |
| 5 | minor | The integrator starts at 0 at the warm-up start instead of V0's value. Source fact: V0 never resets its PID (`LatControl.reset` only clears `sat_time`, `latcontrol.py` L21; controlsd L131–132). | Confirmed in code and source. | **Fixed:** I starts at the logged `i` of the last active cycle before the warm-up (`pl.i_init`). |
| 6 | minor | Definitions differ: runs ≥ 12 s, no 2 s end trim for jumps/hold, length-weighted per-run RMS, tracking drops runs < 12 s. Micro-reversals were not computed. | Confirmed. Trim effect ≤ 1.3% (reviewer). | **Recorded** as the actual definitions (applied identically to sim and log). Reversals **added** (the twitch findings' counter, unchanged). |
| 7 | minor | C5 changed the last KP node (30 m/s), which also lowers KP between 15 and 30 m/s. | Confirmed. | Recorded (wording only; C5 failed anyway). |
| 8 | minor | `u_out[k]` is the rate-limited output of command k−1 (documented as "this cycle's"). The loop timing is consistent with that; only step 1's `dcmd`/`cmd_at` shift by 10 ms. | Plausible; consistent with session 6's timing note. | Recorded. |
| 9 | note | The equivalence check covered only the default and friction-off paths, on 6 E4 runs; the candidate options were checked only numba-vs-numba. | Confirmed. | **Fixed:** the Python reference now has independent per-cycle D2 and C4 paths, and the check runs the production call on 10 runs from all four eras × {V0, friction 0, D2, C4, D2C4}: **max difference 0 (bit-exact)** (`logs/s10-s11-fastcheck3-20261007-114716.log`). Amendment 4 limit cases still exact. |
| 10 | note | Modelling limits: replayed requests (no outer loop), no vehicle dynamics, `s11_robust.py` doesn't perturb a or c, A6 is non-causal by one update, Karnopp misbehaves if fc > fs (not the case for any run). | Agreed. | Recorded as limitations. |

**Remaining replay residual:** on route `0x1e` the open-loop replay from route start still differs from the logged torque by p50 2.4e-3 (about 1 count). That equals a slow integrator difference of about 0.009 m/s²; the integrator starts exactly at 0 at the first engagement, as logged. Probably a freeze/clip timing difference. The closed-loop runs start from the logged integrator, so this does not accumulate there.

**Re-run on the fixed harness** (same plant, same arguments; `analysis/g70-d2c4-20261007/rerun_v2/`, runner `run_s11_rerun_v2.sh`, summary `s12_summary_v2.py`, logs `logs/s10-s11v2-*.log`). The originals are kept as `*.s10.py.bak`.

- **Adequacy (held-out E1/E4, 55+ mph): still passes.** E1 jumps +16%, hold −0.00, T −5%, W +7%; E4 −11%, +0.08, −5%, +0%. Ordering E3 < E4 < E1 is reproduced.
  - Newly reported, not part of the criteria: reversals/min sim vs log E1 55 vs 43, E4 29 vs 27. The steering-proxy comfort metrics (a_s fast RMS, jerk, steps) agree within 6–16% on E1/E4.
- **Ablations:** verdicts unchanged (A3 −56/−56% jumps, A5 −70/−54%, A2 worse; A7 no longer shows a jump change).
- **Candidates:** verdicts unchanged. Nothing in Amendment 3 passes.
- **D2C4 passes the pre-registered criteria on the fixed harness:**

  | Era | Jumps | T | W | Reversals | a_s 0.5–4 Hz RMS | a_s jerk RMS | a_s steps | Mean \|error\| | Curve ratio |
  |---|---|---|---|---|---|---|---|---|---|
  | E1 | −60% | −42% | −11% | −60% | −30% | −31% | −54% | +14.2% | 1.063 (A0 1.068) |
  | E4 | −50% | −37% | −20% | −56% | −29% | −27% | −46% | **+19.3%** | 1.028 (A0 1.029) |

  - **Robustness** (fixed harness): the twitch reductions hold (jumps −47…−63%, T −36…−43%). The E4 tracking change exceeds 20% in 4 of 10 plant perturbations (fs ×0.7 +24.2%, td ×0.5 +21.9%, fc ×0.7 +21.4%, b ×1.2 +20.8%).
- **Curve-regime check** (not identified, observational): simulated A0 vs logged tracking on all engaged 55+ mph runs has mean |error| 0.055 vs 0.060 (E1) and 0.046 vs 0.051 (E4), curve ratio 1.068 vs 1.072 and 1.029 vs 1.033. θ0 is built from the logged angle, so this agreement is partly by construction (finding 1).

**Conclusion of step 1:** the twitch mechanism, the model's adequacy on straights and D2C4's twitch and comfort-proxy reductions survive the review and the fixes. **What does not survive:**
- D2C4's offline pass is not an independent held-out confirmation (finding 2).
- Its tracking criterion is met only marginally and not robustly (finding 1 and the robustness check).

## 2. Step 2 pre-registrations

### 2.1 Amendment 5: comfort metrics and log baselines (step 2e). Written 2026-10-07 before any comfort number was computed.

**Signals (source facts, `c027a92857`):**
- This revision logs no `livePose`. locationd publishes `deviceMotion` (20 Hz, Kalman-filtered; `cereal/log.capnp` L1396, `services.py` L58) and consumes the raw `accelerometer` and `gyroscope` events (104 Hz, logged; `services.py`).
- locationd maps a raw sample `v` to the device frame (x forward, y right, z down) as `[-v[2], -v[1], -v[0]]` for both sensors (`selfdrive/locationd/locationd.py` L111–112, L131–132), and gets `device_from_calib = rot_from_euler(rpyCalib)` from `extrinsicsCalibration` (L150–158, logged at 4 Hz).
- `carState.yawRate` is 0 on this car (twitch findings §5.1).

**Lateral acceleration `a_y` (primary comfort signal):**
- Raw `accelerometer` events of type `acceleration`, timed by their sensor `timestamp` (ns). A sample is dropped when its timestamp is more than 100 ms from the event's `logMonoTime` (locationd's rule, L84).
- Device frame by the locationd mapping, then the calibrated (vehicle-aligned) frame: `a_cal = device_from_calib.T @ a_dev`, using the latest `extrinsicsCalibration.rpyCalib` at or before the sample (the route's first one before it arrives).
- `a_y` = calibrated y component. Resampled by linear interpolation onto the route's 100 Hz controls grid (the same relative time base as the existing extracts: seconds from the first non-`initData` event). Grid samples within 50 ms of a sensor gap > 50 ms are invalid.
- **Validity gate (fixed now):** on engaged 55+ mph samples (all-engaged selection below), the 0.05–0.5 Hz band of `a_y` against V0's logged measurement `actualLateralAccel` (steering-derived) must have |correlation| ≥ 0.8 per era. If an era fails, its IMU comfort numbers are reported as invalid and only the steering-derived proxy is given.
- **Steering-derived proxy `a_s`** (secondary; also what the simulation can produce): V0's measurement (logged `actualLateralAccel`, or in simulation the measurement map applied to the simulated angle). It is a kinematic quantity with no tyre or yaw dynamics, so it overstates fast content relative to what occupants feel. It is never presented as felt acceleration.

**Metrics (each on `a_y` and on `a_s`):**
- **(a) Fast lateral acceleration:** RMS of the 0.5–4 Hz band (zero-phase 4th-order Butterworth band-pass on the whole route, statistics over the selected samples, as in the twitch metrics).
  - **(a') ISO 2631-1 W_d-weighted RMS** of `a_y` (secondary): band-limiting 2nd-order Butterworth high-pass at 0.4 Hz, then the acceleration–velocity transition `H_t(s) = (1 + s/ω3) / (1 + s/(Q4·ω4) + s²/ω4²)` with f3 = f4 = 2 Hz, Q4 = 0.63, by the bilinear transform with pre-warping at 2 Hz. The 100 Hz band-limiting low-pass is above Nyquist and is omitted. Applied causally (it is a weighting, not a band selection).
- **(b) Lateral jerk:** `a` low-passed at 2 Hz (zero-phase 4th-order Butterworth), central-difference derivative; RMS and p95 of |jerk| (m/s³).
- **(c) Step events:** `a` low-passed at 4 Hz (zero-phase 4th-order Butterworth); a step starts where `|a(t + 0.2 s) − a(t)| ≥ 0.1 m/s²` becomes true (rising edges of that condition), counted only where both t and t + 0.2 s are selected; per minute of selected time.
- **(d) Steering-wheel vibration:**
  - column torque `carState.steeringTorque` (raw units): RMS of the 8–20 Hz band (zero-phase 4th-order Butterworth);
  - **20 Hz line** in `steeringTorqueEps` and in `steeringTorque`: Welch PSD (Hann, 2 s segments, 50% overlap) over each selected contiguous run ≥ 8 s; line power = PSD integrated over 19.5–20.5 Hz minus the median PSD of 17–19 and 21–23 Hz times 1 Hz; amplitude = √max(line power, 0) (raw units RMS). Time-weighted over runs.
- **Noise floor:** (a)–(c) of `a_y` and (d) also on stationary samples (v < 0.3 m/s, any mode), so that the IMU's floor is known.

**Selections** (per era E1–E4 × speed band L/M/H):
- **straight-clean engaged:** exactly the twitch selection (`s11_holdjump.select`, runs ≥ 8 s, 2 s trimmed);
- **all engaged:** lateral active, no steering press within ±1 s, no blinker within ±3 s, not saturated (the Amendment 3 tracking selection), runs ≥ 8 s, 2 s trimmed;
- **manual:** lateral not active and v ≥ 9 m/s, no blinker within ±3 s; straight (|κ| < 2.5e-4 with both lane lines > 0.5) and all; runs ≥ 8 s, 2 s trimmed. Manual is a human-input reference, not a target.
- Only the routes in the s11 dataset (engaged routes 4–`0x25`), so manual data is what those routes contain.

**Weaving on logs (step 2e companion):**
- angle W RMS (0.2–0.7 Hz) as in the twitch findings;
- **lane-centre offset** `c = (y_left + y_right)/2` of modelV2 lane lines 1 and 2 at their first x point (20 Hz), only where both probabilities > 0.5: RMS of its 0.05–0.7 Hz and 0.2–0.7 Hz bands (zero-phase 4th-order Butterworth on contiguous 20 Hz runs, 2 s trimmed), on the same selections.

**Reporting:** a baseline table per era × band × selection with jitter (jumps/min, hold fraction, T RMS, reversals), weaving (W RMS, lane-offset band RMS) and comfort (a–d). No pass/fail at this stage: these are today's baselines for the later A/B criteria. Era differences are observational (different roads and days).

#### 2.1.1 Results: log baselines (observation; `analysis/g70-d2c4-20261007/comfort/comfort_baselines.json`)

Tools: `scratch/wsl/sng/s12_imu_extract.py` (`run_s12_imu.sh`, checkout venv @ `c027a92857`; log `logs/s11-imu-extract-20261007-112405.log`), `s12_comfort.py` (`~/venvs/vid`; log `logs/s10-s11-comfort-20261007-112958.log`).

- **IMU extraction:** 23 routes; source `lsm6ds3trc` only; no sample dropped by the locationd rules, no gap > 50 ms, no duplicate timestamps; 101 Hz. The carState time base equals the existing extract's exactly (route 4: max |Δt| 0).
- **Self-tests before reading results:** the W_d filter matches ISO 2631-1 Table 3 within 2% at 0.5/1/2/4/8 Hz; the step counter returns 29.5/min on a 30/min synthetic step train.
- **Validity gate (pre-registered): E1 pass (r 0.84), E2 pass (0.85), E3 fail (0.78), E4 fail (0.77).** By the rule, the IMU comfort numbers of E3 and E4 are reported as **invalid**; only the steering-derived proxy counts for them.
  - *Exploratory diagnostic, after the verdict* (`s12_gate_diag.py`, `comfort/gate_diag_exploratory.json`; does not change the verdict): the IMU's lateral acceleration matches v × the gyroscope's yaw rate (r 0.85–0.91 at zero lag, all eras), and matches the steering proxy without V0's roll term at r 0.84–0.92 with a 0.2 s lag. So the gate failed because its reference (V0's measurement, which contains the roll term and has no vehicle response lag) was a poor reference, not because the IMU signal is wrong. Any later gate should use v × yaw rate (gyro) as the reference; that is a new pre-registration, not a retroactive change.

**Baselines, 55+ mph** (sc = straight-clean engaged, ae = all engaged, ms/ma = manual straight/all; manual cells are small):

| Era / sel | s | Jumps/min | Hold | Angle T RMS (°) | Angle W RMS (°) | Lane offset 0.05–0.7 Hz RMS (m) | a_y 0.5–4 Hz RMS | a_y W_d RMS | a_y jerk RMS / p95 | a_y steps/min | a_s 0.5–4 Hz RMS | a_s jerk RMS / p95 | a_s steps/min | Column torque 8–20 Hz RMS | 20 Hz line EPS / column |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| E1 sc | 729 | 49.8 | 0.45 | 0.121 | 0.107 | 0.051 | 0.147 | 0.148 | 0.87 / 1.69 | 209 | 0.050 | 0.32 / 0.69 | 35.2 | 10.6 | 0.47 / 1.29 |
| E2 sc | 1,138 | 18.1 | 0.65 | 0.050 | 0.130 | 0.050 | 0.116 | 0.122 | 0.68 / 1.30 | 196 | 0.027 | 0.17 / 0.36 | 8.0 | 7.1 | 0.56 / 1.37 |
| E3 sc | 1,155 | 20.6 | 0.64 | 0.047 | 0.121 | 0.047 | *0.115* | *0.122* | *0.67 / 1.31* | *208* | 0.027 | 0.16 / 0.36 | 8.3 | 8.6 | 0.55 / 1.48 |
| E4 sc | 1,364 | 32.1 | 0.55 | 0.072 | 0.141 | 0.044 | *0.121* | *0.129* | *0.71 / 1.37* | *196* | 0.035 | 0.20 / 0.43 | 14.5 | 9.1 | 0.61 / 1.60 |
| E1 ae | 1,277 | 52.0 | 0.41 | 0.130 | 0.161 | 0.085 | 0.140 | 0.146 | 0.83 / 1.65 | 209 | 0.051 | 0.34 / 0.72 | 36.4 | 10.2 | 0.54 / 1.56 |
| E4 ae | 2,366 | 37.6 | 0.49 | 0.079 | 0.190 | 0.070 | *0.116* | *0.127* | *0.69 / 1.35* | *197* | 0.035 | 0.23 / 0.51 | 17.9 | 9.0 | 0.64 / 1.75 |
| E4 ms (manual) | 87 | | | | 0.535 | 0.154 | *0.147* | *0.147* | *0.95 / 2.08* | *165* | | | | 5.4 | 0.02 / 0.43 |
| stationary (E1–E4) | 112–1,062 | | | | | | 0.005–0.010 | 0.005–0.009 | 0.013–0.028 | 0–2.3 | | | | 0.2–0.7 | 0.006–0.009 / 0.04–0.07 |

*Italic: IMU numbers from eras that failed the gate (invalid by the rule; shown for completeness).* Jerk in m/s³, accelerations in m/s², torques in raw CAN units. Jitter columns use the simulator's per-run statistics (runs ≥ 12 s), so they match the model results and differ slightly from the twitch findings' table. The 35–55 mph and 20–35 mph rows are in the JSON.

**Readings (observational; eras differ in roads and days):**
- **Steering-derived comfort follows the jitter.** a_s fast RMS, jerk and step events order E1 > E4 > E2 ≈ E3, like jumps/min and T RMS. E1 has 4× the a_s step events of E2/E3, E4 1.8×.
- **The IMU is dominated by road input in the twitch band.** a_y step events are 150–210/min in every engaged and manual cell and 0–2/min at standstill, so **metric (c) on the IMU cannot isolate the twitch**. The coherence of a_y with the steering proxy is 0.64–0.81 below 0.7 Hz but only **0.23–0.33 at 0.7–1.5 Hz and 0.06–0.10 at 1.5–4 Hz** (exploratory diagnostic). a_y fast RMS still ranks E1 (0.147) above E2–E4 (0.115–0.121), the only valid between-era IMU difference being E1 vs E2.
  - **Consequence for step 4:** a raw-IMU comfort criterion would be insensitive to the twitch. On-car criteria need the steering-coherent part of a_y, a same-road paired comparison, or the steering proxy; to be fixed in the step 4 protocol.
- **Steering-wheel vibration:** the 20 Hz line is present only while engaged (EPS 0.47–0.84 vs ≤ 0.06 manual; column 1.3–3.1 vs ≤ 0.8). Column torque 8–20 Hz is 6.7–10.6 engaged vs 4.8–9.4 manual (hands on the wheel) and 0.2–0.7 at standstill, so the broadband column vibration is not engaged-specific; the 20 Hz line is.
- **Weaving:** lane-offset 0.05–0.7 Hz RMS on straight-clean 55+ mph is 0.044–0.051 m in every era (manual 0.15). Angle W RMS does not follow the jitter ordering (E1 lowest at 0.107°).

### 2.2 Step 2f: restore keys for a CarParams change (source check, done 2026-10-07)

Source facts (`c027a92857`, `openpilot/selfdrive/locationd/`):
- **torqued** restores its cache when `(carFingerprint, lateralTuning type, friction, latAccelFactor, VERSION)` match (`torqued.py` L116, L137–142).
- **paramsd** restores `LiveParametersV2` when `carFingerprint` matches and the cached steerRatio is within 0.5–2× `CP.steerRatio` (`paramsd.py` L203–232).
- **lagd** restores `LiveDelay` when `carFingerprint` matches, the status is not invalid and its `VERSION` matches (`lagd.py` L365–383).
- V0 reads `steeringAngleDeadzoneDeg` once at init (`latcontrol_torque_v0.py` L45) and applies it only to the friction input (L76–77, L100). `configure_torque_tune` writes it into `CP.lateralTuning.torque` (`opendbc/car/interfaces.py` L257–264).
- **So D2 changes no restore key:** torqued, paramsd and lagd all keep their learned state across a D2 install. C4 is controller code, not a CarParams value, unless the implementation adds one.

### 2.3 Amendment 6: swap validation of the frozen D2C4 (user chose it at the step 1 boundary, 2026-10-07; written before any run)

**Question:** does D2C4's offline effect hold on data that played no part in choosing it?
- E1 and E4 informed the candidate design and choice (review finding 2).
- E2 and E3 did not, but they were the plant's fit set.
- So: fit a new plant on E4 only, then test D2C4 on E2 and E3.

**Identification:**
- Same plant structure, bounds and objective as Amendment 2 (`s11_plant_cl.py`; differential evolution seed 2, maxiter 60, popsize 10), H band (55+ mph) only.
- **Fit era E4 only.** Run on the review-fixed harness (§1).
- E2/E3/E1 are not touched by the fit.

**Adequacy of the E4 plant** (the root-cause §4 criteria, unchanged), on E2 and E3 separately, 55+ mph, closed loop with logged requests:
- hold within ±0.10;
- jumps/min within ±35%;
- T RMS within ±35%;
- W RMS within ±40%;
- ordering E2 < E1 and E3 < E1 for jumps and T (E4 is in-sample now).

E1 is reported as secondary. **If E2 or E3 fails adequacy, the swap validation is inconclusive and no candidate verdict is drawn from it.**

**Candidate test:**
- **Only the frozen D2C4** (`steeringAngleDeadzoneDeg` 0.4° + causal first-order 2 Hz desiredCurvature low-pass) vs A0, on **E2 and E3 separately, each must pass**.
- Criteria: Amendment 3 (1)–(3) with the Amendment 4 clarification:
  1. jumps ≥ 40% lower and T RMS ≥ 30% lower (straight-clean);
  2. W RMS not up > 10%;
  3. on all engaged 55+ mph runs, mean |error| not up > 20%, and curve ratio within 0.95–1.04 and ±0.02 of A0 (or, if A0 is outside the band, not further from it).
- E1 and E4 results with this plant are reported as secondary (not independent).
- No other candidate is evaluated on E2/E3 in this amendment.

**Tracking robustness (finding 1):**
- Criterion 3 is evaluated with θ0 windows of 10 s (primary, as before), 30 s and 60 s.
- Criterion 3 counts as **robustly met** only if it passes with all three.
- The plant-perturbation set of `s11_robust.py` is also reported on E2/E3 (exploratory).

**Reported with every result:**
- jitter (jumps, hold, T, reversals);
- weaving (angle W RMS; lane position is not available in simulation because requests are replayed);
- comfort proxy (a_s fast RMS, jerk RMS, step events/min).

**Interpretation:**
- A pass on E2 and E3 is offline evidence from data independent of the candidate choice (but not of the plant structure, which was chosen on all eras).
- A fail is reported as such, and D2C4 is not carried to step 3 without the user's decision.

#### 2.3.1 Results (model results; `analysis/g70-d2c4-20261007/plant_cl_e4/`, `a6/`; runner `run_s11_a6.sh`, summary `s12_summary_a6.py`; logs `logs/s10-s11-a6-plant-e4-par-*`, `logs/s10-s11a6-*`)

**Identification on E4 only** (41 runs, 1,446 s; parallel objective, bit-identical to serial; 4,270 evaluations, 408 s):
- a 4862, b 264, c 125, f_s 199, f_c 72, td 0.068 s, te 0.011 s.
- Ratios close to the E2+E3 plant: a/b 18.5 vs 18.2, f_s/a 0.041 vs 0.049, f_c/a 0.015 vs 0.017. The total EPS lag is similar (79 vs 53 ms), split differently.

**Adequacy of the E4 plant (55+ mph, sim vs log): passes on both primary eras.**

| Era | Role | Jumps/min | Hold | T RMS | W RMS | Verdict |
|---|---|---|---|---|---|---|
| E2 | primary | 18.7 vs 18.1 (+3%) | 0.668 vs 0.654 | +16% | +15% | pass |
| E3 | primary | 18.6 vs 20.6 (−10%) | 0.673 vs 0.637 | +18% | +10% | pass |
| E1 | secondary | 64.2 vs 49.8 (+29%) | 0.392 vs 0.450 | +9% | +10% | pass |
| E4 | in-sample | 31.1 vs 32.1 | 0.584 vs 0.550 | +4% | +5% | |

- Ordering E2 < E1 and E3 < E1 is reproduced for jumps and T.
- Not a criterion: the model overstates micro-reversals (E2 25.5 vs 16.0, E3 24.5 vs 16.2).

**Frozen D2C4 vs A0** (change vs A0 of the same era; criterion 3 with θ0 10 s primary, 30 s / 60 s for robustness):

| Era | Jumps | T | W | Reversals | Hold | a_s RMS / jerk / steps | Mean \|error\| θ0 10 / 30 / 60 s | Curve ratio (10 s) | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| **E2** | −45% | −33% | −20% | −56% | +0.15 | −25% / −23% / −29% | **+21.0%** / +16.9% / +9.0% | 1.030 (A0 1.027) | **fail (criterion 3, primary)** |
| **E3** | −52% | −41% | −25% | −58% | +0.16 | −30% / −28% / −57% | +19.6% / +19.4% / +12.3% | 1.025 (A0 1.025) | pass (robust) |
| E1 (secondary) | −62% | −41% | −7% | −60% | +0.28 | −28% / −31% / −59% | +12.0% / +11.0% / +10.0% | 1.065 (A0 1.069) | pass |
| E4 (secondary) | −56% | −36% | −20% | −57% | +0.20 | −28% / −27% / −47% | +19.1% / +18.5% / +14.7% | 1.030 (A0 1.030) | pass |

- Exploratory robustness on E2/E3 (10 plant perturbations): jumps −42…−55% and T −32…−41% in every case; the tracking change is **+16…+25%**, above 20% in 5 of 10 cases on E2 and 3 of 10 on E3 (one more at exactly 20.0% in each).
- Simulated vs logged A0 tracking: mean |error| 0.049 vs 0.053 (E2), 0.046 vs 0.049 (E3); curve ratios within 0.001.

**Verdict by the pre-registered rule: D2C4 fails the swap validation.** E2 misses criterion 3 by 1.0 point (+21.0% vs 20%); E3 passes.

**Reading:**
- **The twitch and comfort-proxy reductions replicate on data that played no part in choosing D2C4.** Criteria 1–2 pass on both E2 and E3, with weaving reduced, not increased.
- **The tracking cost replicates too:** about +20% mean |error| (+16…+25% across eras and plant variants), so it is systematic, not noise.
  - In absolute terms it is about +0.01 m/s² of mean lateral-accel error at 55+ mph, about 0.02° of steering at 75 mph.
  - Curve ratios are unchanged (within 0.004 of A0).
  - In this model the extra error sits inside the deadzone by design: the friction term no longer pushes on errors inside about 0.10 m/s² at 30 m/s (0.115 m/s² at 33.5 m/s). These figures use V0's own vehicle-model map; see the erratum in §3.1.
  - The model replays logged requests, so whether this error shows up as lane-position drift (the outer loop) cannot be judged offline.
- Per this amendment, **D2C4 is not carried to step 3 without the user's decision.**

**User decision (2026-10-07):** "Accept costs, test transients."
- D2C4 stays the candidate. Its ~+20% mean-error cost is recorded as a known trade-off: the swap-validation result stays "fail on criterion 3", not a pass.
- Next: 2a (request steps/sines) and 2b (curve entry/exit), where extra tracking error would matter most.
- The decision on step 3 comes after those.

### 2.4 Steps 2a–2d

#### 2.4.1 Amendment 7: transient tests 2a (synthetic steps and sines) and 2b (logged curve entry/exit). Written 2026-10-07 before any run.

**Common to both:**
- **Compared:** A0 (as driven) vs the frozen D2C4, on the review-fixed harness.
- **Plants:**
  - the E4-identified plant (§2.3.1) is **primary**: with it, E2/E3 data are independent of the candidate choice;
  - the E2+E3 plant is secondary.
- **Signals:**
  - request a_req = desiredCurvature·v²;
  - response a_s = V0's measurement map of the simulated (0.1°-quantized) angle.
- **Every result reports the three groups:**
  - jitter: jumps/min and hold inside the window;
  - weaving: the sine gains and phases at 0.15–0.6 Hz cover the weave band;
  - comfort proxy: a_s jerk RMS and step events/min.

**2a, synthetic tests** (offline harness with a synthetic request; `fl.closed_loop` called directly):
- **Setup:**
  - speeds 25, 30 and 33.5 m/s (56/67/75 mph);
  - vehicle-model gain A = the median logged A of E4 active samples within ±0.5 m/s of the speed (−0.198, −0.249, −0.287), B = 0 (no roll), angle offset 0, θ0 = 0;
  - lat delay 0.179 s (E4 median); laf 3.638 and friction 0.0827 (E4 median applied);
  - no warm-up from logs: start at rest, integrator 0, command 0; no driver torque.
- **Requests:**
  - **clean:** the synthetic request alone;
  - **with logged jitter:** the synthetic request plus the fast part of real requests. That is logged desiredCurvature from E2/E3 straight-clean 55+ mph runs minus its 0.2 Hz zero-phase low-pass, in consecutive 20 s (steps) or 40 s (sines) segments, up to 40 segments per test. These are the independent eras.
- **Steps:**
  - ±0.3 and ±1.0 m/s², 5 s at zero then 15 s held;
  - both signs pooled;
  - jittered trials ensemble-averaged before the response metrics.
- **Step metrics:**
  - t50 and t90 (time from the step to 50% and 90% of the step);
  - overshoot (peak beyond the step, % of step);
  - settling time (last exit from ±max(10% of step, 0.03 m/s²));
  - mean |error| 1–3 s and 5–15 s after the step;
  - jumps/min and hold fraction during 5–15 s after the step (per trial).
- **Sines:**
  - amplitude 0.3 m/s² at 0.15, 0.25, 0.4 and 0.6 Hz, 40 s;
  - gain |a_s/a_req| and phase lag from a single-frequency projection over the last 30 s, trimmed to whole cycles.
- **Red flags for D2C4 vs A0** (any one, on the primary plant, at any speed and step size, clean or jittered, is reported as a red flag for step 3):
  - **R1:** t50 later by > 0.15 s;
  - **R2:** overshoot higher by > 10 percentage points;
  - **R3:** settling longer by > 1.0 s;
  - **R4:** mean |error| 1–3 s after the step higher by > 50% **and** by > 0.03 m/s²;
  - **R5:** sine gain changed by > 10% or phase lag up by > 15° at any frequency.

**2b, logged curve entry/exit** (all engaged 55+ mph runs ≥ 12 s, closed loop with logged requests as in Amendment 3, θ0 windows 10/30/60 s):
- **Events:**
  - **entry** = |a_req| (0.5 s centred mean) rising through 0.5 m/s², reaching ≥ 0.8 within 4 s;
  - **exit** = falling through 0.5 m/s² from ≥ 0.8 within the previous 4 s;
  - window −2 s … +6 s; at least 3 s after the run start and fully inside the run;
  - non-overlapping (a later event inside an earlier window is dropped).
- **Metrics per event:**
  - peak |a_req − a_s| in the window;
  - mean |a_req − a_s|;
  - lag = the delay (0–1 s, 10 ms steps) maximizing the correlation of a_s with a_req in the window;
  - jumps in the window;
  - a_s jerk RMS.
- **Pooled per era:** E2 + E3 primary (with the E4 plant), E1 and E4 secondary (with the E2+E3 plant, and also the E4 plant for E1).
- **Red flags** (pooled over entries and exits, primary plant and eras, θ0 10 s; also reported at 30/60 s):
  - **C1:** mean peak |error| up > 25%;
  - **C2:** mean lag up > 0.15 s;
  - **C3:** mean in-window |error| up > 25%.

**Interpretation:**
- No red flag: the transient cost of D2C4 is within these bounds in the model, and step 3 can proceed on the user's decision.
- Any red flag is reported with its size, and step 3 waits for the user.
- All of this is offline model evidence. The model replays requests (no outer loop) and has no tyre/yaw dynamics.

#### 2.4.2 Results of Amendment 7 (model results)

Data: `analysis/g70-d2c4-20261007/a7/` (`transient_2a.json`, `curves_2b.json`). Scripts `s12_transient.py`, `s12_curves.py`. Logs `logs/s10-s11a7-*`.

**2a synthetic tests:**
- Jitter: 40 × 20 s and 25 × 40 s segments from E2/E3, request jitter RMS 0.034 m/s² at 30 m/s.
- **Primary-plant red flags: R5 at 0.6 Hz (all speeds) and R3 at 33.5 m/s for the 0.3 m/s² step.** The E2+E3 plant gives the same picture (R5 at 0.6 Hz, and at 0.4 Hz at 33.5 m/s clean; R3 at 33.5 m/s jittered).

| Test (E4 plant) | A0 → D2C4 | Reading |
|---|---|---|
| Steps 0.3 / 1.0 m/s², t50 and t90 | unchanged within 0.01 s at all speeds | the rise is limited by the torque rate limit, so the 2 Hz filter's lag doesn't show |
| Step overshoot | unchanged (±2.6 points) | |
| Step 0.3 at 33.5 m/s: settling (±0.03 m/s²) | clean 9.9 → 13.9 s, jittered 1.9 → 6.1 s (**R3**) | a residual of about 0.03 m/s² (≈ 0.1° of wheel) lingers inside the deadzone (0.115 m/s² at this speed). Error 5–15 s after the step: clean 0.028 → 0.041, jittered 0.016 → 0.015 m/s² |
| Step mean \|error\| 1–3 s | +0.000…+0.009 m/s² | below R4 |
| Steps with jitter: jumps/min and jerk 5–15 s after | jumps −22…−66%, jerk −17…−65% | twitch and comfort benefit inside steps |
| Sines 0.15 / 0.25 / 0.4 / 0.6 Hz: phase lag | +7…+9° / +8…+12° / +12…+14° / **+17…+19.5° (R5)** | the 2 Hz first-order low-pass alone adds atan(f/2) = 4.3° / 7.1° / 11.3° / 16.7°; the rest comes from D2 |
| Sines: gain | −7…+5% | within R5's ±10% |

**2b logged curve entry/exit** (all engaged 55+ mph runs; entries and exits pooled):

| Plant / eras | θ0 | Events | Peak \|error\| | Mean \|error\| in window | Lag | Jumps in window | Jerk RMS |
|---|---|---|---|---|---|---|---|
| **E4 / E2+E3 (primary)** | 10 s | 102 | 0.210 → 0.244 (+16%) | 0.059 → 0.075 (**+28%, C3**) | 0.22 → 0.31 s (+0.09) | −20% | −5% |
| E4 / E2+E3 | 30 / 60 s | 102 | +19% / +17% | +28% / +25% (C3 / C3) | +0.09 / +0.09 | −23% / −22% | −6% / −5% |
| E4 / E1 | 10 s | 32 | +8% | +18% | +0.06 | −17% | −8% |
| E4 / E4 | 10 s | 51 | +18% | +28% (C3) | +0.09 | −27% | −7% |
| E2+E3 / E4 | 10 s | 51 | +20% | +30% (C3) | +0.09 | −24% | −7% |

**Reading:**
- **D2C4's tracking cost is concentrated in transients.**
  - In curve entries and exits the response lags by about 0.09 s more, close to the 2 Hz filter's 80 ms time constant.
  - The in-window error rises by about 28%, which crosses the pre-registered 25% bound (C3). Peak error +16–20% stays inside its bound.
  - In absolute terms the mean in-window error goes from 0.059 to 0.075 m/s².
- **The lag comes from C4 by construction,** and the settling residual comes from D2's deadzone.
- The twitch benefit holds inside transients too: fewer jumps, lower jerk.
- **Exploratory split** (after the pre-registered results; D2 and C4 alone on the same tests; `a7/*_split_exploratory.json`, logs `s10-s11a7x-*`):
  - **R5 (0.6 Hz phase lag) comes from C4:** +16…+17° for C4 alone, +0.6…+1.9° for D2 alone.
  - **R3 (settling at 75 mph) comes from D2:** 1.9 → 7.0 s for D2 alone, 1.9 → 2.5 s for C4 alone.
  - **In curves (E2+E3, primary) the costs add:**

    | Variant | Mean error | Peak error | Lag |
    |---|---|---|---|
    | D2 | +12% | +6% | +0.02 s |
    | C4 | +16% | +11% | +0.06 s |
    | D2C4 | +28% | +16% | +0.09 s |

  - Neither half alone meets the twitch criteria (root-cause findings §7.6/§7.8: D2 T −23/−21%, C4 jumps −27/−26%). So the transient cost is inherent to getting the twitch reduction this way.
- **Status: red flags R3, R5 (2a) and C3 (2b).** Per Amendment 7, step 3 waits for the user's decision. These are offline model results with replayed requests: whether the extra 0.09 s and the ~0.016 m/s² error in curves are noticeable, or change the lane position, cannot be judged offline.

**Data inventory for 2c/2d (observation, `s12_inventory.py`, `analysis/g70-d2c4-20261007/inventory.json`):**
- Lateral control was **never active at a standstill** in any era (0 engaged stops or launches), so there is no logged engaged stop-and-go data.
- Active data below 20 mph: 80–420 s per era, almost none straight-clean.
- 35–55 mph straight-clean runs ≥ 12 s: E1 0, E2 94, E3 145, E4 286 s. All-engaged: 330–750 s per era.
- **2c (35–55 mph) and 2d (low speed / stop-and-go): not covered.** No plant was identified for these bands (too little straight-clean data). They will be observed on-car only (deployment proposal §6).

**User decision after Amendment 7 (2026-10-07):**
- Get D2C4 ready for installation once the device is available.
- A next session tests milder variants.
- A separate kickoff covers the installation.

## 3. Step 3: car-scoped implementation, tests, QA

**Code** (`dragal/custom`, local; on top of the installed `c027a92857`; **final head `89bbe60ab1`**):
- `268040c361`: the change + 5 tests;
- `8593b66148`: float32 test tolerances;
- `66b22ef83f`: re-engagement test (QA round 1);
- `89bbe60ab1`: deadzone kept when the tune is re-run, + 4 tests (QA round 2).

**The two parts:**
- **D2:** `opendbc_repo/opendbc/car/hyundai/interface.py` adds `STEERING_ANGLE_DEADZONE_DEG = {CAR.GENESIS_G70_2024: 0.4}`. The Hyundai `CarInterface.configure_torque_tune` override defaults the deadzone from it (§3.2 #1). Every other car keeps 0.0. The CarParams field is float32 (0.4000000060).
- **C4:** `openpilot/sunnypilot/selfdrive/controls/lib/latcontrol_torque_v0.py` adds `DESIRED_CURVATURE_LP_HZ = {"GENESIS_G70_2024": 2.0}`.
  - It is a `FirstOrderFilter(0, 1/(2π·2), dt, initialized=False)`, updated at the top of `update()`, i.e. every cycle including inactive ones, before anything else uses `desired_curvature`.
  - Source fact: this is the same recursion and start as the harness's C4.
- **Placement rationale:** V0 is the only lateral controller this car runs (`controlsd_ext.initialize_lateral_control`, `EnforceTorqueControl` absent). `desired_curvature` there is exactly the post-`clip_curvature` value logged as `controlsState.desiredCurvature`, which the harness filtered.

**Tests** (x86 shim, `run_s8_tests.sh`; WSL clone at the exact revision):
- **6 new tests** (`test_latcontrol_torque_v0_g70.py`), all pass at `66b22ef83f`: deadzone only for this car; other cars' request unfiltered; first-order response with first-value init; tracking while inactive; re-engagement after inactive cycles with `reset()`; deadzone inside/outside.
- **Mutation checks:**
  - pre-change source: 3 of 5 fail;
  - filter updated only while active: the re-engagement test fails;
  - logs `s8-tests-s11-d2c4-*`.
- **Existing tests at `8593b66148`:**
  - 19 lateral tests OK;
  - opendbc car suites (`run_s11_car_tests.sh`) all OK: car_list, docs, hyundai 13, lateral_limits 480, vehicle_model, platform_configs, car_interfaces 16 (`logs/s11-car-tests-d2c4-20261007-124802/`);
  - QA round 1 ran ruff and codespell on the changed files: clean.
- **Source = harness** (`s12_source_replay.py`, `logs/s11-source-replay-*`): the checkout's V0 vs the harness reference with D2C4, open loop on 4 logged routes from all eras. Max difference **1.9e-5 steering counts** (p99 ≤ 2.8e-6) over 311,849 active samples.
  - This confirms the harness was implemented faithfully.
  - It does not show on-road performance.
- **Deploy dry run** (`deploy/g70-d2c4-20261007/sim_install.sh`, throwaway WSL clone):
  - install to the head, clean tree, firmware file unchanged;
  - filter update 0.07 µs per call (x86);
  - rollback to `c027a92857`, clean;
  - the reboot precheck refuses without `DisableUpdates=1`.
  - Rerun at the final SHA: see the deployment proposal.

**QA round 1 (cooperative), on `8593b66148`:** no blocker, no major. Findings and dispositions:

| # | Finding | Disposition |
|---|---|---|
| 1 | Minor, latent config: with NNLC or `EnforceTorqueControl` on, sunnypilot re-runs `configure_torque_tune` without the deadzone (`openpilot/sunnypilot/selfdrive/car/interfaces.py` L67–69; source fact, confirmed). D2 would drop to 0 while C4 stays (an unvalidated combination). Toyota's 0.2° behaves the same upstream. | **Agreed; generic code not changed** (it would change other cars). The install and reboot prechecks now refuse unless NNLC, `EnforceTorqueControl`, `LateralJerkTorqueController` and `TorqueParamsOverrideEnabled` are all off, which is the validated configuration. Recorded as a known limitation. |
| 2 | Minor, test gap: the inactive-tracking test also passes for a filter updated only while active. | **Fixed:** re-engagement test added (`66b22ef83f`); the active-only mutant now fails it. |
| 3 | Note: a NaN request latches in the filter. | Not changed. controlsd's `clip_curvature` already latches NaN upstream, so this is no new failure mode, and a guard would deviate from what was validated. |
| 4 | Note, logging semantics: `controlsState.desiredCurvature`, `actuators.curvature` and `curvature_limited` stay unfiltered; `torqueState.desiredLateralAccel` and `desiredLateralJerk` are filtered. | **Recorded:** future G70 logs won't satisfy desiredCurvature·v² = desiredLateralAccel. Replays keep using the logged desiredCurvature as the pre-filter input. Lane changes and maneuver mode also see the 2 Hz lag. |
| 5 | Note: the lateral-accel deadzone scales with v² (0.004 / 0.017 / 0.057 / 0.103 / 0.144 m/s² at 5 / 10 / 20 / 30 / 40 m/s), so D2 has little effect at low speed. Doc nit on "0.18 m/s²". | **Confirmed, and it was a real error:** see §3.1. |

**QA round 2** (independent adversarial): see §3.2.

### 3.1 Erratum: steering-angle to lateral-accel conversion in the session 10 docs

- The twitch and root-cause findings (session 10) converted 0.1° of steering to about 0.045 m/s² at 55+ mph with a plain bicycle model.
- V0's own vehicle-model map (the logged A; E4 medians at ±0.5 m/s) gives **0.020 / 0.025 / 0.029 m/s² per 0.1° at 25 / 30 / 33.5 m/s**. So a 0.3–0.4° jump at 75 mph is about **0.09–0.11 m/s²** (not 0.13–0.18), and the 0.4° deadzone is about 0.10–0.115 m/s² at 30–33.5 m/s.
- **No simulation or metric is affected:** they all used the logged map. Only the explanatory conversions in the text were wrong.
- Erratum notes were added to the root-cause findings §7.1 and §7.8.

### 3.2 QA round 2 (independent adversarial), on `66b22ef83f`

**Isolation:**
- The reviewer received only a self-contained package in its prompt: the resulting code at the exact snapshot, unchanged source context, neutral requirements and runtime facts. Round 1 material was excluded; the package was scanned for review/QA references before sending.
- Remote (cloud) isolation was requested. The tool result did not confirm that the agent actually ran remotely; its single tool use is consistent with not reading local files.
- **So enforced isolation is not confirmed.** It is disclosed to the user as instruction-plus-package isolation.

**Findings and dispositions** (each verified by the coordinator):

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | **major** | The deadzone is reset to 0 when NNLC or `EnforceTorqueControl` re-runs the torque tune (same issue as round 1 #1, rated higher). | **Fixed in code** (`89bbe60ab1`). The Hyundai `CarInterface` now overrides `configure_torque_tune` to default the deadzone from its per-car table. sunnypilot's re-run calls it through the instance (`CI.configure_torque_tune`, source fact), so the G70 keeps 0.4 on every path, while other Hyundai cars keep 0.0 and generic code and Toyota are unchanged. The install/reboot configuration guard stays, because NNLC/Enforce + D2C4 remain unvalidated. |
| 2 | minor | The tests didn't prove continuity across off→on with a changing input; a `reset()` that re-initialized the filter would pass. | **Fixed:** reference-recursion test (ramping inactive input with `reset()` each cycle, the first value arriving while inactive, engagement step, a short disengagement, all checked per cycle). |
| 3 | minor | The tests didn't check that the filtered value reaches the request buffer/jerk, feedforward and extension. | **Fixed:** a test checks `desiredLateralJerk` against a filtered-history reference, `f` against filtered request + friction, and the extension's `desired_curvature` argument (spy). |
| 4 | minor | The deadzone test was narrow (one speed, 0.5×/2×). | **Fixed:** 0.95×/1.05× edges at 20 and 30 m/s. |
| 5 | note | Equivalence to the offline simulation is approximate: float32 log values; the runtime filter starts at controlsd's first call, which may differ from the first logged sample; a fixed dt is assumed. Differences decay by ×0.888 per cycle. | Agreed. The source replay measured ≤ 1.9e-5 counts. Recorded as a limit. |
| 6 | note | A NaN latches the filter. | As round 1 #3: unchanged (upstream `clip_curvature` already latches NaN). |
| 7 | note | Other controllers reading `steeringAngleDeadzoneDeg` see 0.4 for this car. | Source fact: upstream v1 reads it (`latcontrol_torque.py` L45). With the #1 fix, v1 under `EnforceTorqueControl` also gets 0.4, a consistent per-car tune; unvalidated, and excluded by the install guard. |
| 8 | note | The car key is a string literal in V0 and the enum in the interface. | Kept: V0 is generic openpilot code. Both lookups are tested; a rename fails the tests. |

No finding was disputed, so no tiebreaker was needed.

**Verification on the final head `89bbe60ab1`:**
- **Tests:** 24/24 lateral tests (10 G70 + 14 existing; `logs/s8-tests-s11-d2c4-r2-*`); opendbc car suites all OK (`logs/s11-car-tests-d2c4-r2-20261007-130641/`); ruff and codespell clean on the changed files.
- **Mutation checks** (`s12_mutations.sh`, `logs/s11-d2c4-mutations-*`): every mutant fails at least one targeted test.

  | Mutant | Fails |
  |---|---|
  | no interface default | 4 tests, incl. the re-run test |
  | `reset()` re-initializes the filter | the reference-recursion test |
  | raw value in the buffer / the extension / the feedforward | the jerk-feedforward-extension test |
  | deadzone 0.43° | the edge, re-run and scoping tests |

- **Source replay:** unchanged (max 1.9e-5 counts; `analysis/g70-d2c4-20261007/source_replay_89bbe60.json`).
- **Deploy dry run at `89bbe60ab1`:** install, reboot precheck and rollback pass. With `EnforceTorqueControl=1` the install aborts and the precheck refuses.

**QA status: full two-round QA complete** for `89bbe60ab1`, with the round 2 isolation caveat above. This is offline evidence only; nothing is validated on-car, and none of it authorizes deployment.

## 4. Amendment 8 (session 12mv): milder variants after the first on-car A/B. Written 2026-10-07 before any run.

**Context:** the on-car A/B ([on-road findings](2026-10-07-g70-d2c4-ab-onroad.md) §4) showed weave up, which the model did not predict. Session 12mv ([milder-variants findings](2026-10-07-g70-milder-variants.md) §3) found:
- the outer-loop policy model is not adequate;
- so weave is ranked by the declared **phase-lag proxy** (that findings doc, §2.4);
- the plant over-predicts D2C4's hold on `0x28`.

**Candidate set and decision rule:** agreed with the user on 2026-10-07 ("All 9 as proposed"; red flags "reported only").

**Candidates** (car-scoped; A0 and the frozen D2C4 as references):

| ID | Change | Harness option |
|---|---|---|
| MV1 | deadzone 0.5° (existing step deadzone) | `fr_dz_deg` 0.5 |
| MV2 | deadzone 0.6° (existing step deadzone) | `fr_dz_deg` 0.6 |
| MV3 | 0.4° continuous (shifted) deadzone on the friction input (= Amendment 4's D3) | `fr_dz_deg` 0.4, `fr_dz_shift` |
| MV4 | 0.3° continuous deadzone | `fr_dz_deg` 0.3, `fr_dz_shift` |
| MV5 | D2 + causal first-order 4 Hz request low-pass | `fr_dz_deg` 0.4, `req_lp_causal` 4.0 |
| MV6 | D2 + 3 Hz | `fr_dz_deg` 0.4, `req_lp_causal` 3.0 |
| MV7 | MV4 + 4 Hz | `fr_dz_deg` 0.3, `fr_dz_shift`, `req_lp_causal` 4.0 |
| MV8 | D2 + partial (shelf) filter: request = LP₂(r) + 0.5·(r − LP₂(r)), LP₂ = the C4 2 Hz recursion | new `req_shelf` [2.0, 0.5] |
| MV9 | D2 + 2 Hz filter on the friction term's input only: the friction term uses the error of a setpoint built from the 2 Hz-filtered request (its own delay buffer); feedforward, P and I use the raw request | new `fr_lp_causal` 2.0 (new loop option) |

**Source facts** (`latcontrol_torque_v0.py` @ `89bbe60ab1`):
- V0's friction term is `get_friction(error, lateral_accel_deadzone, 0.3, params)`. It takes the same `error = setpoint − measurement` as P and I (L98–103), and the deadzone step comes from `apply_center_deadzone`.
- So MV1/MV2 need only the car table value. MV3/MV4/MV7 need a car-scoped shifted error for the friction input. MV5/MV6 need only a different cutoff in the existing C4 table. MV8 and MV9 need small V0 changes.

**Harness** (new file `s15_mv_var.py`; shared scripts imported, not edited):
- a `simulate` wrapper handles MV8, and MV9 through a copy of the numba loop with a separate friction-path request;
- s11_eval, s12_curves and s12_transient are driven through it;
- s12_transient's own `run()` passes `fr_dz_shift = False` for every variant, so the D3-type variants need a new transient runner.

**Checks before any candidate result:**
1. The wrapper equals `s11_eval.simulate` bit-exactly for A0, D2, D3, C4 and D2C4 on ≥ 10 runs from all four eras.
2. The new loop with the friction-path request equal to the request is bit-exact against `s11_fastloop.closed_loop`.
3. MV8 with g = 0 equals C4+D2 exactly; with g = 1 it equals D2 within 1e-12 in the request.
4. The new transient and curve runners reproduce the stored Amendment 7 A0/D2C4 values (`a7/transient_2a.json`, `a7/curves_2b.json`) exactly.

**Runs** (≤ 4 workers, parallel-session rule):
- **Plants:** E4-identified primary, E2+E3 secondary. **Eras:** E2/E3 primary (each must pass), E1/E4 secondary. ≥ 55 mph.
- **Twitch, weave, comfort:** straight-clean runs ≥ 12 s, `s11_eval` statistics: jumps/min, hold, T, W, reversals; steering-proxy comfort (a_s 0.5–4 Hz RMS, jerk, steps).
- **Tracking:** all-engaged runs ≥ 12 s, mean |error| and curve ratio. θ0 10 s primary; 30 s and 60 s reported.
- **Weave proxy** (milder-variants findings §2.4): the request → a_s 0.2–0.7 Hz transfer of the simulated runs (the step 2a M4 estimator: 20 Hz model times, lanes ok, runs ≥ 10 s, Welch 10 s), phase and gain vs A0, same plant and era.
- **Transients:** Amendment 7 2a (steps and sines, R1–R5) and 2b (curve entry/exit, C1–C3), same definitions.

**Decision rule** (E4 plant; E2 and E3 must each pass all of 1–3):
1. **Twitch:** jumps/min ≥ 40% lower **and** T RMS ≥ 30% lower than A0.
2. **Weave (proxy):**
   - simulated W not up vs A0;
   - added weave-band phase lag (full 0.2–0.7 Hz) ≤ 25% of D2C4's added lag on the same plant and era;
   - weave-band gain within ±10% of A0.
3. **Tracking:** mean |error| (θ0 10 s) not up > 20%.
4. **Red flags R1–R5 and C1–C3:** reported for every candidate, **not pass/fail** (user decision). They are used in the ranking.

**Ranking among passes:**
1. smallest added weave-band lag (mean of E2/E3);
2. fewest red flags, then the smallest C3 (curve-window mean error) increase;
3. smallest tracking increase.

**If none passes:** report the trade-off frontier (twitch reduction vs added lag vs tracking and transient cost) and the closest candidates, with the criteria they miss.

**Every result reports** jitter (jumps, hold, T, reversals), weave (W, proxy lag and gain; lane position is not simulated) and comfort (steering-proxy). The IMU cannot be simulated.

**Data independence and limits:**
- E1/E4 informed D2C4's design. E2/E3 were used for its swap evaluation and now for this choice. `0x28` and the A-primary drives were used for model checking. **No logged era is untouched.** The next on-car A/B with a chosen variant is the independent test.
- **The weave criterion is a proxy.** It assumes the on-car weave increase scales with added weave-band lag, which the session 12mv step 2a log check did not confirm (its pre-registered reading: the extra weave came with an exogenous request change).
- The model over-predicted D2C4's hold on `0x28` (§3.2 of the milder-variants findings), so absolute twitch reductions may be optimistic. The comparisons between candidates are relative.
