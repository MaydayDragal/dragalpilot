# Kickoff prompt: after the comfort measures, get the user's decisions, then build a vehicle-response model for scoring the weave (copy-ready)

```text
Resume the dragalpilot project at C:\Users\dre\Documents\DragalPilot\dragalpilot.

Read, in order:
- CLAUDE.md;
- docs/sessions/2026-10-07-s15cm-comfort-measures-handoff.md (main thread);
- docs/findings/2026-10-07-g70-comfort-metrics.md (§1 input facts, §3 Amendment 13, §4 results, §5 options, §6 QA);
- docs/findings/2026-10-07-g70-weave-twitch-sim.md §6.4 and §8.3 (jumps follow slow request reversals; the outer-loop twin);
- CHANGELOG.md (session 15cm), docs/local-storage.md, the project memory notes.

Goal (user): "Ultimately it's driving comfort that we're trying to improve." Offline unless the user authorizes otherwise.
No change to dragal/custom or the WSL clone without asking first. Dither is ruled out.

State:
- On the same road, the comma's felt weave (yaw-derived lateral accel 0.2-0.7 Hz, W_ar) is 1.9x the car's own LKA's and the driver's.
- The fast, steering-caused motion is about the same for all three.
- No twitch measure is validated as pre-registered.
- D2C4 raises the felt weave by about 29% with no felt twitch benefit.
- The bicycle model fits manual driving but not comma or stock driving: under actuator control the car's yaw leads the
  steering-wheel angle (review F1). So the wheel angle is not a faithful input for the vehicle response under the comma.

Steps:
1. Confirm the workspace:
   - outer main @ 606c36b + uncommitted docs;
   - dragal/custom @ 89bbe60ab1 clean; WSL clone clean;
   - E: UniqueId, writability, free space;
   - whether a parallel session (14lv log viewer) is still active.
2. Ask the user the open questions (handoff §7):
   - the decisive same-road stock-vs-comma highway recording with wheel video and labels;
   - the 0x28 bookmark;
   - whether the twitch was seen at the 0x23 moments;
   - D2C4 keep or roll back;
   - focus on the weave.
   Record the answers verbatim.
3. Offline, pre-registered before computing:
   - identify an empirical model from the comma's torque command (or the EPS output torque) to the yaw rate (ESP12), from E4
     comma highway data; handle the closed-loop bias (e.g. the request as an instrument);
   - validate it on held-out routes (gain and phase per band, W_ar and J_r within stated tolerances);
   - if it validates, use it on the simulated torque to score the inner-loop simulator's candidates (A0, D2C4, F7d, S1, S2, MV2,
     MV3) on W_ar and J_r;
   - state the limits: no outer loop; the rack-leads-wheel hypothesis H-col.
4. Test H-col more strictly. The focused review already ruled out ESP12 delay, angle creep and hold selection. Still to separate:
   - a closed-loop cause (what the driving model's correction would predict, and its sign);
   - a rack lead.
5. If the user records the decisive drive and authorizes the pull:
   - read-only pull of rlogs + both road videos + the phone video (CLAUDE.md §3, §6);
   - pre-register V-label and V-stock on it, then run them.
6. Keep the changelog, findings and handoff/kickoff discipline (CLAUDE.md §7). Label source facts, observations, model results and
   hypotheses. Any car change needs the user's OK first, then two-round QA and an on-car A/B on W_ar and J_r.
```
