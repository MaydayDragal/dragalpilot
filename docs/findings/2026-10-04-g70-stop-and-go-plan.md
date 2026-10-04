# G70 2024: stop-and-go and low-speed weave, analysis plan and hands-on-wheel plant input (2026-10-04, session 7)

Prepared before the new drives exist. Everything here is fixed **before** looking at the new data. The thresholds marked *provisional* may be changed by the user before the data arrives, not after.

**Why:**
- The user feels the ~3 s weave most at low speed. The main complaint is stop-and-go behind a lead vehicle.
- None of the recorded engaged data is stop-and-go ([video check](2026-10-04-g70-video-lane-check.md), 24 low-speed windows).
- The steering model is weakest at 20–35 mph and doesn't explain the logged gain there ([weave simulation](2026-10-04-g70-weave-sim.md)).
- Retuning V0's gains doesn't help in the model at highway speed ([latAccelFactor](2026-10-04-g70-laf-speed-schedule.md), [damping / KP](2026-10-04-g70-damping-kp-schedule.md)).

## 1. Drive protocol (for the user; normal driving, no software change)

The device runs the deployed `82f58a9a8c` with the default model. Nothing changes on the car.

| # | What | Target amount | Why |
|---|---|---|---|
| D1 | **Stop-and-go behind a lead**, engaged | ≥ 10 min of stop-and-go in total, with several stop/start cycles | The complaint itself. Nothing like it is recorded engaged. |
| D2 | **The same kind of traffic, driven by hand**, openpilot on but not engaged (the model keeps running and logging) | ≥ 5 min, ideally on the same stretch | Reference. It also shows whether the model's *plan* weaves even when it isn't steering. |
| D3 | **Steady 20–35 mph on marked roads, away from intersections**, engaged | Several unbroken stretches of ≥ 30 s, ≥ 5 min in total | The first held-out low-speed data for the steering model (none exists). |
| D4 | Highway, engaged | Optional; ~1–1.5 h above 34 mph | Fills torqued's last bucket (session 4 status). |

- **Notes while driving:**
  - Hands on the wheel as usual. Hand torque is analysed, not avoided.
  - If a weave is felt, a passenger can tap the onroad bookmark. This logs `userBookmark` (mici UI, source fact `openpilot/selfdrive/ui/mici/layouts/main.py` @ `82f58a9a8c`; not confirmed on the device). The driver shouldn't do it.
  - A rough note of the time and place of felt weaves helps too.
- **After the drives:** pull rlogs (never qlogs) **and both road-camera videos** (`fcamera`, `ecamera`) for all new routes, in the same connection, organized under each route folder (CLAUDE.md §3, `docs/local-storage.md`). Device-access rules (CLAUDE.md §6): current address confirmed, device inactive, one SSH connection.

## 2. Pipeline (offline)

