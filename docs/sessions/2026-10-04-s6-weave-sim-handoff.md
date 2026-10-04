# Handoff: session 6 (2026-10-04): offline weave simulation

Written 2026-10-04 ~16:35 EDT. Reconfirm everything at the next session start.

## Objective

Make sunnypilot drive the user's 2024 Genesis G70 well. This session tested offline whether removing the delay from V0's error, or running upstream v1, would reduce the ~3 s weave.

## User instructions and decisions (this session)

- Commit and push the session-4b docs: done, `c0b25c1` pushed.
- Delete `E:\DragalPilot\temporary\device-pull-20261004d\pull.tar`: done. 7.88 GB and the empty segment folders were removed; small logs and manifests kept; logged in `logs/promote-20261004d.log`.
- Run the offline weave simulation: done. No device access.
- The VM resources were increased; WSL may be adjusted as needed. Not needed: the WSL defaults give 6 CPUs / ~15 GB.
- **Standing (memory):**
  - video pulls/analysis authorized, with §6 mechanics;
  - tool installs on host/WSL authorized;
  - no test re-runs for docs-only commits;
  - stay on the default driving model;
  - reboots and device changes need explicit per-action authorization.

## Exact revisions

- sunnypilot baseline `dev` @ `0b2c431d3abab630df0a32f53236944855a91aa3` (unchanged).
- `dragal/custom` @ `82f58a9a8c4af2f10d23d13fb1631deca98d4efd`, deployed and clean; WSL clone the same, clean.
- **Outer repo `main`:**
  - `c0b25c1` (4b docs) pushed.
  - `d7fd6b3`: session 5 (video lane check, parallel session); pushed together with this session's commit (user-approved).
  - **This session's docs** are in the commit after `d7fd6b3` (pushed, user-approved):
    - `CHANGELOG.md` (session 6 entry);
    - `docs/findings/2026-10-04-g70-weave-sim.md` (new);
    - `docs/findings/2026-10-04-g70-lowspeed-drives.md` (appended result section);
    - this handoff and kickoff;
    - `docs/sessions/README.md`.

## Completed work and evidence

Full write-up: [docs/findings/2026-10-04-g70-weave-sim.md](../findings/2026-10-04-g70-weave-sim.md).

- **Harness:**
  - The source classes run on x86 with the extension stubbed (`s5_ctrl.py`).
  - Source replay vs logs (setpoint exact, carOutput exact 81–95%).
  - Fast re-implementation (`s5_fast.py`) equals the source (≤ 6e-8).
  - Timing: command k → carOutput k+1; steer-limited compares with the output from two cycles back.
- **Plant per band:** overdamped; K 0.89 / 1.21 / 1.29 (20–35 / 35–55 / 55+ mph); held-out VAF 0.91–0.95.
- **Simulation:** V0, v0e, v1 and exploratory v0k, in clean and disturbance-replay modes, on the fit routes (8/0a/0b) and held-out routes (6/7). Synthetic steps and sines.
- **Result:**
  - v0e and v1 fail the criteria; v0e adds 11–21° of lag with almost no gain change.
  - **No device change proposed.**
  - The model points to feedforward scale vs plant dynamic gain at 35+ mph (hypothesis). The vehicle link B (1.21–1.34 at 0.4–0.6 Hz) alone exceeds the C ≤ 1.2 criterion.
- **Artifacts:**
  - scripts `E:\DragalPilot\scratch\wsl\s5\` (`run_s5_batch3.sh` reproduces the final runs);
  - outputs `E:\DragalPilot\analysis\g70-weave-sim-20261004\` (`criteria_tables.md`, `sim_val_r67.json`, `sim_fit_r8ab.json`, `step.json`, `plant_*.json`, `replay_check.json`, `equiv_check.json`; `sim_batch1_superseded_timing.json` is superseded);
  - logs `E:\DragalPilot\logs\s5-*.log`.

## Open hypotheses / questions

- The weave at 35+ mph comes from the feedforward/P scale vs the plant's dynamic torque gain plus its lag, with the vehicle's yaw overshoot on top. Hypothesis; model-based.
- The low-speed weave the user feels is not explained: the model under-predicts the 20–35 mph 0.4–0.6 Hz gain. Candidates: driver hands, friction behaviour, the outer loop through model re-planning, the request itself.
- Whether C ≤ 1.2 is a reachable criterion at 35+ mph (B > 1.2 there).

## Device state and SSH

Not accessed this session. Last observed (session 4b, 18:56Z): `.104`, offroad, `GitCommit=82f58a9a8c`. No SSH connection open.

## QA stages

Analysis only; no code changes. QA not applicable. Code from earlier rounds: focused review done; two-round QA not performed.

## Ordered next steps (user decisions)

1. (Done: session 6 docs and session 5's `d7fd6b3` committed and pushed.)
2. Choose a direction (findings doc "Options"):
   - (a) no change for now;
   - (b) a car-scoped speed-dependent feedforward scale as a new offline hypothesis, validated on new held-out drives, with the criteria revisited;
   - (c) more data first: engaged 20–35 mph and stop-and-go, plus a torqued validity drive.
3. Later: the Hyundai 0x484 forwarding-rule round; keep watching the bus-1 start-up burst.
