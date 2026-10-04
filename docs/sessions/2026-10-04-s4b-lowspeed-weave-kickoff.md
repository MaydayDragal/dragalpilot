# Kickoff prompt: after the session-4b reboot (copy-ready)

```text
Resume the dragalpilot project at C:\Users\dre\Documents\DragalPilot\dragalpilot (the VM was just rebooted).

Read, in order: CLAUDE.md, docs/sessions/2026-10-04-s4b-lowspeed-weave-handoff.md, CHANGELOG.md, docs/local-storage.md,
docs/baseline.md, docs/findings/2026-10-04-g70-lowspeed-drives.md (especially "Follow-up: the ~3 s weave").

1. Confirm the workspace and data-root state:
   - outer repo: session-4b docs are uncommitted unless a later commit says otherwise;
   - sunnypilot/ dragal/custom @ 82f58a9a8c, clean;
   - the WSL clone;
   - E: identity, writability and free space.
   Check whether the video lane-check session left its own handoff.
2. Ask me:
   - whether to commit (and push) the session-4b docs;
   - whether to delete E:\DragalPilot\temporary\device-pull-20261004d\pull.tar.
3. If I approve: the offline weave simulation. No device access.
   - Identify torque -> steering-angle lateral accel dynamics from routes 8/0a/0b, validated on held-out route 7.
   - Simulate V0 as deployed, V0 with setpoint = expected (the v1 error definition), and upstream v1 against the logged setpoints.
   - Report gain/phase at 0.2-0.6 Hz, curve actual/desired, overshoot and error vs the criteria in the findings doc.
   Reuse E:\DragalPilot\scratch\wsl\s4b_loop_xfer.py for the measurements.
4. Write the results to the findings doc with evidence labels. Propose a device change only as a bounded, car-scoped proposal.
   No device changes or reboots.
```
