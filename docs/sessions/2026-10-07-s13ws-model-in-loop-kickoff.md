# Kickoff prompt: run the driving model in closed loop (M4(c)) to rank twitch fixes on simulated lane weave (copy-ready)

```text
Resume the dragalpilot project at C:\Users\dre\Documents\DragalPilot\dragalpilot.

Read, in order:
- CLAUDE.md;
- docs/sessions/2026-10-07-s13ws-weave-twitch-sim-handoff.md (main thread);
- docs/findings/2026-10-07-g70-weave-twitch-sim.md (§3 rule, §6-7 frontier and F7, §8 the driving model offline, §9 review, §10 options);
- docs/findings/2026-10-07-g70-milder-variants.md §7-8 (weave root cause on the car);
- CHANGELOG.md (sessions 12mv, 13ws), docs/local-storage.md, docs/baseline.md (offline driving model row);
- the project memory notes.

Goal: run the real driving model in closed loop with our steering simulation (offline only), check that it reproduces D2C4's on-car
weave, and if it does, rank F7d, S1, S2 and D2C4 on simulated lane weave. No device access. No change to dragal/custom or the WSL
clone without asking first.

Steps:
1. Confirm the workspace:
   - outer main @ 606c36b + uncommitted docs;
   - dragal/custom @ 89bbe60ab1 clean; WSL clone clean; no WSL jobs;
   - E: UniqueId, writability, free space;
   - whether a parallel session is running.
2. Ask the user the two open questions from the handoff §8 if still unanswered:
   - run M4(c)?
   - is F7d's cut in the visible step rate (about -40%, step size unchanged) worth pursuing (complaint clarified: findings §10.5)?
3. Design M4(c) and pre-register it (new amendment in the weave-twitch-sim findings) before any closed-loop result:
   - Loop per model frame (20 Hz), on the M4(b) windows (0x1e, 0x22, 0x24; add more windows by Amendment 11a's rule if time allows):
     - logged frames are re-warped by the simulated deviation from the logged path: lateral via the camera_offset_helper shear,
       heading via the calibration yaw; signs as findings §8.4;
     - the model output becomes the request = logged request + (model_sim - model_base on the same frame);
     - the request feeds the s16_ws_twin inner loop and bicycle model (reuse s16_ws_twin.py's vehicle code; replace the linear policy
       with the model output; frame -> controls latency 0.067 s as findings §8.3).
   - The model's recurrent state must follow the simulated trajectory: one model instance per closed-loop run. A matching base run
     is needed for the request difference (or use the logged request directly, if the reproduction r 0.9997 justifies it; decide and
     pre-register).
   - Adequacy (A0 in the loop vs logged): jumps, hold, T, W within the Amendment 12 V1 bounds; lane and request 0.2-0.7 Hz RMS ±40%;
     no divergence.
   - Reproduction (D2C4 vs A0 in the loop): direction and size vs the on-car deltas: request weave +32% (CI +13…+51%), lane weave
     +41% (+20.5…+65.4%), 0.2-0.4 Hz lag about +18°. With only about 6 min of windows, state the statistical power honestly.
   - Only if adequate and reproducing: rank F7d, S1, S2 (and D2C4) on simulated lane-offset 0.2-0.7 Hz (the §3 rule's
     outer-loop criterion) plus the inner-loop rule.
   - Compute: the model takes about 0.25 s per frame per core; run windows/variants in parallel on all 6 cores (single-threaded each).
4. Get a focused adversarial review of the new closed-loop code and of the untested twin code (s16_ws_twin*.py, s16_ws_polfit.py).
5. Report the result and options. Stop and ask before any change on dragal/custom. A car candidate later needs:
   - code, tests, full two-round QA;
   - artifacts and a dry run;
   - a proposal with an on-car A/B whose weave criteria include the request's 0.2-0.7 Hz band, the 0.2-0.4 Hz request -> wheel lag,
     the lane offset and the reversal latency.
6. Keep the changelog, findings and handoff/kickoff discipline (CLAUDE.md §7). Label source facts, observations, model results and
   hypotheses. Missing data is unknown.
```
