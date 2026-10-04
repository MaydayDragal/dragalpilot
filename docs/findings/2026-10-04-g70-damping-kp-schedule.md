# G70 2024: damping term and KP speed schedule for V0, offline hypotheses (2026-10-04, session 7)

Follow-up to the [latAccelFactor speed-schedule test](2026-10-04-g70-laf-speed-schedule.md), whose interpretation listed these two untested levers. The user asked to test both. **Offline model evidence only; no device access, no code change in `sunnypilot/`.**

## Pre-registration (written before any run of these variants)

### Questions

On this car only (GENESIS_G70_2024):

- **H-D:** would a derivative (damping) term on the measured lateral-accel rate in V0 reduce the controller+EPS link A at 0.3–0.6 Hz at 35+ mph? Without exceeding the lag, tracking, error, step and smoothness limits below.
- **H-KP:** would a changed KP speed schedule do the same?

### Source facts (`dragal/custom` @ `82f58a9a8c`)

- **D path:**
  - V0 calls `self.pid.update(error, -measurement_rate, feedforward=ff, speed=v, freeze_integrator=...)` (`openpilot/sunnypilot/selfdrive/controls/lib/latcontrol_torque_v0.py` L103–107).
  - `measurement_rate` is `(measurement − previous_measurement) / dt`, through a first-order low-pass at 1.2 Hz (L31, L49, L87–89).
  - `PIDController` computes `d = k_d(v) · error_rate` and includes d in the anti-windup test and the output (`openpilot/common/pid.py` L45, L52, L57).
  - V0 passes `KD = 0.0` (L27, L43), so today d = 0.
  - So a non-zero KD is a damping term on the **measurement** (no derivative of the request). Units: s (m/s² per m/s³).
- **KP:** `KP_INTERP = [250, 120, 65, 30, 11.5, 5.5, 3.5, 2.0, 1.0]` at `INTERP_SPEEDS = [1, 1.5, 2, 3, 5, 7.5, 10, 15, 30]` m/s (L25, L28–29). It is interpolated in speed by `PIDController.k_p` (`pid.py` L20–21).
- **Scope:** KD and KP_INTERP are module constants, not per-car. A car-scoped version would need new plumbing (open design question; does not affect this offline test).
- **Engagement boundary:**
  - The measurement-rate filter and `previous_measurement` update only while active (L74–89).
  - `previous_measurement` starts at 0.0 and keeps its last active value through disengagement.
  - With KD > 0, the first cycle after an engagement would see a rate step from a stale value.
  - This is reported (open-loop replay on logged engagements), not simulated away.

### Variants

- **D family:** k_d(v) = interpolation over [12.5, 29] m/s of [d_L, d_H], constant outside.
  - d_L, d_H ∈ {0, 0.05, 0.1, 0.2, 0.3, 0.5, 0.75}: 49 schedules; [0, 0] = V0.
  - KP unchanged.
- **KP family:** KP_INTERP with its values at 10, 15 and 30 m/s multiplied by k10, k15, k30.
  - Each ∈ {0.5, 0.7, 0.85, 1.0, 1.2}: 125 schedules; all 1.0 = V0. Lower speeds unchanged.
  - The bands interpolate between these nodes:
    - 20–35 mph (9–15.6 m/s): mainly 10 and 15;
    - 35–55 mph (15.6–24.6 m/s): 15 and 30;
    - 55+ mph: 15–30 and 30.
  - KD stays 0.
- Everything else as deployed: latAccelFactor 4.0, friction 0.07, KI 0.3, same setpoint and feedforward.
- **Combination (secondary, pre-registered):** if both families select a schedule, the two together are evaluated on held-out with the same criteria.

### Data, model and harness

- **Same as the latAccelFactor test:**
  - selection routes 8 / 0a / 0b;
  - held-out routes 6 / 7 / 4, all simulated with the deployed tune;
  - session 6 plants; clean and dist modes; synthetic steps and sines.
- **No held-out 20–35 mph data exists.**
- **The plant was fitted on the selection routes:** the held-out test is held-out in its inputs and disturbances only.
- **Noise:** in dist mode the re-injected residual contains the logged measurement's noise (including steering-angle quantisation), so the D term sees realistic noise there. In clean mode it doesn't.
- **Harness checks before use:**
  1. The fast re-implementation with D and the KP table matches the source V0 class open loop on logged inputs (routes 0b and 7), for V0 and for at least two non-trivial variants per family. The source class has its `pid` replaced by a `PIDController` built from the variant's tables, then `update_limits()` is called.
  2. The fast variant with all-default parameters equals V0 exactly.

### Selection rule (per family; selection routes only, mechanical)

