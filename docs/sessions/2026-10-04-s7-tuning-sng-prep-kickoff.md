# Kickoff prompt: after session 7 (copy-ready)

```text
Resume the dragalpilot project at C:\Users\dre\Documents\DragalPilot\dragalpilot.

Read, in order: CLAUDE.md, docs/sessions/2026-10-04-s7-tuning-sng-prep-handoff.md, CHANGELOG.md, docs/local-storage.md,
docs/baseline.md, docs/findings/2026-10-04-g70-stop-and-go-plan.md.

1. Confirm the workspace and the data root:
   - outer repo: main = origin/main, clean;
   - sunnypilot/ dragal/custom @ 82f58a9a8c, clean;
   - the WSL clone;
   - E: identity, writability and free space.
2. Ask me whether the new drives (plan section 1: stop-and-go engaged + by hand, steady 20-35 mph) are done, and whether I want to
   change any provisional D-rule thresholds before the data is looked at.
3. When I confirm the device state and authorize the pull: one SSH connection, rlogs + fcamera + ecamera for all new routes
   (CLAUDE.md section 3), verify, promote, then run the plan's pipeline (extracts -> sng_analyze.py -> D1-D5 report; plant check
   at 20-35 mph and the hands models if steady 20-35 mph runs exist).
   Also ask whether to delete E:\DragalPilot\temporary\device-pull-20261004s7\pull.tar.
   No device changes or reboots.
```
