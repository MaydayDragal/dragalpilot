# Kickoff prompt: after session 12mv: attribute the on-car weave (new B drives) and, optionally, an outer-loop model v2 (copy-ready)

Use after the A/B follow-up session has pulled new D2C4 ("B") drives on the same road. If no new B drives exist yet, do only step 3 (offline modelling).

```text
Resume the dragalpilot project at C:\Users\dre\Documents\DragalPilot\dragalpilot.

Read, in order:
- CLAUDE.md;
- docs/sessions/2026-10-07-s12mv-milder-variants-handoff.md;
- the latest A/B follow-up handoff in docs/sessions/README.md (new B drives, videos, the driver's assessment), if one exists;
- docs/findings/2026-10-07-g70-milder-variants.md (§2 pre-registration, §3 results, §4 recommendation, §5 review);
- docs/findings/2026-10-07-g70-d2c4-validation.md §4 (Amendment 8);
- docs/findings/2026-10-07-g70-d2c4-ab-onroad.md (§3 pre-registration, §4 results);
- CHANGELOG.md (sessions 11r, 12mv, and any later), docs/local-storage.md;
- the project memory notes (CPU tooling; Git Bash -> WSL gotchas).

Context:
- D2C4 (89bbe60ab1) is installed; last known-good is c027a92857.
- On the one D2C4 drive (0x28): twitch -42% vs A-primary (its calmer twitch-band request matches the midday A drive 0x20, so probably daylight), weave up (lane 0.2-0.7 Hz +41%).
  - Session 12mv: B's request itself weaved 32% more (above every same-road A drive, at matched speed). The pre-registered rule called it
    exogenous, but the follow-up (findings §6) revised that: D2C4 is the most likely cause, acting through the closed loop.
- Offline, no milder variant passed Amendment 8. All add 15-19 deg of small-signal weave-band lag (D2C4 22 deg). The deadzone
  causes about as much as the filter. MV3/MV2 halve D2C4's transient cost but are expected to weave about as much.
- The lane -> request (outer-loop) ARX model was not adequate, so weave was ranked by a declared phase-lag proxy.

This session:
1. Confirm the workspace (dragal/custom @ 89bbe60ab1 clean, WSL clone clean, E: identity/space) and which B drives exist.
   No device access unless I authorize it.
0. First read docs/findings/2026-10-07-g70-milder-variants.md §7-8 (weave root cause: about 18 deg of lag at 0.2-0.4 Hz, half C4, half the deadzone; the model matches the car in that band) and the handoff §12.
2. If new same-road B drives exist: re-run session 12mv's step 2a (s15_mv_2a.py logic; its M1-M5 metrics and decision rules
   unchanged) with B = all D2C4 drives on B's road and A = the same A arms. Pre-register the added data first. Report whether
   B's request weave and request -> wheel lag differ from A, and per drive and by light condition.
3. Optional (offline): an outer-loop model v2, pre-registered before computing.
   - Candidates: instrumental-variable identification of lane -> request; lane lags >= 1 frame; heading from the full lane-line
     geometry (needs a new extraction from the rlogs).
   - Validate it against 0x28 and the new B drives exactly as session 12mv §2.3 V1/V2 defined. Only an adequate model may
     re-rank MV1-MV9.
4. Report to me: keep D2C4, roll back to c027a92857, or prepare MV3/MV2 (code, tests, two-round QA, artifacts, an A/B
   protocol whose weave criteria include the request's own 0.2-0.7 Hz band). Stop and ask before any code change on
   dragal/custom or any device action.
5. Keep the changelog, findings and handoff/kickoff discipline (CLAUDE.md §7). Outputs go to analysis/g70-weave-attr-<date>/.
   New scripts go in new files (s16_*); shared scripts are not edited.
```
