# sunnypilot patches (reference)

These are the project's changes to sunnypilot, exported with `git format-patch --binary` on 2026-10-09. They're here to read. To work on the code, use the branches in this repo (below), which hold the exact commits.

**Base:** sunnypilot `dev` @ `0b2c431d3abab630df0a32f53236944855a91aa3` (tag `sunnypilot-baseline/dev-20261003` in this repo). Upstream's `dev` is a bot-built, single-commit prebuilt branch that is replaced over time, so this repo keeps the base commit.

| Folder | Patches | What | Branch in this repo |
|---|---|---|---|
| `g70-baseline/` | 0001–0012 | 2024 Genesis G70 port (`GENESIS_G70_2024`), EPS firmware, torque tune and steerRatio 14.1, camera-SCC 0x484 block with its panda firmware, safety-test fixes, soundd/micd audio startup gate. **The working baseline**: on the device since 2026-10-09 (the 10/4 lateral settings). | `sunnypilot/g70-baseline` (`c027a92857`) |
| `d2c4-experimental/` | 0013–0016 | D2C4 steering-twitch experiment: G70 friction deadzone 0.4° plus a 2 Hz desired-curvature low-pass, with tests. Rolled back from the device on 2026-10-09: it reduced jitter but increased weave. See `docs/findings/2026-10-07-g70-*`. | `sunnypilot/dragal-custom` (`89bbe60ab1`) |

## Getting the code

```sh
git clone https://github.com/sunnypilot/sunnypilot.git sunnypilot
cd sunnypilot
git remote add dragal https://github.com/MaydayDragal/dragalpilot.git
git fetch dragal sunnypilot/g70-baseline
git checkout -b g70-baseline FETCH_HEAD
```

Or apply the patches to the base commit: `git am g70-baseline/*.patch`.

## 2026-11-12: `sunnypilot/g70-fingerprint`

Current branch on the device: upstream `dev` @ `d3e1a2f` + `be9fe0d` (car port only) + `c4776c4` (`0x484` fix with rebuilt panda firmware). The patches above are the October history and do not apply as-is to the new base (`CarSpecs.mass` was removed upstream). See `docs/findings/2026-11-12-g70-fingerprint-update-drives.md`.
