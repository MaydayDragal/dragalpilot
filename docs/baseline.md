# Source baseline

## Current baseline

| Item | Value |
|---|---|
| Local path | `C:\Users\dre\Documents\DragalPilot\dragalpilot\sunnypilot` |
| Remote | `origin` = `https://github.com/sunnypilot/sunnypilot.git` (fetch and push) |
| Branch | `dev` (tracks `origin/dev`) |
| Commit | `0b2c431d3abab630df0a32f53236944855a91aa3` |
| Commit date | 2026-09-14T15:43:39Z (author `github-actions[bot]`) |
| Commit subject | `sunnypilot v2026.09.14-4885 version: sunnypilot v2026.003.000 (dev) date: 2026-09-14T15:43:39 master commit: a5f44653d7f43ad57fef2f546f3916ec4cbf3c56` |
| Local tag | `baseline/dev-20261003` → the commit above (local only, not pushed) |
| Acquired | `git ls-remote` 2026-10-03T22:14:56-04:00 and again at 22:20:09-04:00 (America/New_York, EDT), both returned `0b2c431d…`. Clone finished 2026-10-03T22:24:26-04:00 with exit 0. Log: `E:\DragalPilot\logs\clone-20261003.log` |
| Clone command | `git -c core.longpaths=true clone --branch dev --recurse-submodules https://github.com/sunnypilot/sunnypilot.git sunnypilot` (run from the outer project folder) |
| Initial status | Clean: `git status --porcelain` printed nothing. 4,120 tracked files. Working tree ~7.7 GB including `.git` (pack 7.16 GiB, because all 249 remote branches were fetched). |

## Nature of `dev` (confirmed from the checkout)

- `dev` is a **bot-generated prebuilt branch**. Its history is a single squashed commit, it has a `prebuilt` marker file at the root and a committed `compile_commands.json`, and it includes 28 compiled artifacts (`*.so`, etc., e.g. `openpilot/common/libparams_c.so` and `.../longitudinal_mpc_lib/c_generated_code/libacados.so`).
- **No submodules.** There is no `.gitmodules`, and `git submodule status --recursive` printed nothing. The dependencies are vendored as plain directories: `msgq_repo/`, `opendbc_repo/`, `panda/`, `rednose_repo/`, `teleoprtc_repo/`, `tinygrad_repo/`. So there is no submodule initialization to resolve.
- Source and tests are present: 662 tracked paths sit under `test/` or `tests/` directories, including `opendbc_repo/opendbc/safety/tests/`.
- Top-level layout: the openpilot/sunnypilot Python tree is under `openpilot/`. Top-level `docs/`, `tools/`, `scripts/` and `system/` sit alongside it.

## Source commit `dev` was built from

The commit message names master commit `a5f44653d7f43ad57fef2f546f3916ec4cbf3c56`. On 2026-10-03 the upstream `master`, `master-dev` and remote `HEAD` all pointed at this commit (2026-09-14T08:33:48-07:00, "mici: add a refresh models button to the models panel (#2018)"). The full history is available locally as `origin/master`.

Submodule commits pinned at `a5f4465` (from `git ls-tree`):

| Path | Commit | URL (from master `.gitmodules`) |
|---|---|---|
| `msgq_repo` | `e7396e76dadbb49e374d4b664ff6bbb43a39bcb0` | https://github.com/sunnypilot/msgq.git |
| `opendbc_repo` | `f95f996f5917dcbbf2e32fe51b606a24cf836af6` | https://github.com/sunnypilot/opendbc.git |
| `openpilot/sunnypilot/neural_network_data` | `03cac2d30e111e0689c0429cb8c1fe6cb5a905af` | https://github.com/sunnypilot/neural-network-data.git |
| `panda` | `74a0adced421e8b7acd728d0f9988ce225423f13` | https://github.com/sunnyhaibin/panda.git |
| `rednose_repo` | `28d4a7f69e80e1c3e0d24ca0733d7daeaeade3d0` | https://github.com/commaai/rednose.git |
| `teleoprtc_repo` | `1aa8fc433bef1519a95c0700c96258c3be6dfb34` | https://github.com/commaai/teleoprtc |
| `tinygrad_repo` | `f6fc4e3f2c3db5fae1e19cbfbc3ad9fc579a12ae` | https://github.com/sunnypilot/tinygrad.git |

**Not verified:** that the vendored directories in `dev` are byte-identical to these submodule commits. The prebuild step may add or remove files.

## Known checkout limitations (Windows host)

- `core.symlinks=false`, so 6 tracked symlinks were checked out as plain-text placeholder files: `docs/assets/comma-logo.png`, `docs/concepts/safety.md`, `openpilot/sunnypilot/selfdrive/car/car_list.json`, `openpilot/system/hardware/comma/agnos.json`, `openpilot/system/hardware/tici/agnos.json`, `system/hardware/tici/agnos.json`. Read their targets with `git cat-file -p HEAD:<path>`.
- Git commands in this checkout should use `-c core.longpaths=true` (set per command, not globally).

## Upstream development guidance (from the checkout)

- `README.md`: pull requests target `master`.
- `tools/README.md`: development and testing are supported on **Ubuntu 24.04** (primary) or macOS. On Windows, use **WSL 2 with Ubuntu-24.04**. Setup is `tools/op.sh setup`, then `source .venv/bin/activate`, then `scons -u`.
- `.python-version`: `3.12.13`. `pyproject.toml`: `requires-python >= 3.12.3, < 3.13`, dependencies locked in `uv.lock`.
- `docs/CONTRIBUTING.md`: PRs must pass CI and describe how they were verified. Simple, well-tested bug fixes are preferred.
- `docs/AI_POLICY.md`: the submitter must understand and test every change. Driving fixes need real evidence (dongle ID, logs, segments). AI assistance must be disclosed with an `Assisted-by:` trailer, e.g. `Assisted-by: Claude`. No AI-generated media.
- Other guides to read when relevant: `docs/SAFETY.md`, `docs/LIMITATIONS.md`, `docs/DEBUGGING_SAFETY.md`, `docs/INTEGRATION.md`, `docs/contributing/architecture.md`, `tools/test_runner.py`.

