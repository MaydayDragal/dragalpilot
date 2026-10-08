# Handoff: session 10 (2026-10-06/07): check drives verified; steering twitch characterised; root cause modelled

Written 2026-10-07 ~07:50 EDT. Usage: the context counter reports about 170k tokens used in this context window after one earlier compaction; no reliable cumulative figure. Reconfirm everything at the next session start.

## Objective

Make sunnypilot drive the user's 2024 Genesis G70 well. This session:

1. **Verified the session 9 device changes** on 8 check drives:
   - audio fix: works;
   - torqued restore: confirmed.
2. **Characterised the main lateral complaint:** steering-wheel "twitch" on straight roads.
3. **Found its root cause offline** with a stick-slip closed-loop model validated on held-out eras.

## User instructions and decisions (this session)

- **Device pull** (confirmed `.104`, indoors, inactive, no SSH sessions): "pull the videos, rlogs and all other system logs", then verify the audio and torqued changes. Done.
- **Twitch is the primary complaint** (2026-10-06): "constantly correcting or overcorrecting in small amounts" even on straight roads. Wheel videos in `C:\Videos` (filenames = times); bookmarks on the device.
- **"Even pre-restore settings were twitchy. I want to find the root cause. Do #1 [offline stick-slip model] and expand the data you test to earlier routes as well."** Done (see results).
- **Standing (unchanged):**
  - video pulls, tool installs and read-only device pulls are authorized;
  - unneeded files may be deleted;
  - no test re-runs for docs-only commits;
  - durable rules go into CLAUDE.md;
  - device changes and reboots need explicit per-action authorization.
- **Outer docs commit:** not requested; everything since `606c36b` is uncommitted (sessions 8–10).

## Exact revisions

- Baseline `dev` @ `0b2c431d3a…` (unchanged).
- `sunnypilot/` `dragal/custom` @ **`c027a92857`**, clean. WSL clone `~/src/sunnypilot` @ `c027a92857`, clean.
- **Device** (last seen 2026-10-07 02:24Z, offroad):
  - `c027a92857`;
  - LiveTorqueParameters `8a843369…` (8,576 points, valid, laf 3.547; learned on top of the restore).
- **Outer `main`** @ `606c36b` = `origin/main`, with **uncommitted** session 8–10 docs:
  - modified: `CHANGELOG.md`, `CLAUDE.md`, `docs/baseline.md`, `docs/local-storage.md`, `docs/sessions/README.md`, `docs/findings/2026-10-04-g70-tune-0x484-first-drive.md`;
  - new findings: `2026-10-05-*` (3), `2026-10-06-g70-torqued-reconstruction.md`, **`2026-10-06-g70-steering-twitch.md`**, **`2026-10-07-g70-twitch-root-cause.md`**;
  - new proposals: `2026-10-05-soundd-audio-gate-deploy.md`, `2026-10-06-g70-torqued-restore.md` (both now carry check-drive records);
  - new handoff/kickoff pairs for sessions 8, 9 and this one.

## Completed work and evidence

1. **Device pull** (one read-only SSH connection, 2026-10-07 02:24:57–02:31:55Z):
   - routes `0x1e`–`0x25`: 426 rlog/fcamera/ecamera files, all sha256 MATCH, promoted to `recordings/2026/10/06/`; gap `0x21` seg 33 is 0 bytes;
   - diagnostics → `device-logs/2026-10-06_s10_diag/` (902/909 match; the 5 others are files the device was still writing during the pull);
   - staging deleted.
2. **Audio fix verified:** no soundd/micd crash, gate cleared 11–31 s after each start, one early engage correctly refused. **Torqued restore verified:** 7,722 points, laf 3.688 at the first start; G70 fingerprint on all 8 starts. Records in both proposals.
3. **Twitch characterisation** ([findings](../findings/2026-10-06-g70-steering-twitch.md)):
   - **What it is:** a hold-and-jump wheel motion on straight highway (holds of 0.5–1.5 s, jumps of 0.3–0.6°), confirmed on the user's phone videos by a wheel-angle measurement agent (r 0.49–0.90 in 0.7–4 Hz on the `0x22` clips).
   - P and the friction-ramp term carry most of the fast command.
   - It got worse after the restore (jumps 19 → 30/min at highway speed); the original port tune was about twice E3.