- **Same as the latAccelFactor test:**
  - eligible = in every band and both modes:
    - curve ratio 0.95–1.04;
    - mean |error| ≤ 1.20× V0 for both request definitions;
    - A phase at 0.3–0.4 and 0.4–0.6 Hz no more than 5° later than V0;
    - at 20–35 mph, A gain at 0.3–0.6 Hz no more than +0.03.
  - Plus, for both families: item 8 below (dist mode).
- **Choice:** lowest mean A over {0.3–0.4, 0.4–0.6 Hz} × {35–55, 55+ mph} × {clean, dist}.
- **Ties** within 0.01: smallest change, i.e. Σ|d| for the D family and Σ|k − 1| for the KP family.

### Success criteria (held-out set)

1. A gain at 0.3–0.4 and 0.4–0.6 Hz at 35–55 and 55+ mph is lower than V0 by ≥ 0.05, in both modes.
2. A phase in those bands is no more than 5° later than V0.
3. Curve ratio 0.95–1.04 in every band that has curves.
4. Mean |error| (both definitions) up by no more than 20% in any band.
5. 20–35 mph (if held-out runs exist): A gain at 0.3–0.6 Hz up by no more than 0.03, and items 3–4 hold.
6. Synthetic 1.0 m/s² step: **overshoot no more than 1 percentage point above V0**, and t90 ≤ V0 + 0.1 s, in every band.
7. Torque saturation fraction up by no more than 0.5 percentage points.
8. **Command smoothness (new; dist mode, every band):**
   - torque-command RMS in 1–10 Hz up by no more than 25% vs V0;
   - the fraction of cycles where the Hyundai rate/driver limit changes the command by more than 1 count up by no more than 2 percentage points.

**Changes vs the latAccelFactor test:**
- **Item 6:** "overshoot not above V0" is now "≤ V0 + 1 point". The old wording failed a −1.0% → +0.1% change, which has no physical meaning. This is declared here, before these runs. The latAccelFactor result is not re-scored.
- **Item 8 is new:** a derivative term amplifies measurement noise, and the EPS command rate is limited.

Both session 6 originals (C ≤ 1.2; lag not worse than V0) are reported alongside, labelled.

### Also reported (not pass/fail)

- **Open-loop replay of the selected D schedule on all logged engagements** (routes 4, 6–9, 0a, 0b): the D contribution in the first 0.5 s after each engagement (the stale `previous_measurement`).
- **20–35 mph on the selection routes** for both families. This is the band the user feels most, and where the model is weakest (session 6).

### What a pass would and would not mean

- **A pass would justify:** an implementation design (car-scoped plumbing, engagement handling), its tests, and validation on new held-out drives. It would not by itself justify a deployment proposal.
- **A fail means:** no proposal. The result is recorded.

## Results (model result; written after the runs)

### Answer

**Neither family, nor their combination, passes on held-out.**

- **Why:** within the lag, error, curve and smoothness limits, the selection routes allow only very small changes. On held-out these reduce A by 0.005–0.08, short of the 0.05 needed in every band.
- **Larger changes fail:**
  - **Larger D:** more lag, error up to +48%, curve ratio below 0.95 at 20–35 mph, rate-limit binding up 2–8 points.
  - **Larger KP cuts:** more lag (up to 11°) or error up to +45%.
- **No implementation or device change is proposed.**

### Harness checks (observation)

- **Fast vs source, open loop on logged inputs** (routes 0b and 7 complete, including all engagements; `equiv_check.json`): torque ≤ 5.5e-8, rate-limited output identical. Variants checked:
  - V0;
  - D [0.2, 0.5] and [0.75, 0.1];
  - KP [0.5, 0.85, 1.2] and [1.2, 0.7, 0.5];
  - combined [0.3, 0.3 | 0.7, 0.85, 1.0];
  - all-default variants (= V0).
- **D term, open loop on logged driving:**
  - |d| p99 while active (routes 0b / 7) is 0.56 / 0.55 m/s² at [0.2, 0.5], 0.70 / 0.39 at [0.3, 0.3], and 1.63 / 0.53 at [0.75, 0.1]. The medians are only 0.02–0.06, so the D term is driven by short, noisy rate spikes.
  - **Engagement kick** (stale `previous_measurement`): |d| in the first 0.5 s after an engagement reached 0.94 / 1.25 m/s² at [0.2, 0.5], and **3.5 / 4.6 m/s²** at [0.75, 0.1] (routes 0b / 7). Any D implementation would need the rate state reset on engagement.

### Selection (routes 8 / 0a / 0b)

