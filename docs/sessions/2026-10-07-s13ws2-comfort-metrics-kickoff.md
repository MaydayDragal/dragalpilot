# Kickoff prompt: build comfort and twitch measures that match the driver's experience, before any further fix work (copy-ready)

```text
Resume the dragalpilot project at C:\Users\dre\Documents\DragalPilot\dragalpilot.

Read, in order:
- CLAUDE.md;
- docs/sessions/2026-10-07-s13ws2-comfort-metrics-handoff.md (main thread);
- docs/findings/2026-10-07-g70-weave-twitch-sim.md §12 and §12.1 (why the twitch metrics are not validated), §6.4 (event analyses),
  §8.3 (the outer-loop twin and its bicycle model), §10;
- docs/findings/2026-10-06-g70-steering-twitch.md (the complaint, the wheel videos, §4-5);
- docs/findings/2026-10-07-g70-d2c4-validation.md §2.1 (Amendment 5: comfort metrics, IMU gate and diagnostics);
- docs/findings/2026-10-03-g70-fingerprint.md (update sections: ADRV_0x51 yaw rate, stock LKA, torque limits);
- CHANGELOG.md (session 13ws), docs/local-storage.md, the project memory notes.

Goal (user): "Ultimately it's driving comfort that we're trying to improve." Build and validate measures of
  (a) the weave (0.2-0.7 Hz) and
  (b) the faster twitch: the steering wheel visibly stepping by itself while the comma drives, and the comfort upset
      that comes with it,
that match what the driver experiences. Only then re-score D2C4 and the earlier candidates. Offline only. No device access.
No change to dragal/custom or the WSL clone without asking first. Dither is ruled out by the user (rack wear).

Context: the project's twitch metrics (jumps/min, T, hold-steps) fire as often in manual and stock-LKA driving as under the comma.
With the 0.1 deg angle sensor, angle alone can't separate stick-slip from deliberate quick corrections. The user has never noticed
the twitch with the stock LKA.

Steps:
1. Confirm the workspace:
   - outer main @ 606c36b + uncommitted docs;
   - dragal/custom @ 89bbe60ab1 clean; WSL clone clean;
   - E: UniqueId, writability, free space;
   - no parallel session.
2. Brainstorm and pre-register (new findings doc) candidate measures, before computing them on any comparison:
   - Torque-based stick-slip detector: applied torque rises (our command, or the stock camera's LKAS11 in its pass-through periods,
     or the EPS output torque CR_Mdps_OutTq; the driver's column torque in manual) by a meaningful amount while the angle holds,
     then the wheel breaks free. Compare the comma vs stock vs manual.
   - Steering-caused vehicle motion: yaw rate from the device gyro and from ADRV_0x51 (about 0.01 deg/s per count), speed x yaw
     rate, yaw and lateral jerk, in 0.7-4 Hz (twitch comfort) and 0.2-0.7 Hz (weave comfort). Isolate the steering-caused part:
     - coherence/transfer from the steering angle;
     - event-triggered averages of yaw/lateral jerk around wheel steps (per-event upset x event rate = comfort cost per minute);
     - GPS position-aligned, same-road comparisons to cancel the road input.
     Note: the raw IMU lateral accel at 0.7-4 Hz is road-dominated (Amendment 5 diagnostics).
   - Optional: ISO 2631 W_d-weighted versions of the steering-caused part.
3. Validate against the driver's experience:
   - use the user's bookmarks and filmed moments (route 0x22: twitchy; 0x23: bookmarked but rated calm by the old metrics);
   - ask the user to label further moments if needed;
   - a measure counts as valid only if it separates the labelled twitchy moments from calm ones, and the comma from manual and
     stock where the user says they differ. Report honestly if no measure does.
4. With validated measures:
   - re-score the on-car D2C4 vs A drives (same road);
   - check whether the outer-loop twin's bicycle model reproduces the steering-caused motion measures from logged steering;
   - if it does, re-rank the offline candidates (D2C4, F7d, S1, S2, MV2/MV3) on simulated comfort.
5. Identify the ~6 min of stock-LKA steering in the logs (which routes, why the panda was in pass-through) and use them as the
   stock reference. State the sample's limits.
6. Get a focused adversarial review of the new measurement code and of the unreviewed 13ws scripts listed in the handoff §5-6.
7. Report: which measures are valid, what they say about the comma vs stock vs manual, D2C4, and the candidates; options for the
   user. Then stop and ask before any dragal/custom change. A same-road stock-vs-comma recording (comma unplugged or in
   pass-through, with wheel video) may be proposed to the user as the decisive comparison. It needs the user's consent and any
   device steps need authorization.
8. Keep the changelog, findings and handoff/kickoff discipline (CLAUDE.md §7). Label source facts, observations, model results and
   hypotheses. Missing data is unknown.
```
