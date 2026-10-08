# Handoff: session 10 (end, 2026-10-07): steering-twitch root cause and candidate D2C4; next session validates it (4 steps)

Written 2026-10-07 ~09:55 EDT at the user's request ("This is a large conversation, let's write up a detailed handoff and kickoff for the next session to do the 4 recommended steps. Ensure that the analyses are evaluating wheel 'jitter', weaving and overall comfort.").

- **Supersedes as the main thread:** [2026-10-07-s10-twitch-root-cause-handoff.md](2026-10-07-s10-twitch-root-cause-handoff.md), which is kept unchanged as the mid-session record.
- **Token usage:** no reliable cumulative figure; this context window was compacted once.
- Reconfirm everything at the next session start.

## 1. Objective

Make sunnypilot drive the user's 2024 Genesis G70 well.

The **primary lateral complaint**, as clarified by the user on 2026-10-06 after riding along: the steering wheel is **"twitchy"**. Even on a straight road with clear lane lines it "is constantly correcting or overcorrecting in small amounts". Weaving within the lane also happens and still matters.

**Next session's goal:** carry candidate **D2C4** (§4.4) through the 4 recommended steps (§9). Every analysis evaluates **three outcomes together**:
1. **wheel jitter**: the hold-and-jump twitch;
2. **weaving**: the slow 0.2–0.7 Hz lane-position swing;
3. **overall comfort**: what occupants feel.

Defined in §8.

## 2. User instructions and decisions (sessions 10 and earlier, still in force)

**This session:**
- Device pull (user-confirmed `.104`, indoors, inactive, no SSH): videos, rlogs and all system logs; then verify the audio fix and the torqued restore. **Done.**
- The twitch is the primary complaint. The phone wheel videos (`C:\Videos`, filenames = times) and the device bookmarks are evidence. **Analysed.**
- "Even pre-restore settings were twitchy. I want to find the root cause. Do #1 [offline stick-slip model] and expand the data you test to earlier routes as well." **Done.**
- "Agreed; 2 first" (mechanism-targeted candidates). **Done** (Amendment 4).
- This handoff: the next session does the 4 recommended steps, evaluating jitter, weaving and comfort.

**Standing:**
- Video pulls and tool installs (host/WSL) authorized.
- Read-only device pulls unrestricted in scope.
- Unneeded files may be deleted (§3 of CLAUDE.md).
- No targeted test re-runs for docs-only commits.
- Durable rules go into CLAUDE.md in the same session.
- **Every device change, install and reboot needs explicit per-action authorization at the time.**

**Outer docs commit:** not requested yet. Everything since `606c36b` is uncommitted (sessions 8, 9 and 10).

## 3. Exact revisions and workspace (confirmed 2026-10-07 09:54 EDT)

- **Baseline:** `dev` @ `0b2c431d3a…` (unchanged).
- **`sunnypilot/`:** `dragal/custom` @ **`c027a92857`** (local, not pushed), clean. WSL clone `~/src/sunnypilot` @ `c027a92857`, clean.
- **Device**, last observed 2026-10-07 02:24Z:
  - `.104`, `IsOffroad=1`, `IsEngaged=0`;
  - `GitCommit=c027a92857`, `DisableUpdates=1`;
  - `LiveTorqueParameters` `8a843369…` (8,576 points, valid, laf 3.547 / friction 0.0816 / offset −0.054; learned on top of the session 9 restore).
- **Outer `main`** @ `606c36b` = `origin/main`, 20 uncommitted paths:
  - modified: `CHANGELOG.md`, `CLAUDE.md`, `docs/baseline.md`, `docs/local-storage.md`, `docs/sessions/README.md`, `docs/findings/2026-10-04-g70-tune-0x484-first-drive.md`;
  - new findings: `2026-10-05-g70-device-errors.md`, `2026-10-05-g70-sng-drives.md`, `2026-10-05-soundd-audio-gate.md`, `2026-10-06-g70-torqued-reconstruction.md`, **`2026-10-06-g70-steering-twitch.md`**, **`2026-10-07-g70-twitch-root-cause.md`**;
  - new proposals: `2026-10-05-soundd-audio-gate-deploy.md`, `2026-10-06-g70-torqued-restore.md` (both with check-drive records);
  - new handoff/kickoff pairs: s8, s9, s10, and this s10b pair.
