# Kickoff prompt: video lane-position follow-up on the same-loop drives (copy-ready)

Optional. The main thread is session 4b's [weave kickoff](2026-10-04-s4b-lowspeed-weave-kickoff.md). Run this one only if the user wants the model-independent human-vs-engaged comparison. It needs no device access.

```text
Resume the dragalpilot project at C:\Users\dre\Documents\DragalPilot\dragalpilot.

Read, in order: CLAUDE.md, docs/sessions/2026-10-04-s5-video-lane-check-handoff.md, CHANGELOG.md, docs/local-storage.md,
docs/findings/2026-10-04-g70-video-lane-check.md, docs/findings/2026-10-04-g70-lowspeed-drives.md.

Task: measure the lane position from the video (classical detector, E:\DragalPilot\scratch\wsl\vid\, venv ~/venvs/vid) on the
same-loop drives: engaged 0000000a/0000000b vs manual 0000000c/0000000e, on the stretches where lane markings are visible.

1. Confirm the workspace and data root.
2. Extract the logs with vid_log_extract.py (checkout venv). For the manual drives, check what modelV2 and calibration
   contain: 0e ran with OpenpilotEnabledToggle=0 (dashcam mode); verify that modeld ran and calibration exists before relying on it.
3. Select frames by GPS-aligned loop position (as session 4b did), not by model line confidence alone. Run vid_measure.py in
   "all" mode or a new mode, with the same v2 detector.
4. Compare the device position relative to the paint (engaged vs manual, same stretches): the static offset, and the shift vs curvature
   from Kalman yaw rate / v. Hand-check a random sample first and state the error.

Write findings to docs/findings/ with evidence labels, add a changelog entry, update the session docs. No device access.
```
