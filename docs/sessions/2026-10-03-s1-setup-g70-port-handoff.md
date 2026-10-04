# Handoff: session 1 (2026-10-03): setup + G70 2024 fingerprint/port

Written before a user-approved **VM reboot to finish the WSL 2 install**. All state below was last observed 2026-10-03 ~22:50 EDT. Reconfirm everything after the reboot.

## Objective

Get sunnypilot to recognize and support the user's **2024 Genesis G70**. The device ran in dashcam/MOCK mode because this version has no G70 2024 platform.

## User decisions and instructions (this session)

- Source project: `C:\Users\dre\Documents\DragalPilot\dragalpilot` (GitHub `MaydayDragal/dragalpilot`, `main`). `sunnypilot/` is a gitignored nested clone.
- Data root: `E:\DragalPilot`. Recording timezone: America/New_York.
- Baseline stays `dev` @ `0b2c431d`, because that is what the device runs.
- WSL 2 install approved; the VM is dedicated to this project. The user will reboot the VM when told.
- Commit and push the outer docs to `origin/main` (approved).
- **The 4-step plan is approved:** (1) port G70 2024 onto `dragal/custom`; (2) verify the car's CAN layout from rlogs; (3) run upstream tests + a focused QA review; (4) deploy **only** with a separate user approval of a concrete plan (change, validation, resource impact, rollback).
- Device rlog pull approved and done. The user stated the device is indoors, not in the car, and inactive.
- The user pointed to sunnypilot branch `g70-2024-port-new` as the source of the car-specific port.

## Exact revisions