- **Data root `E:`:** UniqueId `daa460f7…`, about 215 GB free.
- **Running:** nothing; no WSL jobs. **SSH:** no connection open; none since 02:31:55Z.
- **Tools added this session:** numba 0.68.0 in `~/venvs/vid` (`logs/s10-install-numba-20261007.log`).

## 4. Completed work and evidence

### 4.1 Check drives (8 routes `0x1e`–`0x25`, 2026-10-06)

- Pull: one read-only SSH connection, 2026-10-07 02:24:57–02:31:55Z.
  - 426 rlog + fcamera + ecamera files, all sha256 MATCH, in `recordings/2026/10/06/`. Gap: `0x21` segment 33 is 0 bytes.
  - Diagnostics in `device-logs/2026-10-06_s10_diag/`: 902 of 909 files match; the other 5 were still being written during the pull.
- **Audio fix verified.** No soundd/micd crash; the gate cleared 11–31 s after each start; one early engage attempt correctly refused (`0x23` at 14 s). [Proposal record](../proposals/2026-10-05-soundd-audio-gate-deploy.md).
- **Torqued restore verified.** Every start logged "restored torque params from cache"; the first message showed 7,722 points, valid, laf 3.688; G70 fingerprint on all 8 starts. Learning continued to 8,576 points. [Proposal record](../proposals/2026-10-06-g70-torqued-restore.md).

### 4.2 Twitch characterisation ([findings](../findings/2026-10-06-g70-steering-twitch.md))

- **What it is:** on straight highway the wheel **holds 0.5–1.5 s, then jumps 0.3–0.6° within about 0.1–0.2 s**, every 1.5–2 s.
  - A 0.3–0.4° jump at 75 mph is a lateral step of about 0.13–0.18 m/s².
  - The amplitudes are small (angle 0.7–4 Hz RMS 0.05–0.13°), but the motion is self-generated and stepwise.
- **Video confirmation:** a background agent measured the hub rotation relative to the dash in the user's 5 phone clips (noise about 0.02–0.06°).
  - The three `0x22` clips match the logged angle in 0.7–4 Hz (r 0.49–0.90) and show the same hold-and-jump steps.
  - `0x23` is inconclusive.
  - `creationdate` = clip start.
- **By era** (55+ mph, straight-clean engaged):

  | Era | Parameters | Jumps/min | Angle T RMS |
  |---|---|---|---|
  | E1 | port tune 2.7 / 0.11 | 48 | 0.134° |
  | E2/E3 | 4.0 / 0.07 | 16–19 | 0.054° |
  | E4 | restored torqued 3.63 / 0.083 | 30 | 0.080° |

- **Controller terms:** P and the friction-compensation term carry 75–83% of the command's 0.7–4 Hz variance.

### 4.3 Root cause ([findings](../findings/2026-10-07-g70-twitch-root-cause.md), pre-registered with Amendments 1–4)

**Step 1 (all eras):**
- The wheel holds about 0.4° short of the controller's target while the command ramps about +30 counts (≈ 8% of STEER_MAX), then breaks free and lands near or past the target.
- **The EPS output torque follows the command during holds** (within-hold correlation 0.87–0.91), so this is **mechanical static friction, not an EPS deadband**.

**Step 2 (model):**
- **Plant:** a stick-slip steering model (EPS lag + delay, aligning stiffness, viscous damping, Karnopp static/kinetic friction, 0.1° sensor), in closed loop with the source-equivalent V0 (bit-exact numba port).
- **Fit:** identified **in closed loop on E2+E3 only** (Amendment 2; the open-loop fits failed).
- **Passes the pre-registered held-out check on E1 and E4 at 55+ mph:** jumps −9…+14%, hold within 0.08, T RMS within 5%, W RMS within 7%; the ordering E3 < E4 < E1 is reproduced.
- **Plant:** static ≈ 3× kinetic friction, delay 31 ms, EPS lag 22 ms.

**Step 3 (ablations):**
- No single ingredient is necessary.
- **Root cause (model-supported):** a stick-slip limit cycle from:
  - (1) steering static friction;
  - (2) V0's error-driven friction-compensation ramp (deadzone 0, ±0.3 m/s²), plus P;
  - (3) small fast jitter in the model's curvature request.
