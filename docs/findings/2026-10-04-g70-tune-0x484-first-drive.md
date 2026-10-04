# G70 2024: first drive after the tune + 0x484 deployment (2026-10-04)

Software: `dragal/custom` @ `82f58a9a8c`, panda firmware `206ea19c…` (initData and the deployment record). Evidence type: **observations from rlogs** of 2 routes plus the user's report. The comparison is against routes 6/7 (same morning, same software except the tune and firmware). The roads and conditions were not controlled, so this is a before/after observation, not a controlled experiment.

## User report

- "Definite improvement, subjectively ~75%." Some ping-pong and oversteer in curves remains, also improved.
- The only takeover was a sharper curve where the steering limits didn't allow enough torque. The user considers this expected and asked that it not be investigated.

## Data

| Route | Start (EDT, GPS) | Length | Lateral engaged |
|---|---|---|---|
| `00000008--03a89eb4e2` | 11:41:17 | ~34 min | 1770 s (1363 s above 25 m/s) |
| `00000009--d42e1d1891` | 12:19:34 | ~3.5 min (segment 4 is a 0-byte file) | 89 s |

- Pull: one read-only listing session and one pull session (2026-10-04T16:30Z; device offroad, indoors, no other SSH session, user-confirmed). 40 rlogs, all sha256 MATCH; promoted to `recordings/2026/10/04/`.
- Tools: the same as the morning analysis (`drive_extract.py`, `lateral_metrics.py`, `hands_warning_scan.py`, `window_scan.py`, `rx_relay_replay.py`) plus `faults_events.py`, `irq_rates.py`, `err_timeline.py` (`E:\DragalPilot\scratch\wsl\`). Logs: `E:\DragalPilot\logs\{lateral-metrics-20261004c,checks-r89-20261004,faults-events-r89-20261004,irq-rates-20261004,bus1-err-timeline-20261004}.log`.

## Question 1: tune (experiment criteria from the deployment proposal)

| Metric | Before: route 6 / 7 | After: route 8 | Criterion | Met |
|---|---|---|---|---|
| Sustained curves: actual/desired lat accel (mean) | 1.073 / 1.076 | **1.007** (per-curve p10/p50/p90 0.96/1.01/1.05; 31 curves) | 0.95–1.04 | yes |
| Peak overshoot in curves (median / max) | 1.06–1.08 / 1.13 | **1.006 / 1.075** | — | — |
| Integrator opposing feedforward in curves | 100% / 71% | **58%** | clearly lower | yes |
| >25 m/s: control-error power share in 0.5–3 Hz (peak) | 0.70 (0.7 Hz) / 0.54 (0.6 Hz) | **0.28 (0.3 Hz)** | lower | yes |
| Mean \|error\| (all engaged, v > 10 m/s) | 0.064 / 0.064 | **0.058** | ≤ +20% | yes |
| Command-torque power share in 0.5–3 Hz | 0.53 / 0.25 | 0.13 | — | — |
| steerFaultTemporary / saturation | 0 / ≤0.15% | **0 / 0.03%** | 0 / ≤1% | yes |
| Lane-centre deviation std (~0.1 Hz wander) | 0.083 / 0.076 m | 0.077 m | — | unchanged |

- **Learners after the change:**
  - `torqued` raw latAccelFactor 4.22 (route 8) / 4.21 (route 9) and friction 0.069 / 0.068. The car's learned value is still slightly above 4.0. calPerc 60, not valid yet; it restarted at the deployment as designed.
  - Roll-corrected curve estimate: median 4.27.
  - `paramsd` steerRatio 13.9; `lagd` 0.17 s.
- **Interpretation (hypothesis):**
  - The systematic over-torque in curves is gone.
  - The remaining felt ping-pong is curve-to-curve variation (±5%) plus a slow (~0.1 Hz) lane-position wander. The wander did not change with the tune, which points at the planned path (model/planner) rather than torque tracking. **Not yet tested.**
  - `torqued` can now apply its ~4.2 estimate itself once valid (clip window 2.8–5.2), so no further offline latAccelFactor change is needed for that.
- The `steerSaturated` alert at 12:02:18 (sharp curve, 17.8 m/s, desired −2.6 m/s²) matches the user's takeover. The user considers it expected; not investigated.

## Question 2: 0x484 and the hands-on warning

- The firmware is active: route 8/9 rlogs show the Hyundai safety mode (param 8) on the panda running `5b8d2b33…` since the deployment boot (deployment record).
- The camera still raises its internal hands-off state (`LFA_SysWarning`, bus 2): route 8 had 4 episodes, including one of 700 s from 12:02:15; route 9 had 3. The panda no longer forwards the camera's 0x484 to the car. **Whether the cluster stayed quiet needs the user's confirmation**; the user reported no warnings.
- openpilot raised a hands-on visual (`steerRequired`) only at 12:02:18 (the `steerSaturated` alert, 2.3 s).
- **Relay malfunction: none.** Real panda: no relay fault; cumulative `safetyTxBlocked` ≤ 5 on route 8 (all in Hyundai mode at engagement boundaries, as before), and the 16 on route 9 all fall in the elm327 startup window. The new safety replayed over both routes: 7.29M rx, 0 invalid, no relay malfunction, no 0x340/0x484/0x485 on bus 0 in the Hyundai mode.

## New observation: `interruptRateCan2` panda fault at startup (bus 1)

- Present on routes 8 and 9; **absent on routes 4–7** (old firmware).
- FDCAN2 is always log bus 1, the CAN-FD network the port doesn't use (`panda/board/drivers/can_common.h` L143–145, harness flipped).
- Timeline (route 8; route 9 similar):
  - At t≈4–8 s, while the panda was still in `elm327` (before the Hyundai mode, no control), bus 1's CAN-FD flag dropped to 0. Bus 1 then logged ~32k errors and one second of 9.5k–18.6k interrupts; the fault threshold is 16k/s (`stm32h7_config.h` L26, `interrupts.h` L33). After that, CAN-FD was re-enabled.
  - Bus 1's error count never increased again on either route, and its interrupt rate was normal (~470/s).
  - The fault bit is sticky until a panda reset (`faults.h`; `PERMANENT_FAULTS = 0`). openpilot acts only on `relayMalfunction` among panda faults (`selfdrived.py` L393).
- On the old firmware (route 7), bus 1 started in classic mode with 4 errors and switched to CAN-FD at ~7 s.
- **Cause unknown.** The firmware change is only one TX-table entry. The correlation is n=2 after vs n=4 before. No control-relevant effect observed.
- Next: watch on further drives. If it persists and matters, compare a boot on the shipped firmware.

## Next

1. The user to confirm whether any dashboard "grasp"/hands-on warning appeared.
2. More driving lets `torqued` reach valid with ~4.2. Then re-measure.
3. Investigate the slow lane-position wander (path/planner level) as a separate question.
4. Next round (user decision): replace the 0x484 `check_relay` entry with a Hyundai forwarding rule; watch the bus-1 startup fault.
