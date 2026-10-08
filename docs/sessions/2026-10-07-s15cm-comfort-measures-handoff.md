# Handoff: end of session 15cm (2026-10-07, offline): comfort and twitch measures built; the weave is the clearest comma–stock difference; no twitch measure validated as pre-registered

- **Main thread.** Ran the [comfort-metrics kickoff](2026-10-07-s13ws2-comfort-metrics-kickoff.md).
- **Kickoff for the next session:** [2026-10-07-s15cm-comfort-measures-kickoff.md](2026-10-07-s15cm-comfort-measures-kickoff.md).
- **Findings:** [2026-10-07-g70-comfort-metrics.md](../findings/2026-10-07-g70-comfort-metrics.md). §1 input facts, §2 brainstorm, §3 Amendment 13 pre-registration, §4 results, §5 reading and options, §6 QA.
- **Token usage:** about 400k by the context counter, past the 250–300k soft target. That is why the handoff comes now.
- Reconfirm everything at the next session start.

## 1. Objective (user)

- **"Ultimately it's driving comfort that we're trying to improve."**
- Build and validate measures of:
  - the weave (0.2–0.7 Hz);
  - the faster twitch: the wheel visibly stepping by itself, and its comfort upset.

  These must match the driver's experience before any further fix work.
- Dither is ruled out (rack wear).

## 2. User instructions and decisions

- **Standing:**
  - offline only;
  - no device access, install or reboot without explicit authorization;
  - no change to `dragal/custom` or the WSL clone without asking first;
  - tool installs and read-only pulls are authorized (CLAUDE.md §6, memory);
  - the VM is dedicated;
  - the outer docs commit has not been requested.
- **No new user input this session.** The user was not consulted during the run, so the questions in §7 are open.

## 3. Revisions and workspace (end of session; reconfirm)

- Baseline `dev` @ `0b2c431d3a`.
- `dragal/custom` @ `89bbe60ab1`: D2C4, installed on the car since 2026-10-07 13:33 EDT; last known-good `c027a92857`. Clean, not pushed.
- WSL clone @ `89bbe60ab1`, clean. Checkout porcelain was 0 after every extraction run.
- **Outer `main`** @ `606c36b` + uncommitted docs. This session added:
  - the comfort-metrics findings;
  - this handoff/kickoff pair;
  - a correction note in the fingerprint findings (ESP12 yaw);
  - the CHANGELOG 15cm section;
  - the sessions README rows.
- **Parallel session 14lv (log viewer)** was active during this session (its own `claude` process; Node tests in `scratch/wsl/rlogviewer`). It owns `tools/log-viewer/` and its CHANGELOG section. Nothing of it was touched.
- **No device access and no SSH** this session. No jobs running at handoff.

## 4. What is known now (details and tables in the findings §4–5)

### 4.1 Inputs

- **ESP12 (0x220) carries the car's yaw rate and lateral acceleration.**
  - The yaw rate matches the device gyro: r ≈ −0.9995, scale 1.00–1.01, 30–40 ms later.
  - ADRV_0x51 relays it 30 ms after that. **This corrects 13ws.**
  - The yaw-derived lateral acceleration v·r is far less road-dominated than the IMU's lateral acceleration.
- Column torque: 0.00781 Nm per raw unit.
- **The stock-LKA reference is route `0x0e`:** dashcam mode (`OpenpilotEnabledToggle = 0`), 6.2 min, on the session 4b low-speed loop.
  - It is the same road, day and driver as the comma laps `0x0a`/`0x0b` (E2 tune) and the manual lap `0x0c`.
  - Only 0.4 min of it is at ≥ 55 mph.