- Removing (2) or smoothing (3) each roughly halves it. Removing (1) makes it worse (continuous oscillation). The 20 Hz request staircase and the 0.1° quantization are not implicated.
- **Why every era twitches:** all three ingredients are always present; the parameters only scale the loop gain.

### 4.4 Candidates

**Amendment 3** (C1–C6): none passed. Every twitch reduction cost tracking error. The closest, C6, failed with E4 error +23%.

**Amendment 4:**
- **D2C4 passes all pre-registered criteria.** It is:
  - **`steeringAngleDeadzoneDeg = 0.4°`**, the existing per-car friction deadzone (`configure_torque_tune`; 0 today for this car);
  - **a causal first-order 2 Hz low-pass of desiredCurvature** (new code).
- **D2C4 results** (change vs as-driven, held-out E1 / E4, 55+ mph):

  | Metric | E1 | E4 |
  |---|---|---|
  | Jumps | −57% | −52% |
  | T RMS | −42% | −39% |
  | W RMS | −9% | −22% |
  | Mean \|error\| (limit +20%) | +14% | **+19.4%** |
  | Curve ratio | 1.061 (A0 1.066) | 1.027 (A0 1.028) |

- **Exploratory robustness** (plant friction ±30%, delay ±50%, stiffness ±20%, EPS lag ×2):
  - the twitch reduction holds (jumps −47…−62%, T −37…−44%);
  - the **tracking cost is +10…+24%** (above 20% on E4 in 4 of 10 cases), so the tracking pass is **marginal**.
- **Others:**
  - D2 alone: jumps −41/−37% but T only −23/−21%.
  - D3 (continuous deadzone): fails the E1 curve criterion.
  - Request-change-keyed friction (J1/J2/H1): no help or worse.
  - P deadzone (P1): error +37/+32%.
- **Source fact:** torqued's restore key (`torqued.py` L137–142) excludes the deadzone. paramsd/lagd keys are not checked.

### 4.5 Open side-finding: 20 Hz EPS pulse (unresolved)

- While engaged: sharp 20/40 Hz lines in `steeringTorqueEps` and a 12–20 Hz column-torque hump (about 9 raw units RMS, threshold 150). Absent in manual driving and at standstill; present in all eras.
- Not locked to MDPS12 frames, our LKAS11 sends or the 0x485 `LFAHDA_MFC` (20 Hz, `SEND_LFA` set). Frequency 19.92 Hz.
- It may contribute to felt "buzz" (comfort). It cannot be seen on 30 fps video.

## 5. Open hypotheses / questions

- **D2C4 is marginal on tracking**, and nothing is known about step and curve-entry responses, 35–55 mph, low speed or stop-and-go.
- **The plant model is single-input and highway-only.** Its validity outside 55+ mph straights/curves is unknown. The outer loop (model re-planning) is not simulated.
- **The comfort impact has not been measured directly yet** (§8.3); the car reports no yaw rate.
- **Driver/hands effects:** all twitch evidence is hands-off. With hands on, the stick-slip may differ.
- **The 20 Hz pulse source** (§4.5).
- **Carried over:** HDA-deselected supervised drive; stop-and-go protocol data; the 0x484 forwarding-rule round.

## 6. Validation limits and QA stages

- **Evidence level:** all twitch, root-cause and candidate results are **offline model evidence at 55+ mph**. No on-car test of any candidate.
- **QA:** **no focused adversarial review** of the session 10 analysis/model/harness has been done. Two-round QA has not been performed for any change. Nothing has been proposed for the device.
- **Harness checks done:**
  - per-sample measurement map vs V0's logged measurement: p99 ≤ 0.004 m/s²;
  - numba loop bit-exact against the Python reference (`s11_fastloop_check.py`), re-checked after the Amendment 4 options;
  - option limit cases exact (`s11_amend4_check.py`);
  - reversal counter tested.

## 7. Artifacts

**Findings:** `docs/findings/2026-10-06-g70-steering-twitch.md` (§3 plan, §5 results), `docs/findings/2026-10-07-g70-twitch-root-cause.md` (§1–6 plan; §7.0–7.9 results and Amendments 1–4).

