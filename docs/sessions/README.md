# Session handoffs

Chronological record of handoff and kickoff pairs. Older pairs are never overwritten.

**Latest handoff:** [2026-10-04-s4-lane-drift-handoff.md](2026-10-04-s4-lane-drift-handoff.md)
**Latest kickoffs (run in this order):**

1. [2026-10-04-s4-lowspeed-drives-kickoff.md](2026-10-04-s4-lowspeed-drives-kickoff.md): low-speed drive analysis. It owns the single device pull for both sessions.
2. [2026-10-04-s4-video-lane-check-kickoff.md](2026-10-04-s4-video-lane-check-kickoff.md): video lane-position check. Start it after session 1 reports its pull is done; it can then run in parallel.

| Date | Session / topic | Handoff | Kickoff |
|---|---|---|---|
| 2026-10-03 | Session 1: project setup, G70 2024 fingerprint, WIP port (pre-WSL reboot) | [handoff](2026-10-03-s1-setup-g70-port-handoff.md) | [kickoff](2026-10-03-s1-setup-g70-port-kickoff.md) |
| 2026-10-04 | Session 2: WSL env, port tests, rlog analysis, focused review, Stage 0 deployment | [handoff](2026-10-04-s2-wsl-tests-deploy-handoff.md) | [kickoff](2026-10-04-s2-wsl-tests-deploy-kickoff.md) |
| 2026-10-04 | Session 3: drive analysis, steering tune, 0x484 panda safety change + firmware, deployment, first drive after | [handoff](2026-10-04-s3-drives-tune-0x484-handoff.md) | [kickoff](2026-10-04-s3-drives-tune-0x484-kickoff.md) |
| 2026-10-04 | Session 4: lane-drift investigation (rlogs), low-speed comparison, torqued status; video lane-check kickoff | [handoff](2026-10-04-s4-lane-drift-handoff.md) | [kickoff 1 (low-speed drives)](2026-10-04-s4-lowspeed-drives-kickoff.md), [kickoff 2 (video check)](2026-10-04-s4-video-lane-check-kickoff.md) |
