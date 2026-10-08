# CLAUDE.md — dragalpilot

Environment facts and standing authorizations for Claude Code sessions in this project. As of 2026-10-08 the project is maintained by Mayday. The previous maintainer's process rules were rescinded at the handoff, and working rules now come from the current developer.

## 1. Layout

- Outer project (this repo, `MaydayDragal/dragalpilot`): `CLAUDE.md`, `README.md`, `CHANGELOG.md`, `docs/`.
- `sunnypilot/`: a clone of `https://github.com/sunnypilot/sunnypilot.git`.
  - It is **gitignored by the outer repo**: not vendored, not a submodule.
  - Its recorded revision is in [docs/baseline.md](docs/baseline.md).
- The sunnypilot `dev` branch is a bot-generated prebuilt branch: vendored deps (no submodules) and committed `.so` binaries.
  - It is built from `origin/master` at the commit named in its commit message (see `docs/baseline.md`).
- Git commands that touch `sunnypilot/` may need `-c core.longpaths=true` per command. It is not set globally.

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
