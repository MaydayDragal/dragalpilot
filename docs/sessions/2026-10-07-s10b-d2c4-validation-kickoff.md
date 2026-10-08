# Kickoff prompt: after session 10 (D2C4 validation, 4 steps) (copy-ready)

```text
Resume the dragalpilot project at C:\Users\dre\Documents\DragalPilot\dragalpilot.

Read, in order: CLAUDE.md, docs/sessions/2026-10-07-s10b-d2c4-validation-handoff.md (main thread), CHANGELOG.md (session 10
entries), docs/local-storage.md, docs/findings/2026-10-06-g70-steering-twitch.md, docs/findings/2026-10-07-g70-twitch-root-cause.md.

Context: the primary lateral complaint is a twitchy steering wheel (small constant corrections on straight roads), plus weaving.
Session 10 traced it, offline, to a stick-slip limit cycle (steering static friction x V0's error-driven friction-compensation
ramp + P x model-request jitter) with a plant validated on held-out eras at 55+ mph, and found candidate D2C4
(steeringAngleDeadzoneDeg 0.4 deg + causal 2 Hz desiredCurvature low-pass) that passes the pre-registered criteria with a
marginal tracking cost.

1. Confirm the workspace and data root (outer main @ 606c36b + uncommitted docs; dragal/custom @ c027a92857 clean; WSL clone
   @ c027a92857 clean; E: identity, writability, free space).
2. Do the 4 recommended steps in the handoff §9, in order:
   (1) focused adversarial review of the session 10 model/harness and Amendment 1-4 results;
   (2) offline D2C4 checks (synthetic steps/sines, curve entry/exit, 35-55 mph band, low-speed coverage, comfort baselines,
       restore keys), each pre-registered before running;
   (3) car-scoped implementation design + tests on dragal/custom, then full QA;
   (4) on-car A/B only with my explicit authorization for each device action.
   Every analysis must report all three outcome groups from handoff §8: wheel jitter (hold-and-jump), weaving (0.2-0.7 Hz /
   lane position) and overall comfort (lateral accel/jerk/step events from livePose/IMU, steering-wheel vibration). Define the
   comfort metrics in a pre-registration before computing them.
3. Stop and ask me before any device access, and at each step boundary if results change the plan.
```
