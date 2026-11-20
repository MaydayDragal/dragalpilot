# CLAUDE.md — dragalpilot

Environment facts and standing authorizations for Claude Code sessions in this project. As of 2026-10-08 the project is maintained by Mayday. The previous maintainer's process rules were rescinded at the handoff, and working rules now come from the current developer.

## 1. Layout

- Outer project (this repo, `MaydayDragal/dragalpilot`): `CLAUDE.md`, `README.md`, `CHANGELOG.md`, `docs/`.
- `sunnypilot/`: a clone of `https://github.com/sunnypilot/sunnypilot.git`.
  - It is **gitignored by the outer repo**: not vendored, not a submodule.
  - Its recorded revision is in [docs/baseline.md](docs/baseline.md).
- The sunnypilot `dev` branch is a bot-generated prebuilt branch: vendored deps (no submodules) and committed `.so` binaries.
  - It is built from `origin/master` at the commit named in its commit message (see `docs/baseline.md`).
- **Current (2026-11-20 about 18:20 local time):** `g70-fingerprint` @ `e3f7ac8` on the device (branch `sunnypilot/g70-scc11-filter`; `sunnypilot/g70-fingerprint` on GitHub is still `df21ce2`). Steering: `TorqueControlTune` 1.0 (upstream V1 controller, stock gains), Lateral Jerk on, Enforce on, override 4.5 / 0.07, friction ramp `/data/g70_friction_threshold` = `0.24 0.40 13 18` (0.24 below 13 m/s, 0.40 from 18 m/s), published delay fixed at 0.33 s, request smoothing `0.2 20 25`, controller-only delay `/data/g70_lat_ctrl_delay` = 0.20 s, **low-speed look-ahead `/data/g70_lat_lookahead_low` = `0.12 13 18` (modeld only; not yet driven)**. Highway steering matches the best drive (`d4`) on the afternoon route (`e1`) and is weaker on the morning route with the same settings: compare drives on the same road only. 20-45 mph still hunts (wheel swings of 1 degree or more 9-14 times a minute). **Speed: openpilot longitudinal is on** (`AlphaLongitudinalEnabled` = 1). Its settings, all in `/data` and described in `openpilot/sunnypilot/selfdrive/controls/lib/g70_long.py`: `g70_long_follow` = `0.85 1.25 1.45 1.75` (four gap settings; distance = time x speed + 6 m + extra, verified for every step down to 0.69 s; **0.85 not yet driven**. At 0.69 s the car braked late and harder than the lead, seven times at 3.0 m/s2 or more in three drives; planner timing tweaks replayed through the real planner did not help, so the gap was raised), `g70_long_stop_extra` = `2.0`, `g70_long_stop_speed` = `0.6` (was 1.0, which stopped firmly 3-5.5 m back; **0.6 not yet driven**), `g70_long_start` = `1.2 0.3` (two-stage restart behind a lead; **not yet driven**; the car itself takes 1.0-1.2 s to let go of its standstill hold whatever is asked), and the files `g70_long_engage_any`, `g70_long_engage_main`, `g70_long_no_lead_alert`, `g70_long_cluster_speed`. Screen: four gap bars; the fan readout is off (create `/data/g70_ui_fan` and reboot to show it again). Panda firmware `c9c5f7f0…` (signature `b2c5c4b3758b072d`): HDA11_MFC and LKAS12 blocked in both longitudinal modes, and the main cruise button enters controls when it turns main cruise on. **Engaging openpilot longitudinal from a button the panda does not accept gives a cruise fault** (`d7`); any change to how it engages needs the panda rule checked with the safety tests, which can be built and run on the comma (2026-11-19 cruise-fault findings, section 4). **Do not kill a process on the comma to restart it: the manager does not bring it back; reboot instead.** Not confirmed: whether the cluster shows an AEB warning with openpilot longitudinal. Rollback branch `g70-fingerprint-prev` is `bb68347`. Drive logs can be read on the PC with `tools/drive-eval/pclog.py`; evaluate steering with `sway.py` and speed control with `gap_check.py`, `gap_safety.py`, `gap_speed.py`, `restart_delay.py`, `brake_events.py` + `brake_plot.py`, `long_baseline.py` (reports stay outside the repo). **Replay a planner change on the parked comma before installing it** (`replay_plan_variants.py`): a change recommended from reading the code moved nothing in replay. See [docs/findings/2026-11-20-g70-hard-braking-behind-a-lead.md](docs/findings/2026-11-20-g70-hard-braking-behind-a-lead.md), [docs/findings/2026-11-20-g70-restart-delay-stops-low-speed-steering.md](docs/findings/2026-11-20-g70-restart-delay-stops-low-speed-steering.md) and the changelog.
- **2026-11-16:** `g70-fingerprint` @ `d833479` on the device (it crashed controlsd on engage with the V0 controller; fixed in `77cc8c6`): as below plus an optional steering-delay offset (`/data/g70_lat_delay_offset`, currently 0.15), an optional friction-ramp width (`/data/g70_friction_threshold`, currently 0.28) and the LKAS12 filter narrowed to status 6 / bit 44. Override 4.2 / 0.07. Rollback branch `g70-fingerprint-prev` is `9954fdf`. `espDisabled` blips come from switching the car's drive modes (user, normal). See [docs/findings/2026-11-16-g70-straight-sway-loop-model.md](docs/findings/2026-11-16-g70-straight-sway-loop-model.md); scripts in `tools/drive-eval/`.
- **2026-11-13:** `g70-fingerprint` @ `4525e88` (branch `sunnypilot/g70-fingerprint` in this repo): upstream `dev` @ `d3e1a2f` + the G70 2024 port + the `0x484` fix + the LKAS12 (`0x53E`) Driver Attention Warning fix, each with rebuilt panda firmware. `DisableUpdates=1`. Rollback branches on the device: `g70-fingerprint-prev` (`c4776c4`), `g70-baseline` (`c027a92857`). See [docs/findings/2026-11-13-g70-drives-daw-lkas12.md](docs/findings/2026-11-13-g70-drives-daw-lkas12.md) and [docs/findings/2026-11-12-g70-fingerprint-update-drives.md](docs/findings/2026-11-12-g70-fingerprint-update-drives.md). The host, WSL and storage sections below describe the October VM, not the PC used on 2026-11-12.
- Previous working branch: `g70-baseline` @ `c027a92857` (on the device 2026-10-09 to 2026-11-12, kept there for rollback; pushed to this repo as branch `sunnypilot/g70-baseline`, D2C4 as `sunnypilot/dragal-custom`, base tag `sunnypilot-baseline/dev-20261003`; readable patches in `sunnypilot-patches/`). This is the G70 2024 port with its lateral tune plus the soundd/micd audio gate. Experimental D2C4 commits are on `dragal/custom`.
- Git commands that touch `sunnypilot/` may need `-c core.longpaths=true` per command. It is not set globally.

