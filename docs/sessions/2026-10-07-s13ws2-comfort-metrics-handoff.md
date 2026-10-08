# Handoff: end of session 13ws (2026-10-07, later part): the twitch metrics are not validated; next, build comfort and twitch measures that match the driver's experience

- **Main thread.** Supersedes [2026-10-07-s13ws-weave-twitch-sim-handoff.md](2026-10-07-s13ws-weave-twitch-sim-handoff.md), which remains the record of the session's simulation work. This handoff adds everything after it and changes the next step.
- **Kickoff:** [2026-10-07-s13ws2-comfort-metrics-kickoff.md](2026-10-07-s13ws2-comfort-metrics-kickoff.md).
- **Token usage:** well past the 250–300k soft target by the context counter; no per-session meter.
- Reconfirm everything at the next session start.

## 1. Objective (restated by the user)

- **"Ultimately it's driving comfort that we're trying to improve."**
- Two comfort problems:
  - a slow **weave** (0.2–0.7 Hz lane offset);
  - a faster **twitch**: the steering wheel visibly stepping by itself while the comma drives, even on straight roads, with the faster comfort upset that comes with it.
- **The complaint, clarified by the user:** the wheel constantly twitching while the comma drives. It is not about feel in the hands.
- The user has driven a lot with the car's own LKA engaged (before the comma) and **never noticed this twitchiness**.

## 2. User instructions and decisions (this session, after the first handoff)

- **Dither is not acceptable** (unnecessary steering-rack wear). It is closed and must not be proposed again.
- Asked for:
  - the component lineage of the 2024 G70 ("V1.5");
  - the torque limits and `ADRV_0x51`;
  - the impact of a faster torque rise;
  - the full list of tunables (the user wanted every tunable, not only those tried);
  - V0 vs V1;
  - NNLC and how to train it;
  - the most logical path.
- **User challenge (decisive):** "Is there a possibility that how we are calculating stick slip is wrong? … we've introduced an assumption or a variable at some point that has contaminated our findings." **Accepted** (§4.1).
- **User direction:** also consider lateral vehicle movement, i.e. the weave plus the faster comfort upset. Comfort is the goal.
- **Standing:**
  - no device access, install or reboot without explicit authorization;
  - no change to `dragal/custom` or the WSL clone without asking first;
  - tool installs and read-only pulls are authorized (CLAUDE.md §6, memory);
  - the VM is dedicated (all cores, bit-identical parallelism);
  - the outer docs commit has not been requested.

## 3. Revisions and workspace (unchanged since the first handoff; reconfirm)

- Baseline `dev` @ `0b2c431d3a`.
- `dragal/custom` @ `89bbe60ab1` (D2C4 installed on the car since 2026-10-07 13:33 EDT; last known-good `c027a92857`). Clean, not pushed.
- WSL clone @ `89bbe60ab1`, clean.
- **Outer `main`** @ `606c36b` + uncommitted docs: sessions 8–13ws, including the new findings docs `2026-10-07-g70-weave-twitch-sim.md` and `2026-10-07-g70-lateral-tunables.md`, the fingerprint findings update, both 13ws handoff/kickoff pairs, CHANGELOG, `docs/baseline.md` and the sessions README.
- **No device access and no SSH** this session. No jobs running.

## 4. What is known now

### 4.1 The twitch metrics are not validated (findings §12.1): treat twitch conclusions as provisional

- **The project's twitch measures do not separate the comma from manual or stock driving:**
  - jumps/min (≥ 0.3° within 150 ms ≈ 2°/s) and T (0.7–4 Hz angle RMS);
  - a stricter hold-step metric (0.3 s hold within 0.1°, then ≥ 0.3° within 150 ms) fires **31–35/min in manual driving**, 20–27 under openpilot, and 18–20 under the stock LKA (6 min sample).
- **Why:** with the 0.1° angle sensor (every angle signal on the car is 0.1°: SAS11, MDPS11, ADRV_0x51), angle alone can't tell creeping from stuck, or a stick-slip jump from a deliberate quick correction.
- **Ruled out as contaminants** (findings §12.1):
  - our LKAS11 frame timing (exactly 100 Hz);
  - EPS torque-overlay dropouts (0.012%, unrelated to jumps).
- **Still established** (session 10): under openpilot the wheel video shows hold-and-jump, and the torque command ramps while the wheel holds, then breaks free.
- **Not established:** that jumps/min or T track the perceived twitch; that the stock LKA behaves the same; why the comma looks twitchier.
- **Provisional:** every twitch result scored on jumps/T, including D2C4's offline selection, its on-car "−42% jumps", MV1–9, F1–F8/F7d, and the frontier (§6–7, §10 of the weave-twitch findings).
- The **weave** findings (0.2–0.4 Hz lag +18° on the car, reversal latency +0.6 s, lane offset +41%) do not depend on these metrics and stand (one B drive).