**Analysis data (E:):**
- `analysis/g70-twitch-20261006/logs/`: twitch metrics, spectra, window plots, EPS spectra.
- `analysis/g70-twitch-20261006/wheel-video/`: video wheel-angle measurement, README, CSVs, plots.
- `analysis/g70-twitch-rc-20261007/`:
  - `dataset/`: per-route 100 Hz model dataset with the V0 measurement map, routes 4–`0x25`;
  - `step1/`: hold-jump, eps-hold;
  - `plant/`, `plant2/`: open-loop fits (failed);
  - **`plant_cl/plant_fit.json`**: the adequate H-band plant;
  - `step2/`: adequacy;
  - `step3/`: ablations;
  - `step4/`: candidates, Amendment 4, robustness;
  - `drives/`: route 3.

**Scripts** (`E:\DragalPilot\scratch\wsl\sng\`):

| Script | Purpose |
|---|---|
| `s11_dataset.py` | dataset; checkout venv via `run_s11_dataset.sh` / `run_s10.sh` |
| `s11_holdjump.py` | selection, eras, hold/jump statistics |
| `s11_eps_hold.py` | EPS output vs command during holds |
| `s11_plant.py` | plant equations, open-loop fit, jump/hold metric |
| `s11_plant_cl.py` | closed-loop identification |
| `s11_fastloop.py` | numba V0 + output stage + plant, with the Amendment 4 options |
| `s11_closed.py` | Python reference loop |
| `s11_fastloop_check.py`, `s11_amend4_check.py` | equivalence and limit checks |
| `s11_eval.py` | variants, twitch metrics, `--tracking` mode |
| `s11_robust.py` | robustness |
| `s10_twitch.py`, `s10_jumps.py`, `s10_spectra_plot.py`, `s10_window_plot.py`, `s10_eps_*.py`, `s10_canpulse*.py` | characterisation and the 20 Hz pulse |

- Runner: `run_s10_vid.sh` (~/venvs/vid). Video scripts: `scratch/wsl/vidwheel/`.
- **Session 6 harness reused:** `scratch/wsl/s5/s5_fast.py` (V0 + Hyundai output stage), `s5_sim.py`.
- **Logs:** `E:\DragalPilot\logs\s10-*.log`, `device-pull-20261006s10.*`, `promote-20261006s10.log`, `user-wheel-videos-20261006s10.sha256`.
- **Disposable:** `temporary/s11-smoke`, `temporary/vidwheel-tmp`, the `temporary/tmp*.so` files, `temporary/s9-*`.

## 8. How the next session must evaluate: jitter, weaving and comfort

Every evaluation in §9 reports all three outcome groups. Logged baselines and simulations use the same definitions. A candidate is judged on all three, never on jitter alone.

### 8.1 Wheel jitter (the twitch)

Definitions as in the twitch findings §3 and root-cause §4; tools `s11_holdjump.py`, `s11_plant.jumps_hold`, `s11_eval.stats`:
- **jumps/min:** ≥ 0.3° within 150 ms;
- **hold fraction:** the 400 ms angle range ≤ 0.1°;
- **steering-angle RMS in 0.7–4 Hz;**
- **micro-reversals ≥ 0.3°/min;**
- **torque-command 0.7–4 Hz RMS** and sign changes/min.

### 8.2 Weaving

- **Steering-angle RMS in 0.2–0.7 Hz.** It is in the Amendment 3/4 criteria: must not rise > 10%.
- **Lateral position:** lane-centre offset and its 0.05–0.7 Hz content from modelV2 lane lines (`lane_drift_extract.py` / session 4–5 methods). Reported on logs, and in simulation where an outer-loop proxy exists.
  - The sim replays the logged request, so lane-position weave can only be judged on logs or on-car. Say so in each result.
- The session 6/7 link metrics where relevant: request → measurement gain/lag in 0.3–0.6 Hz.

### 8.3 Overall comfort (new; define and pre-register before computing)

**Signals:** the car reports no yaw rate (`carState.yawRate` = 0). Extract **livePose** (or `liveLocationKalman`, whichever this revision logs; check the schema) acceleration and angular velocity, plus accelerometer `sensorEvents`, from the rlogs for logged comfort. In simulation, use lateral acceleration from the simulated steering (the measurement map).

**Proposed metrics** (fix them in a pre-registration before looking):
- (a) **Lateral acceleration RMS in 0.5–4 Hz** (plus ISO 2631-1 W_d-weighted RMS if implemented).
- (b) **Lateral jerk RMS and p95** (derivative of the 2 Hz low-passed lateral accel).
- (c) **Step events:** count/min of lateral-accel changes ≥ 0.1 m/s² within 200 ms.
- (d) **Steering-wheel vibration:** column torque (`steeringTorque`) RMS in 8–20 Hz, and the 20 Hz EPS line amplitude (`steeringTorqueEps`).
- Each reported on straight-clean and on all engaged runs, by speed band.

**Baselines:** logged E1–E4 engaged, and manual driving where available.

## 9. Ordered next steps (the 4 recommended steps)

1. **Session start.**
   - Read CLAUDE.md, this handoff, the changelog (session 10 entries), `docs/local-storage.md`, and both twitch findings docs.
   - Confirm:
     - outer `main` @ `606c36b` + the uncommitted docs;
     - `dragal/custom` @ `c027a92857`, clean;
     - WSL clone @ `c027a92857`, clean;
     - E: identity, writability and free space.
2. **Step 1: focused adversarial review** (CLAUDE.md §5) of the session 10 model/harness and the Amendment 1–4 results.
   - **Reviewer:** one new agent, given only the code, the data paths, the neutral question and the pre-registered criteria. No conclusions from this handoff.
   - **Scope:** dataset map, selection, metrics (jumps/hold/T/W), the plant and its identification (incl. Amendment 2's in-sample tuning), bit-exactness, the candidate implementations (D2's opendbc deadzone semantics, C4's causal filter), the tracking metric, the robustness check.
   - Verify every finding independently. Fix agreed defects and re-run what they affect.
   - Record it as a focused review in the root-cause findings.
3. **Step 2: offline D2C4 checks**, each pre-registered as an amendment before running, each reporting jitter, weaving and comfort (§8):
   - (a) **Synthetic tests:** request steps (0.3 and 1.0 m/s²) and sines (0.15–0.6 Hz) at 55+ mph. Overshoot, lag, settling, hold-and-jump inside steps.
   - (b) **Curve entry/exit** on logged curves: curve ratio, peak error, lag.
   - (c) **The 35–55 mph band:** closed-loop identification of an M plant if the data allows (E2–E4 have about 100/150/270 s straight-clean). Otherwise state it as not covered.
   - (d) **Low speed and stop-and-go:** at least quantify how much logged engaged data exists; no claims without a valid model.
   - (e) **Comfort metrics** on logs (§8.3), to establish today's baselines.
   - (f) Re-check torqued/paramsd/lagd restore keys for a CarParams change (D2).
4. **Step 3: implementation design + tests** (car-scoped, GENESIS_G70_2024 only; on `dragal/custom`; no device).
   - **D2:** `steering_angle_deadzone_deg=0.4` in the car port's `configure_torque_tune` call.
   - **C4:** a car-scoped causal desiredCurvature low-pass in the lateral path; define where (V0 controller vs controlsd), the activation boundaries (engage/disengage reset, speed range, lane changes) and the unit tests.
   - Run the checkout's supported tests (CLAUDE.md §4), and replay the logged routes to confirm the source matches the offline harness.
   - Then full QA (round 1 cooperative, round 2 isolated adversarial) before any deployment proposal.
5. **Step 4: on-car A/B** (only after steps 1–3 and the user's explicit authorization of each device action: install, reboot).
   - Write a deployment proposal: concrete change, validation, resource impact, rollback, last known-good config (`c027a92857`).
   - Then an **experiment protocol**:
     - the same road and direction, A (current) and B (D2C4);
     - engaged, hands-off where safe and legal, straight and curved highway sections;
     - phone wheel video + bookmarks;
     - success/failure criteria on jitter, weaving and comfort from §8, fixed beforehand.
6. **Outer docs commit** when the user asks (sessions 8–10 docs are uncommitted).

## 10. Device state and SSH ownership

- No SSH connection open, and none owned by this session.
- The device was last observed offroad and indoors at 2026-10-07 02:24Z.
- Before any device access the user must confirm the current address, the inactive state and the scope (CLAUDE.md §6).
