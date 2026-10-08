# G70 2024: refining D2C4 for both weave and wheel jitter, offline (2026-10-07, session 13ws)

Started from the [weave + twitch simulation kickoff](../sessions/2026-10-07-s12mv2-weave-twitch-sim-kickoff.md). Offline and local simulation only: no device access, no change to `dragal/custom` or the WSL clone without asking the user first.

**Goal:** starting from D2C4, find a change that keeps D2C4's steering-wheel jitter reduction **and** does not make weave worse. The deliverable is an evidence-backed candidate, or an honest frontier if none exists.

Evidence labels: **source fact** (file + revision), **observation** (rlogs, route IDs), **model result**, **hypothesis**, **exploratory**.

## 0. Session start (2026-10-07 ~17:59 EDT)

- Outer `main` @ `606c36b` + 37 uncommitted doc paths (sessions 8–12mv).
- `sunnypilot/` `dragal/custom` @ `89bbe60ab127cf71d238856a19c1e74b16bc36bd`, clean. WSL clone `~/src/sunnypilot` @ `89bbe60ab1` (detached), clean. WSL had just booted: no jobs.
- `E:` UniqueId `daa460f7…` matches; write probe OK; 228.8 GB free. (The s12mv2 handoff said "about 213 GB"; the s12mv start said 228.8 GB. Today's figure is 228.8 GB.)
- **Parallel session:** none found. No new logs on `E:` since 17:47; no WSL jobs. Several `claude` processes exist on the host, but none is writing project data. Treated as no parallel session. All 6 cores may be used (CLAUDE.md §8); re-checked before each large run.
- Outputs: `E:\DragalPilot\analysis\g70-weave-twitch-sim-20261007\`. Scripts: `E:\DragalPilot\scratch\wsl\sng\s16_ws_*.py` (new files only; shared `s11_*`–`s15_*` scripts are imported, never edited). Logs: `E:\DragalPilot\logs\s13ws-*`.

## 1. Feasibility facts for the new methods (source facts and observations; nothing run)

From a read-only survey of the checkout (`89bbe60ab1`; paths under `sunnypilot/openpilot/`) and `origin/master` @ `a5f4465`:

- **The shipped driving model can't run on x86 as is.** `selfdrive/modeld/models/driving_tinygrad.pkl.chunk01–04` (about 176 MB) is a tinygrad JIT pickle compiled for the device GPU (`"DEV": "QCOM"` in `tg_input_devices.json`; "QCOM" strings in chunk01). The prebuilt tree has no `.onnx` files.
- **The ONNX source exists upstream.** `origin/master` @ `a5f4465` (the master commit named by the installed `dev` build) has `selfdrive/modeld/models/driving_supercombo.onnx` as a Git LFS pointer: size 60,881,999 bytes, sha256 `659727c4…`.
  - `selfdrive/modeld/compile_modeld.py` L293–331 compiles from `--onnx`; the device comes from tinygrad's `DEV` env var. `tinygrad_repo` 0.14.0 has a CPU backend (`runtime/ops_cpu.py`).
  - **So a CPU build of the same model is likely feasible** (inference). Its identity with the device model has to be shown by reproducing logged `modelV2` outputs.
- **Which model the device runs:** the device params pulled in sessions 8 and 10 have `ModelManager_ActiveJson` (two model-list URLs) but no active-bundle param. That suggests the bundled default model (*hypothesis*, settled by the reproduction check above).
- **Model inputs** (`compile_modeld.py` L78–128, L202–209): road + wide road, two frames each of 6-channel YUV420 128×256 in the model frame (512×256); `desire_pulse`, `traffic_convention`, `action_t` (lat/long delay) and a recurrent `features_buffer`. The camera → model-frame warp is `get_warp_matrix(rpyCalib, intrinsics, bigmodel)` (`common/transformations/model.py` L65–70), done inside the JIT with nearest-neighbour sampling.
- **Reprojection already exists in sunnypilot:** `sunnypilot/modeld_v2/camera_offset_helper.py` L28–34 shifts the camera laterally by a ground-plane shear of the model warp (`CameraOffset` param). Heading changes are a change of `device_from_calib_euler`. Exact for road-plane pixels only.
- **Native code:** every committed `.so` is aarch64. Session 8 already built x86 copies of `msgq`/`visionipc`/`params` (`build_x86_openpilot_shim.sh`). A direct tinygrad call with numpy inputs needs none of them.
- **Videos on hand:** fcamera + ecamera for routes up to `0x25`, including the A-primary drives `0x1e`, `0x20`, `0x22`, `0x24` on B's road. **Not** for `0x26`–`0x28` (deferred; `metadata/GAPS.md`), so the only D2C4 drive (`0x28`) can't be replayed through the model.
- **`tools/sim`** bridges MetaDrive only (not installed). It simulates a Honda with angle steering; `LatControlTorque` returns 0 for the angle, so the torque controller doesn't steer the sim car without a bridge change. Rendering is synthetic.
- **`tools/lateral_maneuvers`** is an on-device maneuver generator (needs a car or the sim). Its report runs offline.
- **`process_replay`/`model_replay`** need the x86 native libs and a CPU-compiled model; `model_replay.py` targets a fixed CI route.

## 2. Brainstorm (written before running anything)

### 2.1 What the problem needs (from the s12mv root cause)

- The twitch is a stick-slip limit cycle excited by **small, fast** request jitter (0.7–4 Hz) and amplified by V0's **error-driven** friction term (slope ≈ fric·laf/0.3 ≈ 0.9 per m/s² near zero error, as large as P).
- The weave lives at **0.2–0.4 Hz** and needs **small, slow** corrections to stay fast. D2C4 costs about 18° there on the car (8° filter, 10° deadzone).
- **A constraint on linear fixes (Bode gain–phase relation):** the jitter band starts only 2–3× above the weave band. Any causal linear request filter that attenuates 0.7–4 Hz adds lag at 0.3 Hz. A lead network that cancels the lag gives the attenuation back (worked example: (1 + 0.36 s)/(1 + s/4π)⁴ has about 0° at 0.3 Hz but gain 1.16 at 2 Hz). So a linear filter can trade lag for jitter but not escape the trade.
- **The way out has to be nonlinear or path-selective.** Jitter and weave corrections differ in persistence (sign flips every 0.1–0.7 s vs every 1.25–2.5 s), not in amplitude: both are about 0.02–0.04 m/s² RMS on straight roads. A fix should keep friction compensation for small errors that **persist** and drop it for small errors that **flip quickly**. D2 does the opposite of what weave needs: it drops all small errors, slow or fast.

### 2.2 Fix directions not yet tried (hypotheses; all car-scoped, none widens a safety limit or bypasses a check)

| ID | Idea | Mechanism argument | What could go wrong |
|---|---|---|---|
| **F1** | **Frequency-split ("leaky") friction deadzone:** friction input x = e_slow + DZ(e − e_slow), e_slow = causal first-order LP of the error at f_s (0.3–1 Hz). | Slow small errors keep full friction compensation (small-signal 0.2–0.4 Hz response restored); the fast part of the error, where jitter lives, is deadzoned. | The stick-slip hold ramp is itself slow (holds 0.3–0.6 s), so e_slow may re-arm the twitch. Simulation decides. |
| **F2** | **Slow friction input, no deadzone:** x = LP(e) at 0.5–2 Hz (MV9 without its deadzone, and on the error rather than the request). | Removes the friction term's chatter on jitter; keeps slow compensation. | Adds lag in the friction path itself; may destabilise the inner loop. |
| **F3** | **Play-operator (backlash) friction input:** y follows e only when e moves more than ±h from y; x = y. h 0.03–0.1 m/s². | Jitter that reverses within ±h doesn't move the friction term; a persistent trend moves it with no time lag, only an amplitude offset h. Unlike a deadzone it doesn't zero compensation near zero error. | Amplitude-dependent phase lag for corrections smaller than about 2h, like any backlash. |
| **F4** | **Soft deadzone:** slope s (0.25–0.5) inside the band instead of 0, continuous outside. | Interpolates between A0 and D3; C1 (lower slope everywhere) cut jumps 36–42% in session 10, so slope rather than a hard zero may carry most of the benefit. | Probably a point on the same frontier; cheap to check. |
| **F5** | **Lower-lag jitter filter** instead of C4: 2nd-order Butterworth at 3–4 Hz, a notch at the jitter's dominant frequency, or a play operator on the request (fast-jitter only). Chosen from the jump-triggered request spectrum (M6 below). | Spend the filter's lag only where the jitter that actually triggers jumps lives. | Bode: still some lag; the play operator on the request lags small corrections. |
| **F6** | **Phase-lead compensation** on the request (lead-lag at 0.3–1 Hz) combined with C4 or F1. | Cancels the 8° of C4 (or more) in the weave band. | Amplifies the jitter band by the Bode trade (2.1); must be paired with a nonlinear jitter fix. Expected to lose unless F1/F3 carry the twitch reduction. |
| **F7** | **Breakaway release:** on detected wheel motion after a hold, drop the torque built up during the hold by the static−kinetic difference. | Targets the overshoot (41–74%) rather than the hold. | Transport delay (31–68 ms) plus EPS lag likely makes it too late (jumps last tens of ms). Cheap to rule out. |
| **F8** | **Speed-scheduled feedforward gain** (session 6's v0k) on top of the best of F1–F5. | Lowers the inner loop's band peaking (plant gain 1.29× what laf assumes at 55+ mph). | Session 6: v0k added 3–6° of lag at 0.4–0.6 Hz. |
| F9 | Dither (a small 10–20 Hz torque component that keeps the steering in kinetic friction). | The textbook cure for stiction hunting. | It is felt in the wheel (the complaint is wheel jitter), the 20 Hz line already exists, and the Karnopp plant has no pre-sliding, so the model can't judge it. **Not proposed.** |

### 2.3 New analysis and simulation methods

| ID | Method | What it would reveal | Effort | Risk | Validity |
|---|---|---|---|---|---|
| **M1** | **Small-signal lock-in transfer (dual-input describing function):** add a known multisine (e.g. 0.23/0.31/0.37 Hz, 0.01–0.05 m/s²) to the logged requests in the simulator and read the response at exactly those frequencies, per amplitude, with the real jitter still present. | A clean, low-variance in-context lag and gain per amplitude for every candidate: exactly the "small corrections in the weave band" the root cause is about. Supplies the inner-loop describing function for M3. | Low (existing loop; new driver). | Low. | Same plant as the car-validated estimator; must agree with it on A0/D2C4 before use. |
| **M2** | **Re-score every earlier candidate** (C1–C6, D1, D3, J1, H1, P1, MV1–MV9) on the car-validated 0.2–0.4 Hz in-context lag. | The full frontier, not only the deadzone family. C1/C6 (smaller slope, no deadzone) never had a weave metric. | Low. | None. | As the proxy. |
| **M3** | **Semi-empirical outer loop by harmonic balance / sensitivity:** inner-loop describing function from M1 × the policy (lane → request) and vehicle (request → lane) transfers measured on the A-arm logs → loop gain L(A, jω); predicted lane-weave change S_B/S_A and the limit-cycle amplitude/frequency per candidate. | A weave prediction on the lane offset, and why: phase margin at the crossover. **Testable:** it must predict the on-car D2C4 lane +41% (CI +20.5…+65.4%) and request +32% (+13…+51%) from the model's inner-loop change. | Medium. | Medium (closed-loop H1 policy estimates are feedback-biased; s12mv §1). | Only if the reproduction passes. |
| **M4** | **Driving model in the loop on real video.** CPU-compile `driving_supercombo.onnx` (upstream `a5f4465`) with tinygrad; decode fcamera/ecamera of the A drives on B's road; warp each frame by a simulated lateral offset and heading (`camera_offset_helper`'s ground-plane shear + a yaw change). Stages: (a) reproduce the logged `desiredCurvature` from the original frames; (b) **open-loop policy probing**: inject small Δy/Δψ sines through the warp and measure the real policy's response, free of feedback bias; (c) full closed loop: bicycle model + inner sim + model on re-warped frames. | The true lane-keeping policy, which every other outer-loop model only approximates; (b) alone fixes M3's weakest link. (c) is a real digital twin. | High (download, compile, frame pipeline, ~20k frames per drive pass; CPU speed unknown). | High: compile may fail; the default-model assumption must hold; reprojection is exact only on the road plane; the model may react to warp artefacts. | High if (a) reproduces the logs; B's video is missing, so the twin is checked on A drives (A0 in the loop vs logged) and against the on-car D2C4 deltas. |
| **M5** | **Pre-sliding (LuGre/Dahl) plant variant:** add micro-slip compliance before breakaway, fit as Amendment 2/6, adequacy-tested including `0x28`'s holds and the car's 0.2–0.4 / 0.4–0.7 Hz split. | The Karnopp plant has a hard stick: it over-predicts holds on `0x28` (+0.12) and lag at 0.4–0.7 Hz. Real friction has a pre-sliding range that passes part of a small correction. That is exactly what decides how much small-signal lag a deadzone costs. | Medium (new plant in numba, about 10 min of DE on 6 cores). | Medium. | A second plant for robustness, not a replacement unless it passes adequacy better. |
| **M6** | **Event-triggered averages on logs and sim:** (i) jump-triggered average and spectrum of the request, error and friction term before breakaway; (ii) lane-offset-peak-triggered correction onset (latency from lane-offset peak to wheel motion), A vs B vs sim; (iii) hold-exit error distribution. | (i) which jitter frequencies actually trigger jumps, to target F5; (ii) a direct, model-free measure of "small corrections start later" on the car, and a check on the model. | Low. | Low. | Observation (one B drive). |
| **M7** | **Position-aligned multi-drive coherence (GPS):** resample the A drives on B's road by distance and compute the cross-drive coherence of the request and lane offset. | The road-forced (coherent across drives) vs self-excited (incoherent) share of the weave band; whether B's increase is in the self-excited part, as a less-damped loop predicts. | Low. | Low (`0x27` has no GPS; `0x28` has). | Observation. |
| M8 | Plant-uncertainty Monte Carlo (f_s, f_c, td, te, b, laf ±) for the finalists, in AVX-512 lanes (`s13_simd2`) after a bit-identity check, or plain processes. | Robust rather than nominal ranking. | Low–medium. | Low. | Model. |
| M9 | Constrained search (grid, then surrogate/Bayesian) over the best family's parameters on the batched simulator. | The best point on a family's frontier, not a hand-picked one. | Medium. | Overfitting to E2/E3; keep E1/E4 secondary and the on-car A/B as the real test. | Model. |
| M10 | Wavelet time–frequency of weave episodes. | Continuous vs burst weave; episode amplitude for M3. | Low. | Low. | Mostly covered by M6/M7. |
| M11 | Policy identification with an instrument (gyro-derived lateral motion, or lane lags ≥ 2 frames) instead of plain ARX. | A better outer-loop policy if M4 fails. | Medium. | Medium (instrument validity). | **Fallback for M4(b).** |
| M12 | MetaDrive via `tools/sim`. | Closed loop with the real model. | High (install, bridge change for torque steering, CPU rendering). | High. | Low: synthetic images, a kinematic car, not the G70. **Not proposed.** |

### 2.4 Ranking (expected information per effort, then risk and validity)

1. **M2 + M1** (frontier on the car-validated metric, plus a clean small-signal estimator). Cheap; immediately tells whether any old candidate already sits off the deadzone frontier.
2. **F1–F4, F7** in the harness, scored by M1/M2 on the pre-registered rule. These are the most direct test of the "persistence, not amplitude" idea (§2.1).
3. **M6** (jump-triggered spectrum → F5; correction-onset latency on the car).
4. **M3** (semi-empirical outer loop) with its pre-registered reproduction of the on-car D2C4 effect. If it passes, it ranks candidates on predicted lane weave, which the proxy can't.
5. **M4 (a)+(b)** feasibility and policy probing. Highest validity for the outer loop, highest risk. A time-boxed feasibility probe first (download, compile, reproduce one segment), then (b); (c) only if (a) and (b) work and time allows.
6. **M5** (pre-sliding plant) as the robustness plant; **M8** for the finalists; **M9** on the winning family.
7. M7, M10: if time allows.
8. Not proposed: F9 (dither), M12 (MetaDrive).

## 3. Proposed pre-registration (for the user's confirmation; nothing below has been computed)

To be finalised as **Amendment 9** in this doc before any candidate result.

- **Candidates:** A0 and D2C4 (references); M2's earlier candidates; F1–F4, F5 (after M6), F6–F8 with small declared parameter sets; combinations of the best only after their single results.
- **Plants:** E4-identified primary; E2+E3 secondary; the pre-sliding plant (M5) as a robustness plant if it passes adequacy.
- **Eras:** E2 and E3 primary (each must pass); E1 and E4 secondary.
- **Decision rule** (E4 plant; E2 and E3 must each pass all of 1–3):
  1. **Twitch:** jumps/min ≥ 40% lower **and** T RMS ≥ 30% lower than A0.
  2. **Weave:**
     - 0.2–0.4 Hz in-context request → a_s added lag ≤ 5° vs A0, and gain within ±10% of A0 (the s12mv M4 estimator, lo band: the car-validated band);
     - simulated W not up vs A0;
     - only if M3 or M4 passes its reproduction: simulated lane-offset 0.2–0.7 Hz not up vs A0;
     - reported only: 0.4–0.7 Hz lag (the model over-predicts there), M1 lock-in lag per amplitude.
  3. **Tracking:** mean |error| (θ0 10 s) not up > 20%.
  4. Transients R1–R5 and C1–C3 reported for every candidate; they rank, they don't fail.
- **Ranking among passes:** smallest 0.2–0.4 Hz lag (mean E2/E3), then fewest red flags, then smallest tracking increase.
- **Tiers if none passes:** "partial" = lag ≤ 9° (half of D2C4's 17°) with criteria 1 and 3 met. The frontier (twitch reduction vs 0.2–0.4 Hz lag vs tracking/transients) is reported either way.
- **Every result reports** wheel jitter (jumps, hold, T, reversals), weave (W, 0.2–0.4 / 0.4–0.7 Hz lag and gain) and comfort (steering proxy: a_s 0.5–4 Hz RMS, jerk, steps).
- **New models first reproduce the on-car D2C4 result** (pre-registered before they are run): 0.2–0.4 Hz lag about +18° (split 8 / 10); request weave up; lane weave up; jitter down; tracking about +27%; curve lag about +0.09 s. Only an adequate model ranks candidates on simulated weave.
- **Harness discipline:** new options live in new files (`s16_ws_*`), copying the loop; with the new options off, the copy must be bit-identical to `s11_eval.simulate` for A0, D2, C4 and D2C4 on ≥ 10 runs from all four eras before any candidate result. The `s13` speed-ups are adopted only if bit-identical.

## 4. Proposed plan (for the user's OK)

1. **Phase A (cheap; about 1–2 h):** the `s16_ws_var` harness with F1–F4/F7 + the bit-identity check; M1 lock-in estimator, checked against the M4 estimator on A0/D2C4; M2 re-score of all earlier candidates; F1–F4/F7 grid; M6 log analyses. Report the frontier.
2. **Phase B (medium):** M3 semi-empirical outer loop with its reproduction check; F5/F6/F8 and combinations of the best; M5 pre-sliding plant; M8 robustness of the finalists; M9 search on the best family.
3. **Phase C (time-boxed probe, in parallel with A/B where possible):** M4(a): fetch `driving_supercombo.onnx` from upstream LFS (covered by the standing tool/model-install authorization; stored on `E:`), compile for CPU in a separate venv on `E:`, reproduce one logged A-drive segment's `desiredCurvature`. Then M4(b) policy probing if (a) passes; M4(c) only after a check-in.
4. Transients (R1–R5, C1–C3) for the finalists; a focused adversarial review of the new analysis code and of s12mv's root-cause scripts (`s15_mv_rc.py`, `s15_mv_2a_followup.py`, `s15_mv_loband.py`).
5. Stop and ask before any change on `dragal/custom`.

**User decision (2026-10-07, ~18:40 EDT): "All approved"** — the plan (phases A → B, C in parallel), the decision rule of §3 including the "partial" tier, and the M4 driving-model probe (download of `driving_supercombo.onnx` from upstream LFS, CPU compile in a separate environment on `E:`).

## 5. Amendment 9: phase A pre-registration (written 2026-10-07 before any candidate result)

### 5.1 Candidates (car-scoped; A0 and D2C4 as references)

All new options change only the **friction term's input x** (V0's `get_friction(x, …)` with the 0.3 m/s² ramp, `fr_mode` 0) unless stated. P, I and the feedforward are unchanged. err = setpoint − measurement as in V0. dz = |A_k|·0.4° (V0's lateral-accel deadzone map, as D2). LP_f is the causal first-order recursion of C4 at 100 Hz (y += α(u − y), α = 0.01/(1/(2πf) + 0.01)). New filter/operator states start at 0 at the warm-up start (10 s before each run) and update only on active cycles.

| ID | Friction input x | Parameters |
|---|---|---|
| F1a / F1b / F1c | **split deadzone:** e_s = LP_f(err); x = e_s + DZ(err − e_s), DZ = opendbc's step deadzone (0 inside ±dz) | f = 0.3 / 0.5 / 1.0 Hz |
| F1b+C4 | F1b + C4 (2 Hz causal request low-pass) | |
| F2a / F2b / F2c | **slow friction input:** x = LP_f(err), no deadzone | f = 0.5 / 1.0 / 2.0 Hz |
| F2b+C4 | F2b + C4 | |
| F3a / F3b | **play operator:** y ← min(max(y, err − h), err + h); x = y; h = \|A_k\|·h° | h° = 0.2 / 0.4 |
| F3b+C4 | F3b + C4 | |
| F4a / F4b | **soft deadzone:** x = s·err inside ±dz; x = err − sign(err)·(1 − s)·dz outside (continuous) | s = 0.25 / 0.5 |
| F7a / F7b | V0 friction input (A0), plus a **breakaway release** on the torque: when the controller's (0.1°-quantized) angle changes after ≥ 10 unchanged cycles, add −sign(Δθ)·R·(1 − j/10) to the normalized torque for j = 0…9 cycles. Active in the simulated part only. | R = 0.026 (= (f_s − f_c)/a of the E4 plant) / 0.013 |

**M2 re-score** (existing harness options, unchanged): C1, C2, C3, C4, C5, C6, D1, D2, D3, J1, H1, P1, MV1–MV9.

F5, F6 and F8 and combinations of the best are pre-registered in phase B, after phase A's results (F5 needs M6).

### 5.2 Harness and checks (before any candidate result)

- New file `s16_ws_var.py`: a copy of `s15_mv_var.closed_loop_fp` with the options above (new arguments, defaults off), `simulate_ws` and `install()` in the s15 pattern.
- **Check 1:** with the new options off, `simulate_ws` is bit-identical (max |Δ| = 0 on angle, output and request) to the original `s11_eval.simulate` for A0, D2, D3, C4 and D2C4 on 12 runs (3 per era, straight-clean and all-engaged H, as `s15_mv_check`), E4 plant; and to `s15_mv_var.simulate_mv` for MV8 and MV9.
- **Check 2 (limit cases):** F1 with f = 0 (α = 0, e_s ≡ 0) equals D2 exactly; F2 with α = 1 equals A0 within 1e-9 in torque; F3 with h° = 0 equals A0 exactly; F4 with s = 1 equals A0 exactly, and with s = 0 equals D3 (shifted deadzone) within 1e-9 in torque; F7 with R = 0 equals A0 exactly.
- **Check 3:** the grid reproduces the stored `a8/grid.json` entries for A0, D2C4 and MV1–MV9 (twitch, proxy and tracking keys) identically.

### 5.3 Metrics and runs

- As Amendment 8 (§4 of the validation findings): E4 plant primary, E2+E3 plant secondary; eras E2/E3 primary, E1/E4 secondary; ≥ 55 mph; straight-clean runs ≥ 12 s for twitch/weave/comfort; all-engaged runs ≥ 12 s for tracking (θ0 10 s primary; 30/60 s for the finalists only).
- **Weave metric (decision):** the s12mv M4 estimator's **lo band (0.2–0.4 Hz)**, added lag and gain ratio vs A0 of the same plant and era. Full and hi bands reported.
- **M1 lock-in (reported only):** probe p(t) = A_m·Σᵢ sin(2πfᵢt + φᵢ), fᵢ = 0.23 / 0.31 / 0.37 Hz, φᵢ = 0 / 2.1 / 4.2 rad, t = route time; A_m = 0.01 / 0.02 / 0.04 m/s². Added to the request as p/v² **before** the candidate's request filter. Each straight-clean H run ≥ 20 s (E2, E3; E4 plant) is simulated with and without the probe; y = a_s(with) − a_s(without), 2 s trimmed each end. Hᵢ = Σ_runs Yᵢ·conj(Uᵢ) / Σ_runs |Uᵢ|² with Yᵢ, Uᵢ the single-frequency DFT sums of y and p. Reported: gain and phase per fᵢ and A_m, and the mean phase over fᵢ; added lag vs A0. **Consistency check (reported):** D2C4's added lag at A_m = 0.02 vs its M4 lo-band added lag on the same era; "consistent" if within ±5°.
- **Decision rule:** §3 (twitch, weave lo band ≤ 5° and gain ±10% and W not up, tracking ≤ +20%; "partial" tier ≤ 9°). Transients R1–R5 / C1–C3 for passes, partials and the frontier's best, in phase B.
- **Workers:** 4 while the background model probe runs (it is capped at 2 threads), otherwise 6.

## 6. Phase A results (model results unless marked; `analysis/g70-weave-twitch-sim-20261007/a9/`, `m6/`)

### 6.1 Harness checks (all before any candidate result)

- **Check 1:** `simulate_ws` vs `s11_eval.simulate` (A0, D2, D3, C4, D2C4) and vs `simulate_mv` (MV8, MV9), 12 runs from 4 eras: **max difference 0, PASS**.
- **Check 2:** all limit cases exact (F2 with α = 1: torque within 3e-17), and every new candidate differs from A0: **PASS** (`logs/s13ws-check-20261007-182048.log`).
- **Check 3:** the grid reproduces all 456 stored Amendment 8 keys (`a8/grid.json`) **identically** (`logs/s13ws-grid-20261007-182155.log`).

### 6.2 Grid and decision rule (E4 plant; change vs A0; E2 / E3; `a9/grid.json`, `a9/summary_E4plant.json`, `logs/s13ws-summary-*`)

| Variant | Jumps | T | W | Lag 0.2–0.4 Hz | Gain 0.2–0.4 Hz | Lag 0.4–0.7 Hz | Tracking | a_s jerk | Verdict: criteria missed |
|---|---|---|---|---|---|---|---|---|---|
| D2C4 (ref.) | −45 / −52% | −33 / −41% | −20 / −25% | +16.5 / +17.6° | −10 / −16% | +28.9 / +26.6° | +21 / +20% | −23 / −28% | tracking, weave |
| **F7a** release R 0.026 | −31 / −34% | −9 / −12% | −5 / −6% | **+2.2 / +2.6°** | −2 / −4% | +4.1 / +3.5° | **+1 / +1%** | −6 / −8% | twitch (T, jumps) |
| F7b release R 0.013 | −17 / −20% | −5 / −6% | −3 / −3% | +1.2 / +1.3° | −1 / −2% | +2.2 / +2.0° | 0 / +1% | −3 / −4% | twitch |
| F3b play 0.4° | −41 / −42% | −25 / −33% | −8 / −9% | +7.7 / +7.9° | 0 / +1% | +20.6 / +17.2° | +13 / +13% | −13 / −18% | twitch (E2 T), weave |
| F3b+C4 | −60 / −65% | −41 / −46% | −17 / −18% | +15.3 / +15.9° | −4 / −5% | +31.8 / +28.4° | +23 / +23% | −25 / −28% | tracking, weave |
| F3a play 0.2° | −10 / −12% | −5 / −9% | +9 / +9% | +1.2 / +0.5° | +5 / +5% | +6.9 / +6.2° | +8 / +8% | +2 / 0% | twitch, weave (W up) |
| F4a soft s 0.25 | −45 / −49% | −23 / −29% | −12 / −14% | +9.5 / +10.8° | −3 / −4% | +17.5 / +15.3° | +13 / +13% | −14 / −18% | twitch (T), weave |
| F4b soft s 0.5 | −36 / −38% | −16 / −20% | −8 / −9% | +5.9 / +6.4° | −3 / −3% | +11.0 / +9.8° | +9 / +8% | −9 / −12% | twitch, weave |
| F1a split 0.3 Hz | −31 / −32% | −13 / −20% | +7 / +6% | +3.5 / +3.9° | +7 / +8% | +13.6 / +12.9° | +11 / +10% | −2 / −6% | twitch, weave (W up) |
| F1b split 0.5 Hz | −19 / −23% | −10 / −13% | +12 / +12% | +1.1 / +1.1° | +6 / +10% | +8.2 / +8.4° | +9 / +10% | +2 / 0% | twitch, weave (W up) |
| F1b+C4 | −46 / −49% | −24 / −27% | +6 / +4% | +7.4 / +7.2° | +6 / +6% | +20.2 / +20.3° | +19 / +18% | −6 / −10% | twitch (T), weave |
| F1c split 1 Hz | −7 / −10% | −1 / −2% | +11 / +12% | −0.3 / −0.4° | +4 / +7% | +2.9 / +2.4° | +5 / +6% | +4 / +4% | twitch, weave (W up) |
| F2a/b/c slow input 0.5/1/2 Hz | −21…+2% | −14…+5% | +8…+14% | −0.9…+0.6° | +3…+11% | 0…+8.4° | +3…+10% | 0…+6% | twitch, weave (W up) |
| F2b+C4 | −36 / −41% | −15 / −19% | +5 / +4% | +5.9 / +5.7° | +4 / +6% | +15.3 / +15.3° | +16 / +16% | −3 / −6% | twitch, weave |
| C1 (ramp 1.0) | −46 / −50% | −25 / −30% | −11 / −13% | +9.8 / +10.5° | −2 / −2% | +16.6 / +14.7° | +15 / +14% | −14 / −17% | twitch (E2 T), weave |
| C5 (KP 0.7 at 30 m/s) | −27 / −29% | −11 / −13% | −4 / −5% | +4.2 / +4.2° | −1 / −1% | +6.5 / +6.7° | +6 / +6% | −5 / −7% | twitch |
| C4 (2 Hz) | −37 / −39% | −19 / −20% | −7 / −7% | +7.2 / +6.9° | −4 / −1% | +12.5 / +11.8° | +10 / +10% | −10 / −10% | twitch, weave |
| D2 (0.4°) | −27 / −31% | −19 / −23% | −17 / −18% | +9.1 / +10.0° | −10 / −11% | +17.4 / +14.7° | +11 / +10% | −14 / −17% | twitch, weave |
| C3, C6, P1, D3 (= MV3), MV2, MV7 | −51…−73% | −31…−55% | −17…−39% | +13.7…+28.6° | −3…−30% | | +17…+32% | | weave (and tracking for C3, C6, P1) |

Not shown (all miss twitch, weave or both; in the summary JSON): C2, D1, H1, J1, MV1, MV4–MV6, MV8, MV9.

**Verdict by the pre-registered rule: no candidate passes, and none reaches the "partial" tier** (twitch and tracking met with lag ≤ 9°). The candidates that meet the twitch criterion on both eras (D2C4, D3/MV3, MV2, MV7, F3b+C4, C3, C6, P1) all add 13.7–28.6° at 0.2–0.4 Hz.

- **E2+E3 plant (secondary):** the same picture. F7a: jumps −39 / −37%, T −10 / −13%, lag +3.2 / +2.9°. The F1/F2 families lose their jump reduction on this plant (F1b −1 / −5%, F2b +17 / +12%). F3b is weaker (jumps −31 / −34%).
- **Secondary eras E1/E4 (E4 plant):** F7a jumps −14 / −27%, lag +0.8 / +1.1°; F3b jumps −50 / −45%, lag +2.0 / +5.4°.

**Reading:**
- **The frontier.** Among the friction-input and filter variants, jump reduction costs 0.2–0.4 Hz lag at a roughly fixed rate: about 0.2–0.4° per % of jump reduction.
- **Two mechanisms beat that rate:**
  - **F3b (play operator):** −41% jumps for 7.8° (0.19°/%);
  - **F7a (breakaway release):** −33% jumps for 2.4° (0.07°/%), with no tracking cost (+1%) and W down.
- F7a is the first candidate in this project that reduces jumps substantially without slowing small corrections (also §6.3–6.4). Its weakness: T (the 0.7–4 Hz angle RMS, i.e. jump size) falls only 9–13%.
- **F1/F2 (slow-error friction compensation) keep the small-signal response but raise W by 4–14%.** Restoring the friction push for slow errors makes the wheel move more in the weave band. On the E2+E3 plant they lose their jump reduction.

### 6.3 M1 lock-in (reported only; `a9/lockin.json`, `logs/s13ws-lockin-20261007-182408.log`)

Added lag vs A0 (mean over 0.23 / 0.31 / 0.37 Hz) and gain change, E2 / E3, E4 plant:

| Variant | A_m 0.01 m/s² | 0.02 | 0.04 |
|---|---|---|---|
| D2C4 | +22.3° −35% / +36.0° −37% | +23.7° −32% / +27.7° −22% | +22.0° −11% / +22.0° −13% |
| F7a | +5.1° −8% / +7.4° −2% | **+3.5° −8% / +4.7° −4%** | +2.6° −3% / +2.7° −4% |
| F3b | +18.6° −13% / +21.4° −12% | +16.0° −8% / +17.1° −7% | +11.5° +5% / +11.2° +3% |
| F4b | +6.0° −9% / +13.0° −10% | +6.7° −8% / +9.6° −7% | +6.0° −1% / +6.8° −4% |
| C5 | +4.6° −6% / +9.8° −7% | +4.7° −7% / +7.4° −4% | +4.1° −1% / +4.7° −2% |
| F1b | −0.2° +9% / +5.6° +9% | +3.2° +6% / +3.9° +9% | +0.8° +10% / +3.1° +8% |

A0 absolute (E2): gain 0.99 / 1.03 / 1.05, phase −35.3 / −33.3 / −30.2°.

- **Consistency check (pre-registered): not consistent.** At A_m = 0.02, D2C4's lock-in lag (+23.7 / +27.7°) exceeds its M4 lo-band lag (+16.5 / +17.6°) by 7–10° (bound ±5°). The car validated the M4 estimator (+18°), so the lock-in stays a secondary readout.
- **What it adds:** the lag of a deadzone or play operator grows as the correction gets smaller. F3b's in-context +7.8° becomes +16–21° for a 0.01–0.02 m/s² probe, as the play-operator argument predicted (§2.2). F7a stays small at every amplitude (+2.6…+7.4°).

### 6.4 M6 event-triggered analyses (exploratory; observation for logs, model result for sim; `m6/m6.json`, `logs/s13ws-m6-*`)

**(i) What triggers a jump.** Mean of each request band in the 1 s before a jump, aligned with the jump's direction **in steering-angle units**, in units of that band's RMS (0 = no relation). *Sign correction (focused review, §9):* A < 0, so in request (a_s) units every value below has the opposite sign; see the follow-up after the table.

| Source | Jumps | 0.2–0.7 Hz | 0.7–1.5 Hz | 1.5–3 Hz | 3–6 Hz |
|---|---|---|---|---|---|
| E2 log | 302 | +0.71 | +0.15 | +0.04 | +0.01 |
| E2 sim A0 | 322 | +0.72 | +0.15 | +0.06 | 0.00 |
| E3 log | 341 | +0.71 | +0.15 | +0.05 | 0.00 |
| E3 sim A0 | 311 | +0.81 | +0.16 | +0.07 | 0.00 |
| E4 log | 658 | +0.57 | +0.17 | +0.04 | +0.01 |

- **Follow-up in request units** (after the review; `s16_ws_m6sign.py`, `logs/s13ws-m6sign-*`; observation, E2 / E3 / E4 logs):
  - the jump moves the wheel **toward** the request in 97 / 99 / 99% of jumps (mean error before the jump +0.11 m/s² in the jump's direction);
  - the request changed **toward** the jump over the second before it (+0.064 / +0.058 / +0.039 m/s²; the 0.2–0.7 Hz band +0.055 / +0.050 / +0.033);
  - the slow band's level in that second is on the **opposite** side (−0.71 / −0.71 / −0.57 of its RMS).
  - So jumps happen as the slow request **turns back** from a swing: the wheel holds through the reversal, the error builds as the request moves away, then the wheel jumps to catch up.
- **The jumps are the wheel following the slow, weave-band request through stick-slip, not a response to the fast jitter** (observation, every era; the model reproduces the band pattern).
- So D2/C4-type fixes cut jumps mainly by following those slow small corrections later, which is exactly the weave-band lag (§6.2). This explains the frontier.
- A filter aimed at the fast jitter (F5) is **not supported**: the 1.5–6 Hz bands show almost no relation to the jumps. Limitation: an aligned mean can't see triggers that act through timing rather than direction (jitter tipping an already-loaded wheel over the edge).
- This revises part of the session 10 story ("small fast jitter keeps re-triggering it"): the excitation that matters is mostly the slow request's reversals; the fast jitter is secondary (*hypothesis*, consistent with A5's 1 Hz zero-phase smoothing also removing part of the 0.7–1.5 Hz content).

**(ii) Reversal latency** (the request's 0.2–0.7 Hz band turns → the wheel moves one 0.1° quantum in the new direction; median in s / fraction censored at 2 s):

| Source | Small (0.01–0.03 m/s²) | Mid (0.03–0.06) | Large (≥ 0.06) |
|---|---|---|---|
| **Car A-primary (A0), log** | 0.92 / 20% | 0.90 / 10% | 0.71 / 0% |
| sim A0 on the same requests | 0.86 / 20% | 0.78 / 7% | 0.62 / 0% |
| sim D2C4 | 2.0 / 59% | 1.78 / 47% | 0.94 / 6% |
| sim F7a | 0.93 / 22% | 0.83 / 8% | 0.65 / 0% |
| sim F3b | 1.62 / 47% | 1.16 / 31% | 0.80 / 1% |
| sim F4a / C1 / D2 / C4 | 1.41 / 1.27 / 1.41 / 1.14 | 1.07 / 1.07 / 1.08 / 0.96 | 0.76–0.81 |
| **Car B `0x28` (D2C4), log** | 1.56 / 35% | 1.36 / 35% | 0.93 / 2% |
| sim D2C4 on B's requests | 1.95 / 46% | 1.51 / 42% | 0.99 / 5% |
| sim A0 on B's requests | 0.88 / 21% | 0.83 / 11% | 0.70 / 1% |
| sim F7a on B's requests | 1.11 / 23% | 0.93 / 12% | 0.72 / 1% |

- **A model-free view of the weave mechanism on the car:** with D2C4 the wheel takes 0.4–0.6 s longer to start a small or mid correction (B 1.56 / 1.36 s vs A 0.92 / 0.90 s), and a third of small/mid reversals don't move the wheel within 2 s. Large corrections are barely affected (+0.2 s). One B drive; different days.
- **Model check:** the model's A0 matches the car's A drives within 0.06–0.12 s. With D2C4 on B's own requests it over-predicts the latency (1.95 vs 1.56 s small; 1.51 vs 1.36 s mid; 0.99 vs 0.93 s large), in the same direction as its hold over-prediction (s12mv §3.2).
- **F7a keeps the reversal latency within about 0.1 s of A0** on the A-primary requests (0.25 s on B's small bin); every deadzone/filter variant lengthens it.

## 7. Amendment 10: phase B pre-registration (written 2026-10-07 after phase A, before any phase B result)

**Why these candidates:**
- §6.4 shows that jumps are pushed by the slow request. So any fix that ignores small errors slows exactly the corrections lane-keeping needs.
- F7 (breakaway release) is the only mechanism that cut jumps without that cost (§6.2–6.4). It acts on what happens **after** a breakaway (the overshoot from torque built up while the wheel was stuck), not on whether the wheel follows a small request.
- Phase B therefore (a) explores the F7 family, and (b) combines F7 with the cheapest-lag partial fixes, to reach the T criterion with as little lag as possible.

**Dropped (with reasons, before running):**
- F5: a fast-jitter filter has no target, because the 1.5–6 Hz bands carry no directional push (§6.4).
- F9 (dither): not proposed (§2.2).
- M3 (semi-empirical outer loop): its policy transfer would come from feedback-biased closed-loop estimates (s12mv §1). It is deferred until the M4 probe shows whether the real policy can be probed open-loop. It would be pre-registered then.

### 7.1 Candidates

| ID | Change | Parameters |
|---|---|---|
| F7c / F7d | release as F7a, larger | R = 0.039 / 0.052 (1.5× / 2× F7a), 10-cycle linear decay |
| F7e | release as F7a, longer | R = 0.026, 20-cycle linear decay |
| F7f / F7g | **adaptive release:** R = κ·max(0, s·(τ_onset − τ_hold)), where τ_hold is the controller torque (before any release) on the cycle the hold began (the last angle change), τ_onset the torque on the onset cycle, s the motion direction; 10-cycle decay | κ = 0.5 / 1.0 |
| F7a+X | F7a combined with X ∈ {F4b, C5, C4, F3b, C1, D2} | X as in phase A |
| F7*+X | the best F7 variant combined with the same six X. **F7\* rule:** among F7a–F7g, the largest mean E2/E3 jump reduction with 0.2–0.4 Hz lag ≤ 5° and tracking ≤ +20% on both eras (E4 plant). If F7\* = F7a, this row is skipped. | |
| F6 | D2C4 + a causal lead-lag on the request before C4, (1 + s/ω_z)/(1 + s/ω_p), bilinear at 100 Hz, DC gain 1. Documents the Bode cost of cancelling C4's lag with a linear filter. | f_z = 0.6 Hz, f_p = 1.2 Hz |
| F8a / F8b | v0k-type feedforward scale at 55+ mph: latAccelFactor × 1.29 (session 6's K for the H band) / the same + F7a | laf_scale 1.29 |

The F7 family stays car-scoped controller logic acting only on the commanded torque before the existing output stage. It changes no torque, rate or driver-override limit, and no safety check.

### 7.2 Harness and checks (before any phase B result)

- `s16_ws_var.py` gains `rel_n` (decay cycles, default 10) and `rel_k` (κ, default 0) at the end of the loop's signature, and `req_lead` [f_z, f_p] in `simulate_ws`.
- **Check 1 and Check 2** (§5.2) are re-run on the edited file and must pass unchanged.
- **Check 4:** the edited harness reproduces `a9/grid.json` identically for every phase A key.
- **Check 5 (limit cases):**
  - F7 with rel_n = 10 and κ = 0 equals F7a exactly;
  - κ > 0 with R = 0 differs from A0 (active);
  - `req_lead` with f_z = f_p equals the unfiltered request within 1e-12.

### 7.3 Metrics and decision

- As Amendment 9 (§5.3) and the §3 rule: E4 plant primary, E2 and E3 each must pass; the E2+E3 plant and E1/E4 secondary. Twitch: jumps ≤ −40% and T ≤ −30%. Weave: 0.2–0.4 Hz lag ≤ 5°, gain ±10%, W not up. Tracking ≤ +20%. "Partial": lag ≤ 9° with twitch and tracking met.
- The M1 lock-in at A_m = 0.02 and the M6 reversal latency are reported for passes, partials and the frontier's best (secondary readouts).
- **Transients** (Amendment 7 R1–R5, C1–C3, via the s15 runners pointed at `simulate_ws`) for passes, partials and the frontier's best, in phase B2, after this grid.

### 7.4 Amendment 10b: robustness of the F7 family (written 2026-10-07 after the phase B grids, before this run)

- **Why:** F7 acts on the breakaway dynamics (static vs kinetic friction, transport delay, EPS lag), the parts of the plant that are least certain.
- **Plants:** the 10 E4-plant perturbations of `s11_robust.py` (nominal; f_s ×0.7 / ×1.3; f_c ×0.7 / ×1.3; td ×0.5 / ×1.5; b ×0.8 / ×1.2; te ×2).
- **Eras:** E2 and E3. **Variants:** A0, D2C4 (reference), F7a, F7d.
- **Metrics:** the grid's (s16_ws_grid.grid_file, unchanged): jumps, T, W, 0.2–0.4 Hz lag and gain, tracking (θ0 10 s), each vs A0 on the same perturbed plant.
- **Pre-registered reading:** F7d is "robust on its strengths" if, in all 10 plants × 2 eras, jumps ≤ −30%, 0.2–0.4 Hz lag ≤ 5° and tracking ≤ +10%. Otherwise the failing plants are named.

**Result (model; `a10t/robust.json`, `logs/s13ws-robust-20261007-183711.log`): not robust by the pre-registered reading.**
- F7d keeps 0.2–0.4 Hz lag ≤ 5° and tracking ≤ +3.2% in 18 of 20 cells. The exceptions are td ×0.5: lag +5.4 / +5.8°, with jumps −48 / −56%.
- **Its jump reduction collapses when the transport delay is longer:** td ×1.5 gives jumps −9 / −13% (F7a −12 / −14%). Every other perturbation keeps F7d at −35…−44%.
- D2C4 is insensitive to every perturbation (jumps −42…−55%, lag +14.8…+20.3°).
- **Reading:** F7 releases torque after it detects motion, so it helps only if the release reaches the wheel before the jump is over. Whether it works on the car therefore depends on how the car's jump duration compares with the command → steering delay. That is testable on the logs (§7.5).

### 7.5 Amendment 10c: jump-profile check (written 2026-10-07 before this run)

- **Question:** do the model's jumps evolve on the car's time scale? F7's benefit is only credible if they do.
- **Jumps:** onsets as `jumps_hold` (≥ 0.3° within 15 samples, re-armed after 30). Straight-clean H runs ≥ 12 s, 2 s trimmed.
- **Profile of each jump** (angle at 100 Hz, sign-aligned):
  - t_first = the first 0.1° change after the onset sample;
  - t90 = the time from t_first to the first sample at ≥ 90% of the maximum excursion within 300 ms after t_first;
  - overshoot = (maximum excursion − excursion 300 ms after t_first) / maximum excursion.
- **Sources:** logs of E2, E3, E4; sim A0 with the E4 plant and with the E2+E3 plant on the same runs; and the E4 plant with td ×1.5 and td ×0.5.
- **Reading:**
  - "the model's jump timing matches the car" if the median t90 of sim A0 (E4 plant) is within ±30% of the logs' median in each era;
  - the td-perturbed plants show which delay is closer to the car's timing.

**Result (`a10t/jprof.json`, `logs/s13ws-jprof-20261007-183856.log`):**

| Era | Log: jumps / median t90 (p25–p75) | sim A0, E4 plant | E2+E3 plant | E4 td ×1.5 | E4 td ×0.5 |
|---|---|---|---|---|---|
| E2 | 300 / 150 ms (120–240) | 321 / 180 ms | 309 / 180 ms | 427 / 190 ms | 197 / 190 ms |
| E3 | 340 / 170 ms (130–250) | 308 / 170 ms | 286 / 160 ms | 414 / 190 ms | 192 / 180 ms |
| E4 | 653 / 160 ms (120–230) | 647 / 170 ms | 586 / 160 ms | 798 / 190 ms | 448 / 175 ms |

- **The model's jump timing matches the car** in every era (t90 +20% / 0% / +6%; criterion ±30%).
  - Jumps take about 150–180 ms to reach 90% of their excursion. That is longer than the nominal command → motion delay (td + te = 79 ms on the E4 plant, 53 ms on E2+E3), which is why a release triggered by the first 0.1° change can still shorten them.
  - The median excursion is 0.4° (4 sensor quanta) everywhere, and the 0.1° quantization makes the overshoot measure uninformative (median 0).
- **t90 does not discriminate the delay variants (all 175–190 ms), but the jump rate does:**
  - the nominal E4 plant reproduces the logged rate within −9…+7%;
  - td ×1.5 over-predicts it by +22…+42%;
  - td ×0.5 under-predicts it by −31…−44%.
  - So the logs favour a delay near nominal, where F7 works. They don't exclude a longer delay, because the plant's delay was fitted together with other parameters (td and te trade off: 68 + 11 ms on E4, 31 + 22 ms on E2+E3).
- **Hypothesis to carry forward:** F7's on-car benefit depends on the actual command → steering delay. If it were about 1.5× the fitted value, F7 would do little. An on-car test (or a direct delay measurement from logged command steps vs angle) would settle it.

### 7.6 Exploratory: command → EPS torque delay on the logs (`s16_ws_delay.py`, `logs/s13ws-delay-*`; not pre-registered)

- **Method:** FIR least squares of Δ`steeringTorqueEps` (the EPS's reported motor torque, latest carState at each controls tick) on Δ(logged output command), lags 0–300 ms. Straight-clean H runs, per era.
- **Result (observation):**

  | Era | FIR peak | Step response t10 / t50 / t90 |
  |---|---|---|
  | E1 | 30 ms | 14 / 23 / 64 ms |
  | E2 | 30 ms | 14 / 24 / 57 ms |
  | E3 | 30 ms | 13 / 24 / 63 ms |
  | E4 | 30 ms | 13 / 23 / 67 ms |

- **Reading:**
  - The EPS motor torque responds to the command with a t50 of about 23 ms in every era.
  - The plants' fitted command → torque delay (td + te: 79 ms E4, 53 ms E2+E3) is longer. It lumps the mechanical path and the angle measurement into one delay.
  - The td ×1.5 case where F7 fails (about 113 ms) is therefore unlikely to describe the actuator (*hypothesis*).
  - **Limits:** the reported EPS torque may be an internal estimate with its own latency; controls-tick sampling adds up to 10 ms; the angle sensor's latency, which F7's detection depends on, is not separated.

### 7.7 Amendment 10d: M9 constrained search around F7 (written 2026-10-07 before this run)

- **Family** (all combinations; 288 points):
  - release R ∈ {0.026, 0.039, 0.052, 0.065};
  - decay rel_n ∈ {10, 20} cycles;
  - feedforward scale laf_scale ∈ {1.0, 1.1, 1.2, 1.29} (55+ mph);
  - KP at ≥ 30 m/s ∈ {1.0, 0.85, 0.7};
  - friction input: V0, or soft deadzone (0.4°) with s ∈ {0.75, 0.5}.
- **Selection set:** E2 and E3, E4 plant (the grid's metrics, unchanged).
- **Selections** (by mean E2/E3 T change, most negative first):
  - **S1:** best T among points with 0.2–0.4 Hz lag ≤ 5°, gain within ±10%, W not up, tracking ≤ +20% and jumps ≤ −40%, each on both eras;
  - **S2:** the same, with lag ≤ 9° ("partial" tier).
- **Validation of S1/S2:** E1/E4 (E4 plant) and all eras on the E2+E3 plant, reported against the §3 rule.
  - A selected point that meets the §3 rule on E2/E3 is labelled **"pass (search-selected)"**: the selection used the same eras, so its pass is optimistic. It needs the secondary eras/plant and transients before it can be a candidate.

**Result (model; `a10d/search.json`, `a10d/validation.json`, `logs/s13ws-search-20261007-184228.log`; a first run crashed on a JSON type error before any output and was re-run unchanged):**
- **No point meets the §3 rule.** T ≤ −30% is never reached with lag ≤ 9° under the other constraints.
- **S1 (lag ≤ 5°): one feasible point, `R 0.026, n 10, laf ×1.1, KP 1.0, no deadzone`** (= F7a + a 10% feedforward scale):
  - jumps −41 / −44%, T −16 / −20%, W −11 / −13%, lag +4.1 / +4.2°, gain −6 / −8%, tracking −0.3 / −0.6%;
  - secondary: E1/E4 jumps −23 / −38%, lag +1.2 / +2.6°; E2+E3 plant jumps −30…−48%, lag +2.2…+5.8°.
- **S2 (lag ≤ 9°): `R 0.026, n 10, laf ×1.1, KP 1.0, soft deadzone s 0.75`:**
  - jumps −49 / −58%, T −23 / −28%, W −16 / −18%, lag +7.5 / +8.0°, gain −8 / −10%, tracking +4%;
  - secondary similar; gain −11.7% on E3 with the E2+E3 plant.
- **Pareto frontier** (mean E2/E3 lag → mean T change, under the jumps/gain/W/tracking constraints):

  | Lag | T |
  |---|---|
  | 4.1° | −17.8% |
  | 5.3° | −20.8% |
  | 6.1° | −22.6% |
  | 7.8° | −25.5% |
  | 9.1° | −28.2% |
  | 10.6° | −30.4% |
  | 11.9° | −32.5% |

  For comparison, D2C4 is at 17.1° / −37% with tracking +21%. **The F7-based frontier dominates D2C4** in this model: for the same T reduction it costs about 6° less lag and a quarter of the tracking cost. But the T criterion still needs about 10.5° of lag.
- The unconstrained best T (−55…−59%) comes with 24–30° of lag and −33…−39% gain: the trade-off holds at every scale.

## 8. Phase C: the driving model in the loop

### 8.1 M4(a) feasibility and reproduction: PASS (delegated probe, verified by the coordinator)

- **Model (source facts):**
  - `driving_supercombo.onnx` was fetched from GitHub LFS (`sunnypilot/sunnypilot`) to `E:\DragalPilot\cache\s13ws_model\`. Coordinator check: sha256 `659727c4…8f009b` matches the `a5f4465` pointer.
  - Its `model_checkpoint` string appears verbatim in the shipped `driving_tinygrad.pkl.chunk01of04`, so it is the installed model.
  - The rlog's managerState shows stock `modeld` running. The `ModelManager_ActiveBundle` param is absent and `CameraOffset` is 0.
- **Toolchain:**
  - the checkout's tinygrad 0.14.0, imported read-only, with `DEV=CPU:LLVM` (system libLLVM 20.1.2);
  - the JIT is built with `compile_modeld.py`'s own functions, so the NV12 warp runs inside it as on the device;
  - ffmpeg 6.1.1 for HEVC decoding;
  - installed: apt `clang` 18 and its LLVM 18 dependencies (`logs/s13ws-model-apt.log`).
- **Speed:** about 247 ms per frame on one core (tinygrad's CPU backend is single-threaded), so about 4 fps per process. Peak RSS about 450 MB.
- **Reproduction** (pre-registered criteria; route `0x20` segments 6–7, 110 s after a 10 s warm-up, frame-matched, 70–76 mph):

  | Criterion | Bound | Result |
  |---|---|---|
  | Pearson r of desiredCurvature | ≥ 0.95 | **0.99969** |
  | 0.2–0.7 Hz coherence (mean / min) | ≥ 0.8 | 0.989 / 0.985 |
  | 0.2–0.7 Hz gain | 0.8–1.25 | 1.006 (0.978–1.031) |
  | lane-centre offset r | ≥ 0.95 | 0.99934 |

  - The curvature difference RMS is 2.8% of the signal. 0.7–4 Hz coherence is 0.78.
  - Segment 5 (with a lane change, desire replicated) also passes: r 0.9986.
  - The residual is attributed (*hypothesis*) to HEVC compression, the device's float16 build, and vEgo timing.
  - Curvature is computed from the plan with `get_curvature_from_plan` (this ONNX has no action head), as modeld does.
- **Coordinator verification** (`s16_ws_probe_verify.py`, `logs/s13ws-pverify-*`):
  - the probe's "logged" column is an exact contiguous run of session 10's independently extracted `modelV2` desiredCurvature;
  - recomputed r = 0.99969, RMS difference 1.59e-5 vs 5.62e-4 1/m.
- **Camera-offset smoke test:** a +0.2 m `camera_offset_helper` shear on segment 7 shifts the model's lane-centre offset by −0.203 m and its desiredCurvature by −9.8e-5 1/m (−0.12 m/s² at 34.3 m/s, steady over 20 s).
  - In the logs' own convention (s12mv §1: lane offset → request coupling is positive), a negative lane-offset change with a negative request change is a **corrective** response (inference from the empirical sign, not from source conventions).
- **Checkouts unchanged** (outer repo, `sunnypilot/`, WSL clone; checked by the coordinator). No device access.
- **Meaning:** the real lane-keeping policy can be run offline on logged video with a simulated lateral offset. M4(b) (open-loop policy probing) is feasible.
- **Limits:** one route, highway speed, 2.7 min; the shear is exact for road-plane pixels only.

### 8.2 Amendment 11: M4(b) open-loop policy probing (written 2026-10-07 before any probe result)

- **Question:** what is the real policy's response (curvature request) to the car's lateral position and heading in the weave band, free of the feedback bias that defeated the ARX (s12mv §3.3)?
- **Drives and windows:**
  - A-primary drives on B's road that have video: `0x1e`, `0x20`, `0x22`, `0x24`.
  - Windows: engaged, v ≥ 24.6 m/s, no blinker or steering press, straight (|logged curvature| < 2.5e-4 1/m and both lane probabilities > 0.5), contiguous ≥ 70 s (10 s warm-up + ≥ 60 s analysed).
  - Taken in route order until ≥ 6 min analysed in total and ≥ 1 window per drive where one exists.
- **Probes** (applied to both camera warps; time t = frame time from the window start):
  - **lateral offset** Δy(t) = 0.04 m · Σᵢ sin(2πfᵢt + φᵢ), fᵢ = 0.11 / 0.23 / 0.37 / 0.53 / 0.71 Hz, φᵢ = 0 / 1.3 / 2.6 / 3.9 / 5.2 rad, through the `camera_offset_helper` ground-plane shear (sign as that helper);
  - **heading** Δψ(t) = 0.13° · Σⱼ sin(2πgⱼt + θⱼ), gⱼ = 0.17 / 0.29 / 0.43 / 0.61 Hz, θⱼ = 0.7 / 2.0 / 3.3 / 4.6 rad, as a yaw added to the calibration (device_from_calib) used by the warp. Its sign convention is determined and reported.
  - Both act together; the frequency sets are disjoint.
- **Runs per window:** base (no probe) and probe on identical frames and inputs.
- **Responses:**
  - Δa = (κ_probe − κ_base)·v² (m/s²), the request change;
  - Δc, the change of the model's own lane-centre offset (perception).
- **Estimator:** the model is deterministic, so differences contain only the probe response. Single-frequency DFT sums over each window's analysed part, pooled over windows: H = Σ Y·conj(U) / Σ |U|². Gain and phase per frequency.
- **Outputs:**
  - P_y(f) = Δa/Δy (m/s² per m) and P_ψ(g) = Δa/Δψ (m/s² per rad);
  - the perception transfers Δc/Δy and Δc/Δψ;
  - the per-window spread (min/max gain, phase).
- **Linearity check:** one window repeated at half amplitude. "Linear enough" if every frequency's gain is within ±10% and phase within ±10° of the full-amplitude result. Otherwise both are reported and the outer-loop use (§8.3) waits.
- **Reported comparisons (no verdict):** P_y in the 0.2–0.4 / 0.4–0.7 Hz bands vs s12mv §1's closed-loop H1 estimate (lane → request gain 1.00 / 1.56, phase +50° / +45°, in a_s units per m of lane offset; signs reconciled through Δc/Δy).
- **Next (pre-registered separately before it runs):** an outer-loop twin from P_y, P_ψ, the dynamic bicycle model and the nonlinear inner-loop sim. It must reproduce the on-car D2C4 effect before ranking candidates (§3).

### 8.3 Amendment 12: outer-loop twin (written 2026-10-07 before any M4(b) result and before any twin result)

**Structure** (`s16_ws_twin.py`; deviation form as s12mv §2.3):
- **Inner loop:** the nonlinear stick-slip simulator unchanged (`closed_loop_ws` copied line by line), any candidate.
- **Vehicle:** opendbc's dynamic bicycle model, driven by the deviation of the simulated from the logged steering angle. Parameters:
  - road-wheel δ = (θ_sim − θ_log)·π/180 / sR, both 0.1°-quantized;
  - cF, cR = sf × tyre stiffness (sf, sR per sample from liveParameters);
  - m, j, aF, aR from the route's carParams (GENESIS_G70_2024: 1905 kg, 3579 kg·m², 1.132 / 1.698 m, 250,373 / 263,859 N/rad);
  - Euler integration at 1 ms.
  - The output is the car's lateral and heading deviation from its logged path, at the camera: Δy_R = −(y + l_cam·ψ), Δψ_R = −ψ (modelV2 frame, y right).
- **Policy:** Δa = H_y[Δy_R] + H_ψ[Δψ_R], delayed by L. Evaluated every 5th cycle (model rate) and held, then added to the request. The request change also passes the candidate's own causal request filter (C4), since the filter is linear.
- **Lane offset in the twin:** c_sim = c_log − Δy_R at the model times.
- **Fitting H_y and H_ψ (from the pooled M4(b) points):**
  - form (k₀ + k₁s)/(1 + Ts)·e^(−sτ), least squares on the complex points, each normalised by |P|;
  - fit adequacy: every probe frequency within ±15% gain and ±15° phase;
  - if not met: (k₀ + k₁s + k₂s²)/(1 + T₁s + T₂s²)·e^(−sτ); if still not met, the twin is not built.
  - Discretised by the bilinear transform at 100 Hz.
- **Delay:** L = τ + 0.067 s (frame end-of-exposure → modelV2 publish, median 52 ms on `0x20`, `s16_ws_lat.py`; plus 1.5 controls cycles to reach controlsd, s12mv §1), rounded to 10 ms.
- **Camera position:** l_cam = 0 (primary); 1.0 m (sensitivity).
- **M4(b) must pass its linearity check** before the twin is used.

**Checks (done, before any twin result; `logs/s13ws-twincheck-*`):**
- T1: with the policy off, the twin equals `simulate_ws` bit-exactly for A0, D2C4, F7d, F3b and MV9 on 8 runs from 4 eras. **PASS** (max difference 0).
- T2: the bicycle model's steady-state lateral acceleration equals V0's own measurement map |A|·Δθ at 25 / 30 / 33.5 m/s (0.00%), and the Euler integration converges to it. **PASS**.

**Runs:**
- The A-primary drives on B's road (`0x26`, `0x1e`, `0x20`, `0x22`, `0x24`, road masks as s12mv), E4 plant (primary), E2+E3 plant (secondary).
- Straight-clean H runs ≥ 12 s for twitch, W and weave; all-engaged H runs ≥ 12 s for tracking.
- The lane offset on 20 Hz model times with both lanes ok, as s12mv §2.1 M3.

**V1, adequacy of A0 in the twin** (sim vs logged, A-primary):
- hold within ±0.10; jumps ±35%; T ±35%; W ±40%;
- lane-offset 0.2–0.7 Hz RMS ±40%; request 0.2–0.7 Hz RMS ±40%;
- no divergence: |Δy_R| p99 < 0.5 m.

**V2, reproduction of the on-car D2C4 effect** (D2C4 vs A0, both in the twin, same runs). All of these must lie within the on-car 95% CIs (s12mv §2.3 V2 and §3.1):
- jumps −55.8…−25.2%;
- T −48.0…−27.7%;
- W > 0 and within −9.6…+44.8%;
- lane-offset 0.2–0.7 Hz +20.5…+65.4%;
- request 0.2–0.7 Hz +13…+51%;
- tracking +16.2…+39.2%.

Reported, not a criterion: the 0.2–0.4 Hz request → a_s added lag (car +18°) and its gain.
- **Deviation from s12mv V2:** curve entry/exit lag is dropped. It is a transient measure already covered by the curve runner, and the twin has no curve-event runner.

**If V1 and V2 pass (E4 plant):** the twin ranks A0, D2C4, F7a, F7d, S1, S2, F7a+F3b, MV3, D2, C4, F3b and F8b.
- The §3 rule gains its pre-registered outer-loop criterion: **simulated lane-offset 0.2–0.7 Hz not up vs A0**.
- Request 0.2–0.7 Hz is reported.

**If not:** the twin is reported as not adequate, with the criteria it misses. No candidate is ranked on it.

**Twin eval smoke test (policy off; `twin/eval_off.json`, `logs/s13ws-twin-off-*`; before any policy result):**
- The first version of `s16_ws_twin_eval.py` computed tracking and the request metrics against the C4-filtered request. The project's tracking definition (`s11_eval._track_file`) uses the **raw** request. The bug showed as D2C4 tracking +1% instead of the stored +18%.
- **Fixed:** the twin now outputs the policy's raw request change, and tracking, request weave and the request → a_s transfer use the raw request (logged + Δa). Check T1 was re-run: PASS.
- With the policy off, the eval now reproduces s12mv §3.2's stored A-primary values for sim A0 and D2C4: jumps 32.8 / 15.3, hold 0.580 / 0.772, tracking 0.0460 / 0.0542, 0.2–0.4 Hz phase −27.8 / −45.1°.
- Open-loop the lateral deviation drifts (|Δy| p99 about 12–25 m), as expected without a policy. The band-passed lane metric is barely affected.
- **Clarification before any policy result:** the twin uses one delay line for both policy blocks, so τ is fitted **jointly** for H_y and H_ψ (one shared τ; `s16_ws_polfit.py`). The rest of the fit is as pre-registered.

## 9. Focused review (one independent adversarial agent; 2026-10-07)

**Scope:**
- this session's `s16_ws_*` analysis code and runner;
- session 12mv's still-unreviewed root-cause scripts (`s15_mv_rc.py`, `s15_mv_2a_followup.py`, `s15_mv_loband.py`).

**Conditions:**
- The reviewer worked against the extracted pre-registrations only (`E:\DragalPilot\scratch\review-s13ws\requirements.md`; no results).
- It was read-only, used ≤ 2 processes, and was barred from the repo docs, logs and results. Its scripts and logs are in `E:\DragalPilot\scratch\review-s13ws\`.
- The outer-loop twin code (`s16_ws_twin*.py`, `s16_ws_polfit.py`) was written after the review started and is **not** covered.

**Result: no blocker or major.** Every finding was verified by the coordinator.

| # | Severity | Finding | Coordinator verification | Disposition |
|---|---|---|---|---|
| 1 | minor | F7f/F7g (adaptive release): the hold torque started at 0, so the first release of every run used the absolute torque. | Confirmed in the code. | **Fixed** in `s16_ws_var.py` and `s16_ws_twin.py`. Re-run (`logs/s13ws-fix-*`): checks 1, 2, 5 and T1/T2 PASS; stage-1 grid keys identical except F7f/F7g (43 keys). F7f jumps −31 / −31% (was −32 / −32%), F7g −38 / −39% (was −38 / −39%), lag within 0.4°. F7\* stays F7d. No verdict changes. |
| 2 | minor (definition) | "≥ 10 unchanged cycles" is coded as 10 unchanged comparisons (11 equal samples). The 10-sample reading gives slightly more releases. | The reviewer's unpatched rows reproduce the grid exactly. With 10 samples: F7d E2 jumps −41.0% (was −39.7%), F7a −32.4%; T within 0.4 points. | **Recorded as a sensitivity.** The coded reading stays. F7d's §3 verdict is unchanged (T fails). |
| 3 | minor | s12mv T3 counted holds cut off by the selection edge. | The reviewer's "all" rows equal the stored T3 values exactly (B 18.57, A 14.47, `0x20` 18.91 holds/min). Without the censored holds: mean duration B 1.95 vs A 1.60 s, \|e\| at hold end 0.063 vs 0.055. | **Recorded.** Same directions; the s12mv §8 reading is unchanged. |
| 4 | note | M6's trigger sign used the angle-jump direction, but A < 0. | Confirmed. | **Re-analysed in request units** (§6.4 follow-up): jumps follow the slow request's reversals, toward the request. §6.4 wording corrected; the conclusion is unchanged and sharper. |
| 5 | note | The lock-in tones are close in frequency, so each picks up some of the others. | Reviewer's synthetic test: ≤ 0.5° on the mean phase, mostly common to A0 and the candidate. | Recorded. The lock-in is a secondary readout. |
| 6 | note | The jump-profile window drops 0.3–1% of jumps. | Median t90 unchanged. | Recorded. |
| 7 | note | The transient runner ignores options it doesn't pass through; unknown names fall back to A0. | Not triggered by the 7 names used. | Recorded. |
| 8 | note | The summary decides on rounded grid values. | Can flip only within ±0.1%. | Recorded. |
| 9 | note | `laf_scale` also acts during the 10 s warm-up. | Affects only the integrator state at the run start. | Recorded. |

**Also checked and found correct by the reviewer:**
- check 1/2 re-runs;
- F1–F4 and the F7 release as specified;
- the probe, lead-lag (+12.5° at 0.3 Hz, matching the continuous filter) and parameter plumbing;
- no state leaks across forked workers; result order;
- the decision logic (signs, both eras, partial tier);
- the lock-in, M6, jprof and delay FIR definitions;
- `s15_mv_rc` T1/T2/T4, the bootstrap and arms; the follow-up's masks; loband's sign.

**QA stage:** focused review of the analysis done (no product change; two-round QA does not apply). The twin code is not yet reviewed.

### 8.4 Amendment 11a: M4(b) window selection (written 2026-10-07 after the window search, before any probe result)

**Why:** under §8.2 the four drives give only 242 s of windows (`0x1e` 71 s, `0x22` 78.5 s, `0x24` 92.5 s analysed; `0x20` none, its longest run 27 s).
- The binding criterion is the per-frame |κ| < 2.5e-4: only 64–78% of otherwise eligible frames pass it, and the |κ| p90 is about 8e-4.
- The probe estimate is a difference between two runs on identical frames, so road curvature doesn't contaminate it. The criterion only keeps the windows representative of straight-road driving.

**Amended selection** (all other §8.2 criteria unchanged):
- per frame |logged desiredCurvature| < 1.0e-3 1/m (excludes curves tighter than about 1 km radius);
- per window, mean |κ| < 2.5e-4;
- long eligible runs are split into consecutive windows of ≤ 130 s, each with its own 10 s warm-up;
- windows are taken in route order (`0x1e`, `0x20`, `0x22`, `0x24`), at most 2 per drive, until ≥ 6 min are analysed.

**Linearity check:** on the first selected window. The window list is reported.

Everything else in §8.2 is unchanged: probes, estimator, outputs, criteria.

**Sign conventions** (determined by the probe agent before any probe run; source facts at `89bbe60ab1` and observations on `0x24`):
- lane-line y is positive to the right (`fill_model_msg.py` L54/L56); positive desiredCurvature is a right turn (`latcontrol_angle.py` L24, `latcontrol_pid.py` L22 pass −desiredCurvature to the steer-from-curvature map);
- +0.5° calibration yaw rotates the lane lines by −0.51° over 40 m with almost no shift at the car, i.e. the car heads 0.5° to the right of the road; the response is Δκ −1.33e-4 (a left, corrective turn);
- +0.2 m shear puts the car to the right; the response is Δκ −8.0e-5 (left, corrective);
- **so a corrective policy has negative P_y and P_ψ** (phase near ±180° at low frequency). These are the same signs as the twin's Δy_R and Δψ_R (right-positive): +Δy_R = car to the right, +Δψ_R = car heading right.

### 8.5 M4(b) results: the real policy's response, measured open-loop (observation of the model; `model_probe/m4b_policy.json`, `model_probe/m4b/`, `logs/s13ws-model-m4b-*`)

**Windows** (Amendment 11a; round 1 reached 360 s):

| Window | Route | Segments | Mean \|κ\| | Mean v |
|---|---|---|---|---|
| w0 | `0x1e` | 2–4 | 1.57e-4 | 31.9 m/s |
| w1 | `0x22` | 6–8 | 1.35e-4 | 34.3 m/s |
| w2 | `0x24` | 3–5 | 1.16e-4 | 29.8 m/s |

- Each window is 130 s with 120 s analysed.
- `0x20`'s only candidate failed the mean-|κ| test (2.91e-4).
- No lane change or lane-turn state in any window.

**Pooled transfers** (pre-registered single-frequency DFT; phase = response − input; per-window range in brackets). A corrective response sits near −180°.

| P_y (m/s² per m, right-positive offset) | 0.11 Hz | 0.23 Hz | 0.37 Hz | 0.53 Hz | 0.71 Hz |
|---|---|---|---|---|---|
| gain | 1.07 [1.00–1.14] | 1.79 [1.32–2.09] | 2.09 [1.67–2.36] | 2.79 [2.34–3.37] | 4.05 [3.38–4.72] |
| phase | −136° | −138° | −133° | −123° | −129° |

| P_ψ (m/s² per rad, right-positive heading) | 0.17 Hz | 0.29 Hz | 0.43 Hz | 0.61 Hz |
|---|---|---|---|---|
| gain | 20.5 [15.9–24.2] | 28.2 [23.7–31.1] | 25.8 [21.1–31.6] | 30.3 [28.3–31.8] |
| phase | −162° | −152° | −166° | −178° |

- **Perception C_y** (the model's lane-centre change per m of simulated offset): gain 0.90–0.97, phase 172–180°. So the model sees almost the full offset, with little lag.
- **C_ψ is contaminated by DFT leakage** between the closely spaced tones. The probe agent's synthetic self-test shows a spurious 0.35–0.81 m/rad. Its supplementary joint least-squares fit (labelled supplementary; the pre-registered numbers are unchanged) agrees with the DFT within 2% / 2.3° for P_y and 5% / 4° for P_ψ.
- **Coordinator verification** (`s16_ws_m4b_verify.py`, `logs/s13ws-m4bv-*`): an independent DFT on the raw run files reproduces the pooled P_y and P_ψ to every printed digit. The applied heading probe is in radians (peak 0.0084 rad = 4 × 0.13° summed).

**Linearity check (pre-registered): NOT LINEAR.**
- Half amplitude on w0: P_y gain ratios 1.08 / 0.87 / 0.86 / 0.77 / 0.83 (phase within 5.5°); P_ψ phase differences −3.5 / −16.5 / −15.4 / −14.3°.
- The two base runs of w0 from separate processes are bit-identical, so this is not run-to-run noise.
- Perception C_y is linear (ratios 0.99–1.06).
- **By §8.2, the outer-loop twin of §8.3 is not built on these transfers.**

**Readings** (observations of the model, offline; hypotheses where marked):
- **The real policy is a strongly phase-leading corrector.** Its response to a lateral offset sits about 45–57° ahead of a pure correction across 0.1–0.7 Hz, and its gain rises with frequency (1.1 → 4.0 m/s² per m), a P+D-like shape.
  - The phase lead agrees with s12mv's closed-loop estimate (+45…+50°).
  - The gain is about 2× that estimate (1.8–2.1 vs 1.0 at 0.2–0.4 Hz): the closed-loop estimate was biased low, as s12mv §1 warned.
- **The policy is weaker for smaller deviations:** at ±0.1 m peak instead of ±0.2 m, its gain at 0.23–0.71 Hz is 13–23% lower and its heading response lags 14–17° more. *Hypothesis:* the model responds less than proportionally to very small lane errors. That would add to the inner loop's small-signal weakness under D2C4.
- **Consequence for the twin:** a single linear policy block is not adequate. A twin needs either the policy's amplitude dependence, or the model itself in the loop (M4(c)). M4(c) needs no linearisation; its cost is about 0.25 s per frame per core, so about 11 min per 130 s window per variant on one core.

## 10. Conclusions and options (offline evidence only; for the user's decision)

### 10.1 What this session shows

- **No candidate meets the pre-registered rule** (§3): twitch (jumps ≥ 40% and T ≥ 30% down), weave (0.2–0.4 Hz lag ≤ 5°, gain ±10%, W not up) and tracking (≤ +20%).
  - Nothing reaches the "partial" tier either.
  - A 288-point search (§7.7) maps the frontier: **T −30% costs about 10.5° of 0.2–0.4 Hz lag**, and T −18% costs about 4°.
- **Why (observation, car logs; the model agrees):**
  - the wheel's jumps happen as the slow request turns back from a swing, and they move the wheel toward the request (97–99%);
  - the stick-slip is how the wheel follows slow small corrections; the fast jitter plays a minor role (§6.4);
  - so any fix that ignores small errors delays the small corrections lane keeping needs. On the car D2C4 starts small corrections 0.4–0.6 s later (§6.4 ii).
- **A new mechanism beats the old frontier: F7, the breakaway release** (§6.2, §7):
  - when the wheel breaks free after a hold, the controller removes the torque built up while it was stuck;
  - F7d cuts jumps by 40–41% (E2+E3 plant: 52–59%) for +3.4 / +4.6° of lag and +2% tracking, with 1 transient red flag (D2C4: 8) and curve-window cost of +3% / +0.007 s (D2C4: +28% / +0.089 s);
  - small-correction latency stays within about 0.1 s of A0;
  - **but T falls only 14–18%**, so it fails the twitch criterion;
  - **its benefit depends on the actuator delay:** with td 1.5× the fitted value it nearly vanishes. The logs favour the fitted delay (EPS torque t50 about 23 ms; jump rate), but don't exclude a longer one (§7.4–7.6).
- **With F7 as the base, the frontier dominates D2C4:**
  - for the same T reduction it needs about 6° less lag and a quarter of the tracking cost;
  - but every point that meets the T criterion still adds ≥ 11.5° of lag.
- **The real driving model now runs offline on logged video** and reproduces the device (r 0.9997), §8.1. Its lane-keeping response was measured open-loop for the first time (§8.5):
  - a strongly phase-leading corrector (+45–57° of lead), with about 2× the gain the closed-loop estimates suggested;
  - **not linear**: it responds 13–23% less to smaller deviations.
  - So the linear outer-loop twin was not built (pre-registered rule). Running the model itself in the loop (M4(c)) needs no linearisation.

### 10.2 Candidates worth carrying forward (model results; none passes the rule)

| Candidate | Jumps | T | 0.2–0.4 Hz lag | Tracking | Transients | Main risk |
|---|---|---|---|---|---|---|
| **F7d** (release R 0.052, 10 cycles) | −40 / −41% | −14 / −18% | +3.4 / +4.6° | +2% | 1 flag; curve +3% | actuator delay; T barely down |
| **S1** (F7a + feedforward ×1.1) | −41 / −44% | −16 / −20% | +4.1 / +4.2° | 0% | not run | as F7d; laf interacts with torqued |
| S2 (S1 + soft deadzone 0.75) | −49 / −58% | −23 / −28% | +7.5 / +8.0° | +4% | not run | lag above 5° |
| D2C4 (installed) | −45 / −52% | −33 / −41% | +16.5 / +17.6° | +21% | 8 flags; curve +28% | weave (car-confirmed mechanism) |

### 10.3 Options (the user decides)

1. **M4(c), the driving model in the loop** (offline, about 1 h of compute on the three M4(b) windows):
   - first a pre-registered reproduction: A0 in the loop vs the logged drives, then D2C4 vs A0 against the on-car deltas (request weave +32%, lane weave +41%, 0.2–0.4 Hz lag +18°);
   - if it reproduces, rank F7d, S1, S2 and D2C4 on simulated **lane weave**: the outcome the user actually feels, which the inner-loop proxy can't measure.
   - Needs the user's OK (the plan put M4(c) after a check-in).
2. **Decide what "twitch" should mean for the car.** F7-type fixes cut the number of jumps but not their size (T).
   - If the felt complaint is how *often* the wheel twitches, F7d/S1 meet it with almost no weave cost.
   - If it is how *big* each twitch is, nothing found here does both.
   - The session 10 wheel-video measurement could tell which matches the driver's impression.
3. **Later, on the car:** F7d or S1 would need car-scoped controller code, tests, full two-round QA, artifacts, a dry run, and a proposal with an on-car A/B. Its weave criteria would include:
   - the request's own 0.2–0.7 Hz band;
   - the 0.2–0.4 Hz request → wheel lag;
   - the lane offset;
   - the reversal latency (§6.4 ii), which also directly tests F7's delay assumption.
   - **No change to `dragal/custom` without the user's OK.**

### 10.4 What the model cannot show

- Felt comfort.
- The 35–55 mph band and low speed.
- The actual actuator delay at the rack.
- The pre-sliding friction behaviour (M5 was not done).
- The outer loop's lane-weave outcome (pending M4(c)).
- All car evidence for D2C4's weave is one B drive.

### 10.5 User clarification of the complaint (2026-10-07, after §10)

- **User:** "The complaint isn't the wheel feeling twitchy in my hands. It's that the wheel is constantly twitching while the Comma is driving, even on a straight roadway." The user also pointed back to the session 10 wheel videos.
- This matches the session 10 record ([steering-twitch findings](2026-10-06-g70-steering-twitch.md) §1, §4).
  - The video shows the wheel moving **by itself** in a hold-and-jump pattern: holds of 0.5–1.5 s, jumps of 0.3–0.6° within 0.1–0.2 s, every 1.5–2 s on straight highway.
  - Its fast motion matches the logged angle (r 0.90, 0.14° vs 0.13° RMS on `1815 second`).
- **Consequence:**
  - §10.3 option 2 was framed wrongly ("felt in the hands"). The complaint is the **visible, self-initiated stepping** of the wheel: its rate (jumps/min, a direct measure) and the size of each step (0.3–0.6°; T mixes rate and size).
  - The decision is therefore whether a reduction in how often the wheel visibly steps, with weave timing kept (F7d: jumps −40…−41%, step size about unchanged), is worth pursuing. M4(c) checks the weave side.
- **F9 (dither) is reopened as a hypothesis** (§2.2 set it aside mainly on felt vibration):
  - keeping the column out of static friction could turn the steps into smooth motion without delaying corrections;
  - open risks: a buzz felt with hands on the wheel (an engaged 20 Hz line already exists); the Karnopp plant has no pre-sliding, so the model can't judge it; it needs its own offline design (and probably a better friction model, M5) before anything else.
- **User decision (2026-10-07): dither is not acceptable** ("it would create unnecessary wear on the steering rack"). F9 is closed; it must not be proposed again.

## 11. Parameter map: everything in the lateral path that affects stick-slip and weave (user question, 2026-10-07)

Source facts at `89bbe60ab1` unless marked. Effects are model results (E4 plant, E2 / E3, change vs A0) or observations, with where they come from. "Untested" means no project test exists.

| Stage | Parameter (where) | Value on this car | Effect on stick-slip twitch | Effect on weave (0.2–0.4 Hz lag) |
|---|---|---|---|---|
| Model output | `LAT_SMOOTH_SECONDS` (modeld.py L44) | 0.0 (off) | untested (acts like a request filter) | untested (adds lag like C4) |
| controlsd | `clip_curvature`: MAX_LATERAL_JERK 5 m/s³, MAX_LATERAL_ACCEL_NO_ROLL 3.0 (drive_helpers.py L13–41) | default | untested; *hypothesis*: not binding on straight roads | untested |
| Request filter | `DESIRED_CURVATURE_LP_HZ` (latcontrol_torque_v0.py) | 2.0 Hz (C4, installed) | C4 alone: jumps −37 / −39% | +7° (car: +8°) |
| Friction term | `friction` (torqued; fallback `override.toml` 0.07) × latAccelFactor | 0.081–0.085 (torqued, E4) | largest lever: off −55…−57%; ×0.5 −25…−29% (session 10) | off: tracking +23% |
| Friction term | `FRICTION_THRESHOLD` (ramp width) | 0.3 m/s² | 1.0: jumps −46 / −50% | +9.8 / +10.5° |
| Friction term | `steeringAngleDeadzoneDeg` | 0.4° (D2, installed) | D2 alone: −27 / −31% | +9 / +10° (car: +10°) |
| P | `KP_INTERP` (1.0 at ≥ 30 m/s, 2.0 at 15, 3.5 at 10 m/s …) | default | KP ×0.5: −26…−29%; KP 0.7 at 30 m/s: −27 / −29% | +4.2°; session 7 KP schedules failed for weave |
| I | `KI` | 0.3 | untested (*hypothesis*: small, slow) | untested |
| D | `KD` (+ 1.2 Hz measurement-rate filter) | 0.0 (off) | untested for twitch | session 7: damping failed for weave (lag, error) |
| Gain scale | `latAccelFactor` (torqued; fallback 4.0) | 3.55–3.69 (E4) | scales P and feedforward (not friction torque). ×1.29 (F8a): −39 / −40%. E1 (2.7 / 0.11) was about 2× as twitchy as E3 (observation) | +4.2 / +4.6°, gain −11 / −10% |
| Offset | `latAccelOffset` | −0.02…−0.07 | constant bias; *hypothesis*: none | none expected |
| Delay | `lat_delay` (lagd) | about 0.18 s | V0's setpoint = lat_delay·jerk + expected = the current request, so the delay cancels | session 6: a delay-free error variant was worse |
| Integrator freeze | steer_limited_by_safety, steeringPressed, v < 5 m/s | default | minor | minor |
| Measurement map | paramsd steerRatio, stiffness, angleOffset, roll | sR about 14.1 (learned) | scales the measured lateral accel (loop gain) and the deadzone's size; untested | untested |
| Output stage | STEER_MAX / DELTA_UP / DELTA_DOWN (values.py; panda hyundai.h) | 384 / 3 / 7 | max not reached on highway straights (max 331). Up 3 → 7: jumps +3…+7% | ≤ 1° better |
| Output stage | driver allowance 50, multiplier 2, factor 1; STEER_THRESHOLD 150 | default | only with driver torque (STEER_THRESHOLD sets steeringPressed, which freezes I) | — |
| Not software | static ≈ 3× kinetic friction; command → motion delay (td + te 53–79 ms; EPS torque t50 about 23 ms); 0.1° angle sensor | car hardware | the source of the stick-slip | sets the inner-loop lag |
| Proposed (not in code) | F7 release R, decay | — | F7d: −40 / −41% jumps | +3.4 / +4.6° |

- Inactive on this car: the sunnypilot torque extension (NNLC, lateral-jerk extension, torque overrides; session 6).
- torqued changes laf, friction and offset over time; the E3 → E4 restore raised friction 0.070 → 0.083 and twitch +59% (session 10, observation).

## 12. Stick-slip while the car's own LKA steered (user question, 2026-10-07; observation, small sample)

**Source fact:** in the panda `hyundai` mode, LKAS11 is an openpilot transmit message with `check_relay = true` (`safety/modes/hyundai.h` L29; `safety.h` L267–276). The camera's LKAS11 is therefore never forwarded to the EPS while openpilot controls the car. The stock system can only steer when the panda is in pass-through (`elm327`).

**Observation** (`s16_ws_stock_lka.py`, `s16_ws_stock_sticks.py`; all 500 segments; logs `logs/s13ws-stock-lka-*`, `s13ws-stock-sticks-*`):
- Of 8.3 min of stock-camera torque requests, **72% (about 6 min) occurred in `elm327` mode** with no openpilot LKAS11 sent and the EPS reporting `CF_Mdps_ToiActive = 1`. The car's own LKA steered then. The rest were blocked (openpilot in control).
- Runs ≥ 8 s, not steering-pressed; jump and hold definitions as `s11_plant.jumps_hold`; 0.7–4 Hz angle RMS by an FFT band-pass (numpy; the checkout venv has no scipy). No straight-road filter (mean |angle| is the curviness proxy).
- **Erratum (session 15cm focused review, finding S1; reproduced by the coordinator):** the FFT band-pass in `s16_ws_stock_sticks.py` / `s16_ws_holdstep.py` removes only each run's mean, not its start-to-end trend. That trend leaks into the 0.7–4 Hz band.
  - Compared with the zero-phase Butterworth filter on the same runs, the "angle 0.7–4 Hz RMS" values are inflated by about ×1.15 (openpilot ≥ 55 mph), ×1.29 (openpilot 35–55), ×1.33 (stock 20–35), ×1.48 (manual 35–55) and ×2.53 (manual ≥ 55).
  - The torque-request RMS column uses the same filter.
  - **The counts (jumps/min, hold, hold-steps/min) are not affected.**
  - Corrected cross-source comparisons on the same road are in the [comfort-metrics findings](2026-10-07-g70-comfort-metrics.md) §4.3.

| Source, speed band | Runs | Minutes | Jumps/min | Hold | Angle 0.7–4 Hz RMS | Mean \|angle\| | Torque request 0.7–4 Hz RMS (counts) |
|---|---|---|---|---|---|---|---|
| **Stock LKA**, ≥ 55 mph | 1 | 0.4 | **40.3** | 0.41 | 0.119° | 1.3° | 5.9 |
| openpilot, ≥ 55 mph | 216 | 166 | 36.4 | 0.51 | 0.129° | 2.6° | (ours, see §6) |
| Stock LKA, 35–55 mph | 5 | 2.4 | 31.1 | 0.54 | 0.078° | 2.1° | 5.5 |
| openpilot, 35–55 mph | 101 | 63 | 73.5 | 0.35 | 0.264° | 3.8° | |
| Stock LKA, 20–35 mph | 5 | 2.1 | 88.0 | 0.24 | 0.187° | 3.2° | 6.8 |
| openpilot, 20–35 mph | 45 | 22 | 70.8 | 0.40 | 0.469° | 4.4° | |

**Reading:**
- **The hold-and-jump pattern is also present when the car's own lane keeping steers.** At highway speed the stock system produced 40 jumps/min with the wheel held 41% of the time, about the same as openpilot (36 / 51%).
- This supports the session 10 conclusion that the stick-slip comes from the steering hardware's friction. It is not something openpilot alone creates: any controller that steers this rack in small corrections meets it.
- At 35–55 mph the stock system moved the wheel less (31 vs 74 jumps/min, fast motion 0.08° vs 0.26°), but on different, straighter stretches.
- **Limits:** the stock highway sample is a single 24 s run; there are 11 stock runs in total; roads, days, curvature and conditions differ; there is no straight-road filter. *Not a controlled comparison.*

### 12.1 Correction: the twitch metrics are not validated against the complaint (user challenge, 2026-10-07)

**User:** "I've driven the car plenty with the stock system engaged and I've never noticed the twitchiness I do with the Comma… we've introduced an assumption or a variable at some point that has contaminated our findings."

**§12's reading is withdrawn.** "Jumps ≥ 0.3° within 150 ms" is a rate threshold (about 2°/s) that any normal correction meets. Session 10 already showed manual driving at 69–91 jumps/min. So §12 does not show that the stock system twitches.

**Contamination checks** (observation; E4 + A/B routes `0x1e`–`0x28`, openpilot steering ≥ 55 mph, not pressed, 74 min; `s16_ws_eps_events.py`, `logs/s13ws-eps-events-*`):
- **Our LKAS11 is not dropping frames:** panda TX echo at 100.00 Hz. The apparent > 15 ms gaps pair with ~0 ms intervals (log timestamp batching), not bus gaps.
- **The EPS almost never drops the torque overlay:** MDPS12 ToiActive = 0 in 0.012% of frames (16 episodes of 1–6 frames in 74 min). Our ActToi = 0 frames: 19.
- Jump onsets do not coincide with either: 7 of 2,838 jumps (0.25%) have a dropout within −0.3…+0.05 s, vs 0.12% at random times.
- **So the "EPS handles our commands differently" hypothesis is not supported for dropouts or timing.** Other differences, such as the LKAS11 field contents or the torque command shape, are untested.

**A stick-slip-specific metric doesn't separate the sources either** (`s16_ws_holdstep.py`, `logs/s13ws-holdstep-*`). HOLD-STEP = the angle within 0.1° for 0.3 s, then a change ≥ 0.3° within 150 ms.

| Source | Speed | Minutes | Jumps/min | Hold-steps/min |
|---|---|---|---|---|
| Manual (driver) | ≥ 55 mph | 13.1 | 98.7 | **34.7** |
| Manual (driver) | 35–55 mph | 34.5 | 121.4 | 32.2 |
| Manual (driver) | 20–35 mph | 16.9 | 117.8 | 30.7 |
| openpilot | ≥ 55 mph | 166.0 | 36.4 | 21.4 |
| openpilot | 35–55 mph | 63.2 | 73.5 | 26.9 |
| openpilot | 20–35 mph | 22.1 | 70.8 | 19.8 |
| Stock LKA | ≥ 55 mph | 0.4 | 40.3 | 20.2 |
| Stock LKA | 35–55 mph | 2.4 | 31.1 | 17.9 |
| Stock LKA | 20–35 mph | 2.1 | 88.0 | 20.3 |

**Reading:**
- **With a 0.1° angle sensor, these log metrics fire as often (or more often) in manual and stock driving as under openpilot.** They don't measure what the user perceives as twitch.
- What is established (session 10): the wheel video shows hold-and-jump motion under openpilot, and the logs show the torque command ramping while the wheel holds, then breaking free. That is physical stick-slip behaviour under openpilot.
- **Not established:**
  - that jumps/min or T track the perceived twitch;
  - that the stock system experiences the same thing;
  - why it looks different under openpilot.
- Session 10 also noted that the bookmarked, filmed `0x23` moments rated calm by these metrics. This is consistent with the metric problem.
- **Consequence:** every twitch result in sessions 10–13ws that uses jumps/min or T as the criterion rests on an unvalidated proxy. This includes D2C4's offline selection, the on-car "−42% jumps", the MV and F candidates, and the frontier. They are *provisional* until a twitch measure is validated against the user's perception: labelled moments, a same-road stock vs comma comparison with video.
- The weave findings (0.2–0.4 Hz lag, reversal latency, lane offset) don't depend on these twitch metrics.
