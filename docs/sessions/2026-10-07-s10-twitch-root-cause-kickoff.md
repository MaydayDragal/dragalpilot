# Kickoff prompt: after session 10 (copy-ready)

```text
Resume the dragalpilot project at C:\Users\dre\Documents\DragalPilot\dragalpilot.

Read, in order: CLAUDE.md, docs/sessions/2026-10-07-s10-twitch-root-cause-handoff.md, CHANGELOG.md (session 10 entries),
docs/local-storage.md, docs/findings/2026-10-06-g70-steering-twitch.md and docs/findings/2026-10-07-g70-twitch-root-cause.md.

1. Confirm the workspace and data root:
   - outer main = origin/main @ 606c36b plus the uncommitted session 8-10 docs;
   - sunnypilot/ dragal/custom @ c027a92857 (clean); WSL clone @ c027a92857 (clean);
   - E: identity, writability and free space.
2. The twitch root cause is modelled at 55+ mph (stick-slip: steering static friction x V0's error-driven friction ramp + P x
   model-request jitter). Mechanism-targeted candidate D2C4 (0.4 deg steeringAngleDeadzoneDeg + causal 2 Hz desiredCurvature
   low-pass) passes the pre-registered criteria offline, with a marginal tracking cost (findings 2026-10-07 §7.8). Ask me which
   next step to take: focused adversarial review of the model/harness; offline D2C4 step/curve/M-band checks; implementation
   design; or an on-car A/B (device change: needs my authorization).
3. No device access unless I confirm address, state and scope at the time.
```
