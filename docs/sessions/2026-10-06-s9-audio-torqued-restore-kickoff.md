# Kickoff prompt: after session 9 (copy-ready)

```text
Resume the dragalpilot project at C:\Users\dre\Documents\DragalPilot\dragalpilot.

Read, in order: CLAUDE.md, docs/sessions/2026-10-06-s9-audio-torqued-restore-handoff.md, CHANGELOG.md (session 9 entry),
docs/local-storage.md, docs/baseline.md ("Device runtime notes"), docs/proposals/2026-10-05-soundd-audio-gate-deploy.md and
docs/proposals/2026-10-06-g70-torqued-restore.md (both deployment records), docs/findings/2026-10-06-g70-torqued-reconstruction.md.

1. Confirm the workspace and data root:
   - outer main = origin/main @ 606c36b plus the uncommitted session 8 and 9 docs;
   - sunnypilot/ dragal/custom @ c027a92857 (clean); WSL clone @ c027a92857 (clean);
   - E: identity, writability and free space.
2. The device runs c027a92857 (audio fix) with the restored torqued cache (sha256 2883e5da...). When I report a drive, I confirm
   the address and that the device is inactive; then pull the new route(s) read-only (rlogs + fcamera + ecamera + swaglog), and verify:
   - audio: "soundd audio stream ready" in swaglog, any "soundd (audio starting)" only early, no soundd crash;
   - torqued: "restored torque params from cache", first lateralTorqueParameters with 7,722 points, valid, calPerc 100,
     decay ~250, latAccelFactorFiltered ~3.688, and a G70 (not MOCK) fingerprint.
   Record the results in both proposals and the changelog.
3. Then ask me what to work on next (open items are listed in the handoff).
```
