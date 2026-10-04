# G70 2024: speed-dependent latAccelFactor scale, offline hypothesis (2026-10-04, session 7)

Option (b) of the [weave simulation](2026-10-04-g70-weave-sim.md) "Options", chosen by the user while new drives are pending. **Offline model evidence only; no device access, no code change in `sunnypilot/`.**

## Pre-registration (written before any result of this session)

### Question

On this car (GENESIS_G70_2024 only), would scaling V0's latAccelFactor by a speed-dependent factor s(v) reduce the closed-loop amplification of 0.3–0.6 Hz content at 35+ mph? Measured in the controller+EPS link A (request → steering-angle lateral accel). The change must not worsen lag beyond a stated tolerance, curve tracking, error or step response, and must not degrade 20–35 mph.

### Source facts the design rests on (`dragal/custom` @ `82f58a9a8c`)

- **V0's output conversion:** `output_torque = torque_from_lateral_accel(output_lataccel, torque_params)` (`openpilot/sunnypilot/selfdrive/controls/lib/latcontrol_torque_v0.py` L108). For this car that is `lateral_accel / latAccelFactor` (`opendbc_repo/opendbc/car/interfaces.py` L215–220; no Hyundai override).
  - So scaling latAccelFactor scales feedforward, P and I together, in torque.
- **The speed argument is missing:** the V0 call passes no speed, so a car-specific `torque_from_lateral_accel` cannot see v. How s(v) would be implemented is an open design question. It does not affect this offline test.
- **Friction is unchanged by the scale:** it is `friction · latAccelFactor` in lat-accel space (`opendbc_repo/opendbc/car/lateral.py` L204–212), so in torque it does not depend on latAccelFactor.
- **PID limits are unchanged too:** they are `±steer_max · latAccelFactor` (V0 L59–61), so in torque they are the same.
- **torqued:** when `useParams`, controlsd overwrites latAccelFactor with torqued's filtered value (`openpilot/selfdrive/controls/controlsd.py` L95–98). torqued bounds it to ±30% of the offline 4.0 (`openpilot/selfdrive/locationd/torqued.py` L26, L100–101).
  - So s(v) is defined as a **multiplier on whatever latAccelFactor the controller holds** (offline or learned).
  - Last observed: torqued not yet valid; raw estimate 4.0–4.25, at most 4.47 over the four tune drives ([low-speed findings](2026-10-04-g70-lowspeed-drives.md)).

### Candidate family

- **Schedule:** s(v) = linear interpolation over the speeds [12.5, 20.0, 29.0] m/s (the synthetic-test speed of each band) with values [s_L, s_M, s_H], held constant outside that range.
  - In the controller, latAccelFactor_eff = latAccelFactor_base · s(v) every cycle.
  - Everything else in V0 is unchanged.
- **Grid:**
  - s_L ∈ {0.9, 1.0};
  - s_M ∈ {1.0, 1.1, 1.2, 1.3};
  - s_H ∈ {1.0, 1.1, 1.2, 1.3, 1.4}.
  - Base latAccelFactor 4.0, friction 0.07 (deployed).
- The grid brackets the session 6 plant gains (K 0.89 / 1.21 / 1.29). The values come from the fitted plant, not from a tuning target.

### Data split

- **Selection (design) set:** routes 8, 0a and 0b (the plant-fit routes), session 6 dataset.
- **Held-out set:**
  - routes 6 and 7 (the session 6 held-out routes);
  - routes 4 and 9, if they contain clean engaged runs ≥ 30 s. They are new to the simulation and give the first held-out data at 20–35 mph.
  - All held-out routes are simulated with the deployed tune (4.0 / 0.07) as the V0 base, whatever tune they were driven with. The logged requests, speed, roll and driver torque are the inputs.
- **Limitation, stated up front:** the plant model was fitted on the selection routes. So the held-out evaluation is held-out in its inputs and disturbances, not in the plant. True validation needs new drives (pending).

### Selection rule (selection set only, applied mechanically)

- **Eligible schedules** satisfy all of the following in every band, in both modes (clean, dist):
  - curve ratio 0.95–1.04;
  - mean |error| ≤ 1.20× V0, for both the delayed and the current request;
  - A phase at 0.3–0.4 and 0.4–0.6 Hz no more than 5° later than V0;
  - at 20–35 mph, A gain at 0.3–0.4 and 0.4–0.6 Hz no more than 0.03 above V0.
- **Choice:** the eligible schedule with the lowest mean A gain over {0.3–0.4, 0.4–0.6 Hz} × {35–55, 55+ mph} × {clean, dist}.
- **Ties** (within 0.01 of that minimum): take the one closest to s ≡ 1 (smallest Σ|s − 1|).
- **No eligible schedule:** report it, and evaluate the K-matched schedule [0.89, 1.21, 1.29] on held-out as a diagnostic only.

### Success criteria (held-out set; revised from session 6)

