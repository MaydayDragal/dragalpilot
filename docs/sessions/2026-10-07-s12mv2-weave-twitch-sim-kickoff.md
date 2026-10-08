# Kickoff prompt: refine D2C4 offline into a fix for both weave and wheel jitter, and explore new analysis/simulation methods (copy-ready)

```text
Resume the dragalpilot project at C:\Users\dre\Documents\DragalPilot\dragalpilot.

Read, in order:
- CLAUDE.md;
- docs/sessions/2026-10-07-s12mv2-weave-twitch-sim-handoff.md (main thread; it lists everything known, the tools and the data);
- docs/findings/2026-10-07-g70-milder-variants.md (§3 results, §6 follow-up, §7-8 weave root cause);
- docs/findings/2026-10-07-g70-d2c4-validation.md (Amendments 5-8: metrics, transient tests, decision rules);
- docs/findings/2026-10-07-g70-twitch-root-cause.md (§7: stick-slip mechanism, candidates tried);
- docs/findings/2026-10-04-g70-weave-sim.md (session 6: plant gain vs latAccelFactor, v0k);
- CHANGELOG.md (sessions 11, 11r, 12mv), docs/local-storage.md;
- the project memory notes (CPU / AVX-512 tooling; Git Bash -> WSL gotchas).

Goal: starting from D2C4, find a change that keeps D2C4's steering-wheel jitter reduction AND does not make weave worse.
Work offline and in local simulation only ("Let's see how far we can get with this while simulating locally").
- No device access.
- No change to dragal/custom or the WSL clone without asking me first.
- The deliverable is an evidence-backed recommended candidate, or an honest frontier if none exists.

What we know (details in the handoff §4):
- Twitch: a stick-slip limit cycle. Steering static friction + V0's error-driven friction term (and P) keep ramping torque on
  small errors while the wheel is stuck; small fast request jitter keeps re-triggering it.
- D2C4 = 0.4 deg friction deadzone (D2) + 2 Hz request low-pass (C4). It roughly halves the twitch.
- Weave root cause (car, one drive; the model agrees in this band): at 0.2-0.4 Hz, D2C4 adds about 18 deg of
  request -> wheel lag: 8 deg from C4 and 10 deg from the deadzone. The deadzone part is small-signal: small corrections
  are weaker and later, and the wheel is held longer. Lane keeping loses phase margin at its weave frequency.
- The model's 0.2-0.4 Hz in-context lag matches the car for D2C4. Its 0.4-0.7 Hz lag does not, and it over-predicts holds.
- None of MV1-MV9 (deadzone sizes or shapes, higher cutoffs, shelf, friction-path filter) gives back more than about 5 deg:
  each keeps a deadzone >= 0.3 deg.

Steps:
1. Confirm the workspace:
   - outer main @ 606c36b + uncommitted docs;
   - dragal/custom @ 89bbe60ab1 clean; WSL clone clean; no WSL jobs;
   - E: UniqueId, writability, free space.
   Check whether a parallel session is running (if so: <= 4 CPU workers, no in-place edits of shared scripts,
   append-only edits of CHANGELOG / sessions README / CLAUDE.md).

2. Brainstorm first, before running anything. Write the brainstorm into a new findings doc.
   Aim: new ways to analyse the data or simulate the tests that this project has NOT used yet, which could reveal new data
   or new approaches. Be concrete and creative, then rank by expected information per effort, risk and validity.
   Consider at least these, and add your own:
   - Closed-loop digital twin: stick-slip plant + opendbc dynamic bicycle model + a lane-perception noise model + a lane
     keeping policy. The policy could be identified better than session 12mv's ARX (instrumental variables, lane lags >= 1
     frame, heading from the full lane-line geometry), or taken from the driving model itself.
   - Driving model in the loop. The checkout has modeld + the tinygrad driving model, process_replay/model_replay.py,
     tools/sim (simulator bridge) and tools/lateral_maneuvers.
     - Can the real model run on this x86 VM (CPU)?
     - Can logged road video frames be reprojected or warped to a simulated lateral offset and heading, so the model's
       real response to the car's position is measured offline?
     - Can a simulator (e.g. MetaDrive through tools/sim) give closed-loop lane keeping with our controller + plant?
     Discover what this checkout supports; don't assume older structure.
   - Describing-function / harmonic-balance analysis of the deadzone + stiction + lane-keeping loop: predict the
     weave limit-cycle amplitude and frequency analytically and compare with the logs.
   - Loop-gain / phase-margin estimation from natural excitation on the logs (A vs B), per amplitude.
   - Event-triggered averaging (around holds, jumps and lane-offset peaks); time-frequency (wavelet) analysis of weave
     episodes; position-aligned comparison of drives on the same road (GPS) to cancel road curvature.
   - The gyro yaw rate as ground truth for vehicle motion; road video for lane position (classical lane-marking
     measurement, as session 5 did).
   - Surrogate / Bayesian optimisation over a parametric controller family with constraints, on AVX-512 lane-batched
     simulation (s13_simd2 prototype) after a bit-identity check.
   - Plant-uncertainty Monte Carlo, to rank candidates by robust rather than nominal performance.
   Also brainstorm new FIX directions not yet tried, for example:
   - a frequency-split deadzone (deadzone only on the fast part of the error, so slow small errors keep friction
     compensation);
   - phase-lead compensation at 0.2-0.4 Hz to cancel D2C4's lag;
   - a deadzone or hysteresis on the request jitter instead of the error;
   - P/I behaviour inside the band; a stiction-aware breakaway pulse or dither;
   - a speed-scheduled feedforward gain (session 6's v0k);
   - combinations.
   Never propose bypassing safety checks or widening safety limits (CLAUDE.md §2).
   Present the ranked brainstorm and a proposed plan to me, and get my OK before the large runs.

3. Before any candidate result, pre-register (an amendment in the validation findings, or the new findings doc):
   - candidates (D2C4 and A0 as references) and the plants (E4 primary, E2+E3 secondary);
   - eras (E2/E3 primary, E1/E4 secondary);
   - one decision rule, chosen before looking. Proposal to confirm with me:
     - twitch: jumps >= 40% and T >= 30% lower than A0;
     - weave: 0.2-0.4 Hz in-context added lag <= 5 deg and gain within +-10% of A0 (this is the car-validated band;
       0.4-0.7 Hz is reported only), plus simulated W not up; with an adequate outer-loop twin, also simulated
       lane-offset 0.2-0.7 Hz not up;
     - tracking: mean error not up > 20%;
     - transients R1-R5 / C1-C3 reported (they rank, they don't fail);
   - every result reports wheel jitter, weave and comfort (steering-proxy).
   Any new model (outer-loop twin, model-in-the-loop) must first reproduce, pre-registered, the on-car D2C4 result:
   - 0.2-0.4 Hz lag about +18 deg (split 8 / 10);
   - request weave up; lane weave up;
   - jitter down; tracking about +27%; curve lag about +0.09 s.
   Only an adequate model may rank candidates on simulated weave.

4. Run with the existing harness:
   - s15_mv_var.py install() pattern: add new options in NEW files that copy the loop, with a bit-identity check against
     s11_eval.simulate before use;
   - s15_mv_grid / s15_mv_transient / s15_mv_curves / s15_mv_summary;
   - adopt s13 speed-ups only if bit-identical.
   Use all cores (CLAUDE.md §8) unless a parallel session runs. Outputs go to analysis/g70-weave-twitch-sim-<date>/,
   logs to logs/s13ws-*, scripts to s16_ws_* (new files only).

5. Report:
   - the trade-off frontier (twitch reduction vs 0.2-0.4 Hz lag vs tracking/transient cost);
   - the best candidate(s), with what the model can and cannot show.
   Get a focused adversarial review of the new analysis code (and of session 12mv's root-cause scripts s15_mv_rc.py,
   s15_mv_2a_followup.py, s15_mv_loband.py, still pending).
   Then stop and ask me before any code change on dragal/custom. A candidate for the car later needs:
   - code, tests and full two-round QA (CLAUDE.md §5);
   - artifacts and a dry run;
   - a proposal with an on-car A/B whose weave criteria include the request's own 0.2-0.7 Hz band, the 0.2-0.4 Hz
     request -> wheel lag and the lane offset.

6. Keep the changelog, findings and session handoff/kickoff discipline (CLAUDE.md §7). Checkpoint during long runs.
   Distinguish source facts, observations, model results and hypotheses. Missing data is unknown.
```
