# Handoff: session 5 (2026-10-04): video check of the lane-position findings

Written 2026-10-04, ~16:45 EDT. Reconfirm everything at the next session start. This session ran in parallel with session 4b (low-speed drives / weave); its handoff is [2026-10-04-s4b-lowspeed-weave-handoff.md](2026-10-04-s4b-lowspeed-weave-handoff.md).

## Objective

Check the session-4 lane-drift findings (left bias, curve-inside shift, real slow motion) with the road videos, using a method independent of the driving model. Describe the visual context of the short engaged low-speed windows.

## User instructions and decisions (this session)

- Kickoff: [2026-10-04-s4-video-lane-check-kickoff.md](2026-10-04-s4-video-lane-check-kickoff.md). No device changes or reboots. Rlogs never qlogs. Shared-file etiquette with the parallel session.
- The user paused the session for a VM reboot (~15:50 EDT) and resized the VM: **6 vCPU, 32 GB**. WSL now sees 6 CPUs and ~16 GB (default; no `.wslconfig` was written).
- Standing authorizations used: video analysis, tool installs (memory, 2026-10-04).

## Exact revisions

- sunnypilot baseline `dev` @ `0b2c431d` (unchanged); `dragal/custom` @ `82f58a9a8c` (unchanged, clean); WSL clone `~/src/sunnypilot` @ `82f58a9a8c`, clean.
- Outer repo: `main` @ `c0b25c1` (session 4b's commit) at the time of writing. This session adds the findings doc, this handoff/kickoff pair, a changelog entry and a sessions-index row (see `git log` / `git status` for whether they are committed).

## Completed work and evidence

Full write-up: [docs/findings/2026-10-04-g70-video-lane-check.md](../findings/2026-10-04-g70-video-lane-check.md).

1. **Frame alignment verified:**
   - `modelV2.frameId` → `narrowRoadEncodeIdx` (segmentNum, segmentId) → frame in `fcamera.hevc`.
   - 1200/1200 frames per segment; every model frame on routes 4 and 6–9 maps.
   - Overlays land on the paint; the comparison's lag peaks at 0.
2. **Classical lane-marking detector** (bird's-eye ridge filter + joint parallel-line fit, no model input).
   - v1 → v2 after a hand check found a concrete-seam false detection.
   - Hand check on 15 random frames: stripe-centre error RMS ≈ 1.3 cm, max 2.6 cm.
3. **Highway comparison**, routes 6/7/8, eligible frames at 5 Hz (detector success 93–95%):
   - Lane centre at 12 m: video − model **+0.4 to +0.7 cm**.
   - Device **0.14–0.20 m left** of centre on straights, by both methods.
   - Curve-inside slope at x = 0 vs Kalman curvature: video 0.40/0.39/0.23 vs model 0.40/0.37/0.24 m per 1/1000 m.
   - Slow variation correlation 0.90–0.97.
   - The model draws its lines 6–9 cm inboard of the paint centres on both sides.
   - Conclusion (observation): the bias and curve shift are real relative to the paint, i.e. the model's path choice, not a perception error.
4. **24 low-speed windows described** (table in the findings):
   - Intersections, turns, turn-bay openings and unmarked streets; none stop-and-go.
   - With a close lead and weak lines, the model's lines bend toward the lead (observation, not quantified).

## Open hypotheses / questions

- Whether a human drives with the same left offset and curve shift on the same highway roads: no manual highway reference.
- The camera's lateral position within the device and the device's position relative to the car's centreline: unmeasured. The video check shares the camera and calibration with the model.
- Lead-following with weak lines at low speed: visual only.

## Workspace, running operations, artifacts

- No background jobs running. No SSH connection; no device access this session.
- Data root `E:\DragalPilot` (UniqueId verified at start and after the reboot; ~248 GB free).
- Scripts: `E:\DragalPilot\scratch\wsl\vid\`. Separate venv `~/venvs/vid` in WSL (the checkout's `.venv` is untouched).
- Outputs: `E:\DragalPilot\analysis\g70-video-lane-20261004\` (includes `CHECKPOINT.md` from before the reboot, now superseded by this handoff). Logs: `E:\DragalPilot\logs\vid-*.log`.
- Videos of routes 3, 4, 8, 9 and the new routes 0a–0e are in `recordings/` (promoted by session 4b). `temporary/device-pull-20261004d/pull.tar` (7.9 GB duplicate) is still there; deleting it is session 4b's open question to the user.

## Validation and limitations

- Hand-check and noise estimates as above. The detector was tuned after a hand check on the same data (exploratory); v1 and v2 conclusions agree within ~1 cm.
- Highway, daytime, model-confident frames only. Widths and slopes inherit an unverified height/scale.

## QA stages

Analysis only; no code changes. QA not applicable.

## Device state and SSH

- Not accessed this session. Last observed (session 4b, 18:56Z): `.104`, offroad, `GitCommit=82f58a9a8c`. No SSH connection open.

## Ordered next steps

1. The main thread continues with session 4b's next steps (offline weave simulation, pending the user's decision; see its handoff).
2. Optional, video follow-up ([kickoff](2026-10-04-s5-video-lane-check-kickoff.md)): apply the video measurement to the same-loop engaged (0a/0b) and manual (0c/0e) drives where lines are visible, for a model-independent human-vs-engaged lane position.
3. Data wanted for the lane-position question: a few minutes of manual highway driving on the route 6–8 roads (human reference for the bias and the curve shift).
