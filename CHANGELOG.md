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