## 1a. Dates and times

- **Notes use local time** (US Eastern: UTC−5 in winter, UTC−4 in summer). This applies to file names under `docs/findings/`, changelog headings, the "Current" line above and device records, from the evening of 2026-11-19 on.
- The comma, its logs and its route timestamps are in UTC. When quoting a log time, say so (`Z`) or convert it. An evening drive is the next day in UTC.
- Notes written before that are in UTC and marked with `Z`; they were not converted. Two of them are named for the UTC date although the work was the local evening before.
- The comma's clock can be unset after a reboot (it showed 2026-07-28 on 2026-11-19); take the time from the PC then.

## 2. Host environment

- Host: Windows Server 2025 (QEMU VM). Shells: PowerShell 5.1 and Git Bash.
- WSL: Ubuntu-24.04, with its disk at `E:\DragalPilot\cache\wsl\Ubuntu-24.04\ext4.vhdx`.
- See [docs/baseline.md](docs/baseline.md) for tooling status and known gaps, such as the Linux build/test environment.
- CPU: AMD Ryzen 9 9955HX (Zen 5), 6 logical CPUs visible to the VM.
  - Full AVX-512, AVX2, FMA and AVX-VNNI.
  - No AMX and no AVX512-FP16.
- **The VM is dedicated to this project.** Analyses may use all of its compute, memory and storage: 6 logical CPUs and 32 GB RAM, of which WSL sees about 15 GB.
  - Parallelize CPU-bound work across all cores.
  - Prefer parallelization that leaves results bit-identical to the serial method, e.g. independent runs spread across processes and reassembled in order. Check that it does.
  - Note it when parallelizing would change an established method (e.g. an optimizer's update order or search path).

### Second PC (used from 2026-11-16 evening)

- Windows 11, Git Bash and PowerShell 5.1, Python 3.13 with numpy, Pillow, pycapnp and zstandard. No WSL, no `E:` drive, no openpilot tooling. Since 2026-11-20 rlogs can be read on this PC with `tools/drive-eval/pclog.py` (set `CEREAL_DIR` to the checkout's `openpilot/cereal` and `CAR_CAPNP_DIR` to a folder holding `car.capnp`, kept in `Documents\DragalPilot\cache\capnp`); the older extract scripts (`extract.py`, `extract_long.py`) still run on the parked device.
- The checkout path can be long: clone with `-c core.longpaths=true`. `core.autocrlf` is on; the sunnypilot files are LF in the index.
- Device access: its own SSH key under `~/.ssh` (registered on the GitHub account; the device re-fetches keys only when the GitHub username is re-entered). Over USB, SSH goes through `adb forward tcp:8022 tcp:22` (Google platform-tools, not installed system-wide); the USB network interface does not work with Windows. The USB link drops at times, so verify pulls by sha256 and retry. After a reboot the comma can stay missing from `adb devices` for minutes; restart the adb server (`adb kill-server`, `adb start-server`) and wait. Wifi from this PC has not worked: on 2026-11-20 the comma held an address on the PC's network and did not accept connections. See the 2026-11-17 findings §2.
- Data on this PC lives under `Documents\DragalPilot` (`recordings/YYYY/MM/DD/`, `analysis/`), following the data-root layout.

## 3. Storage

- Data root: **`E:\DragalPilot`** (volume `Data1`, NTFS, about 275 GB).
  - Layout, naming and the pre-flight check are in [docs/local-storage.md](docs/local-storage.md).
  - Top-level folders: `recordings/`, `analysis/`, `cache/`, `scratch/`, `temporary/`, `deploy/`, `logs/`, `device-logs/`.
- `device-logs/` may contain device secrets (e.g. tokens in params). Keep them out of the repo and docs.

## 4. Device facts

- Device CPU and logging overhead is safety-sensitive. High-volume debug logging once overwhelmed the device while it was actively controlling the car.

## 5. Standing authorizations

These were granted by the previous maintainer and remain valid:

- **Tool installs:** download and install any tools, dependencies or local vision models that help the project, without asking first.
  - Scope: the Windows VM and WSL. This does not cover the comma device.
- **Deleting files:** files that are no longer useful may be deleted. Examples: staging tars and copies after the promoted files are verified, superseded scratch and temp files.
  - Never delete the only copy of anything.
- **Read-only device pulls:** any read-only pull from the comma device, with no per-pull approval. This covers rlogs, videos (fcamera/ecamera, dcamera when recorded), boot/crash/swag logs, params, system state and diagnostics.
  - It does not cover writes, installs, param changes, deploys or reboots on the device.
