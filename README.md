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
| [tools/live/](tools/live/README.md) | Light live steering reader over ssh / USB (run only with the car off so far) |
| [tools/panda-fw/](tools/panda-fw/build_fw.sh) | Panda firmware build script for the Windows PC (reproduces the shipped firmware byte for byte) |
| `sunnypilot/` | Clone of https://github.com/sunnypilot/sunnypilot.git (`dev`). **Gitignored** by this repo, with its own `.git`. Not vendored and not a submodule. |

Logs, videos, datasets, analysis outputs and caches are **never** stored in this repo. They live under `E:\DragalPilot`.

## Status

- **2026-11-19 (evening):** the device runs `g70-fingerprint` @ `5ad67b7`: openpilot longitudinal with four gap settings (0.75–1.75 s) shown as four bars on the cluster and the comma screen, engagement from the cruise button or either toggle, the set speed matched to the cluster, an earlier stop request at low speed, and panda firmware that accepts the cruise button. A cruise fault on the way there is written up, with the safety tests now run on the comma. See [docs/findings/2026-11-19-g70-openpilot-longitudinal-cruise-fault-gap-ui.md](docs/findings/2026-11-19-g70-openpilot-longitudinal-cruise-fault-gap-ui.md).
- **2026-11-19 (late):** the device ran `g70-fingerprint` @ `87e6a9e`: V1 torque controller with a 0.20 s controller delay and a 0.40 friction ramp (the first setup without either the highway ping-pong or the wobble), and openpilot longitudinal switched on with four gap settings (1.05–1.75 s), 2 m of extra distance to a lead and engagement from either toggle. The longitudinal settings are not yet driven. See [docs/findings/2026-11-19-g70-friction-ramp-openpilot-longitudinal.md](docs/findings/2026-11-19-g70-friction-ramp-openpilot-longitudinal.md).
- **2026-11-19 (early):** the device ran `g70-fingerprint` @ `ee06954`: V1 torque controller with feedback gain 0.6 and a 0.10 s controller delay, Lateral Jerk, override 4.5 / 0.07, friction ramp 0.24, steering delay fixed at 0.33 s, request smoothing 0.2 s above 45–56 mph. The gain change is not yet driven. Drives are scored with `tools/drive-eval/sway.py`. See [docs/findings/2026-11-19-g70-sway-tool-controller-delay.md](docs/findings/2026-11-19-g70-sway-tool-controller-delay.md).
- **2026-11-18:** the device ran `g70-fingerprint` @ `500ba91` (branch `sunnypilot/g70-scc11-filter`): V0 torque controller with Lateral Jerk, override 4.5 / 0.07, friction ramp 0.24, steering delay fixed at 0.33 s, request smoothing 0.2 s above 45–56 mph, SCC11 re-sent by openpilot with the standstill prompt hidden, attention-warning text and chime filters. V0 with smoothing, the SCC11 filter and the chime filter are not yet confirmed in the car. See [docs/findings/2026-11-18-g70-smoothing-scc11-chime-curves.md](docs/findings/2026-11-18-g70-smoothing-scc11-chime-curves.md).
- **2026-11-17:** the device ran `g70-fingerprint` @ `466c14c`: controlsd crash fix, upstream V1 torque controller with Lateral Jerk, override 4.5 / 0.07, friction ramp 0.24, steering delay fixed at 0.33 s, request smoothing 0.2 s (the last two not yet driven). See [docs/findings/2026-11-17-g70-crash-fix-v1-delay-creep.md](docs/findings/2026-11-17-g70-crash-fix-v1-delay-creep.md).
- **2026-11-16:** the device ran `g70-fingerprint` @ `d833479` (optional steering-delay offset and friction-ramp width, narrower attention-warning filter; settings Lateral Jerk on, override 4.2 / 0.07, friction ramp 0.28, offset 0.15 s; not yet driven). See [docs/findings/2026-11-16-g70-straight-sway-loop-model.md](docs/findings/2026-11-16-g70-straight-sway-loop-model.md). Analysis scripts: [tools/drive-eval/](tools/drive-eval/README.md).
- **2026-11-13:** the device ran `g70-fingerprint` @ `4525e88` (branch `sunnypilot/g70-fingerprint`): upstream `dev` @ `d3e1a2f` + the G70 2024 port + the `0x484` fix + the Driver Attention Warning ("take a break") fix that re-sends the camera's LKAS12, AGNOS 19.9, `DisableUpdates=1`. The DAW fix is not yet confirmed in the car. See [docs/findings/2026-11-13-g70-drives-daw-lkas12.md](docs/findings/2026-11-13-g70-drives-daw-lkas12.md) and [docs/findings/2026-11-12-g70-fingerprint-update-drives.md](docs/findings/2026-11-12-g70-fingerprint-update-drives.md). The entries below are the October history.
- Baseline: `dev` @ `0b2c431d3abab630df0a32f53236944855a91aa3` (tag `baseline/dev-20261003`), built from master `a5f44653d7f4`.
- Customization branch `dragal/custom` (local): WIP G70 2024 platform port @ `7e9d0755d9` (focused review done, see docs/findings). Targeted opendbc tests pass and the car's real FW resolves to `GENESIS_G70_2024`. Parked-car rlogs confirm CRC8 checksums and clean CarState and safety rx parsing. First-drive logs support `CAMERA_SCC`. Low-speed behaviour and tune quality are unvalidated. Focused review done (no two-round QA).
- Test environment: WSL 2 + Ubuntu 24.04 (distro disk on the data root). See [docs/baseline.md](docs/baseline.md#wsl-test-environment).
- Device: runs `dragal/custom` @ `7e9d0755d9` (deployed 2026-10-04, `DisableUpdates=1`). See [docs/proposals/2026-10-04-g70-2024-deploy.md](docs/proposals/2026-10-04-g70-2024-deploy.md). First drives 2026-10-04: engaged ~5 min, no faults; see docs/findings/2026-10-04-g70-first-drives.md.
