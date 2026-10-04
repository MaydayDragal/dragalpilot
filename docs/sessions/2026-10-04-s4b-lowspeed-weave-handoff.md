# Handoff: session 4b (2026-10-04): low-speed drives pull + analysis, 3 s weave

Written 2026-10-04 ~15:45 EDT, before a user-requested VM reboot. Reconfirm everything at the next session start.

## Objective

Make sunnypilot drive the user's 2024 Genesis G70 well. This session:

- pulled the user's low-speed data drives;
- compared engaged vs manual driving on the same road;
- traced the weave the user still feels (~3 s per cycle) to the steering loop.

## User instructions and decisions (this session)

- **Weave description (user):** occasional; rhythm about 3 s; a few inches of left-right vehicle movement; the wheel visibly moves back and forth; no specific locations recalled; some segments are now very good, but some weaving is still detectable.
- **Device pull** for both sessions (low-speed + video): user confirmed `.104`, not driving, indoors, no other SSH session, "you may proceed".
- **Open questions** (asked of the user, not answered yet):
  - (1) run the proposed offline plant-identification + closed-loop simulation?
  - (2) delete the 7.9 GB duplicate `E:\DragalPilot\temporary\device-pull-20261004d\pull.tar`?
  - (3) commit/push this session's docs?
- **Standing (memory):**
  - video pulls and analysis authorized, with CLAUDE.md §6 mechanics;
  - tool installs on host/WSL authorized;
  - no test re-runs for docs-only commits;
  - stay on the default driving model;
  - reboots and device changes need explicit per-action authorization.
- The video lane-check session ran in parallel. The user stopped it safely before this reboot. Its outputs and handoff are its own; check the changelog and `docs/sessions/` for them.

## Exact revisions

- sunnypilot baseline `dev` @ `0b2c431d3abab630df0a32f53236944855a91aa3` (unchanged).
- `dragal/custom` @ `82f58a9a8c4af2f10d23d13fb1631deca98d4efd` (deployed; no code changes this session). Checkout clean.
- WSL clone `~/src/sunnypilot` @ `82f58a9`, clean.
- **Outer repo:** `main` = `origin/main` @ `6afe57e`. **Uncommitted** (this session):
  - `CHANGELOG.md` (Session 4b entry);
  - `docs/findings/2026-10-04-g70-lowspeed-drives.md`;
  - this handoff and kickoff;
  - `docs/sessions/README.md`.

## Completed work and evidence

Full write-up: [docs/findings/2026-10-04-g70-lowspeed-drives.md](../findings/2026-10-04-g70-lowspeed-drives.md), including the "Follow-up: the ~3 s weave" section.

1. **Pull.**
   - One read-only SSH connection, 18:49:57Z–18:56:09Z (script `E:\DragalPilot\scratch\device\pull_lowspeed_20261004.sh`).
   - 258 files, 7.88 GB, all sha256 MATCH; promoted by move. Provenance written. **Connection closed.**
   - New routes:
     - `13-51-50__0000000a`, `14-04-39__0000000b`: engaged;
     - `14-16-31__0000000c`: manual;
     - `14-28-03__0000000e`: manual, `OpenpilotEnabledToggle=0`, so dashcam/noOutput by design;
     - `recordings/undated/0000000d`: 8 s, bounded 14:27:22–14:28:04.
   - Videos for routes 3, 4, 8, 9 added.
2. **Same loop.**
   - By GPS, 0b/0e follow 0c's track for 92–94% of their length; 0a covers parts.
   - Sections S1 (25–30 mph, no confident lines), S2 (30–35 mph, lines), S3 (35–55 mph), S4 (highway).
3. **Slow path (< 0.3 Hz).**
   - The car follows the plan.
   - The engaged path differs from the human more than human-vs-human only in S1 (no lines). It is repeatable between engaged runs, and largest at a left-turn bay (0.4–0.7 m left).
   - No extra curve-cutting vs the human at low speed.
   - The human sits 5–8 cm left of centre where lines are confident.