- sunnypilot clone: `dev` = `0b2c431d3abab630df0a32f53236944855a91aa3` (tag `baseline/dev-20261003`), built from master `a5f44653d7f4`.
- **`dragal/custom` = `392f9b6ea9`** (one WIP commit on the baseline). Working tree clean. Local only, not pushed.
- Reference refs in the clone: `origin/g70-2024-port-new` = `ed8397c6`; `refs/ext/g70-opendbc` = opendbc `cfb743f4095225daddb0b4b060fc2257b58a6e6a` (identical to commaai/opendbc PR #1134).
- Outer repo `main`: see `git log`. Docs commits were pushed through `b9a4c30`, and this handoff's commit follows it.

## Completed work and evidence

1. Setup: clone and baseline verification, `CLAUDE.md`, `README.md`, `docs/baseline.md`, `docs/local-storage.md`, `CHANGELOG.md`.
2. Device inspection, one read-only SSH session: installed software = `dev` @ `0b2c431d`; `CarParamsPersistent` = MOCK/dashcamOnly; VIN (model year 2024) and FW captured. Details: `docs/findings/2026-10-03-g70-fingerprint.md`. Raw output: `E:\DragalPilot\logs\device-fp-inspect-20261003.log`.
3. Source analysis: no exact or fuzzy match to any existing G70 platform. The car's camera and radar FW exactly match the port's fingerprint entry.
4. **rlog pull**, one SSH session, 2026-10-04T02:43Z, device `IsOffroad=1`: 7 `rlog.zst` files staged at `E:\DragalPilot\temporary\device-pull-20261003\`. All sha256 match the device. See `PROVENANCE.md` there. One is 0 bytes on the device (`eb903c3c31--1`); two are small and possibly truncated.
5. **Port (step 1), commit `392f9b6ea9` on `dragal/custom`**, 6 files under `opendbc_repo/opendbc/`:
   - `car/hyundai/fingerprints.py`, `car/hyundai/values.py`: applied cleanly from cfb743f4.
   - `car/hyundai/hyundaican.py`: manual merge, adding `GENESIS_G70_2024` to the LKAS11 LDWS list.
   - `car/torque_data/override.toml`: manual merge into the `# port extensions` section.
   - `sunnypilot/car/car_list.json`: entry **hand-written**; must be checked with `opendbc/sunnypilot/car/platform_list.py` and `sunnypilot/car/tests/test_car_list.py`.
   - `car/tests/routes.py`: added to `non_tested_cars` port extensions (the PR's reference routes are not in CI).
   - **No safety/panda changes.** commaai/panda PR #2045 (adds `0x484` TX) was deliberately NOT included; it would widen the safety TX allowlist and needs separate justification.

## Not done / pending

- **Nothing has been built or tested.** There is no Python or Linux toolchain yet.
- WSL: elevated `wsl --install -d Ubuntu-24.04 --no-launch` ran and exited. `wsl -l -v` → no distributions; Virtual Machine Platform not active; **reboot pending**.
- rlogs not decoded. Route start times and which routes are the G70 are unknown, so nothing is promoted to `recordings/` yet.
- QA: none performed. Step 3 requires at least a focused adversarial review (see CLAUDE.md §5); if reviewer isolation can't be enforced, report it as pending.
- Camera-to-filename mapping is still unverified (`docs/local-storage.md`).

## Open questions and hypotheses

- Hypothesis: the 2024 G70 uses camera-based SCC (SCC11/12 `0x420/0x421` from the camera on bus 2) with CRC8 checksums, matching the port's flags. **Verify from rlog CAN** before trusting the port.
- The port's specs (mass 1769, wheelbase 2.83, steerRatio 12.9 "guesstimate") and torque `[2.7, 2.7, 0.11]` are unvalidated for this car.
- How sunnypilot features (e.g. NNLC fingerprint tests, `openpilot/sunnypilot/...`) treat a new platform: check when the tests run.
- What was the user's "backup option"? It is probably no longer needed.

## Device state and connection ownership

- Device `192.168.98.104` (DHCP, so reconfirm), user `comma`, key `~/.ssh/id_ed25519_dragalpilot` (the public key is on GitHub `MaydayDragal`, and the device fetched it). Host key in `~/.ssh/known_hosts`.
- Last observed: offroad, indoors, inactive. **No SSH connection is open.** There were 2 stale `pts` sessions from 2026-07-28 (tmux), not ours.
- No device changes, installs, param writes, or reboots have been done or authorized beyond read-only inspection and the rlog pull.

## Ordered next steps

1. After the reboot, finish WSL: `wsl -l -v`; if Ubuntu-24.04 isn't installed yet, `wsl --install -d Ubuntu-24.04` (it may prompt for a Linux username and password: ask the user). Keep the sunnypilot working copy for WSL tooling inside WSL's ext4 filesystem or on the Windows path as decided. **Decide and document** where the WSL-side checkout lives and where its caches go (caches → data root, e.g. `/mnt/e/DragalPilot/cache`).
2. In WSL, set up per `tools/README.md` (`tools/op.sh setup`, then `uv`/`.venv`), with caches and temp redirected to the data root.
3. Run the targeted tests on `dragal/custom`: `opendbc/car/tests/test_routes.py`, `test_docs.py`, `opendbc/sunnypilot/car/tests/test_car_list.py` (regenerate `car_list.json` with `platform_list.py` if it differs), `opendbc/car/hyundai/tests/test_hyundai.py`, `opendbc/car/tests/test_fw_fingerprint.py`, the NNLC fingerprint test, and the opendbc safety tests for Hyundai (unchanged, but a regression check). Use the checkout's actual runner (`tools/test_runner.py` / pytest) after inspecting it.
4. Decode the staged rlogs: initData (start time, version), carParams, CAN by bus and address (0x420/0x421 SCC, 0x340 LKAS11, 0x251 MDPS12, 0x484/0x485, checksum style). Write the findings. Promote verified rlogs to `recordings/…`.
5. A fingerprint test using this car's actual FW (from `CarParamsPersistent`) against the patched code: it should resolve to `GENESIS_G70_2024` by exact match.
6. Focused adversarial QA → fixes → then prepare the deployment proposal (step 4) for user approval.