## Host tooling status (2026-10-03)

| Tool | Status |
|---|---|
| Git | 2.56.0.windows.1 |
| git-lfs | 3.8.0 (installed; the checkout has no `.gitattributes` and uses no LFS) |
| Python | **not installed** (only the Windows Store alias) |
| uv | **not installed** |
| WSL | 2026-10-03: WSL 2 with `Ubuntu-24.04`. See below. |

The upstream tooling does not run on the Windows host itself. It runs in WSL (next section).

## WSL test environment

Set up 2026-10-03 (session 2, after the VM reboot).

| Item | Value |
|---|---|
| Distro | `Ubuntu-24.04` (Ubuntu 24.04.5 LTS), WSL 2, kernel `6.18.40.1-microsoft-standard-WSL2`. 4 vCPU, ~3 GB RAM. |
| Disk | Moved with `wsl --manage Ubuntu-24.04 --move` to **`E:\DragalPilot\cache\wsl\Ubuntu-24.04\ext4.vhdx`**, so the venv, uv/pip caches, apt packages and test clone all live on the data root (native ext4). Nothing remains under `%LOCALAPPDATA%\wsl`. |
| Warning | `wsl` prints "Nested virtualization is not supported on this machine", but the distro boots and runs normally. |
| User | `dev` (default via `/etc/wsl.conf`, `systemd=true`). Password locked. Passwordless sudo (`/etc/sudoers.d/dev`) only because `tools/setup_dependencies.sh` calls `sudo` for udev rules. The VM is dedicated to this project. |
| Packages | apt list copied from `tools/setup_dependencies.sh` (`build-essential`, `libcurl4-openssl-dev`, `git` 2.43, …; gcc 13.3). uv 0.12.23 from the upstream installer. |
| Test clone | `~/src/sunnypilot` (in WSL), cloned with `--single-branch` from the **Windows clone**, remote named `win`. **The Windows clone stays canonical:** commit there, then `git fetch win dragal/custom && git checkout --detach FETCH_HEAD` in WSL. Symlinks are real in this clone (they are placeholders on Windows). |
| Python env | `tools/setup_dependencies.sh` → `uv sync --frozen --all-extras` → `.venv` (Python 3.12.13, ~650 MB), exit 0. Log: `E:\DragalPilot\logs\wsl-setup-deps-20261003.log`. |
| Helper scripts | `E:\DragalPilot\scratch\wsl\*.sh` (run with `sed 's/\r$//' <script> \| bash` inside WSL). |
| ffmpeg | 6.1.1 from Ubuntu apt (installed 2026-10-04 for video review). |
| Panda firmware source | `~/src/panda`: clone of `https://github.com/sunnyhaibin/panda.git`, detached at the pinned `74a0adced421e8b7acd728d0f9988ce225423f13`. Its `board/` and `python/` are identical to the vendored `panda/` in `dev`. |
| Panda firmware build | `E:\DragalPilot\scratch\wsl\build_panda_fw.sh <name> <sunnypilot rev>`: `git archive` of the pinned panda into a git-free dir (version string `DEV-unknown-DEBUG`), opendbc safety from the WSL clone at `<rev>`, toolchain `arm-none-eabi-gcc` 13.2.1 from the venv, DEBUG-signed. **Verified 2026-10-04:** on the unmodified safety it reproduces the shipped `panda_h7.bin.signed`, `main.bin` and bootstub byte-for-byte. Outputs: `E:\DragalPilot\deploy\g70-fw-20261004\`. |
| Safety coverage note | Each libsafety build leaves `tmp*.gcno/.os` files in `opendbc/safety/tests/libsafety/`. Stale ones break gcovr after a line shift in a safety header, so `run_safety_cov.sh` runs `git clean -X` on that folder first. |

**Limitation (confirmed source fact, `dev` @ `0b2c431d`):** the prebuilt `dev` tree has **no `SConstruct`**, and its committed `.so` files are **AArch64** device builds (e.g. `openpilot/common/libparams_c.so`, ELF machine `0xb7`). So on x86, anything that imports `openpilot.common.params` (or other native libs) fails to load. `dlopen` misreports this as "No such file". opendbc car and safety tests are unaffected: libsafety is compiled at test time. Running openpilot-side tests needs a source build from `origin/master` @ `a5f4465`. Not done yet.

## Baseline change log

| Date | Change | Old → New | Reason | Validation |
|---|---|---|---|---|
| 2026-10-03 | Initial baseline | — → `0b2c431d` | Project start (kickoff: latest `dev`) | Remote/branch/SHA/status verified as above |

## Decisions (2026-10-03, user)

- **Customization baseline stays `dev` @ `0b2c431d`**, because it is what is installed on the device. (Not yet confirmed from the device itself.) `origin/master` @ `a5f4465` is a reference for history and submodule commits only.
- **Customization branch:** `dragal/custom`, created from `baseline/dev-20261003` and local only. Current head: see the changelog and the latest handoff.
- **Build environment:** install WSL 2 + Ubuntu-24.04 on this VM (the VM is dedicated to this project). The install was started 2026-10-03. See the changelog for its status.
