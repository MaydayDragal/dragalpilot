# Handoff: end of session 13ws (2026-10-07): D2C4 refinement offline; F7 breakaway release; the real driving model runs offline

- **Main thread.** Supersedes [2026-10-07-s12mv2-weave-twitch-sim-handoff.md](2026-10-07-s12mv2-weave-twitch-sim-handoff.md).
- **Kickoff:** [2026-10-07-s13ws-model-in-loop-kickoff.md](2026-10-07-s13ws-model-in-loop-kickoff.md) (M4(c), the driving model in closed loop). It needs the user's OK before its large runs.
- **Token usage:** about 290k cumulative by the context counter; no per-session meter.
- Reconfirm everything at the next session start.

## 1. Objective

- Make sunnypilot drive the user's 2024 Genesis G70 well.
- The complaints: the steering wheel is twitchy on straight roads, and the car weaves.
- **This session:** starting from D2C4 (installed), find offline a change that keeps D2C4's twitch reduction and does not worsen weave, or report an honest frontier. Explore new analysis and simulation methods.

## 2. User instructions and decisions (this session)

- Kickoff: [s12mv2 weave + twitch simulation](2026-10-07-s12mv2-weave-twitch-sim-kickoff.md). Offline and local simulation only.
- **"All approved"** (about 18:40 EDT): the brainstorm plan (phases A → B, phase C driving model in parallel); the decision rule (§3 of the findings) with a "partial" tier; downloading the driving model ONNX.
- **Standing:**
  - no device access without explicit authorization;
  - no change to `dragal/custom` or the WSL clone without asking first;
  - tool installs and read-only pulls are authorized (CLAUDE.md §6, memory);
  - the VM is dedicated (use all cores; bit-identical parallelism);
  - the outer docs commit has not been requested.

## 3. Exact revisions and workspace (confirmed 2026-10-07 ~19:35 EDT)

- **Baseline:** `dev` @ `0b2c431d3a…` (unchanged).
- **`sunnypilot/`:** `dragal/custom` @ **`89bbe60ab127cf71d238856a19c1e74b16bc36bd`** (D2C4), clean, not pushed. **WSL clone** `~/src/sunnypilot` @ `89bbe60ab1` (detached), clean.
- **Device:** D2C4 installed since 2026-10-07 13:33 EDT (last known-good `c027a92857`). Not accessed this session. No SSH.
- **Outer `main`** @ `606c36b` + 40 uncommitted doc paths:
  - sessions 8–13ws;
  - this session adds the findings doc, this handoff/kickoff pair, and edits to CHANGELOG, `docs/baseline.md` and `docs/sessions/README.md`.
- **Data root `E:`:** UniqueId `daa460f7…`, about 228 GB free.
- **WSL:** no jobs running; apt `clang` 18 + llvm-18 were installed this session.

## 4. What is known (details: [findings](../findings/2026-10-07-g70-weave-twitch-sim.md))

### 4.1 Frontier and mechanism (model results; logs where marked)

- **No candidate meets the pre-registered rule** (twitch: jumps ≥ 40% and T ≥ 30% down; weave: 0.2–0.4 Hz added lag ≤ 5°, gain ±10%, W not up; tracking ≤ +20%). None reaches the partial tier (lag ≤ 9°).
  - The search (§7.7) puts T −30% at about 10.5° of lag.
- **Why (observation, car logs; the model agrees):** jumps happen as the slow request turns back from a swing, and they move the wheel toward the request (97–99%). The stick-slip is how the wheel follows slow small corrections. A deadzone or filter therefore delays exactly what lane keeping needs.
  - **On the car, D2C4 starts small corrections 0.4–0.6 s later** (reversal latency 1.56 vs 0.92 s, small bin; §6.4 ii).
- **F7, the breakaway release:** when the angle moves after ≥ 10 unchanged cycles, the controller subtracts R·(1 − j/10) from the normalized torque, in the direction of motion, for 10 cycles.
  - **F7d (R 0.052):** jumps −40 / −41%, T −14 / −18%, lag +3.4 / +4.6°, tracking +2%, 1 transient flag (D2C4: 8), curve-window error +3% (D2C4: +28%).
  - **S1** (F7a + feedforward ×1.1): jumps −41 / −44%, T −16 / −20%, lag +4.1°, tracking 0%.
  - **Fails at td ×1.5** (robustness). The logs favour the fitted delay (EPS torque t50 about 23 ms, jump rate) but don't exclude a longer one.
- The F7-based frontier dominates D2C4: about 6° less lag and a quarter of the tracking cost at equal T. But any point with T ≥ 30% still adds ≥ 11.5° of lag.
- Earlier candidates (C1–C6, D1–D3, J1, H1, P1, MV1–MV9), F1–F4 and F6 (lead) are all on or below the frontier (§6.2).

### 4.2 The driving model offline (§8)

- `driving_supercombo.onnx` (upstream LFS, sha256 `659727c4…`; the installed model, matched by checkpoint string) is CPU-compiled with the checkout's tinygrad. It reproduces the logged modelV2 at r 0.9997 (verified by the coordinator).
- **M4(b), open-loop policy probing** on 3 windows (`0x1e`, `0x22`, `0x24`; 360 s): the policy is a phase-leading corrector.
  - P_y gain 1.1 → 4.0 m/s² per m over 0.11–0.71 Hz, phase −123…−138°; P_ψ 20–30 m/s² per rad.
  - **Not linear** (13–23% less gain at half amplitude). By the pre-registered rule the linear outer-loop twin is not built.
