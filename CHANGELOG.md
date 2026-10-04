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