4. **3 s weave (0.3–0.6 Hz).**
   - Actual motion is 1.05–1.9× the requested lateral accel with a 24–48° lag, at all speeds, before and after the tune.
   - Controller/EPS link 0.96–1.38×; vehicle link (yaw vs the steering-angle model) 1.04–1.35×.
   - The control-error spectrum peaks at 0.30–0.40 Hz on route 8 and 0a/0b above 35 mph.
   - The tune fixed only the low-frequency gain.
5. **Source facts (`82f58a9a8c`).**
   - The device runs `LatControlTorqueV0` (`controlsd_ext.py` L36–46).
   - V0's error = current desired − steering-angle measurement, so it contains the actuator delay (`latcontrol_torque_v0.py` L79–92).
   - Upstream v1 (`selfdrive/controls/lib/latcontrol_torque.py`) uses the delayed setpoint: KP 0.8 at 30 m/s, KI 0.15.
   - The `EnforceTorqueControl` toggle that selects v1 also re-runs `configure_torque_tune` and changes `torqued` and override behaviour.
6. **Other checks.**
   - No steer faults; CPU within baseline.
   - Real panda: no relay malfunction.
   - Route 0b's safety-replay "7,247 blocked" is a replay artifact: the real panda blocked 0 in Hyundai mode.
   - `torqued`: not valid, calPerc 70; limiting bucket 38/100 (about 1.3 h more highway driving).
   - Bus-1 start-up burst: on every boot since the firmware change. The sticky `interruptRateCan2` bit is set only when the peak crosses 16k/s. No control effect.

**Scripts** (`E:\DragalPilot\scratch\wsl\`):

- New: `lowspeed_timeline.py`, `lowspeed_drives.py`, `s4b_gps_extract.py`, `s4b_track_match.py`, `s4b_make_stretches.py`, `s4b_path_diff.py`, `s4b_path_peaks.py`, `s4b_peak_state.py`, `s4b_curve_shift.py`, `s4b_initdata_params.py`, `s4b_weave.py`, `s4b_loop_xfer.py`, plus `run_s4b_*.sh`.
- Modified: `lane_drift_extract.py` (lead and steer-torque fields; old version kept as `.session4a.py.bak`).
- Outputs: `E:\DragalPilot\analysis\g70-lowspeed-20261004\`.
- Logs: `E:\DragalPilot\logs\s4b-*.log`, `device-pull-20261004d.*`, `promote-20261004d.log`.

## Open hypotheses / questions

- **Weave cause (hypothesis):** a lightly damped steering loop. V0's P term acts on a delay-containing error, plus the vehicle's yaw gain above its steady-state model. Not yet tested by simulation or on the car.
- Why the user feels it most at low speed: open. The data shows similar gain at all speeds. Stop-and-go is still unmeasured.
- Absolute lane position at S1 (no lines): needs the video lane measurement.

## Device state and SSH

- Last observed 18:56Z: `.104`, offroad, indoors, `GitCommit=82f58a9a8c`. **No SSH connection open.** No device changes were made.

## QA stages

Analysis only; no code changes. QA not applicable. Code from earlier rounds: focused review done; two-round QA not performed.

## Ordered next steps

1. After the reboot: confirm the workspace (outer repo with uncommitted docs, `sunnypilot/`, WSL clone, data root). Ask the user about commit/push and the `pull.tar` deletion.
2. If the user approves, the **offline weave simulation** (findings doc, "Proposed next step"):
   - identify torque → steering-angle lateral accel dynamics on routes 8/0a/0b, validated on route 7;
   - simulate V0, V0 with `setpoint = expected`, and v1 against logged setpoints;
   - criteria: C gain at 0.3–0.6 Hz ≤ 1.2 with lag not worse, curve actual/desired 0.95–1.04, mean |error| ≤ +20%.
3. Only if it passes: a bounded, car-scoped code change proposal (tests, focused review, same-loop drive, rollback).
4. Data still wanted: stop-and-go engaged + manual on the same stretch; `torqued` validity check drive.
5. Later: the Hyundai 0x484 forwarding-rule round; keep watching the bus-1 start-up burst.