- Sign conventions: lane y right-positive; desiredCurvature right-positive; a +shear means the car sits right; a +yaw means the car heads right. A corrective policy has a negative transfer.

### 4.3 QA

- **Focused review** (one independent agent) of the `s16_ws_*` analysis and of s12mv's root-cause scripts (`s15_mv_rc.py`, `s15_mv_2a_followup.py`, `s15_mv_loband.py`): no blocker or major; 1 minor fixed; others recorded (findings §9).
- **Not reviewed:** the twin code (`s16_ws_twin.py`, `s16_ws_twin_eval.py`, `s16_ws_twin_check.py`, `s16_ws_polfit.py`) and the probe agent's `s13ws_model/*` scripts (their key outputs were independently re-computed by the coordinator).

## 5. Tooling

| Path (`E:\DragalPilot\scratch\wsl\`) | Purpose |
|---|---|
| `sng/s16_ws_var.py` | Harness: `closed_loop_ws` (= s15 loop + F1–F4, F7 incl. adaptive), `simulate_ws` (+ probe, lead-lag), `install(f7star)` (WS, WS2, combos). Bit-exact with options off. |
| `sng/s16_ws_grid.py`, `s16_ws_grid2.py`, `s16_ws_summary.py` | Grid (twitch/weave proxy/tracking), variant-list override, decision table. |
| `sng/s16_ws_lockin.py`, `s16_ws_m6.py`, `s16_ws_m6sign.py`, `s16_ws_jprof.py`, `s16_ws_delay.py` | M1 lock-in; M6 jump trigger / reversal latency; jump profile; command → EPS delay. |
| `sng/s16_ws_transient.py`, `s16_ws_curves.py`, `s16_ws_robust.py`, `s16_ws_search.py` | Transients and curves via the new loop; F7 robustness; M9 search. |
| `sng/s16_ws_twin.py`, `s16_ws_twin_eval.py`, `s16_ws_twin_check.py`, `s16_ws_polfit.py` | Outer-loop twin (bicycle model + linear policy), eval on the A-primary drives, checks (T1 bit-exact, T2 vehicle steady state), policy fit. Ready; not used (policy not linear). |
| `sng/run_s16_ws.sh <tag> <script> args` | Runner (`~/venvs/vid`, logs `logs/s13ws-<tag>-*`). |
| `s13ws_model/run_model.py`, `m4b_run.py`, `m4b_estimate.py`, `extract_refs.py`, `extract_m4b.py`, `r_*.sh` | Driving model on CPU: reproduction, probe runs with shear/yaw (base/probe/half variants share one JIT), estimator. |

- **Outputs:** `E:\DragalPilot\analysis\g70-weave-twitch-sim-20261007\` (`a9`, `a10`, `a10fix`, `a10s2`, `a10t`, `a10d`, `m6`, `twin`, `model_probe`).
- **Model:** `E:\DragalPilot\cache\s13ws_model\`.
- **Speed:** the model takes about 0.25 s per frame per core (single-threaded tinygrad CPU), so about 11 min per 130 s window per variant per core.

## 6. Validation limits

- Everything is offline model evidence plus log observations. The car evidence for D2C4's weave is one B drive.
- No logged era is untouched by candidate selection.
- The plant is Karnopp friction without pre-sliding (M5 not done). The actuator delay is uncertain, and F7 depends on it.
- 55+ mph only.
- The M4(b) windows are 3 (`0x20` excluded by the mean-curvature rule). Reprojection is exact on the road plane only.

## 7. Running operations, device, SSH

- None running: no background agents, no WSL jobs.
- No device access and no SSH this session.

## 8. Open questions

- **Complaint clarified by the user (findings §10.5):** the wheel visibly steps by itself while the comma drives, even on straight roads; it is not about feel in the hands. Open: is F7d's cut in step rate (about −40%, step size unchanged) worth pursuing? F9 (dither) is ruled out by the user (rack wear).
- Does the driving model in closed loop (M4(c)) reproduce D2C4's on-car weave? If yes, how do F7d/S1/S2 rank on simulated **lane weave**?
- What is the actual command → rack delay? (It decides F7's benefit.) The on-car reversal latency would test it.
- Carried over: the D2-only / C4-only on-car isolation; the videos of `0x26`–`0x28`; the driver's assessment of the B drive; 35–55 mph; stop-and-go.

## 9. Ordered next steps

1. **User decision:** M4(c), per the [kickoff](2026-10-07-s13ws-model-in-loop-kickoff.md); and/or the twitch-meaning question.
2. If M4(c) runs: pre-register its reproduction first, then rank the candidates.
3. Any car candidate (F7d/S1): ask before any `dragal/custom` change. Then code, tests, two-round QA, artifacts, dry run, and a proposal with an on-car A/B (weave criteria: the request's 0.2–0.7 Hz band, the 0.2–0.4 Hz request → wheel lag, the lane offset, the reversal latency).
4. The outer docs commit, when the user asks.
