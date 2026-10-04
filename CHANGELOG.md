# Changelog

One dated entry per session, including research-only sessions. Times are America/New_York.

## 2026-10-03: Session 1, project setup

- Agreed paths with the user. Source project: `C:\Users\dre\Documents\DragalPilot\dragalpilot` (existing GitHub repo `MaydayDragal/dragalpilot`). Data root: `E:\DragalPilot`. Recording timezone: America/New_York. The nested `sunnypilot/` clone is gitignored.
- Checked the data root: volume `Data1` (NTFS, fixed virtual disk, ~274.75 GB free). The folder was empty. Created the storage layout plus a `logs/` folder, and a write test passed.
- Cloned `https://github.com/sunnypilot/sunnypilot.git` `dev` with `--recurse-submodules`. Clone exited 0. Baseline is `0b2c431d3abab630df0a32f53236944855a91aa3` (2026-09-14T15:43:39Z), tagged locally as `baseline/dev-20261003`. Working tree clean.
- Finding: `dev` is a bot-generated prebuilt, single-commit branch. Dependencies are vendored (no submodules), and it includes compiled `.so` artifacts. It was built from master `a5f44653d7f4`, which is the current upstream `master` and `master-dev`. The full master history is available locally.
- Finding: the upstream toolchain needs Ubuntu 24.04, macOS, or WSL 2. This host has no Python, uv or WSL, so no build or test checks can run yet.
- Wrote `CLAUDE.md`, `README.md`, `docs/baseline.md`, `docs/local-storage.md`, `docs/sessions/README.md`, `.gitignore`, and the verbatim kickoff `docs/kickoff/Startup.md`.
- No runtime behavior changes. No device access. No QA required (documentation and setup only).
- Open: choice of customization baseline (`dev` prebuilt vs `master` source), build environment, camera-to-filename mapping verification, and first investigation goal.
- User decisions: keep `dev` as the baseline (it is what the device runs); install WSL 2 (dedicated VM); commit and push docs; first goal is G70 vehicle fingerprinting.
- Created local branch `dragal/custom` from `baseline/dev-20261003`. Generated a dedicated SSH key `~/.ssh/id_ed25519_dragalpilot` (private key stays in the user profile, never in project docs).
- User pointed to sunnypilot branch `g70-2024-port-new`: it pins opendbc `cfb743f4` (identical to PR #1134). Fetched for reference; dry-run apply on `dev` gives 2 clean files and 2 context-only conflicts. No source changes made.
- Device inspection (user-authorized, device inactive, one read-only SSH session, 22:35 EDT): installed software is `dev` @ `0b2c431d` (matches baseline). Fingerprint result was MOCK/dashcamOnly. VIN and camera/radar/EPS firmware were captured, and rlogs exist on the device. See [docs/findings/2026-10-03-g70-fingerprint.md](docs/findings/2026-10-03-g70-fingerprint.md).
- Source finding: no exact or fuzzy match to any G70 platform in the pinned opendbc. The firmware exactly matches the unmerged draft commaai/opendbc PR #1134 (`GENESIS_G70_2024`, CAN, CAMERA_SCC + CHECKSUM_CRC8). Its panda dependency #2045 (unmerged) widens the safety transmit allowlist (`0x484`).
- WSL install: elevated `wsl --install -d Ubuntu-24.04 --no-launch` ran and exited. No distribution installed yet; Virtual Machine Platform is not active, and a VM reboot is likely needed (awaiting user authorization).
- rlog pull (approved; device offroad at 02:43Z, one SSH session): 7 rlogs staged at `E:\DragalPilot\temporary\device-pull-20261003\`, all sha256 verified against the device. No qlogs, no video.
- Step 1 port: `dragal/custom` @ `392f9b6ea9` adds the `GENESIS_G70_2024` platform (adapted from opendbc cfb743f4 / PR #1134), plus sunnypilot `car_list.json` and `non_tested_cars` entries. No safety changes. Untested (no toolchain yet).
- Session closed with handoff and kickoff `docs/sessions/2026-10-03-s1-setup-g70-port-*` before the VM reboot for WSL. QA: none yet. Usage reporting is not available to me, so no token figure is recorded.

## 2026-10-03: Session 2, WSL environment and G70 port tests

- Confirmed after the reboot (~23:00 EDT): outer repo clean at `d809131`; `sunnypilot/` on `dragal/custom` @ `392f9b6ea9`, clean; data root `E:` UniqueId matches, write probe OK, ~274.68 GB free.
- WSL: installed `Ubuntu-24.04` (WSL 2; it prints a nested-virtualization warning but runs) and moved its disk to `E:\DragalPilot\cache\wsl\Ubuntu-24.04\`. Created user `dev` (password locked; passwordless sudo inside WSL, needed by the upstream setup script's udev step). Installed the upstream apt list and uv 0.12.23. `tools/setup_dependencies.sh` exited 0 (Python 3.12.13). A first run hung on a `sudo` password prompt and was stopped. Details: `docs/baseline.md` § WSL test environment.
- Test clone `~/src/sunnypilot` in WSL, fetched from the Windows clone (canonical).
- Targeted tests: on `392f9b6ea9`, `test_hyundai` failed (`GENESIS_G70_2024` has no EPS FW entry). Fixed in `dragal/custom` @ **`5cdfe3c082`** by adding the car's captured EPS FW. On `5cdfe3c082`, car_list, routes, docs, hyundai, fw_fingerprint and the Hyundai safety tests all pass. The NNLC fingerprint test was not run: the `dev` prebuilt has AArch64 `.so` files and no `SConstruct`.
- FW replay of the car's real `carFw`: baseline gives no match; candidate gives an exact match to `GENESIS_G70_2024`. See the findings doc.
- No device access. QA: none yet (focused adversarial review pending).
- Pushed outer `main` `d809131..7cac8f6` (user-approved).
- rlog decode and offline replay ([docs/findings/2026-10-03-g70-rlog-can.md](docs/findings/2026-10-03-g70-rlog-can.md)):
  - All 3 routes are the parked G70 (no driving).
  - The LKAS11 checksum is CRC8 on 100% of frames (supports `CHECKSUM_CRC8`).
  - Buses 0 and 2 are passthrough, so the SCC origin (`CAMERA_SCC`) can't be determined from these logs.
  - The candidate's CarState had `canValid` throughout, and the panda safety replay had 0 invalid rx out of ~1.53M.
- Promoted `00000000--eb903c3c31` (17:54:05 EDT) and `00000001--ed6394b42a` (17:55:51 EDT) to `recordings/2026/10/03/`, sha256 verified. `00000002--3ea363e27d` has an unknown start time.
- Classic CAN vs CAN-FD: buses 0 and 2 are classic CAN (frames ≤8 bytes, the panda never enables FD). Bus 1 is a separate CAN-FD network that the port doesn't use.
- Pushed `7cac8f6..0f024f7` (user-approved).
- Storage convention (user delegated the choice): undated routes go to `recordings/undated/<route-id>/`, with inferred time bounds in metadata. Filed `00000002--3ea363e27d` there, sha256 verified. All 7 rlogs are now promoted.
- Focused adversarial review of `dragal/custom` @ `5cdfe3c082` started (single reviewer; it was given only the diff, neutral requirements and the raw evidence, not these findings).

## 2026-10-04: Session 2 (continued past midnight), focused review

- Review complete ([docs/findings/2026-10-04-g70-port-focused-review.md](docs/findings/2026-10-04-g70-port-focused-review.md)): no blockers or majors, 6 minor/info findings, all verified.
- Fixed: the reference-route comment in `routes.py` now cites PR #1134 (`dragal/custom` @ **`f9325699ed`**, comment-only). Targeted tests re-run on `f9325699ed`: all pass.
- User decisions:
  - Alpha long stays as upstream (no `UNSUPPORTED_LONGITUDINAL`). The user won't enable the toggle.
  - The car has Harness F, so the docs entry is now `hyundai_f` (`dragal/custom` @ **`7e9d0755d9`**, docs-only).
  - User preference: no targeted test re-runs for docs-only commits.
- Deployment proposal drafted: [docs/proposals/2026-10-04-g70-2024-deploy.md](docs/proposals/2026-10-04-g70-2024-deploy.md). **Not authorized.**
  - Basis: confirmed updater and launcher behaviour (`updated.py`, `launch_chffrplus.sh`) and the cache rules in `fingerprint()`.
  - Artifact: a git bundle of `7e9d0755d9` (sha256 `bf73cc…3d16`). The install/rollback dry run passed in WSL.
  - Device-load baseline from existing rlogs (CPU mean 53–82%, p95 80–88%). New data-root folder `deploy/`.
- **User approved the deployment plan** and the `DisableUpdates=1` param write; reboots and stages are confirmed at the time. The user will run the in-car stages alone, so an in-car checklist was written. The Stage 0 install script was generated and simulated in WSL.
- **Deployed (Stage 0), 2026-10-04 ~00:27–00:29 EDT** (user-authorized; device at `.104`, confirmed inactive and indoors, no other SSH session):
  - Installed `dragal/custom` @ `7e9d0755d9` from the bundle (hash verified) and set `DisableUpdates=1`.
  - A guarded reboot followed. The post-boot check confirmed `GitCommit=7e9d0755d9`, the updater not running, and the staged baseline update not installed.
  - Three sequential SSH connections (install, reboot, post-check), never concurrent. Record: `docs/proposals/2026-10-04-g70-2024-deploy.md` § Deployment record.
- Next: the user runs the in-car checklist (drive not engaged → closed-area engagement → data drives). Afterwards, an rlog pull and analysis.
- Session 2 closed with handoff/kickoff `docs/sessions/2026-10-04-s2-wsl-tests-deploy-*`. QA: focused review done; two-round QA not performed. Token usage reporting not available.

## 2026-10-04: Session 2 (continued), first drives analysis

- The user's partner drove with the port (00:31 and 00:36 EDT). The user reports a successful engagement and a micd/soundd failure (known sunnypilot build bug, per the user) that needed a restart.
- rlog pull (user-confirmed: device at .104, offroad, indoors, no other SSH session): one SSH session at 13:28Z, 14 rlogs from 2 routes, all sha256 MATCH. Promoted to `recordings/2026/10/04/`.
- Findings ([docs/findings/2026-10-04-g70-first-drives.md](docs/findings/2026-10-04-g70-first-drives.md)):
  - Fingerprint exact. **`CAMERA_SCC` supported:** SCC appears on bus 2 with the relay engaged.
  - ~304 s engaged at 6-72 mph with no steer faults, no saturation, and no clear oscillation (preliminary).
  - Safety replay with real TX: no unsafe TX. The 9 blocked CANCEL buttons on route 3 are explained.
  - CPU stays within baseline. Low-speed behaviour and tune quality are still unvalidated.

## 2026-10-04: Session 3, morning drives: steering tune and hands-on warnings

- Workspace confirmed: outer `main` @ `5d57a93`, clean, nothing unpushed; `sunnypilot/` `dragal/custom` @ `7e9d0755d9`, clean; data root UniqueId OK, ~269 GB free.
- User report: stage C clean. Stage D: steering ping-pongs (oversteers into curves, then corrects), a few "driver engagement" alerts, micd/soundd crash again.
- Device access (user-authorized to connect and download logs and videos; device at .104, offroad, indoors, no other SSH session):
  - Three sequential read-only SSH sessions (listing; pull; steering params). No device changes.
  - Pulled 3 new routes (`00000005`–`00000007`, 09:47–10:25 EDT): rlogs + `fcamera`/`ecamera`, 114 files, all sha256 MATCH. Promoted to `recordings/2026/10/04/` with provenance.
- Camera-to-filename mapping verified against `loggerd.h` and recorded in `docs/local-storage.md`.
- Findings ([docs/findings/2026-10-04-g70-drives-tune.md](docs/findings/2026-10-04-g70-drives-tune.md)):
  - The device runs `LatControlTorqueV0` (source fact).
  - `torqued` estimates latAccelFactor ~4.0–4.5 and friction ~0.07, vs the port's 2.7 / 0.11, and it can never exceed 3.51 because of its ±30% clip (source fact). Curve data agrees (roll-corrected ~3.5–4.7). This is consistent with over-strong feedforward → overshoot and correction.
  - `paramsd` steerRatio ~14.1 (port 12.9); `lagd` delay ~0.17 s.
  - The "engagement" alerts did not come from sunnypilot: no DM alerts, no openpilot hands-on requests. The stock camera raised 4 LFA hands-off warnings while openpilot steered. The path to the cluster is unconfirmed (related to excluded panda PR #2045).
  - Real panda: no faults, 0 invalid rx, ≤4 blocked tx per route; no steer faults. CPU within baseline.
- No code changes. QA: not applicable (analysis only). A tune change will be proposed as a separate bounded change.
- Pushed outer `main` `5d57a93..27dc28c` (user-approved).

## 2026-10-04: Session 3 (continued): tune, 0x484 safety change, firmware build, review

- User: the 4 camera hands-off times match their alerts. They supplied a wheel video (~09:55); it was filed with route 6 and aligned approximately with the logs (curve-entry overshoot +22% at 09:54:3x). Decisions:
  - proceed with the tune;
  - push approved;
  - **bring in the upstream panda safety change** (commaai/panda#2045) for this car.
- `dragal/custom` (local, not pushed), on top of the deployed `7e9d0755d9`:
  - `c895200ecb`: torque `[4.0, 2.7, 0.07]`.
  - `2623b19329`: steerRatio 14.1.
  - `92e72004ac`: hyundai camera-SCC (non-long) TX table gains `{0x484, 0, 8, .check_relay = true}`, which blocks forwarding of the camera's HDA11_MFC; test expectations updated.
  - `d2accb8980`, `c1806292fa`, `82f58a9a8c`: harness `test_tx_hook_on_wrong_safety_mode` no longer compares a class with its own parameterized variants that have an identical TX list.
  - `cb66129698`: rebuilt `panda_h7.bin.signed` (sha256 `206ea19c…`).
- Source facts:
  - The safety code runs in the panda firmware, which `dev` ships prebuilt and DEBUG-signed.
  - `pandad` flashes on signature mismatch at start.
  - The firmware build reproduces the shipped binary byte-for-byte on unchanged code.
- Tests @ `82f58a9a8c`, all pass: targeted car tests, full safety suite + 100% coverage, MISRA. Also:
  - Negative check: removing the 0x484 line fails the camera-SCC fwd/relay tests.
  - `test_models` on the KONA_2022/KONA_EV_2022 reference routes: 14 OK.
  - New safety replayed over all 5 G70 drives: no relay malfunction, 0 invalid rx.
- **Focused adversarial review** ([findings](docs/findings/2026-10-04-g70-tune-0x484-focused-review.md)):
  - No blockers.
  - 1 major: relay-malfunction exposure from `check_relay`; accepted with the replay and Kona evidence.
  - 2 small fixes applied.
  - Two-round QA not performed.
- Deployment proposal: [docs/proposals/2026-10-04-g70-tune-0x484-deploy.md](docs/proposals/2026-10-04-g70-tune-0x484-deploy.md). **Not authorized yet.** No device access since the morning pull.
- WSL: installed ffmpeg; cloned the pinned panda source (see `docs/baseline.md`).
- Pushed outer `main` `27dc28c..16d280c` (user-approved).
- **Deployed 2026-10-04 ~11:31–11:34 EDT** (user-approved plan and reboot; device `.104`, inactive, indoors, no other SSH session):
  - WSL dry run passed.
  - One-connection install of `dragal/custom` @ **`82f58a9a8c`** (bundle sha256 verified, ff-only).
  - Guarded reboot; on boot `pandad` flashed the panda (signature `599ef38d…` → `5b8d2b33…`, "Done flashing", no mismatch).
  - Post-boot read-only check OK.
  - Record: `docs/proposals/2026-10-04-g70-tune-0x484-deploy.md` § Deployment record.
  - Next: the user's drive per the experiment definition, then an rlog pull and before/after analysis.
- User decision: the next round of enhancements includes a Hyundai-specific forwarding rule. It blocks the camera's 0x484 without a `check_relay` entry, so there's no relay-malfunction watch on 0x484, closer to the original commaai/panda#2045. It replaces the current `check_relay` entry (needs safety code, tests, coverage, review, firmware rebuild). The user is now driving to test the deployed `82f58a9a8c`.

## 2026-10-04: Session 3 (continued): first drive after the deployment

- User: subjectively ~75% better; some ping-pong and curve oversteer remain; one takeover at a sharp curve (steering limit). The user considers it expected; not investigated.
- Pull: device `.104`, offroad, indoors, no other SSH session (user-confirmed). One listing session and one pull session (16:30Z): routes `00000008` (11:41 EDT, 34 min) and `00000009` (12:19 EDT). 40 rlogs, all sha256 MATCH, promoted.
- Findings ([docs/findings/2026-10-04-g70-tune-0x484-first-drive.md](docs/findings/2026-10-04-g70-tune-0x484-first-drive.md)):
  - **Every tune criterion met.** Curve actual/desired 1.07 → 1.007. Integrator opposing feedforward 71–100% → 58%. 0.5–3 Hz error share above 25 m/s 0.54–0.70 → 0.28. Mean error 0.064 → 0.058. No steer faults. torqued now estimates ~4.2 (can apply it itself when valid). The slow (~0.1 Hz) lane wander is unchanged, which suggests the path/planner level (hypothesis).
  - 0x484: the camera still raises its hands-off state internally, but it is no longer forwarded. No relay malfunction (real panda and replay).
  - New: a sticky `interruptRateCan2` panda fault from a ~3 s startup error burst on bus 1 (unused CAN-FD network) while still in elm327; never repeats while driving. Present on both new-firmware routes, absent before. Cause unknown; no control effect observed. Watching.
- User confirmed: no dashboard "grasp not detected" warning on the drive after the change. Pushed `16d280c..8786028` (user-approved).
- Next task (user decision): a fresh session investigates the slow (~0.1 Hz) lane drift. Session 3 closed with handoff/kickoff `docs/sessions/2026-10-04-s3-drives-tune-0x484-*`. QA: focused review done for this round's code; two-round QA not performed. Token usage reporting not available.
- Pushed `8786028..3d0828f` (user-approved). Deleted staging folders `temporary/device-pull-20261004{,b,c}` (~7.1 GB, user-approved) after re-verifying all 168 files against `recordings/`. Device manifests moved to `E:\DragalPilot\logs\device-pull-20261004*.remote.sha256`; provenance pointers updated.

## 2026-10-04: Session 4, lane-drift investigation (rlogs only)

- Workspace confirmed:
  - outer `main` = `origin/main` @ `3d0828f`, clean;
  - `sunnypilot/` `dragal/custom` @ `82f58a9a8c`, clean;
  - WSL clones `82f58a9`/`74a0adc`, clean;
  - data root UniqueId OK, write probe OK, ~257.5 GB free.
- No device access.
- Findings ([docs/findings/2026-10-04-g70-lane-drift.md](docs/findings/2026-10-04-g70-lane-drift.md)):
  - **Model:** no downloaded bundle. Stock `modeld` runs the built-in default model (`mici`, no chestnut).
  - **Calibration:** stable (pitch ~1.2°, yaw ~−1.1°, height 1.20 m).
  - **Source fact:** `CameraOffset` and `PlanplusControl` are read only by `modeld_v2`, so they have no effect in this configuration.
  - **Signs (GPS-checked):** positive `desiredCurvature` = right turn; model y is right-positive.
  - **Correction:** the "~0.1 Hz" wander was the lower edge of the search band. The lane-offset spectrum has no peak.
  - Road curvature explains 64–82% of the offset variance. The car sits ~0.25–0.4 m toward the inside of a 1 km curve, plus a static ~0.15–0.19 m left bias of the device.
  - The motion is real (the lane lines move together, kinematically consistent), and the model plans it.
  - The car executes the plan: curvature tracking gain 1.02–1.08, phase within ±2.5° at 0.05–0.25 Hz.
  - Hypothesis: the model's path choice (curve-cutting), not the controller.
- New scripts: `E:\DragalPilot\scratch\wsl\{model_calib_identity,lane_drift_extract,lane_drift,lane_drift_spectrum,sign_check_gps}.py`. Outputs in `E:\DragalPilot\analysis\g70-lane-drift-20261004\`.
- No code changes. QA: not applicable (analysis only).
- Options for the user: a manual reference drive, measure the device mount offset, or a model-choice proposal. Controller changes are not indicated for this symptom.
- User input:
  - The drift is unusual and noticeable, and worst in slow stop-and-go traffic. The user will record engaged and manual logs there.
  - The device is mounted at the windshield centre (±3 mm).
  - Stay on the default model for now.
- Model list from the device's cache (77 bundles): none brand-specific. The web search found no Hyundai-tuned model.
- Existing data has only ~155 s engaged below 10 m/s, and the lane lines are rarely confident there. The user asked about calming the curve-inside push downstream of the model; the answer and options were given in chat, with no change made.
- 25–30 mph vs highway, from today's logs:
  - Only 54 s engaged at 25–30 mph, all in brief passes (≤ 17 s windows); 8 s left after the clean-data filters on the new tune.
  - Fast band (0.3–3 Hz): no more oscillation at low speed than on the highway (sway 0.19 vs 1.07 cm).
  - Slow band (< 0.3 Hz): can't be measured from these passes.
  - Needs a dedicated low-speed drive (engaged + manual).
- `torqued` validity (source facts + bucket reconstruction, which matches the logged totals within 0.2%):
  - Total points are sufficient. The limit is the outermost negative-torque bucket: 23/100, filling at ~49 per engaged highway hour, so ~1.5–2 more hours of similar driving above 34 mph (road-dependent).
  - Once valid, it moves latAccelFactor 4.0 → ~4.2 gradually (time constant ~4–20 min).
  - Below 15 m/s it learns nothing.
- User decisions and standing authorizations (saved to memory):
  - Pull and analyze all comma 4 videos at any time (the CLAUDE.md §6 SSH, IP and state mechanics still apply).
  - Install helpful tools, dependencies and local vision models on the host or WSL (data on E:; the device is not covered).
  - The conflict with CLAUDE.md §0.3 was flagged to the user.
- Low-speed drive protocol written into the lane-drift findings: a curvy 30–35 mph road first, then stop-and-go, then a curvy 45–55 mph road; engaged then manual on the same stretch.
- Wrote handoff `docs/sessions/2026-10-04-s4-lane-drift-handoff.md` and an optional kickoff for a video lane-position check (`2026-10-04-s4-video-lane-check-kickoff.md`). QA: not applicable (analysis only). Token usage reporting not available.
- The user reported the low-speed drives done. Pushed outer `main` `3d0828f..20f4242` (session 3's final commits `c9bbd13` and `20f4242`, doc-only, made at 12:50 after this session's start snapshot; pushed together with this request and inspected after the push) plus this session's docs commit (user-approved).
- Added kickoff `docs/sessions/2026-10-04-s4-lowspeed-drives-kickoff.md` and set the order:
  1. The low-speed session runs first and does the single device pull: the new drives' rlogs + videos, plus videos of routes 3, 4, 8, 9.
  2. The video lane-check session starts after that pull and runs offline in parallel.
  - Both sessions follow shared-file and commit etiquette.

## 2026-10-04: Session 4b, low-speed drives (pull and analysis)

- Workspace confirmed:
  - outer `main` = `origin/main` @ `6afe57e`, clean;
  - `sunnypilot/` `dragal/custom` @ `82f58a9a8c`, clean;
  - data root UniqueId OK, write probe OK, ~265 GB free;
  - no local ssh/scp processes.
- **Device pull** (user-confirmed: `.104`, not driving, indoors, no other SSH session). One read-only SSH connection, 18:49:57Z–18:56:09Z. Listing, on-device sha256 and the tar stream all ran in that connection (`IsOffroad=1` checked by the script). Script: `E:\DragalPilot\scratch\device\pull_lowspeed_20261004.sh`; log: `E:\DragalPilot\logs\device-pull-20261004d.log`.
  - New routes `0000000a`–`0000000e`: rlog + fcamera + ecamera.
  - Videos (fcamera/ecamera) for routes 3, 4, 8, 9. All of them were still on the device. Segment 9 of route 4 and segment 4 of route 9 are 0-byte files, kept as received.
  - 258 files, 7.88 GB: all sha256 MATCH after extraction and after promotion (move). No connection is open.
  - Promoted to `recordings/2026/10/04/` with provenance:
    - `13-51-50__0000000a`, `14-04-39__0000000b` (engaged);
    - `14-16-31__0000000c` (manual, openpilot on);
    - `14-28-03__0000000e` (manual, `OpenpilotEnabledToggle=0`, so dashcam mode / `noOutput` by design, card.py L133–138).
  - `0000000d` (8 s, no GPS fix, unsynced clock) is in `recordings/undated/`, bounded to 14:27:22–14:28:04 EDT.
  - The staging folder `temporary/device-pull-20261004d/` still holds `pull.tar` (7.9 GB duplicate). It will be deleted only with user approval.
- Analysis ([docs/findings/2026-10-04-g70-lowspeed-drives.md](docs/findings/2026-10-04-g70-lowspeed-drives.md)). By GPS, the four drives cover the same loop: engaged `0a`/`0b`, manual `0c`/`0e`. Sections: 25–30 mph without confident lane lines; 30–35 mph with lines; 35–55 mph; highway.
  - **Controller at 25–35 mph:** it follows the model's plan in the slow band (gain 0.95–0.97, phase −7°, coherence 0.99). The fast-band sway is within the range of the manual runs. There's no sign of low-speed oscillation from the higher KP.
  - **Slow-band path difference** (lane-line independent, odometer + GPS aligned):
    - With lane lines, and on the highway, engaged differs from the human no more than the two human runs differ from each other.
    - At 25–30 mph without lines, it differs 1.06–2.0× more. The two engaged runs agree closely (0.075 m), so this is a repeatable model path choice.
    - The largest difference is 0.4–0.7 m further left than the human, where a left-turn bay opens on a road with no right edge line (video context, approximate alignment).
    - There is no extra curve-cutting relative to the human at low speed.
  - Stop-and-go behind a lead is essentially absent from the data, so the main complaint is still not covered.
  - Where lines are confident, the human sits 5–8 cm left of centre and engaged −4…+1 cm. The curve shift vs a human is inconclusive (too little data).
  - `torqued`: still not valid (calPerc 70). The limiting bucket is at 38/100, so roughly 1.3 h more highway driving.
  - Bus-1 start-up burst: on every route since the firmware change. The sticky `interruptRateCan2` bit is set on some boots only (0c, 0d→0e), depending on the peak rate.
  - Route 0b's safety-replay "blocked" count is a replay artifact: the real panda blocked 0 in Hyundai mode.
  - No steer faults; CPU within baseline.
- Scripts: `E:\DragalPilot\scratch\wsl\`.
  - New: `lowspeed_timeline.py`, `lowspeed_drives.py`, `s4b_*.py`.
  - `lane_drift_extract.py` gained lead and steer-torque fields; the old version is kept as `.session4a.py.bak`.
  - Outputs: `E:\DragalPilot\analysis\g70-lowspeed-20261004\`. Logs: `E:\DragalPilot\logs\s4b-*.log`.
- No code or device changes. QA: not applicable (analysis only). Recommendation: no software change. Next data: stop-and-go engaged + manual, and the user's description of where the swing is felt.
- **Follow-up, the user's weave** (~3 s per cycle, the wheel visibly moves, a few inches, occasional, no specific places). It matches a steering-loop effect at 0.3–0.6 Hz, not the slow path difference. Analysis (`s4b_loop_xfer.py`, `s4b_weave.py`):
  - In 0.3–0.6 Hz, the car's motion is 1.05–1.9× the requested lateral accel, lagging 24–48°, at all speeds, before and after the tune. Two links contribute:
    - controller/EPS 0.96–1.38×;
    - vehicle yaw vs the steering-angle model 1.04–1.35×.
  - The control-error spectrum peaks at 0.30–0.40 Hz on route 8 and on 0a/0b above 35 mph.
  - The tune fixed only the low-frequency over-torque.
  - Source fact: V0's error = current desired − measurement, so it contains the actuator delay (`latcontrol_torque_v0.py` L79–92). Upstream v1 uses the delayed setpoint.
  - The `EnforceTorqueControl` toggle that selects v1 also changes the torque tune and `torqued` behaviour.
  - Hypothesis: a lightly damped steering loop.
  - The earlier "no software change" recommendation is superseded for the weave.
  - Proposed: offline plant identification + closed-loop simulation (V0 / V0 with a delay-free error / v1) with criteria, before any device change. Not started; user decision.
- Before a user-requested VM reboot (~15:45 EDT):
  - No background processes were running; no SSH connection is open.
  - Wrote handoff/kickoff `docs/sessions/2026-10-04-s4b-lowspeed-weave-*` and updated the sessions index.
  - Docs are uncommitted, pending the user's decision. QA: not applicable (analysis only). Token usage reporting not available.

## 2026-10-04: Session 5, video check of the lane-position findings (parallel to 4b)

- Workspace confirmed at start (`main` @ `6afe57e`, `sunnypilot/` `dragal/custom` @ `82f58a9a8c` clean, data root UniqueId OK) and again after the user's VM reboot. The VM was resized to 6 vCPU / 32 GB; WSL now sees 6 CPUs and ~16 GB (default, no `.wslconfig`). No device access.
- Videos: routes 6/7 from session 3; route 8 from session 4b's pull (`device-pull-20261004d`, all sha256 MATCH, promoted by 4b).
- Frame alignment verified: `modelV2.frameId` → `narrowRoadEncodeIdx` → `fcamera.hevc` frame. 1200/1200 per segment; every model frame on routes 4 and 6–9 maps.
- New classical lane-marking measurement, independent of the model: bird's-eye ridge filter + joint parallel-line fit, using the pinned `mici`/os04c10 intrinsics and the logged calibration.
  - A hand check on random frames found a concrete-seam false detection (v1) → seam suppression (v2), and everything was re-run.
  - v2 hand check: stripe-centre error RMS ≈ 1.3 cm, max 2.6 cm.
- Findings ([docs/findings/2026-10-04-g70-video-lane-check.md](docs/findings/2026-10-04-g70-video-lane-check.md)), routes 6/7/8, eligible highway frames:
  - Lane centre at 12 m: video − model **+0.4 to +0.7 cm**.
  - Device **0.14–0.20 m left** of centre on straights, by both methods.
  - Curve-inside shift confirmed: at x = 0 vs Kalman curvature, video 0.40/0.39/0.23 vs model 0.40/0.37/0.24 m per 1/1000 m.
  - Slow lane-position variation seen by both methods (correlation 0.90–0.97, lag 0).
  - The model draws its lines 6–9 cm inboard of the paint centres on both sides (its lane is 0.14–0.16 m narrower). The centre is barely affected.
  - Conclusion: the bias and curve shift are real relative to the paint, i.e. the model's path choice, not perception. The camera and calibration are shared with the model, so the camera's lateral position in the car is not checked.
- The 24 engaged low-speed windows (routes 4, 6–9), described from video:
  - intersections, turns, turn-bay openings and unmarked residential streets; none is stop-and-go;
  - both lines confident < 50% of the time in 11 of 24;
  - with a close lead and weak lines, the model's lines bend toward the lead (observation).
- Tools: a separate WSL venv `~/venvs/vid` (OpenCV 5.0.0, numpy 2.5.3, scipy 1.18.1, matplotlib; the checkout `.venv` is untouched). Scripts `E:\DragalPilot\scratch\wsl\vid\`, outputs `E:\DragalPilot\analysis\g70-video-lane-20261004\`, logs `E:\DragalPilot\logs\vid-*.log`.
- No code or device changes. QA: not applicable (analysis only). Handoff/kickoff `docs/sessions/2026-10-04-s5-video-lane-check-*` (the kickoff is an optional follow-up; 4b's remains the main thread). Token usage reporting not available.
