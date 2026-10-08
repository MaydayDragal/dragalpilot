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
  - **Update (session 4):** tested from the rlogs in [2026-10-04-g70-lane-drift.md](2026-10-04-g70-lane-drift.md). There is no 0.1 Hz peak (that was a band-edge artifact). The variation is mostly the model positioning the car toward the inside of curves, and the car follows the plan closely.
  - `torqued` can now apply its ~4.2 estimate itself once valid (clip window 2.8–5.2), so no further offline latAccelFactor change is needed for that.
- The `steerSaturated` alert at 12:02:18 (sharp curve, 17.8 m/s, desired −2.6 m/s²) matches the user's takeover. The user considers it expected; not investigated.

### Follow-up (session 4): when `torqued` becomes valid

**Source facts** (`selfdrive/locationd/torqued.py`, `locationd/helpers.py`, `selfdrive/controls/controlsd.py` @ `82f58a9a8c`):

- **What it learns from.** A point is added only when:
  - lateral is engaged for ≥ 2 s;
  - no steering override;
  - v > 15 m/s;
  - |torque| > 0.02 and |lat accel| ≤ 1 m/s².
  - Points are sorted into 8 torque buckets with minimums 100/300/500/500/500/500/300/100 (outermost = |torque| 0.3–0.5), and at least 4000 points in total are needed.
- **The cache restarted at the deployment.** The cache key includes the offline latAccelFactor and friction (L137–142). Points carry over between drives (cached every 60 s).
- **What controls uses.** `controlsd` applies the filtered values whenever `useParams` is set (L96–97), but the filter only moves once the estimate is valid. Until then the controller runs on the offline 4.0/0.07.
- **After validity.** The filter's time constant starts at about 250 s and grows to about 1250 s. The value is clipped to 2.8–5.2 (latAccelFactor) and 0.035–0.105 (friction).

**Reconstruction** (approximate; script `torqued_buckets.py`, log `torqued-buckets-20261004.log`): it matches the logged totals within 0.2% (6,849 vs 6,862 points) and calPerc 61 vs 60.

| Bucket (torqued torque sign) | −0.5…−0.3 | −0.3…−0.2 | −0.2…0.2 (4 buckets) | 0.2…0.3 | 0.3…0.5 |
|---|---|---|---|---|---|
| Points after route 9 / minimum | **23 / 100** | 218 / 300 | full | 553 / 300 | **55 / 100** |
| Rate on route 8 (per hour engaged > 15 m/s) | ~49 | ~390 | — | — | ~117 |

- The total (6,849) is already above 4,000. **The limit is the outermost bucket on the negative side** (positive actuator torque, by openpilot's left-positive convention): high torque that still gives ≤ 1 m/s².
- At route 8's rate, it needs **~1.5–2 more hours of similar engaged driving above 34 mph**. This depends strongly on the road; curvier roads fill it faster.
- Expected effect once valid: latAccelFactor 4.0 → ~4.2 (+5%), friction 0.07 → ~0.068. That is about 5% less torque for the same lateral accel. Small.
- If it never becomes valid, the controller simply stays on the deliberately chosen 4.0/0.07.

## Question 2: 0x484 and the hands-on warning

- The firmware is active: route 8/9 rlogs show the Hyundai safety mode (param 8) on the panda running `5b8d2b33…` since the deployment boot (deployment record).
- The camera still raises its internal hands-off state (`LFA_SysWarning`, bus 2): route 8 had 4 episodes, including one of 700 s from 12:02:15; route 9 had 3. The panda no longer forwards the camera's 0x484 to the car. **The user confirmed no dashboard "grasp not detected" warning on this drive.**
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

1. ~~Dashboard warning~~ **Confirmed by the user (2026-10-04): no "grasp not detected" warning appeared on this drive.** The 0x484 change works as intended on this car (user observation; one drive).
   - **Update (session 8, 2026-10-05):** this conclusion is weaker than stated. On routes 8/9 the camera's `LFA_SysWarning` was only 3 (`lfa_error` per `hyundai_can.dbc` L1695), never 5/6 (keep hands on wheel). So the drive never contained a hands-off escalation to suppress. The first 5/6 episode with the change active (route `1a`, 2026-10-05 06:43:20) coincides with a reported "grasp not detected". See [2026-10-05-g70-device-errors.md](2026-10-05-g70-device-errors.md) §4.
2. More driving lets `torqued` reach valid with ~4.2. Then re-measure.
3. Investigate the slow lane-position wander (path/planner level) as a separate question.
4. Next round (user decision): replace the 0x484 `check_relay` entry with a Hyundai forwarding rule; watch the bus-1 startup fault.