4. **Root cause** ([findings](../findings/2026-10-07-g70-twitch-root-cause.md); pre-registered, Amendments 1–3):
   - **Mechanism:** mechanical static friction (the EPS applies the ramping torque while the wheel stays put; breakaway about +30 counts).
   - **Model:** stick-slip plant identified in closed loop on E2+E3. **Passes held-out E1 and E4** at 55+ mph.
   - **Ablations:** the root cause is the combination of steering static friction × V0's error-driven friction-compensation ramp (+P) × small fast jitter in the model's request. Each parameter era only changes its strength.
   - **Candidates:** none passes the pre-registered criteria; every twitch reduction costs some tracking error. Closest is C6 (friction ramp threshold 1.0 + causal 2 Hz request filter): twitch about −57% jumps, −42% T RMS; error +14% / +23% (limit 20%).
5. **New, unresolved:** a 20 Hz pulse in the EPS output torque and a 12–20 Hz wheel vibration while engaged, in all eras. Not locked to MDPS12, LKAS11 or 0x485 sends.
6. **User chose option 2** (mechanism-targeted candidates; Amendment 4, pre-registered). **D2C4 passes all criteria:** the 0.4° `steeringAngleDeadzoneDeg` (existing per-car friction deadzone) + a causal 2 Hz desiredCurvature low-pass.
   - Held-out E1/E4: jumps −57/−52%, T RMS −42/−39%, error +14/+19.4% (limit 20%).
   - Exploratory robustness: the twitch cut is robust (−47…−62% jumps); the tracking cost of +10…+24% is marginal.
   - Request-change-keyed friction (J1/J2/H1) does not help in the model.
   - Findings §7.8.

## Open hypotheses / questions

- **Is the criteria trade-off acceptable?** About +0.01 m/s² of tracking error (≈ 0.02° of steering) for half the twitch. This is the user's call; the pre-registered criteria were not met.
- **Smarter candidates not yet tested:** friction compensation keyed to the direction of the requested motion (setpoint rate / jerk) instead of the error; an error deadband sized to the stiction band; dither. They would need Amendment 4 before running.
- **35–55 mph and low speed:** not modelled.
- **Source of the 20 Hz EPS pulse.**
- **Carried over:** HDA-deselected supervised drive; stop-and-go protocol data; the 0x484 forwarding-rule round.

## Running operations, SSH, device

- **None running.** No SSH connection open. No background agents.
- WSL: only the system's unattended-upgrades helper.
- **Device last observed:** 2026-10-07 02:24Z, `.104`, `IsOffroad=1`, `IsEngaged=0`, `c027a92857`, `DisableUpdates=1`.

## Validation limits and QA stages

- All twitch/root-cause results are offline model evidence at 55+ mph. No closed-loop on-car test.
- **QA:** no focused review of the session 10 analysis/model harness yet. Two-round QA not performed for any change. Nothing proposed for the device.

## Artifacts

- **Analysis:** `analysis/g70-s10-checkdrive-20261006/`, `analysis/g70-twitch-20261006/` (logs, wheel-video, wheel-frames), `analysis/g70-twitch-rc-20261007/` (dataset, step1–4, plant*, drives).
- **Scripts:** `scratch/wsl/sng/s10_*`, `s11_*`, `run_s10*.sh`, `run_s11_dataset.sh`; `scratch/wsl/vidwheel/`; `scratch/device/pull_all_20261006s10.sh`, `extract_verify_20261006s10.sh`; `scratch/promote_20261006s10.ps1`, `provenance_20261006s10.sh`.
- **Logs:** `logs/s10-*.log`, `logs/device-pull-20261006s10.*`, `logs/promote-20261006s10.log`, `logs/user-wheel-videos-20261006s10.sha256`.
- **Disposable:** `temporary/s11-smoke`, `temporary/vidwheel-tmp`, the `temporary/tmp*.so` files, plus the older `s9-*` scratch.

## Ordered next steps

1. **Session start:** reconfirm the workspace and E:.
2. **Ask the user** about D2C4's next steps. Recommended order:
   - (a) a focused adversarial review of the s11 model/harness and the Amendment 1–4 results (CLAUDE.md §5);
   - (b) offline D2C4 checks: synthetic steps / curve entry, the M band (closed-loop identification if data allows), low-speed impact;
   - (c) then a design + tests for a car-scoped implementation (D2 = car port value; C4 = new controller code);
   - (d) an on-car A/B on the same road with explicit authorization.
   - Quicker alternative: an on-car check of D2 alone (still a code change in the car port).
3. **Outer docs commit** when the user asks.
