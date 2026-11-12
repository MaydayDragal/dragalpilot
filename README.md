# dragalpilot

Independent sunnypilot customization project: source investigation, local log and video analysis, controlled experiments, and carefully validated customizations.

## Layout

| Path | Purpose |
|---|---|
| [CLAUDE.md](CLAUDE.md) | Durable working rules for Claude Code sessions and agents |
| [CHANGELOG.md](CHANGELOG.md) | Dated entry per session |
| [docs/baseline.md](docs/baseline.md) | Exact upstream revision, nature of the `dev` branch, host tooling status |
| [docs/local-storage.md](docs/local-storage.md) | Data root (`E:\DragalPilot`), layout, recording rules |
| [docs/sessions/](docs/sessions/README.md) | Handoff and kickoff documents between sessions |
| [docs/kickoff/Startup.md](docs/kickoff/Startup.md) | Original project kickoff prompt (verbatim) |
| [tools/log-viewer/](tools/log-viewer/README.md) | Standalone HTML rlog viewer: open `log-viewer.html`, drop rlogs, plot any field (jotpluggler-compatible paths and layouts) |
| `sunnypilot/` | Clone of https://github.com/sunnypilot/sunnypilot.git (`dev`). **Gitignored** by this repo, with its own `.git`. Not vendored and not a submodule. |

Logs, videos, datasets, analysis outputs and caches are **never** stored in this repo. They live under `E:\DragalPilot`.

## Status

- **2026-11-12:** the device runs `g70-fingerprint` @ `c4776c4` (branch `sunnypilot/g70-fingerprint`): upstream `dev` @ `d3e1a2f` + the G70 2024 port + the `0x484` fix, AGNOS 19.9, `DisableUpdates=1`. See [docs/findings/2026-11-12-g70-fingerprint-update-drives.md](docs/findings/2026-11-12-g70-fingerprint-update-drives.md). The entries below are the October history.
- Baseline: `dev` @ `0b2c431d3abab630df0a32f53236944855a91aa3` (tag `baseline/dev-20261003`), built from master `a5f44653d7f4`.
- Customization branch `dragal/custom` (local): WIP G70 2024 platform port @ `7e9d0755d9` (focused review done, see docs/findings). Targeted opendbc tests pass and the car's real FW resolves to `GENESIS_G70_2024`. Parked-car rlogs confirm CRC8 checksums and clean CarState and safety rx parsing. First-drive logs support `CAMERA_SCC`. Low-speed behaviour and tune quality are unvalidated. Focused review done (no two-round QA).
- Test environment: WSL 2 + Ubuntu 24.04 (distro disk on the data root). See [docs/baseline.md](docs/baseline.md#wsl-test-environment).
- Device: runs `dragal/custom` @ `7e9d0755d9` (deployed 2026-10-04, `DisableUpdates=1`). See [docs/proposals/2026-10-04-g70-2024-deploy.md](docs/proposals/2026-10-04-g70-2024-deploy.md). First drives 2026-10-04: engaged ~5 min, no faults; see docs/findings/2026-10-04-g70-first-drives.md.
