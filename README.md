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
- No customizations yet. Customization branch `dragal/custom` (from the `dev` baseline, local only).
- WSL 2 + Ubuntu 24.04 install in progress (user-approved; dedicated VM).
- No device access has been authorized or performed.
