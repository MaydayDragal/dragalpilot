# Handoff: end of session 12mv (2026-10-07): weave root cause found; next: refine D2C4 offline into a fix for both weave and twitch

Written at the user's request: "Let's see how far we can get with this while simulating locally. Write a handoff and kickoff prompt for the next session to perform the necessary simulation, offline testing and analysis to start with D2C4 and refine it to a solution that addresses both the weave and the steering wheel jitteriness. Instruct it to brainstorm on potential new methods of analyzing the data or simulating the tests that may be novel compared to what we're doing today that could reveal new data or potential approaches to the problem that have yet to be explored in this project."

- **Main thread.** Supersedes [2026-10-07-s12mv-milder-variants-handoff.md](2026-10-07-s12mv-milder-variants-handoff.md) (still the detailed record of this session's steps; its §11–12 hold the later revisions).
- **Kickoff:** [2026-10-07-s12mv2-weave-twitch-sim-kickoff.md](2026-10-07-s12mv2-weave-twitch-sim-kickoff.md). The [weave-attribution kickoff](2026-10-07-s12mv-weave-attribution-kickoff.md) remains for when new B drives exist.
- **Token usage:** no reliable cumulative figure available.
- Reconfirm everything at the next session start.

## 1. Objective

- Make sunnypilot drive the user's 2024 Genesis G70 well.
- Primary complaint: the steering wheel is twitchy on straight roads. Weaving also matters.
- **Next session:** starting from D2C4, find **offline / in local simulation** a change that keeps D2C4's twitch reduction **and** does not make weave worse. Explore new analysis and simulation methods as well.

## 2. User instructions and decisions (this session)

- Ran the milder-variants kickoff. Chose "All 9 as proposed" (MV1–MV9), with red flags "reported only".
- Challenged the "exogenous" reading of the weave: "An increase of 32% being caused by the same exact model on the same stretch of roadway on a clear day is illogical." **The reading was revised:** D2C4 is the most likely cause.
- "I'd rather find a logical defensible root cause for the weave in D2C4 because it seems to have addressed a lot of the other concerns." Done (§4.6).
- **"Let's see how far we can get with this while simulating locally."** The next session is offline/local simulation. No device work implied.
- **Standing:**
  - every device change, install and reboot needs explicit per-action authorization;
  - no code change on `dragal/custom` without asking first;
  - video pulls, tool installs and read-only pulls are authorized (§6 rules apply);
  - the VM is dedicated (use all cores, bit-identical parallelism; ≤ 4 workers if a parallel session runs);
  - the outer docs commit has not been requested.

## 3. Exact revisions and workspace (confirmed 2026-10-07 ~18:00 EDT)

- **Baseline:** `dev` @ `0b2c431d3a…` (unchanged).
- **`sunnypilot/`:** `dragal/custom` @ **`89bbe60ab127cf71d238856a19c1e74b16bc36bd`** (D2C4), clean, not pushed. **WSL clone** `~/src/sunnypilot` @ `89bbe60ab1`, clean. No WSL jobs.
- **Device:** D2C4 (`89bbe60ab1`) installed since 2026-10-07 13:33 EDT; last known-good `c027a92857`. Last observed by session 11r (offroad, partner's workplace, 18:59Z). Not accessed since.
- **Outer `main`** @ `606c36b` + 35 uncommitted doc paths (sessions 8–12mv).
- **Data root `E:`:** UniqueId `daa460f7…`, about 213 GB free.

## 4. What is known (evidence; details in the findings)

Findings: [milder variants and weave root cause](../findings/2026-10-07-g70-milder-variants.md) (§2–8), [D2C4 validation](../findings/2026-10-07-g70-d2c4-validation.md) (Amendments 5–8), [on-car A/B](../findings/2026-10-07-g70-d2c4-ab-onroad.md), [root cause of the twitch](../findings/2026-10-07-g70-twitch-root-cause.md).

### 4.1 The twitch (session 10, model-supported)

- The twitch is a **stick-slip limit cycle**, from three ingredients:
  - static friction in the steering (about 3× kinetic);
  - V0's error-driven friction-compensation term (deadzone 0, full ramp over ±0.3 m/s²) plus P, which keep ramping torque while the wheel is stuck;
  - small fast jitter in the model's curvature request.
- The wheel holds, then jumps 0.3–0.4°.

### 4.2 D2C4

- **The change:** `steeringAngleDeadzoneDeg` 0.4° on the friction input (D2) + a causal first-order 2 Hz low-pass of desiredCurvature (C4), G70 only.
- **Offline:** jumps −45…−60%, T −33…−42%, tracking error about +20%, curve lag +0.09 s.
- **On the car** (one drive, `0x28`):
  - jumps −42% vs the A drives, but only on par with the light-matched midday A drive (22.0 vs 19.3/min);
  - transient costs as predicted;
  - **weave up**: lane-centre offset 0.2–0.7 Hz +41%, request weave +32%, wheel weave +27%. B is above every same-road A drive, at matched speed.

### 4.3 Weave root cause (§7–8 of the findings; hypothesis well supported in this band; one B drive)

- **At 0.2–0.4 Hz** (the car's ~3 s weave band), the wheel lags the request **18° more** with D2C4 (CI −28…−11°).
  - The logged setpoint is post-filter on B, so the car data split it: **8° from C4** (exactly the filter's theoretical lag) and **10° after it, from the deadzone** (CI excludes 0).
- **The deadzone part is small-signal.** B's small-amplitude response is weaker (−26%) and later (−27°); large amplitudes are unaffected. Time with the wheel held: 40% → 59%.
- **The closed loop:** tracking-error weave +18%, twice as coherent with the lane offset; the model corrects harder (lane → request coherence 0.38 → 0.71). Lane-keeping lost about 18° of phase margin at its weave frequency.
- **The stick-slip model reproduces this split at 0.2–0.4 Hz** (D2C4 17–18°: C4 7°, D2 9–10°; in-context estimator). It **over-predicts at 0.4–0.7 Hz** (+27° vs about +3° on the car).
  - So the **0.2–0.4 Hz in-context request → wheel lag** is the weave metric with car validation (one drive).

### 4.4 Model status and biases (use with care)

- **Plant:** single-input stick-slip (Karnopp), first-order EPS, quantized angle; θ0 from the logged angle. Fitted on E4 (primary) or E2+E3, at 55+ mph only.
- **Biases:**
  - it over-predicts D2C4's hold on `0x28` (adequacy fails on hold, +0.12);
  - its A0 lags about 13° less than the car over the full band.
- **No outer loop.** An ARX lane → request policy model was not adequate (14.9% of the held-out weave band explained, ≥ 20% needed). Requests are replayed open-loop.
- 35–55 mph and low speed are not modelled.

### 4.5 Candidates tried (Amendment 8; model, E4 plant, E2/E3)

- **Nothing in MV1–MV9 fixes weave.** 0.2–0.4 Hz lag: D2C4 +17°; the others +11…+16°, because each keeps a deadzone ≥ 0.3°:
  - MV1/MV2: step deadzone 0.5/0.6°;
  - MV3/MV4: continuous deadzone 0.4/0.3°;
  - MV5/MV6: D2 + 4/3 Hz filter;
  - MV7: MV4 + 4 Hz;
  - MV8: D2 + shelf filter;
  - MV9: D2 + friction-path-only filter.
- **MV2/MV3 match D2C4's twitch reduction with half its curve lag** and no R5/C3 flags.
- **Earlier:**
  - C1–C6, D1, J1/J2, H1 and P1 failed;
  - C3 (friction 0) halves the twitch but costs +23% tracking;
  - P1 (P deadzone) cuts it by 70%, at +37% tracking;
  - session 6: v1 / delay-free error do not help weave; the feedforward gain is too high for the plant's dynamic gain (v0k reduced the band gain).

### 4.6 Implications for design

- A fix must cut the stick-slip excitation or response at **0.7–4 Hz and small amplitudes**, while preserving (or restoring) **small-signal response and phase at 0.2–0.4 Hz**.
- **Directions not yet tried** (hypotheses for the next session to evaluate):
  - frequency-split deadzone: apply the deadzone only to the fast part of the error, so slow small errors still get friction compensation;
  - phase-lead compensation at 0.2–0.4 Hz to offset the 18°;
  - a deadzone on the request jitter instead of the error;
  - the integrator / P working inside the band;
  - stiction-aware compensation (breakaway pulse, dither);
  - a speed-scheduled feedforward gain (session 6's v0k).

## 5. Tooling (E:\DragalPilot\scratch\wsl\sng\; shared `s11_*`–`s14_*` scripts are never edited)

| Tool | Purpose |
|---|---|
| `s15_mv_var.py` | Harness extension: `closed_loop_fp` (the shared loop + a separate friction-path request), `simulate_mv` (= `s11_eval.simulate` + shelf/friction-path options; θ0 cached per route), `MV` table, `install()` (adds variants and points `s11_eval.simulate` at it in-process). Bit-exact for existing variants. |
| `s15_mv_grid.py` | Twitch/comfort stats, weave proxy (in-context request → a_s transfer per band) and tracking for a variant list, E1–E4, both plants; reproduces Amendment 6 exactly. |
| `s15_mv_transient.py`, `s15_mv_curves.py` | Amendment 7 steps/sines (R1–R5) and curve events (C1–C3) for any variant (`s12_transient.run` ignores `fr_dz_shift`, so use these). |
| `s15_mv_summary.py`, `s15_mv_loband.py` | Decision-rule table; 0.2–0.4 / 0.4–0.7 Hz lag per variant. |
| `s15_mv_2a.py`, `s15_mv_rc.py`, `s15_mv_2a_followup.py` | On-car log metrics: request/wheel/lane weave, transfer decomposition, amplitude bins, holds, error weave, same-road pairs. |
| `s15_mv_3.py` | Plant check on a logged drive. |
| `s15_mv_arx.py` | Policy ARX (inadequate; a starting point for v2). |
| `s13_sim.py`, `s13_simd2.py` | About 11× bit-identical sim speed-up and AVX-512 lane batching (prototype); not wired in yet. |
| `run_s15_mv.sh <tag> <script> args` | Generic runner (`~/venvs/vid`, logs `logs/s12mv-*`). |

- **Data:**
  - datasets `analysis/g70-twitch-rc-20261007/dataset` (E1–E4) and `analysis/g70-d2c4-ab-20261007/dataset` (`0x26`–`0x28`);
  - drive extracts (modelV2 lanes) as listed in `s15_mv_grid.DRV`;
  - IMU extracts `analysis/g70-d2c4-20261007/imu`;
  - plants: `analysis/g70-d2c4-20261007/plant_cl_e4/plant_fit.json` (E4) and `analysis/g70-twitch-rc-20261007/plant_cl/plant_fit.json` (E2+E3).
- **Outputs of this session:** `analysis/g70-milder-variants-20261007/{explore, 2a, 3, 2b, a8, rc}`.
- **Videos:** fcamera/ecamera for routes up to `0x25`. Those for `0x26`–`0x28` are deferred (`metadata/GAPS.md`).
- **Checkout tooling observed but not tried** (source presence only; runnability on this x86 VM unverified):
  - `openpilot/tools/sim` (simulator bridge);
  - `openpilot/tools/lateral_maneuvers`;
  - `openpilot/selfdrive/test/process_replay/{process_replay.py, model_replay.py}`;
  - `openpilot/selfdrive/modeld/` with the tinygrad driving model (`driving_tinygrad.pkl` chunks) and `tinygrad_repo/`.
- **Venvs:** checkout venv (pycapnp, rlog readers) and `~/venvs/vid` (numba/scipy). From Git Bash use `MSYS_NO_PATHCONV=1` and runner files (project memory).

## 6. Validation limits and QA

- Everything is offline model evidence or log observation from one D2C4 drive. No logged era is untouched by candidate selection. The next on-car A/B is the independent test.
- **QA this session:** focused review of the analysis scripts (findings §5; 3 minor fixed or recorded, no verdict change). The root-cause scripts (`s15_mv_rc.py`, `s15_mv_2a_followup.py`, `s15_mv_loband.py`) have **not** been reviewed yet; a focused review is pending.
- D2C4 code `89bbe60ab1`: full two-round QA (session 11).

## 7. Running operations, device, SSH

- None running. No background agents, no WSL jobs.
- No device access and no SSH this session.
- Any device access needs the user's authorization, a confirmed address and state, and no other session (CLAUDE.md §6).

## 8. Open questions

- Which mechanism gives the twitch reduction **without** small-signal lag at 0.2–0.4 Hz?
- Can an outer-loop model be made adequate? Options: instrumental variables, the driving model itself in the loop, full lane-line geometry.
- Would the on-car isolation (D2-only, C4-only) confirm the 10°/8° split?
- Carried over:
  - 20 Hz EPS pulse source;
  - 35–55 mph and low speed;
  - stop-and-go;
  - `0x27` without GPS;
  - the videos of `0x26`–`0x28`;
  - the driver's assessment of the B drive.

## 9. Ordered next steps

1. **Next session:** the [weave + twitch simulation kickoff](2026-10-07-s12mv2-weave-twitch-sim-kickoff.md) (offline/local).
2. In parallel, or later: the A/B follow-up (videos, new B drives, the driver's assessment). Then the [weave-attribution kickoff](2026-10-07-s12mv-weave-attribution-kickoff.md).
3. The outer docs commit, when the user asks.
