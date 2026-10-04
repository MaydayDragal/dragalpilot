# Session handoffs

Chronological record of handoff and kickoff pairs. Older pairs are never overwritten.

**Latest handoffs (two parallel sessions):**

- [2026-10-04-s4b-lowspeed-weave-handoff.md](2026-10-04-s4b-lowspeed-weave-handoff.md): low-speed drives + 3 s weave, written before a VM reboot. **Main thread.**
- [2026-10-04-s5-video-lane-check-handoff.md](2026-10-04-s5-video-lane-check-handoff.md): video check of the lane-position findings, finished after the reboot.

**Latest kickoffs:**

- [2026-10-04-s4b-lowspeed-weave-kickoff.md](2026-10-04-s4b-lowspeed-weave-kickoff.md): main thread (weave).
- [2026-10-04-s5-video-lane-check-kickoff.md](2026-10-04-s5-video-lane-check-kickoff.md): optional video follow-up on the same-loop drives.

The video lane-check session ([kickoff](2026-10-04-s4-video-lane-check-kickoff.md)) ran in parallel with 4b. The user paused it for the reboot, and it finished afterwards (session 5 row below).

Earlier kickoffs (done): [low-speed drives](2026-10-04-s4-lowspeed-drives-kickoff.md) (its pull is complete), [video check](2026-10-04-s4-video-lane-check-kickoff.md).

| Date | Session / topic | Handoff | Kickoff |
|---|---|---|---|
| 2026-10-03 | Session 1: project setup, G70 2024 fingerprint, WIP port (pre-WSL reboot) | [handoff](2026-10-03-s1-setup-g70-port-handoff.md) | [kickoff](2026-10-03-s1-setup-g70-port-kickoff.md) |
| 2026-10-04 | Session 2: WSL env, port tests, rlog analysis, focused review, Stage 0 deployment | [handoff](2026-10-04-s2-wsl-tests-deploy-handoff.md) | [kickoff](2026-10-04-s2-wsl-tests-deploy-kickoff.md) |
| 2026-10-04 | Session 3: drive analysis, steering tune, 0x484 panda safety change + firmware, deployment, first drive after | [handoff](2026-10-04-s3-drives-tune-0x484-handoff.md) | [kickoff](2026-10-04-s3-drives-tune-0x484-kickoff.md) |
| 2026-10-04 | Session 4: lane-drift investigation (rlogs), low-speed comparison, torqued status; video lane-check kickoff | [handoff](2026-10-04-s4-lane-drift-handoff.md) | [kickoff 1 (low-speed drives)](2026-10-04-s4-lowspeed-drives-kickoff.md), [kickoff 2 (video check)](2026-10-04-s4-video-lane-check-kickoff.md) |
| 2026-10-04 | Session 4b: low-speed drives pull (+ videos for routes 3/4/8/9), engaged vs manual on the same loop, 3 s weave traced to the steering loop | [handoff](2026-10-04-s4b-lowspeed-weave-handoff.md) | [kickoff](2026-10-04-s4b-lowspeed-weave-kickoff.md) |
| 2026-10-04 | Session 5: video check of the lane-position findings (classical lane-marking measurement vs modelV2), low-speed window context | [handoff](2026-10-04-s5-video-lane-check-handoff.md) | [kickoff (optional follow-up)](2026-10-04-s5-video-lane-check-kickoff.md) |
