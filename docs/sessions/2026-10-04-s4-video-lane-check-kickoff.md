# Kickoff prompt: video lane-position check (copy-ready)

Start this **after** the low-speed session ([kickoff](2026-10-04-s4-lowspeed-drives-kickoff.md)) reports its device pull is done. That pull fetches the videos this session needs, so normally this session needs no device access.

```text
Resume the dragalpilot project at C:\Users\dre\Documents\DragalPilot\dragalpilot.

Read, in order: CLAUDE.md, docs/sessions/2026-10-04-s4-lane-drift-handoff.md, CHANGELOG.md, docs/local-storage.md,
docs/baseline.md, docs/findings/2026-10-04-g70-lane-drift.md.

Task: independently check the lane-drift findings with the road videos. So far every lane-position number comes from the
driving model's own laneLines. The video gives a second measurement from the same camera with a different method.

1. Confirm the workspace and data-root state.
2. Videos:
   - Routes 5-7 have fcamera/ecamera locally.
   - The low-speed session should already have pulled routes 3, 4, 8, 9 (if still on the device) and the new drives.
     Check recordings/ and its changelog entry.
   - Only if something is missing: ask me first. Another session may hold the SSH connection. Then confirm the current IP
     and offroad state, use exactly one SSH connection, verify hashes and promote per docs/local-storage.md.
   - The new low-speed drives with video are also usable for step 5.
3. Build the measurement:
   - Use the narrow road camera, the pinned device intrinsics (mici; DEVICE_CAMERAS in the checkout), the logged calibration
     (rpyCalib, height) and frame-to-log alignment via the frame ids / encode indices in the rlogs (verify the mapping;
     label approximate alignment).
   - Measure the lane-marking positions at a near distance (about 8-15 m) with a method independent of the model: classical
     CV, or a local lane-detection model. Installs are authorized; keep weights and caches on E:.
   - Validate the measurement on a few hand-checked frames first, and state its error.
4. Compare with modelV2.laneLines at the same distance on the eligible highway stretches of routes 6-8:
   - the static left bias (model: device 0.15-0.19 m left of centre; the device is mounted at windshield centre ±3 mm);
   - the inside-of-curve shift (model: ~0.25-0.4 m per 1/1000 m of curvature).
5. Look at the short low-speed engaged windows listed in E:\DragalPilot\logs\lowspeed-windows-20261004.log (routes 4, 7, 8, 9)
   and describe the visual context: lead vehicle, markings, intersections.

Write findings to docs/findings/ with evidence labels, add a changelog entry, and update the session docs.
No device changes or reboots. Rlogs never qlogs.

Shared-file etiquette (the low-speed session may run in parallel):
- re-read CHANGELOG.md / docs/sessions/README.md right before editing;
- add your own dated changelog entry;
- commit only your own files;
- don't commit at the same moment as the other session.
WSL has ~3 GB RAM; if a vision model needs more, raise it in .wslconfig and record it (machine-level setting).
```