1. Promote the pulled routes per [local-storage.md](../local-storage.md).
2. `drive_extract.py` and `lane_drift_extract.py` (unchanged scripts, checkout @ the installed revision) into `E:\DragalPilot\analysis\g70-sng-<date>\{drives,lane}\`.
3. `sng_analyze.py` (this session, `E:\DragalPilot\scratch\wsl\sng\`): episode detection, metrics, decision rules (sections 3–5) → JSON plus a table.
4. If D3 gives clean engaged runs ≥ 30 s at 20–35 mph:
   - `s5_dataset.py`, then the session 6 plant check at 20–35 mph, held out;
   - the hands-input models of section 6.
5. Frame sheets (`vid_windows.py` pattern) for the episodes, using the videos pulled with the rlogs, for a visual check of the scene, lead and lines. The classical lane measurement (`vid_detect.py`) applies only where paint is visible (it is tuned for v > 15 m/s and confident lines).

## 3. Definitions

**Signals** (all exist in the extracts; source facts at `82f58a9a8c`):

| Name | Signal | Notes |
|---|---|---|
| κ_act | `controlsState.curvature` | Curvature from the steering angle through the vehicle model (`selfdrive/controls/controlsd.py` L91). Valid engaged and manual. |
| κ_plan | `modelV2.action.desiredCurvature` | The model's plan, logged engaged **and** manual. While engaged, controlsd clips it to the jerk and lat-accel limits (`clip_curvature`, `drive_helpers.py` L28–41) and logs it as `controlsState.desiredCurvature`. When not engaged, `desiredCurvature` equals κ_act (controlsd L145), so κ_plan is used for both. |
| θ | `carState.steeringAngleDeg` | The felt cue: the wheel moving. |
| h | `carState.steeringTorque` = `MDPS12.CR_Mdps_StrColTq` | Column torque sensor, raw counts (`hyundai_can.dbc`: scale 1, offset −1024). Another Hyundai DBC scales it 1/128 Nm per count; unverified for this car. `STEER_THRESHOLD` 150. |
| τ_eps | `carState.steeringTorqueEps` = `CR_Mdps_OutTq` | EPS motor output torque (scale 0.1; unit not documented). |
| u | `carOutput.actuatorsOutput.torque` | The command after the Hyundai rate/driver limits. |
| κ_lead | 2·y_L / x_L² | Pure-pursuit curvature toward the model's lead (`leadsV3[0]` x[0], y[0], device frame) when prob > 0.5 and 3 m < x_L < 40 m. |
| κ_lane | 2·c(x_a) / x_a² | Pure-pursuit curvature toward the lane centre c at look-ahead x_a = clip(1.5 s · v, 6, 20) m, from `laneLines[1..2]`, when both line probs > 0.5. |

**Bands:**
- weave band W = 0.2–0.6 Hz;
- slow band S = 0.05–0.2 Hz;
- Welch with 10 s Hann windows, 50% overlap (0.1 Hz bins). Data inside a window must be contiguous; no gaps over 0.05 s.

**Speed classes:**
- creep 1–3 m/s;
- crawl 3–9 m/s;
- low 9–15.6 m/s (20–35 mph);
- samples below 1 m/s (openpilot's `MIN_SPEED`) are excluded from spectra.

**Episodes** (contiguous, all within one engagement state):

| Name | Definition |
|---|---|
| **SNG** (stop-and-go) | v ≤ 9 m/s, lead prob > 0.5 with x_L < 30 m for ≥ 80% of the time, and either a stop (v < 0.5 m/s) within the episode or a speed range ≥ 4 m/s. Length ≥ 20 s, counting standstill. Its spectral segments are the parts with v ≥ 1 m/s that last ≥ 10 s. |
| **LS** (steady low speed) | 9–15.6 m/s, |κ_plan| < 0.005 1/m (radius > 200 m), both line probs > 0.7 for ≥ 80% of the time, length ≥ 10 s (≥ 30 s for plant ID). |
| Exclusions (all) | blinker within 3 s; |κ_act| > 0.02 1/m (turns, radius < 50 m); steering pressed (episodes with presses are kept, but listed separately for section 5 D4). |
| Engaged / manual | `carControl.latActive` true / false for the whole episode. |

## 4. Metrics (per episode, then pooled per class × engagement)

1. Band RMS in W and S of θ, κ_act, κ_plan and h.
2. **Request → response** (engaged): coherence, gain and phase of κ_plan → κ_act in W.
3. **Plan couplings** (engaged and manual): coherence and gain of κ_lead → κ_plan and of κ_lane → κ_plan in W and S.
4. **Hands:** coherence of h → κ_act in W; fraction of time |h| > 50 counts; `steeringPressed` fraction; `driverMonitoringState` wheel-touch `driverInteracting`.
5. **Controller state** (engaged):
   - KP(v);
   - integrator-frozen fraction (v < 5 m/s, press or steer-limited);
   - `saturated` fraction;
   - fraction of cycles where the rate/driver limit changed the command by more than 1 count;
   - τ_eps vs u (gain and coherence in W).
6. **Outer loop** (engaged): cross-correlation of κ_act(t) with κ_plan(t + τ), τ = 0–1.5 s, in W.
   - A peak at τ > 0 that is larger than the manual baseline means the plan reacts to the car's own motion.

## 5. Decision rules (pre-declared; thresholds *provisional*)

**D1. Is there a low-speed weave beyond the human reference?**
- Engaged θ band RMS in W ≥ **1.3×** manual, in the same class (SNG or LS).
- The 90% bootstrap CI (resampling episodes) must exclude 1.
- Reported per class. If there are fewer than 3 episodes on either side: "insufficient data", not "no".

**D2. Where does the engaged W content come from?** Evaluated only when D1 is yes, or when engaged θ band RMS in W is ≥ 0.5°.

| Outcome | Rule |
|---|---|
| **Plan-driven** | coherence(κ_plan → κ_act) ≥ 0.6, gain 0.7–1.3, and RMS_W(κ_plan) ≥ 0.7 × RMS_W(κ_act) |
| **Loop-amplified** | coherence ≥ 0.6 and gain > 1.3 |
| **Loop / disturbance** | RMS_W(κ_plan) < 0.5 × RMS_W(κ_act), or coherence < 0.4 |
| Mixed | otherwise |

**D3. Does the plan follow the lead?** (SNG, engaged and manual separately)
- coherence(κ_lead → κ_plan) in W or S ≥ **0.5**;
- and higher than coherence(κ_lane → κ_plan) on the same episodes where both exist.
- If it holds in manual too, it is the model's behaviour, independent of the steering loop.

**D4. Do the hands take part?** (engaged)
- coherence(h → κ_act) in W ≥ **0.5**;
- or the episodes with presses have ≥ 1.5× the θ band RMS of those without.
- A yes makes the hands-input models (section 6) the next step.

**D5. Does the plan react to the car's motion (outer loop)?**
- Engaged cross-correlation peak (τ > 0) ≥ 0.3 and ≥ 2× the manual value.

**Reporting:**
- each rule's numbers and outcome, plus the episode count;
- missing classes are reported as missing, never as normal.
- No rule alone justifies a software change. A change proposal would get its own pre-registration (as in the earlier offline tests).

## 6. Hands on the wheel as a plant input (definition)

### Baseline (session 6, model M2, per speed band)

- **Output:** y = the controller's measurement (steering-angle lateral accel).
- **Input:** w = −4.0 · u (the EPS command in lat-accel units).
- **Equation:**

```text
ÿ = ωn² · ( K·w(t − T) + c_r·g·roll + b − y − F_c·tanh(ẏ/ε) ) − 2ζωn·ẏ
```

- At 20–35 mph, simulated V0 gives A 0.81 at 0.4–0.6 Hz where the logs show 1.19. Everything not explained by w (hands, road, the vehicle-to-steering coupling) sits in the residual. That residual is 35–72% of the 0.2–0.6 Hz motion.

### Physics

- The column sensor h measures the torsion-bar torque between the steering wheel and the EPS. It is the driver's torque on the column, from two sources:
  - active hand torque (intent);
  - passive hand impedance, i.e. the hands' resistance to the wheel's motion.
- The EPS adds motor torque τ_eps from the LKAS command **and** from its own assist on h (speed-dependent; not documented for this car).
- So h enters the rack in two ways: directly, and amplified by the assist.

### Candidate models

Each is fitted per speed band with the session 6 method (output error, 20 s chunks, same chunk selection unless noted):

| Model | Change from M2 | What it answers | Caveat |
|---|---|---|---|
| **M3a: hands as exogenous input** | `K·w(t−T)` → `K·w(t−T) + K_h·h(t−T_h)`. K_h (lat accel per count) and T_h ≥ 0 are new parameters; the sign of h is fitted, not assumed. Fitted on clean chunks, and again with press chunks included. | How much of the unexplained motion lines up with the measured hand torque. | h is partly a *reaction* to the motion (impedance), so replaying logged h in a closed-loop simulation of a *different* controller is only approximate. Valid for explaining the logs (model adequacy); weaker for counterfactuals. |
| **M3b: hands as impedance** | M2 fitted separately on hands-light and hands-firm chunks, classed by RMS(h) in the chunk (split at the median of engaged chunks). ωn, ζ, K, F_c are compared. | Whether the hands change the steering's dynamics (damping, stiffness), which a counterfactual simulation *can* use (pick the parameter set). | Needs enough chunks in each class; RMS(h) mixes active and passive torque. |
| **M3c: split actuator and steering** | Two stages: (1) u → τ_eps (rate limit, delay, gain, and any low-speed behaviour); (2) τ_eps + K_h'·h → y. | Whether the low-speed shortfall is in the actuator (the EPS not delivering what's commanded) or in the steering/hands dynamics. | The τ_eps unit is unknown; its gain is fitted. |

### Acceptance (held-out chunks, 20–35 mph first)

A hands model is accepted over M2 if, on held-out chunks:
1. VAF improves by ≥ **0.03** and the W-band residual RMS falls by ≥ **20%**;
2. **and** the simulated V0 A gain at 0.4–0.6 Hz at 20–35 mph moves toward the logged value, closing ≥ 50% of the gap (0.81 vs 1.19 on the session 6 fit routes).

- For M3b, item 1 applies per class, and item 2 with the matching class's parameters.
- Fitting before held-out D3 data exists is allowed as exploration (session 6's leave-one-route-out). It is labelled as such and doesn't count for acceptance.

### Feasibility on existing data (section 7, run now)

Before any fit: does h carry W-band content during engaged clean runs, and is it coherent with the session 6 plant residual? If not, M3a can't help, and M3b/M3c become the only hands-related options.

## 7. Preparation done now (results in the next section of this doc)

- `sng_analyze.py` implemented and dry-run on the existing routes 4, 6–9, 0a, 0b, 0c, 0e. Their lane extracts for routes 4 and 6–9 were re-made with the lead fields into `analysis\g70-sng-prep-20261004\lane\`.
  - **Expected:** few or no SNG episodes. This exercises the code and shows what the existing data can and cannot say.
- The hands feasibility check from section 6.

## Amendments after the dry run (before any new data)

The dry run on existing routes exposed tool-design problems, not weave outcomes on the target data. Fixed in `sng_analyze.py`; the pre-amendment version is kept as `sng_analyze.v0_dryrun.py.bak`.

| # | Problem found | Change |
|---|---|---|
| A1 | SNG spectral segments required v ≥ 1 m/s for ≥ 10 s. Real stop-and-go moves for only a few seconds between stops, so the manual SNG episodes gave no spectra. | SNG spectra use the whole episode, standstill included. The angle-based signals (θ, κ_act, κ_plan, h) are defined at standstill. LS is unchanged (v ≥ 1 m/s, ≥ 10 s). |
| A2 | The D5 cross-correlation used only lags where the plan *follows* the car, so it couldn't locate the peak. It also can't separate "the plan reacts to the car" from "the car follows the plan". | The lag profile runs from −1.5 to +1.5 s (peak lag reported). **D5 is now:** engaged κ_plan band RMS in W ≥ 1.3× manual in the same class, with a 90% bootstrap CI above 1. If the plan wanders more when the car steers itself, the loop through the model is implicated. |
| A3 | D4 (h ↔ κ_act coherence) can't tell active hand torque from the steering wheel's inertia and passive hand impedance. The column sensor measures all three. | The phase is reported. A D4 "yes" now reads "hands/column participate", not a cause. It points to M3b/M3c rather than M3a. |
| A4 | A manual "SNG" episode on route 0a never moved (v ≤ 0.3 m/s). | An SNG episode must also reach v ≥ 3 m/s. |

**Not a design change, a bug:** the rate-limit fraction compared the command of cycle k with the carOutput of cycle k. The deployed timing (session 6) puts it in cycle k+1. Fixed: the fraction went from an implausible 40–53% to 6–16% engaged, matching the simulated V0 (14–18%).

## Results of the preparation

### Dry run on existing routes (observation; tooling check)

- **Time-base check:** the two extracts agree exactly (max Δv = 0.0 on all 9 routes).
- **Episodes:**

| Class | Engaged | Manual |
|---|---|---|
| SNG | 0 | 2 (routes 8, 9: 68 s and 75 s, lead 100%, lines confident 0–2%) |
| LS | 9 (routes 0a, 0b; 190 s) | 8 (routes 0c, 0e; 189 s) |

  Routes 4, 6 and 7 have no qualifying episodes.
- **LS (20–35 mph), as a check of what the rules do, not as an answer:**
  - **D1:** engaged/manual θ W-band RMS ratio 0.78 (90% CI 0.58–1.10), so no. This agrees with session 4b.
  - **D2** (gate passed on θ W RMS 1.03°): coherence κ_plan → κ_act 0.91, gain 0.92, plan/act RMS 1.03, so "plan-driven", meaning the inner loop tracks the plan.
    - In manual driving the plan matches the human's steering just as closely (coherence 0.84, gain 0.96).
    - So at these speeds, plan and steering motion move together whoever steers. D2 says nothing about *why* the plan moves; that is D3 and D5.
  - **D5:** plan W ratio engaged/manual 0.92 (0.70–1.19), so no. The lag-profile peak is at −0.2 s engaged and −0.1 s manual (the plan leads by about the actuator delay).
  - **D4:** coherence 0.63, phase −79° (κ_act lags h). Per A3, "participates". The phase is velocity-like, consistent with passive column/hand dynamics.
  - **EPS actuator:** command → τ_eps coherence 0.92, phase −6° in W. The EPS delivers the command in the weave band at 20–35 mph.
  - **Controller:** KP ≈ 2.0–2.6, saturation 0, rate-limited 6–16% of cycles.
- **SNG manual** (2 moving episodes, after A4; log `sng-dry-20261004-173755.log`): D3 lead → plan coherence 0.05 (W) and 0.34 (S); lines were almost never confident. Too little data for any SNG rule. D1 and D5 report "insufficient data", as designed.

### Hands feasibility (section 6; observation)

`hands_feas.py`: engaged clean runs ≥ 30 s, session 6 plants, routes 8 / 0a / 0b / 6 / 7 / 4.

| Band | Runs (s) | h W RMS (counts) | \|h\| > 50 | Plant residual / y, W RMS | Coherence h → residual (0.2–0.3 / 0.3–0.4 / 0.4–0.6 Hz) | Coherence h → y (phase) |
|---|---|---|---|---|---|---|
| 20–35 mph | 5 (227) | 7.0 | 5.4% | 0.038 / 0.087 | 0.03 / 0.33 / 0.24 | 0.27–0.68 (−56° to −131°) |
| 35–55 mph | 12 (561) | 8.2 | 1.8% | 0.053 / 0.145 | 0.05 / 0.08 / 0.21 | 0.54–0.68 (−72° to −99°) |
| 55+ mph | 14 (2,648) | 5.2 | 1.0% | 0.040 / 0.063 | 0.18 / 0.36 / 0.23 | 0.43–0.65 (−74° to −107°) |

- **Hands are light:** column torque is mostly far below `STEER_THRESHOLD` 150.
- **h moves with the steering, leading it by 56–131°.** That is the signature of the wheel's inertia and passive hand impedance, i.e. a *reaction* to the motion.
- **h is coherent with the plant residual only at 0.03–0.36** (magnitude-squared), so it explains at most about a third of the residual power in any bin, usually under a quarter. **M3a can only explain a modest part of the residual**, and its causal reading is doubtful.
- **M3b split** (runs with light vs firmer hands, median split):
  - At 20–35 mph the residual is 0.38 of the motion with light hands and 0.52 with firmer hands. But that is 3 vs 2 runs.
  - At 35+ mph: no difference (0.39 / 0.36 and 0.63 / 0.64).
  - The hands range in the data is narrow (h RMS 11–20 counts). **Inconclusive.**
- **M3c stage 1** (command → EPS torque) is clean at 20–35 mph (dry-run D4 line above). Any low-speed shortfall is therefore more likely in the steering/hands dynamics (stage 2) or in the request than in the actuator.

### What this changes

- **The hands model is defined.** On existing data it is unlikely to close the session 6 low-speed gap through M3a alone.
- **Priority when D3 data exists:**
  1. M3c stage 2 (τ_eps + h → y);
  2. M3b with a wider hands range, which normal driving may or may not provide (hands-off driving is not requested).
- **The stop-and-go tool works end to end.** The existing data can't answer the stop-and-go question (no engaged SNG episodes), which confirms the drive protocol is needed.

### Artifacts

- Scripts in `E:\DragalPilot\scratch\wsl\sng\`: `sng_analyze.py` (+ `.v0_dryrun.py.bak`), `hands_feas.py`, the runners `run_sng_*.sh` and `run_hands_feas.sh`, and `_amend*.py` (the amendment patches, kept for the record).
- Outputs in `E:\DragalPilot\analysis\g70-sng-prep-20261004\`: `lane\` (routes 4, 6–9 with lead fields), `sng_dry_existing.json`, `hands_feasibility.json`.
- Logs: `E:\DragalPilot\logs\sng-*.log`.