### 4.2 Platform facts found this session (fingerprint findings, update sections)

- `GENESIS_G70_2024` is its own platform, but the steering path is the shared Hyundai classic-CAN controller with default limits (384 / +3 / −7).
- **No other car shares the EPS (a new firmware family) or the radar.**
- **The radar is the CAN-FD generation:** bus-1 traffic matches opendbc's CAN-FD FRONT_RADAR messages plus ADRV_0x51 exactly.
- `ADRV_0x51` relays the steering angle (0.1°), the yaw rate (about 0.01°/s per count) and the speed. **It is the only car-side yaw-rate source**; carState.yawRate is 0.
- **Stock LKA torque:** max 218 observed (8.8 min; a lower bound), steps up to 7 / 6 per 10 ms. Our up-rate limit binds in 67% of rising steps.
  - A faster rise changes the simulated twitch/weave very little and would fail comma's ISO 11270 jerk test above +4.
  - MAX_LAT_ACCEL_MEASURED (2.7) is an unverified guess.
- **The panda always blocks the camera's LKAS11 while openpilot runs** (`check_relay`).
  - About 6 min of the logs were nevertheless steered by the stock LKA, in `elm327` pass-through with the EPS active. Which drives, and why, is not identified.

### 4.3 Other references

- **Tunables:** [2026-10-07-g70-lateral-tunables.md](../findings/2026-10-07-g70-lateral-tunables.md) (117 items, source-verified in part); weave-twitch findings §11 (the tested parameters and their effects).
- **V1:** the upstream controller, selectable with `EnforceTorqueControl` + `TorqueControlTune` = 1.0. It compares the measurement with the delayed request, has KP 0.8 / KI 0.15, and a friction input of error + 0.3 × look-ahead jerk with a 0.2 m/s² ramp. Untested on the stick-slip model.
- **NNLC:** it would fall back to the older-G70 model (similarity 0.815). Training needs [sp-nnlc-docker](https://github.com/CHendrick00/sp-nnlc-docker) (NVIDIA CUDA GPU; this VM has none). Not recommended for the twitch.
- **The driving model runs offline** (CPU, r 0.9997). The real policy was probed open-loop (findings §8.5); the outer-loop twin is built and checked (§8.3) but not used (the policy is not linear).

## 5. Tooling added after the first handoff (`E:\DragalPilot\scratch\wsl\sng\`)

| Script | Purpose |
|---|---|
| `s16_ws_bus1.py` | Bus-1 address inventory vs the CAN-FD DBC |
| `s16_ws_lkas_adrv.py`, `s16_ws_adrv_decode.py`, `s16_ws_adrv_scale.py` | Stock vs our LKAS11 limits; ADRV_0x51 decode and scales |
| `s16_ws_dup.py` | Simulated torque-rise limits (bit-exact at +3) |
| `s16_ws_nnlc_match.py`, `s16_ws_nnlc_json.py` | NNLC model matching and format |
| `s16_ws_stock_lka.py`, `s16_ws_stock_sticks.py`, `s16_ws_holdstep.py` | Who steered (stock vs comma); angle metrics by source (stock / openpilot / manual) |
| `s16_ws_eps_events.py` | TX timing, EPS dropouts vs jumps |
| `s16_ws_srcprobe.py` | CAN source codes (src 128 = our TX echo, 130 = forwarded to the camera) |

- These run in the checkout venv (no scipy; numpy FFT band-pass where needed).
- Outputs: `analysis/g70-weave-twitch-sim-20261007/platform/`. Logs: `logs/s13ws-*`.

## 6. QA status

- Focused review done for the `s16_ws_*` simulation and analysis code and s12mv's root-cause scripts (findings §9).
- **Not reviewed:**
  - the twin code;
  - the probe agent's `s13ws_model/*`;
  - all scripts listed in §5 above (read-only analyses, written after the review).

## 7. Open questions

- What measure tracks the driver's experience of the twitch? Candidates are in the kickoff.
- Does the stock LKA produce the same steering-caused lateral upsets as the comma on the same road?
- Why does the comma look twitchier than the stock system, if it does by a valid measure? The command shape and the LKAS11 field contents are untested.
- Carried over: D2C4 keep or roll back (user's call); M4(c), the driving model in closed loop; the videos of `0x26`–`0x28`; more B drives.

## 8. Ordered next steps

1. Next session: the [comfort-metrics kickoff](2026-10-07-s13ws2-comfort-metrics-kickoff.md). Build and validate comfort and twitch measures before any further fix work.
2. Then re-score D2C4 on the car and the offline candidates with the validated measures; then M4(c) if still warranted.
3. Any car change: ask first, then code, tests, two-round QA, artifacts, a dry run, and a proposal with an on-car A/B on the validated measures.