1. A gain at 0.3–0.4 and 0.4–0.6 Hz at 35–55 and 55+ mph is **lower than V0 by ≥ 0.05** in both modes.
2. A phase in those bands is **no more than 5° later** than V0.
3. Curve ratio 0.95–1.04 in every band that has curves.
4. Mean |error|, for both request definitions, is **up by no more than 20%** in any band.
5. At 20–35 mph (if held-out runs exist): A gain at 0.3–0.6 Hz up by no more than 0.03, and items 3–4 hold.
6. Synthetic tests: 1.0 m/s² step overshoot not above V0 in any band; t90 not longer than V0 + 0.1 s.
7. Torque saturation fraction up by no more than 0.5 percentage points.

**Deviations from the session 6 criteria** (made because session 6 showed the originals can't be met by any steering-loop change):
- "C ≤ 1.2" is replaced by item 1. The vehicle link B alone is 1.21–1.34 at 35+ mph.
- "Lag not worse than V0" is relaxed to ≤ 5°.

Both originals are still reported, labelled, alongside the results.

### Sensitivity (reported, not part of pass/fail)

- The chosen schedule and V0 at base 4.2 (torqued's expected value) and 4.47 (the highest raw estimate seen).
- V0 at base 4.2 alone, i.e. what torqued would do without any schedule.

### What a pass would and would not mean

- **A pass would justify:** an implementation design and its tests, followed by a validation on new held-out drives. It would not by itself justify a deployment proposal.
- **A fail means:** no proposal. The result is recorded.

## Results (model result; written after the runs)

### Answer

**By the pre-registered criteria, the selected schedule fails on held-out (item 6), and its benefit is small.**

- It meets items 1–5 and 7 on held-out. Item 1 is met only at the threshold at 55+ mph.
- **What it buys:** 0.2–0.6 Hz motion down ~5%, and C at 0.4–0.6 Hz above 55 mph still 1.38.
- **What blocks larger gains:** every schedule that cuts more costs over 5° of lag.
- It is **not robust to torqued's learned value.**
- **No implementation or device change is proposed.**

### Harness and data checks (observation)

- **Wrapper:** s ≡ 1 reproduces V0 exactly (difference 0.0 on every metric; `selection.json`).
- **New routes, source V0 replayed on logged inputs** (`s5_replay_check.py`):
  - route 4 at its driven tune 2.7 / 0.11: setpoint ≤ 2.4e-7, carOutput exact on 89.1% of cycles;
  - route 9 at 4.0 / 0.07: carOutput exact on 92.2%.
  - Session 6 got 81–95% on its routes.
- **Clean engaged runs ≥ 30 s:**
  - route 4: 37 s at 35–55 mph and 79 s at 55+ mph; it ran with the default lat delay 0.3 s;
  - route 9: none.
  - **No held-out route has a 20–35 mph run**, so item 5 could not be evaluated on held-out. The 30 s rule was not relaxed.
- **Held-out pool:** routes 6, 7 and 4; 229 s at 35–55 mph, 1,270 s at 55+ mph.

### Selection (routes 8 / 0a / 0b)

- **The rule chose s = [0.9, 1.3, 1.1]** at [12.5, 20, 29] m/s. Score 1.004 vs V0 1.080, the mean A gain over 0.3–0.6 Hz at 35+ mph.
  - Only 13 of 40 schedules were eligible.
  - **Lag is the binding constraint:** every schedule with s_H ≥ 1.2 adds more than 5° at 55+ mph.
  - Several neighbours fail by small margins:
    - [1.0, 1.3, 1.1]: curve 0.948 at 20–35 mph;
    - [1.0, 1.0, 1.2]: lag 5.1°.
  - So the choice sits near the edge of the allowed region.
- **Fit-route 20–35 mph:** A changes by +0.007 to +0.019 (within the +0.03 guard), lag 0.4–1.1° less, error 2–4% lower.

### Held-out, s = [0.9, 1.3, 1.1] vs V0 (both at base 4.0)

| Band, mode | ΔA 0.3–0.4 / 0.4–0.6 Hz | ΔPhase (− = more lag) | C 0.4–0.6 Hz, V0 → cand | Curve | Mean \|e\| ratio (delayed / current) | 0.2–0.6 Hz motion RMS |
|---|---|---|---|---|---|---|
| 35–55 mph, clean | −0.075 / −0.086 | −2.2° / −3.1° | 1.18 → 1.08 | 1.01 → 0.977 | 1.03 / 1.06 | 0.149 → 0.142 |
| 35–55 mph, dist | −0.093 / −0.085 | −2.8° / −2.5° | 1.25 → 1.15 | 1.00 → 0.966 | 0.98 / 1.03 | 0.145 → 0.138 |
| 55+ mph, clean | **−0.050** / −0.060 | −1.4° / −2.3° | 1.46 → 1.38 | 1.04 → 1.02 | 0.93 / 0.96 | 0.0451 → 0.0428 |
| 55+ mph, dist | −0.052 / −0.066 | −1.9° / −3.2° | 1.24 → 1.15 | 1.02 → 1.01 | 0.98 / 0.98 | 0.0460 → 0.0443 |

Torque saturation is unchanged (0.0 pp).

**Synthetic tests** (1.0 m/s² step; overshoot / t90):

| Band | V0 | Candidate |
|---|---|---|
| 20–35 mph | −1.0% / 1.02 s | +0.1% / 0.94 s |
| 35–55 mph | +4.8% / 0.87 s | −0.8% / 0.97 s |
| 55+ mph | +26.1% / 0.76 s | +20.9% / 0.76 s |

**Criteria (held-out):**

| Item | Result |
|---|---|
| 1. ΔA ≤ −0.05 | pass. At 55+ mph 0.3–0.4 Hz: exactly −0.050 (clean), −0.052 (dist) |
| 2. lag ≤ 5° | pass (≤ 3.2°) |
| 3. curve | pass (0.966–1.02) |
| 4. error | pass (≤ +6%) |
| 5. 20–35 mph | **not evaluable on held-out** (fit routes: pass) |
| 6. step | **FAIL:** at 20–35 mph the overshoot goes from −1.0% (V0 does not quite reach the request) to +0.1%. 35–55 mph t90 is +0.10 s, exactly at the tolerance. |
| 7. saturation | pass |

- **On item 6:** the 20–35 mph failure is a 1.1-point change with no physical significance. It still counts as a fail: the criterion was pre-registered as written, and it is not re-defined after the result.
- **Original session 6 criteria:**
  - C ≤ 1.2 still fails at 55+ mph 0.4–0.6 Hz (clean, 1.38);
  - lag is worse than V0 in every band, by 1.4–3.2°.

### Diagnostic and sensitivity (held-out)

- **K-matched [0.89, 1.21, 1.29] (diagnostic):**
  - larger effect at 55+ mph: ΔA −0.13 to −0.17, C 0.4–0.6 Hz 1.46 → 1.24 (clean), step overshoot 26 → 12%, motion RMS −11%;
  - but **+5.2° to +8.4° lag** at 55+ mph, so it fails item 2 (and item 6 at 20–35 mph).
- **torqued alone (V0 at base 4.2 vs 4.0):** ΔA −0.020 to −0.034, lag 0.5–1.6°. That is about 40% of the selected schedule's effect at 55+ mph, with no schedule at all. It fails item 1 by size, as expected.
- **Selected schedule at base 4.2 vs V0 at 4.2:**
  - ΔA about the same (−0.050 to −0.092);
  - error up to +13% (35–55 mph clean);
  - 35–55 mph step t90 +0.13 s (fails item 6).
- **Selected schedule at base 4.47 vs V0 at 4.47:**
  - **fails items 3 and 4:** curve 0.946 (35–55 mph dist), error +25% (35–55 mph clean);
  - the effective latAccelFactor at 20 m/s is then 5.8.
  - A multiplier on torqued's learned value is therefore **not robust** if torqued learns high.

### Interpretation (hypothesis)

- In this model, scaling feedforward + P + I by speed is a **weak lever on the weave.** At 55+ mph it trades gain for lag at roughly 3–5° per 0.1 reduction in A (selected schedule and K-matched alike).
  - The most it can do within a 5° lag budget is a ~4–5% reduction in 0.2–0.6 Hz motion.
  - That is small next to the model's absolute uncertainty (±0.15 in A) and likely not noticeable.
  - This fits session 6's reading: the plant's lag (~90° at 0.5 Hz) and the vehicle's own yaw response (B 1.2–1.3) set most of the peak, not the controller's gain scale.
- **torqued becoming valid** (expected ~4.2) gives part of the same effect without any code change. A schedule defined as a multiplier on top of it would compound with it.
- **Levers not tested here:** the KP speed schedule, and a damping (derivative) term. V0 passes the filtered measurement rate to the PID but KD = 0 (V0 L27, L103–107). Each would be a new hypothesis, with its own pre-registration.

### Limitations

- The plant model was fitted on the selection routes. The held-out test is held-out in its inputs and disturbances only.
- No held-out 20–35 mph data.
- The low-speed weave is not explained by the model (session 6), so nothing here speaks to it.
- The limitations of the session 6 model all carry over: single-input plant, constant per-band parameters, no outer loop, C = A × B_emp.

### Artifacts

- Scripts in `E:\DragalPilot\scratch\wsl\s7\`: `s7_sched.py`, `s7_sim.py`, `s7_step.py`, `s7_select.py`, `s7_criteria.py`, `s7_inventory.py`, and the runners `run_s7_*.sh`. These wrap the session 6 `s5_*.py` unchanged.
- Outputs in `E:\DragalPilot\analysis\g70-laf-sched-20261004\`:
  - `dataset/` (r4, r9 new; r6, r7 copied, sha256-checked);
  - `grid_fit_*.json`, `selection.json`, `eval_heldout_r674.json`, `eval_fit_sens.json`, `step.json`;
  - `replay_check_r4_2.7.json`, `replay_check_r9_4.0.json`.
- Logs: `E:\DragalPilot\logs\s7-*.log`, `s5-s7-*.log`, `s5-replay-check-s7-*.log`.
- Environment: `~/venvs/vid` (Python 3.12.13, numpy 2.5.3, scipy 1.18.1) for the simulation; the checkout `.venv` @ `82f58a9a8c` for the dataset build and the replay check.