- The driver's hands were equally light under the stock LKA and the comma: column torque 0.14 vs 0.10 Nm RMS, |τ| ≥ 0.3 Nm in 4.8% vs 4.7% of the time.
- **Bookmarks:**
  - `0x22` 553.4 / 629.7 s (629.7 is in manual driving, so it can't be scored);
  - `0x23` 209.3 / 261.7 s;
  - `0x1a` 92.5 s (the grasp warning);
  - **`0x28` 238 s (D2C4 drive, unexplained)**.

### 4.2 Results (focused review done, §6)

- **Mechanism:** a comma wheel hold-step at highway speed changes lateral acceleration by about 0.15 m/s² within 0.45 s (z 27–44). The twitch moves the car.
- **Validation (Amendment 13):**
  - **V-label is not evaluable as pre-registered:** one of the five episodes has no comma data.
  - With a four-episode adaptation chosen after seeing the results (exploratory):
    - the yaw-derived J_r (0.7–4 Hz jerk) and A_wd (W_d-weighted) pass;
    - the wheel-angle measures (T, jumps, hold-steps), the new torque-based S_act and U fail.
  - **V-stock** (same road): see the next block.
  - **Strictly, no twitch measure is validated.** W_ar is the recommended weave measure.
- **V-stock: comma / stock on the same road:**

  | Measure | Comma / stock | Verdict |
  |---|---|---|
  | **Felt weave W_ar** (0.2–0.7 Hz) | **1.88 [1.58, 2.30]** | pass (manual / stock: 1.02) |
  | Twitch-band jerk J_r | 1.05 | not separated |
  | Steering-coherent part of J_r (exploratory) | 1.12 | not separated |
  | Hold-steps | 1.28 | pass |
  | S_act | 1.43 | not separated |

- **The bicycle check fails as pre-registered:**
  - under the comma at highway speed, the measured yaw response to the wheel angle is 1.35× / 1.96× the model's at 0.2–0.7 / 0.7–1.5 Hz, and leads it by 29–37°;
  - so no candidate was re-ranked on simulated comfort.
  - **Review F1, reproduced: the mismatch depends on who steers.** The model fits manual driving at medium speed (gain 1.02–1.08, phase −5…−17°, about the ESP12 delay). Under actuator control the yaw leads the wheel (comma up to +37°, stock +14°).
  - So **under actuator control the wheel angle is not a faithful input** for the car's response. The cause is the rack leading the wheel (H-col) or closed-loop bias.
  - The 13ws outer-loop twin is affected the same way.
- **Exploratory (H-col):**
  - before comma and stock wheel steps (not manual ones), the car's yaw rate starts rising during the 0.3 s hold (+0.10 °/s comma, +0.06 stock);
  - the column torque winds the opposite way.
  - The review's controls tie the rise to the coming step, only under actuator control. It is not explained by ESP12 delay, angle creep (about 0.01°) or hold selection.
  - Hypothesis: on this rack-type EPS the wheel catches up with a rack that has already started moving. A closed-loop cause is not ruled out.
- **Exploratory: what the EPS receives.**
  - The comma's torque command is a staircase: flat 50% of 10 ms steps, 19% exactly +3. The stock's changes almost every step by 1–2 counts.
  - The comma has a third more 0.2–0.7 Hz torque.
  - LKAS11 icon/status fields differ (LdwsSysState 3/4 vs 0; Opt_USM 2/2 vs 0/0). Any effect on the EPS is untested and low prior.
- **D2C4 on the car** (B `0x28` vs A on B's road, ≥ 55 mph):
  - felt weave W_ar **+29% [+12, +49]**; lane offset +49%;
  - felt twitch-band jerk J_r −4% [−17, +9] (no change);
  - only the wheel-step counts fall (−21…−26%).
- **Reading:**
  - the weave is the clearest comfort difference between the comma and the car's own LKA (and the driver);
  - the fast, steering-caused motion is about the same;
  - hypothesis: the visible "constant twitching" is the wheel following the comma's larger weave in steps;
  - D2C4 worsens the felt weave without a felt twitch benefit.

## 5. Tooling (`E:\DragalPilot\scratch\wsl\cm\`)

| Script | Purpose |
|---|---|
| `cm_extract.py` (`run_cm_extract.sh`, checkout venv) | One-pass extraction of all segments |
| `cm_t0.py` (`run_cm_t0.sh`) | Route time base (`drive_extract.py` convention) |
| `cm_lib.py` | Route assembly, CAN decoding (ESP12, MDPS12, LKAS11, ADRV), IMU rotation, filters, runs, W_d |
| `cm_checks.py`, `cm_checks_print.py` | Input checks C0–C4 |
| `cm_selftest.py` | Synthetic self-tests (all pass) |
| `cm_route.py` | Per-route measure inputs (sources, selections, band signals, events, nulls) |
| `cm_eval.py`, `cm_eval_print.py` | Amendment 13: mechanism, V-label, V-stock, weave consistency, descriptive tables, J_coh, hands |
| `cm_bike.py` | Bicycle check; per-route model yaw and sub-band jerks |
| `cm_ab.py` | D2C4 re-score |
| `cm_eta.py`, `cm_explore.py`, `cm_lkas.py` | Exploratory: event-locked averages, shared-road J_coh and finer V-label views, LKAS11 fields and command shape |

- Runner: `run_cm_vid.sh <script> <tag>` (`~/venvs/vid`).
- Outputs: `analysis/g70-comfort-metrics-20261007/{extract,routes,bike,checks,eval}/`. Logs: `logs/s15cm-*`.

## 6. QA status

- Self-tests pass.
- **Focused adversarial review** (one independent agent) of the new `cm_*` code, the unreviewed 13ws read-only scripts (`s16_ws_bus1/lkas_adrv/adrv_decode/adrv_scale/dup/nnlc_*/stock_lka/stock_sticks/holdstep/eps_events/srcprobe`) and a skim of the twin: **done** (findings §6; report `scratch/wsl/cm/review/review.md`).
  - **No blocker.** Decoding, sources, events, filters, the validation mechanics and the bicycle equations are all correct.
  - **Major findings:**
    - F1: the bicycle mismatch depends on who steers (the reading is revised);
    - F2: V-label can't pass as pre-registered (already reported);
    - S1: the 13ws FFT band-pass inflates the "angle 0.7–4 Hz RMS" by ×1.15–2.53, most for manual driving. An erratum is added to the weave-twitch findings §12; the counts are unaffected.
  - The coordinator verified F1, F2, S1 and F10 (`cm_verify_review.py`).
  - **Minor findings, noted without changing results:**
    - F3: held values reset per segment, so runs split every ~60 s, with no bias;
    - F4–F7: ≤ 3% effects;
    - F8: borderline V-stock passes are fragile; W_ar's isn't;
    - F10: B road restriction, no effect;
    - S3: the ADRV lag-search range (the documented lags agree with this session's measurement).
- **Not reviewed:** `s13ws_model/*` (the M4(b) probe), and the twin code beyond a skim. The twin was not used for results.

## 7. Open questions for the user

1. **The decisive recording.** Would the user drive the same highway stretch twice, once with the car's own lane keeping and once with the comma? The setup:
   - for the stock run, openpilot is switched off by the user in the device settings (dashcam mode, as on `0x0e`);
   - a passenger films the wheel and bookmarks both twitchy **and calm** moments;
   - the hands state is noted.

   The pull afterwards needs authorization.
2. What was the **`0x28` bookmark** (238 s, D2C4 drive) for?
3. At the filmed `0x23` moments, did the user see the wheel twitch?
4. **D2C4:** keep, or roll back to A (`c027a92857`), given the felt weave +29% and no felt twitch benefit?
5. **Next work:** focus on the weave (the clearest difference), with W_ar as the outcome?

## 8. Ordered next steps

1. Next session: the [15cm kickoff](2026-10-07-s15cm-comfort-measures-kickoff.md). Collect the user's answers to §7 first.
2. **Offline, regardless of the answers:** an empirical vehicle-response model **from the comma's torque command (or the EPS output torque) to the yaw rate**, not from the wheel angle (review F1).
   - Handle the closed-loop bias, for example with the request as an instrument.
   - Validate it on held-out routes.
   - Then the simulator's candidates can be scored on W_ar and J_r through their simulated torque.
   - Test H-col more strictly: a closed-loop cause, and the sign predicted by a model correction.
3. If the user records the decisive drive: pull it (authorized, read-only, rlogs + both road videos + the phone video), then run V-label and V-stock on it. Pre-register before looking.
4. Any car change: ask first, then code, tests, two-round QA, artifacts, a dry run, and a proposal with an on-car A/B on W_ar and J_r.
