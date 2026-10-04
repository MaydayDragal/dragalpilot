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
