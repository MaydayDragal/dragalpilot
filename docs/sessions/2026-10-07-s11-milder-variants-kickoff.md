# Kickoff prompt: after sessions 11 and 11r: milder D2C4 variants or another twitch fix, offline (copy-ready)

Updated 2026-10-07 after session 11r's first on-car A/B. This kickoff had not been run before the update. The on-car result changes the question:
- D2C4's twitch reduction and its transient costs came out on the car about as the model predicted;
- **but weaving got worse, which the model did not predict.**

```text
Resume the dragalpilot project at C:\Users\dre\Documents\DragalPilot\dragalpilot.

Read, in order:
- CLAUDE.md;
- docs/sessions/2026-10-07-s11-d2c4-ready-handoff.md (main thread);
- docs/sessions/2026-10-07-s11r-remote-pull-ab-handoff.md (the on-car A/B);
- docs/findings/2026-10-07-g70-d2c4-ab-onroad.md (§2.3 data, §3 pre-registration, §4 results, §5 review);
- CHANGELOG.md (session 11 and 11r entries);
- docs/local-storage.md;
- docs/findings/2026-10-07-g70-d2c4-validation.md;
- docs/proposals/2026-10-07-g70-d2c4-deploy.md (§1 and §6);
- docs/findings/2026-10-04-g70-weave-sim.md (session 6's weave model and its open question about the outer loop);
- the project memory notes (CPU/instruction-set tooling; Git Bash -> WSL gotchas).

Context:
- D2C4 is implemented on dragal/custom @ 89bbe60ab1 with full two-round QA, and INSTALLED on the device since
  2026-10-07 13:33 EDT. Last known-good: c027a92857.
  - D2 = steeringAngleDeadzoneDeg 0.4 deg; C4 = a causal 2 Hz desiredCurvature low-pass; GENESIS_G70_2024 only.
- Offline (model), D2C4 roughly halved the twitch, with transient costs I accepted:
  - curve-window error +28% and lag +0.09 s (C3);
  - 0.6 Hz phase lag +17-19 deg (R5, from the filter);
  - slower small-step settling at 75 mph (R3, from the deadzone);
  - mean tracking error about +20%.
  - The model predicted weave W down 7-25%.
- First on-car A/B (session 11r; ONE D2C4 drive, route 0x28, vs 5 same-road, same-direction drives on c027a92857; all preliminary):
  - jitter: jumps/min -42%, angle 0.7-4 Hz RMS -39%, reversals -35%. This matches the model. But one midday A drive was
    as calm as B, so it is not yet separable from day-to-day variation.
  - costs, as predicted: tracking error +27%, curve lag +0.094 s, curve in-window error +33%, peak +19%.
  - comfort: steering-proxy jerk -23%; 20 Hz line / column vibration unchanged; IMU not evaluable (gate).
  - WEAVE WORSE, not predicted:
    - angle W (0.2-0.7 Hz) RMS +18% (+22% on the Amendment 5 masks; fails the 15% limit; the CI includes 0);
    - lane-centre offset 0.2-0.7 Hz RMS +41% (CI +20...+65%, excludes 0); the 0.05-0.7 Hz band +7%.
  - steering presses 5 in 11.4 min on B vs 4 in 28 min on A (cause unknown until the road video is pulled).
  - The driver (my partner) has not given an impression yet.
- Leading hypothesis (session 11r, not tested):
  - C4's extra phase lag in the 0.2-0.7 Hz band (R5) acts through the OUTER loop: the model/planner re-plans
    desiredCurvature from the car's lane position, so loop delay becomes weave.
  - Neither the session 6 weave model nor the session 10/11 stick-slip harness has that outer loop: they replay the logged
    requests open-loop. That is why they could not predict the weave increase. A deadzone also adds effective delay/hysteresis,
    so D2 is not automatically innocent.

This session: find, OFFLINE, a fix for the twitch that keeps most of the reduction WITHOUT making weave worse, and with less
transient cost than D2C4. Candidates are milder D2C4 variants, OR another approach if the evidence points there. Examples to
consider, not a fixed list:
- deadzone-only variants (no filter, so no C4 phase lag);
- higher filter cutoffs;
- a filter that removes only the twitch band instead of everything above the cutoff;
- addressing the stick-slip at the actuator/command side rather than smoothing the request.
Propose the candidate set with reasons and get my OK before running the grid.

1. Confirm the workspace and data root:
   - outer main @ 606c36b + the uncommitted docs;
   - dragal/custom @ 89bbe60ab1, clean; WSL clone @ 89bbe60ab1, clean;
   - E: identity, writability and free space.
   - No device access in this session. A separate A/B follow-up session (docs/sessions/2026-10-07-s11r-ab-followup-kickoff.md)
     may pull videos and new drives at the same time.
2. Weave has to be modelled before variants can be ranked on it. Investigate (and pre-register before computing):
   a) a log check that needs no new model: does B's extra weave line up with the request? Compare the request (desiredCurvature,
      unfiltered in the logs) and the lane-centre offset in the 0.2-0.7 Hz band, B vs the same-road A drives. Does the
      model/planner's request itself weave more on B (an outer-loop effect), or only the wheel/lane response?
      Data: analysis/g70-d2c4-ab-20261007/{dataset,drives,match/masks}; s14_* tools.
   b) whether an outer-loop model can be identified from the logs (lane-centre offset and heading -> desiredCurvature, with
      the model's delay), and closed around the existing stick-slip plant. Validate it against the on-car D2C4 result before
      trusting it on variants. Pre-register what "reproduces" means: jitter about -40%, W up, lane 0.2-0.7 Hz up, tracking about
      +27%, curve lag about +0.09 s.
   c) if no adequate outer-loop model is found, fall back to a pre-registered proxy, e.g. added phase lag in 0.2-0.7 Hz must
      stay below a bound. Say plainly that it is a proxy.
   Note the data independence: the 0x28 drive and its same-road A drives are now used for model checking, so they are no
   longer an independent test. The next on-car A/B with a chosen variant is.
3. Also use 0x28 as a plant check. Replay its logged requests through the harness with D2C4 (source = harness was verified to
   1.9e-5 counts) and compare the simulated twitch and comfort metrics with the logged angle. This is the first engaged data
   with D2C4 active.
4. Pre-register the variant/approach evaluation (a new amendment in the validation findings, before any run):
   - candidates (from step 0's agreed set) plus D2C4 and A0 as references;
   - plants: the E4-identified plant primary, the E2+E3 plant secondary (plus the outer-loop model, if step 2b validates);
   - eras: E2/E3 primary, E1/E4 secondary; no logged era is untouched by selection;
   - one decision rule chosen before looking:
     - twitch: jumps >= 40% lower, angle 0.7-4 Hz RMS >= 30% lower;
     - weave: W not up AND lane-offset 0.2-0.7 Hz not up (on the outer-loop model or the step 2c proxy);
     - tracking: mean error not up > 20%;
     - the Amendment 7 red flags R1-R5 and C1-C3;
     - ranking among the passes, e.g. least weave risk and transient cost among those meeting the twitch criteria;
   - every result reports all three outcome groups: wheel jitter, weaving and comfort (steering-proxy metrics; the IMU is not
     usable in simulation).
5. Run it with the existing harness:
   - s11_eval.py (twitch, --tracking), s12_transient.py, s12_curves.py (env S12_VARIANTS);
   - new variants via new files (e.g. s15_mv_*.py) that import the existing modules and extend their variant tables;
   - use all cores (CLAUDE.md §8), but see the parallel-session limit in step 7;
   - adopt the s13 speed-ups only if they are bit-identical (memory/handoff);
   - call WSL from Git Bash with MSYS_NO_PATHCONV=1, through runner files;
   - checkout venv for rlog readers, ~/venvs/vid for s11_eval-based scripts.
6. Report the trade-off frontier and a recommendation:
   - keep D2C4 while more on-car data come in;
   - roll back to c027a92857;
   - or replace D2C4 with a variant or another approach. That then needs the code change, tests, QA round(s) per CLAUDE.md §5,
     new artifacts and a dry run, an updated proposal with an on-car A/B protocol whose weave criterion uses the lane-offset
     0.2-0.7 Hz band too, and nothing on the device.
   Stop and ask me before changing the install plan or the code on dragal/custom.
7. Parallel-session rules (the A/B follow-up session may be running):
   - do not change the sunnypilot/ checkout or the WSL clone (~/src/sunnypilot stays at 89bbe60ab1);
   - do not edit shared scripts in place (s11_*.py, s12_*.py, s13_*.py, s14_*.py, run_*.sh): put new code in new files;
   - keep CPU pools to at most 4 workers while the other session runs;
   - for CHANGELOG.md, docs/sessions/README.md and CLAUDE.md: re-read right before each edit and append only;
   - write your own findings doc, handoff and kickoff (unique session/topic suffix);
   - outputs go to analysis/g70-milder-variants-<date>/.
8. Keep the changelog, findings and session handoff/kickoff discipline (CLAUDE.md §7).
```
