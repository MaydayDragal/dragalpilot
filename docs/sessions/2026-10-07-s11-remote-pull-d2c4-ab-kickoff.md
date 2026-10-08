# Kickoff prompt: remote (SSH-proxy) log pull and first analysis of the D2C4 drives (copy-ready)

This session is unique: the device is **out of the vehicle at the user's partner's workplace**, not on the home LAN.
- Its first task is to research how to reach it through the openpilot/comma remote SSH proxy.
- Then it pulls **rlogs only** (videos later) and analyses them.
- It may run **in parallel** with the milder-variants session ([kickoff](2026-10-07-s11-milder-variants-kickoff.md)).

```text
Resume the dragalpilot project at C:\Users\dre\Documents\DragalPilot\dragalpilot.

Read, in order:
- CLAUDE.md (especially §3 storage/recording rules, §6 device rules, §7);
- docs/sessions/2026-10-07-s11-d2c4-ready-handoff.md;
- docs/proposals/2026-10-07-g70-d2c4-deploy.md (all of it: the deployment record and the §6 A/B protocol with its
  pre-registered success criteria);
- docs/findings/2026-10-07-g70-d2c4-validation.md (§2.1 comfort definitions, §3 log semantics);
- docs/local-storage.md;
- CHANGELOG.md (session 11 entries).

Context:
- D2C4 (G70 2024 steering-twitch fix) was installed 2026-10-07 13:33 EDT: dragal/custom @ 89bbe60ab1, last known-good
  c027a92857.
- The device's cache files show a probable drive at ~13:27 EDT the same day on the OLD code (c027a92857); it can serve as an
  "A" comparison. Since then I have driven with D2C4 ("B").
- The device is now out of the car at my partner's workplace, so it is not on the home network (192.168.98.104 is not
  reachable).

PART 1: research only, no connection yet.
Find out what we need to reach the device through the openpilot / comma remote SSH proxy, from primary sources: the pinned
checkout (e.g. system/athena/athenad.py and any local-proxy / port-forward handlers, tools/ and docs/ about SSH, sunnypilot's
sunnylink code) and the official comma/openpilot documentation. Answer:
1. How the proxy works and what it requires:
   - account pairing; prime/subscription;
   - athenad connectivity (device online over wifi/cellular, and whether it must be onroad or offroad);
   - which SSH key it accepts (the device's GithubSshKeys vs our key ~/.ssh/id_ed25519_dragalpilot);
   - the exact SSH command / ProxyCommand;
   - whether sunnypilot's sunnylink offers an alternative.
2. What credentials or info I must supply (dongle ID, account login/JWT, GitHub username, etc.), and where they are stored.
   Secrets never go into the repo or docs; anything sensitive stays on E: or in my own hands.
3. Bandwidth and practicality: the size of the rlogs to pull (estimate per segment from earlier pulls), connection
   stability, and how to make the pull resumable and hash-verified.
4. Any risk to the device (e.g. a remote session waking it, or interfering with athenad/uploader), and how to keep the access
   strictly read-only.
Write the findings into a new doc (docs/findings/<date>-remote-ssh-proxy.md) with sources. Then STOP and ask me for whatever
I need to provide or do (for example on the device or in my comma account), and for authorization to connect. Do not create
accounts, change device params or settings, or pair anything yourself.

PART 2: the pull, only after my explicit authorization for this connection.
- Device rules still apply (CLAUDE.md §6):
  - I confirm the device ID/route to it and that it is inactive (offroad, not in a car);
  - exactly ONE SSH connection at a time, through the proxy (count my own sessions and other tools);
  - read-only; no writes, installs, param changes or reboots.
- **Scope: RLOGS ONLY, never qlogs**, for the routes since the last pull:
  - at least the ~13:27 EDT "A" drive and every drive on 89bbe60ab1;
  - identify them from initData/gitCommit;
  - plus small read-only diagnostics that confirm the install took effect: the swaglog lines for the torqued/paramsd/lagd
    restores and a copy of CarParamsPersistent. Nothing large.
- **One-time exception to CLAUDE.md §3 (user-authorized 2026-10-07):** no videos in this pull, because of the remote link.
  - Record every route/segment's missing fcamera/ecamera as a gap in metadata/, marked "deferred: remote pull, rlogs only".
  - Note in the handoff that the videos for the same segments must be pulled over the LAN later, before the device's deleter
    removes them.
  - Never qcamera.
- Storage as usual:
  - transfers into E:\DragalPilot\temporary\ first, verified by sha256 against hashes computed on the device;
  - then promoted to recordings/YYYY/MM/DD/HH-MM-SS__<route>/ (America/New_York start time) with provenance;
  - the pull must be resumable across a dropped connection.

PART 3: analysis (offline; pre-register before computing anything).
- Confirm from the logs:
  - which routes ran 89bbe60ab1 vs c027a92857;
  - that CarParams has steeringAngleDeadzoneDeg 0.4 on the B routes;
  - that torqued/paramsd/lagd restored their caches;
  - the device params relevant to the validated configuration (NNLC, EnforceTorqueControl etc. all off).
- Write a pre-registration (new findings doc) BEFORE computing:
  - which A and B data qualify (the same road and direction where possible; otherwise say how they differ);
  - selections; the exact metrics.
  - Use the proposal §6 criteria unchanged:
    - jitter: jumps/min, angle 0.7-4 Hz RMS, reversals, hold;
    - weaving: angle 0.2-0.7 Hz RMS, lane-centre offset;
    - comfort: steering-proxy jerk/steps; IMU lateral-accel with the validity gate redefined against v * gyro yaw rate;
      column 8-20 Hz, the 20 Hz EPS line;
    - tracking: mean error, curve entry/exit lag and error, curve ratio, override/hands-on events.
- Log semantics after D2C4:
  - controlsState.desiredCurvature is the UNFILTERED request;
  - torqueState.desiredLateralAccel is filtered.
  - Use desiredCurvature * v^2 for request-based tracking metrics in both arms.
- Tools (reuse; never edit them in place, put new code in new files, e.g. s14_ab_*.py):
  - drive_extract.py, lane_drift_extract.py, s11_dataset.py (its runner), s12_imu_extract.py, s11_holdjump.py,
    s12_comfort.py, s11_eval.stats.
  - Curve entry/exit on LOGS needs a log-only version of s12_curves' event and metric code, in a new file.
- Report every result with the three outcome groups (jitter, weaving, comfort) plus tracking, against the pre-registered
  criteria, with plain limitations:
  - one or few drives; different roads, traffic and weather between arms;
  - no wheel video yet;
  - my subjective impression is still to be collected (ask me how the drive felt, and record it verbatim).
- No code or device changes come out of this session. Recommendations only (keep D2C4 / roll back / variant), and I decide.

Parallel-session rules (the milder-variants session may be running at the same time):
- do not change the sunnypilot/ checkout or the WSL clone (~/src/sunnypilot stays at 89bbe60ab1);
- do not edit shared scripts in place;
- keep CPU pools to at most 4 workers while the other session runs;
- for CHANGELOG.md, docs/sessions/README.md and CLAUDE.md: re-read right before each edit and append only;
- write your own findings docs, handoff and kickoff with a unique session/topic suffix;
- analysis outputs go to E:\DragalPilot\analysis\g70-d2c4-ab-<date>\.

Stop and ask me at each boundary: after the research (before connecting), and after the pre-registration if the data turn out
to differ from what the protocol assumes.
```