- **D family: 3 of 48 eligible.**
  - **Choice: d = [0, 0.05]** (score 1.054 vs V0 1.080). The other eligible ones are [0.1, 0] and [0.05, 0].
  - The schedules with the lowest score (d_H 0.5–0.75: 0.72–0.88) all fail, on error +21–48%, lag 5–8°, 20–35 mph curve 0.93–0.95, and rate-limit binding +2.4 to +8.2 points.
- **KP family: 39 of 124 eligible.**
  - Best eligible score 1.067 ([*, 0.85, 0.85]). By the smallest-change tie rule, the **choice is k = [1.0, 1.0, 0.85]**.
  - All schedules scoring 1.016–1.044 fail, on lag (7.6–10.8° at 55+ mph with k30 0.5) or error (+20–45%).
- **20–35 mph** (selection routes; this is where the model is weak):
  - D at low speed lowers A there by up to 0.17 (d_L 0.75), but every such schedule fails curve (0.93–0.95) or error (+20–48%) at 20–35 mph.
  - KP cuts at 10–15 m/s lower it by at most 0.04 and fail error.

### Held-out (routes 6 / 7 / 4; vs V0)

| Candidate | ΔA 35–55 mph (clean / dist, 0.3–0.4 & 0.4–0.6 Hz) | ΔA 55+ mph | Lag added | 0.2–0.6 Hz motion | 55+ mph step overshoot (V0 26.1%) | Criteria |
|---|---|---|---|---|---|---|
| D [0, 0.05] | −0.011 to −0.020 | −0.027 to −0.050 | ≤ 1.5° | −1 to −3% | 21.7% | **fail 1**; 2–8 pass |
| KP [1.0, 1.0, 0.85] | −0.005 to −0.010 | 0.000 to −0.034 | ≤ 3.9° | ≤ −1% | 24.5% | **fail 1**; 2–8 pass |
| Combined | −0.019 to −0.030 | −0.040 to −0.083 | ≤ 4.8° | −1 to −4% | 19.8% | **fail 1**; 2–8 pass |

- **Errors:** ratios to V0 between 0.98 and 1.05 (both definitions).
- **Smoothness (item 8):**
  - 1–10 Hz command RMS ×0.93–1.05;
  - rate-limit binding change −1.8 to +1.6 points (V0 18.7–19.5%).
- **Not evaluable:** item 5 (no held-out 20–35 mph runs).
- **Original session 6 criteria:** C at 0.4–0.6 Hz above 55 mph stays above 1.2 for all three (1.35–1.43 clean). Lag is worse than V0 for all three.

### Interpretation (hypothesis)

- **Three controller-parameter families tested this session** (latAccelFactor scale, D, KP) **give the same picture.**
  - Within a 5° lag budget and the error and tracking limits, the model allows at most about −0.05 to −0.09 in A at 35+ mph.
  - That is about −4 to −5% of 0.2–0.6 Hz motion.
  - Changes that cut more slow the response to the request: more lag, larger error, lower curve ratio.
- This is consistent with session 6:
  - the peak is set mainly by the steering plant's lag (~90° at 0.5 Hz) and the vehicle's own yaw response (B 1.2–1.3);
  - V0's gains are not far from the best trade-off available to this controller structure on this plant model.
- Within V0's parameters, the model does not support a tuning fix for the highway weave.
- The **low-speed weave** remains unexplained by the model. The low-speed D effect is large but fails tracking, and the model is weakest there. This points back to data (session 6/7 option c: stop-and-go, steady 20–35 mph, request-vs-loop split).

### Limitations

- The plant was fitted on the selection routes (held-out in inputs only).
- No held-out 20–35 mph data.
- Single-input plant with constant per-band parameters; no outer loop.
- The D term's noise realism depends on the dist-mode residual. Clean mode has no measurement noise.

### Artifacts

- Scripts in `E:\DragalPilot\scratch\wsl\s8\`: `s8_fast.py`, `s8_equiv_check.py`, `s8_sim.py`, `s8_step.py`, `s8_select.py`, `s8_criteria.py`, and the runners `run_s8_*.sh`. These wrap the session 6 `s5_*.py` and session 7 `s7_*.py` unchanged.
- **Scorer bug:** the first `s8_criteria.py` run keyed both error definitions to one name, so only the current-request error was checked. It was fixed and rescored (log `s8-criteria-20261004-172505.log`); no verdict changed.
- Outputs in `E:\DragalPilot\analysis\g70-damping-kp-20261004\`: `equiv_check.json`, `grid_fit_*.json` (+ `_extra`), `selection.json`, `eval_heldout_r674.json` (+ `_extra`), `step.json`.
- Logs: `E:\DragalPilot\logs\s5-s8-*.log`, `s8-select-*.log`, `s8-criteria-*.log`.
