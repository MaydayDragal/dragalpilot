# Kickoff prompt: after session 8 (copy-ready)

```text
Resume the dragalpilot project at C:\Users\dre\Documents\DragalPilot\dragalpilot.

Read, in order: CLAUDE.md, docs/sessions/2026-10-05-s8-sng-errors-audio-handoff.md, CHANGELOG.md (2026-10-05 entry),
docs/local-storage.md, docs/baseline.md (WSL rows incl. "openpilot Python tests (x86)"), docs/findings/2026-10-05-g70-device-errors.md
(Follow-ups 1-5), docs/findings/2026-10-05-soundd-audio-gate.md, docs/proposals/2026-10-05-soundd-audio-gate-deploy.md.

1. Confirm the workspace and data root:
   - outer main = origin/main @ 606c36b plus the uncommitted session 8 docs listed in the handoff;
   - sunnypilot/ dragal/custom @ c027a92857 (local, not pushed); WSL clone detached @ c027a92857, clean;
   - E: identity, writability and free space.
2. Ask me whether to install the audio fix now. If yes: I confirm the device address and that it is inactive,
   then run E:\DragalPilot\deploy\audio-gate-20261005\install.sh (one SSH connection). The reboot needs my
   separate explicit OK (precheck_reboot.sh), then postboot_check.sh. Record it in the proposal and the changelog.
3. Main task: restore torque learning (torqued) to its state at the end of route 0x16, as described in the
   handoff ("Torque restore" and next step 3):
   - build an offline replay with the checkout's unmodified TorqueEstimator over routes 8 to 0x16 in driving order;
   - validate it per route against the logged lateralTorqueParameters, with tolerances defined before running;
   - produce the LiveTorqueParameters bytes at the last 60 s cache point of route 0x16;
   - check them with the real restore path;
   - get a focused adversarial review.
   No device access for this part.
4. Then write a restore proposal (backup, write with Params().put while offroad, verification, rollback) and ask me
   for authorization. Nothing is written on the device without my explicit OK at the time.
```
