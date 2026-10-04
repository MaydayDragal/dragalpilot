# Kickoff prompt: session 4 (copy-ready)

```text
Resume the dragalpilot project at C:\Users\dre\Documents\DragalPilot\dragalpilot.

Read, in order: CLAUDE.md, docs/sessions/2026-10-04-s3-drives-tune-0x484-handoff.md, CHANGELOG.md,
docs/baseline.md, docs/local-storage.md, docs/findings/2026-10-04-g70-tune-0x484-first-drive.md,
docs/findings/2026-10-04-g70-drives-tune.md.

The device runs dragal/custom @ 82f58a9a8c (GENESIS_G70_2024 port + torque tune [4.0, 2.7, 0.07] +
camera-SCC 0x484 panda firmware). The tune fixed most of the curve overshoot, but a slow (~0.1 Hz)
lane-position drift remains. Immediate next task: confirm workspace state, then investigate the slow lane drift
from the existing rlogs (start with the handoff's "Lane-drift investigation" section; record the active driving
model and calibration first). Ask me before any device access; no device changes or reboots without my explicit
authorization.
```
