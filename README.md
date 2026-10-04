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
| `sunnypilot/` | Clone of https://github.com/sunnypilot/sunnypilot.git (`dev`). **Gitignored** by this repo, with its own `.git`. Not vendored and not a submodule. |

Logs, videos, datasets, analysis outputs and caches are **never** stored in this repo. They live under `E:\DragalPilot`.

## Status

- Baseline: `dev` @ `0b2c431d3abab630df0a32f53236944855a91aa3` (tag `baseline/dev-20261003`), built from master `a5f44653d7f4`.
- Customization branch `dragal/custom` (local): WIP G70 2024 platform port @ `5cdfe3c082`. Targeted opendbc tests pass and the car's real FW resolves to `GENESIS_G70_2024`. CAN layout not yet verified from rlogs; no QA yet.
- Test environment: WSL 2 + Ubuntu 24.04 (distro disk on the data root). See [docs/baseline.md](docs/baseline.md#wsl-test-environment).
- Device: one read-only SSH inspection on 2026-10-03 (user-authorized, inactive device). See docs/findings/
