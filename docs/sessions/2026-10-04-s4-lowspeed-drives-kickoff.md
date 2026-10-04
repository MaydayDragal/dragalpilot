# Kickoff prompt: low-speed drive analysis (copy-ready)

Run this session **first**. It holds the only device connection; the video lane-check session starts after its pull is done.

```text
Resume the dragalpilot project at C:\Users\dre\Documents\DragalPilot\dragalpilot.

Read, in order: CLAUDE.md, docs/sessions/2026-10-04-s4-lane-drift-handoff.md, CHANGELOG.md, docs/local-storage.md,
docs/baseline.md, docs/findings/2026-10-04-g70-lane-drift.md (especially "Low-speed data drive protocol"),
docs/findings/2026-10-04-g70-tune-0x484-first-drive.md.

The user has completed the low-speed data drives from the protocol (engaged and manual stretches, after route 9).

1. Confirm the workspace and data-root state.
2. Ask me for the device's current IP, confirm it is offroad, and check no other session or tool holds an SSH connection.
   Then, in exactly ONE SSH connection (read-only):
   - list the routes after 00000009;
   - pull rlogs + fcamera/ecamera for all new routes (standing video authorization; see memory);
   - in the same connection, pull fcamera/ecamera for routes 00000003, 00000004, 00000008 and 00000009 if still on the device
     (they are for the video lane-check session).
   Verify hashes, promote per docs/local-storage.md, close the connection. Then tell me the pull is done, so I can start the
   video session (docs/sessions/2026-10-04-s4-video-lane-check-kickoff.md).
3. Ask me for the approximate times or landmarks of each engaged and manual stretch and the road type.
4. Analysis (reuse E:\DragalPilot\scratch\wsl\*.py; adapt their speed thresholds and window lengths, don't fork silently):
   - Find the sustained low-speed stretches (25-35 mph, stop-and-go) and the 45-55 mph ones; engaged vs manual.
   - Slow band (0.05-0.3 Hz) and fast band (0.3-3 Hz):
     - lateral sway from yaw rate;
     - lane offset where both lines are confident;
     - plan vs execution (model desiredCurvature vs actual; plan-centring and realised-vs-planned decomposition).
   - Watch for band-edge artifacts in any peak-frequency result.
   - Engaged vs manual on the same stretch: does the car swing more, and does it come from the plan or from the controller?
     Controller facts: V0 KP 2.9 at 12 m/s, 11.5 at 5 m/s; KD 0; integrator frozen below 5 m/s.
   - Use the videos for visual context: lead car, markings.
   - Check torqued state (calPerc, valid, applied values) and the bus-1 interruptRateCan2 fault on the new routes.
5. Write findings to docs/findings/ with evidence labels. If a change is warranted, propose it as a bounded change with
   question, criteria and validation. No device changes or reboots.

Shared-file etiquette (the video session may run in parallel):
- re-read CHANGELOG.md / docs/sessions/README.md right before editing;
- add your own dated changelog entry;
- commit only your own files;
- don't commit at the same moment as the other session.
```
