# G70 2024: low-speed data drives, engaged vs manual (2026-10-04, session 4b)

Question (from the [lane-drift findings](2026-10-04-g70-lane-drift.md)): the user feels an unusual lane-position swing that is worst at low speed. At 25–35 mph, does the car swing more when engaged than when driven by hand on the same road? If so, does it come from the model's plan or from the controller?

Evidence types:

- **Observations from rlogs** (and approximately aligned video frames) of 4 routes driven by the user on 2026-10-04, 13:51–14:41 EDT.
- **Confirmed source facts** (file + revision `82f58a9a8c`).
- Roads and traffic were not controlled beyond driving the same loop several times.
- Software on every route: `dragal/custom` @ `82f58a9a8c` (initData), panda firmware `206ea19c…`, default model.

## Data

| Route | Start (EDT, GPS) | Length | Mode | Notes |
|---|---|---|---|---|
| `0000000a--60d952ae7a` | 13:51:50 | 737 s | engaged 481 s (9 spans) | covers parts of the loop |
| `0000000b--b6bf0ba2e9` | 14:04:39 | 677 s | engaged 590 s (2 spans) | full loop |
| `0000000c--9ee7c74d10` | 14:16:31 | 650 s | manual, openpilot on | full loop; reference track |
| `0000000d--16ac681d19` | undated (14:27:22–14:28:04) | 8 s | — | start-up only, no GPS |
| `0000000e--edc17c5e04` | 14:28:03 | 775 s | manual | `OpenpilotEnabledToggle=0` (initData), so card set CarParams.passive and safety `noOutput`: dashcam mode by design (`selfdrive/car/card.py` L133–138). Model and logging ran normally. |

- **Pull:** one read-only SSH connection, 18:49:57Z–18:56:09Z (device `.104`, offroad, indoors, no other SSH session; user-confirmed).
  - Rlogs and road videos of the new routes, plus videos of routes 3, 4, 8, 9.
  - 258 files, all sha256 MATCH. Promoted per `docs/local-storage.md`.
- **Same road (GPS):** every route was matched to route 0c's track by position (≤ 25 m) and heading (≤ 45°), using `s4b_track_match.py`.
  - 0b and 0e follow it for 94% / 92% of their length.
  - 0a covers two parts.
  - So engaged and manual runs exist on the same road, in the same direction.
- **Sections** (on 0c's time base; speed and lane-line coverage from `lowspeed_timeline.py`):

| Section | 0c time | Speed | Both lane lines > 0.5 | Runs (E = engaged, M = manual) |
|---|---|---|---|---|
| S1 | 14:17:21–14:19:41 | 25–30 mph (v ≈ 11.5–13 m/s) | ~2% | E-a, E-b, M-c, M-e |
| S2 | 14:19:41–14:21:41 | 30–35 mph (≈ 14 m/s) | 86–92% | E-b, M-c, M-e |
| S3 | 14:21:41–14:25:07 | 35–55 mph, mixed, includes turns | 81–88% | E-b, M-c, M-e |
| S4 | 14:25:07–14:26:14 | highway, 52–65 mph | 94–98% | E-a, E-b, M-c, M-e |

- **Engaged quality:**
  - S1/S2: 86–97% engaged with no steering override.
  - S3 (E-b): 9.7% override, including a turn with the blinker on.
  - S4: 100%.
- **Stop-and-go: essentially absent.** The model saw a lead vehicle in 0% of S1/S2 frames. Only route 0a has a few stops behind a lead (13:54:35, 13:59:42), all of them driven manually. **The stop-and-go complaint is not covered by this data.**

Tools: scripts in `E:\DragalPilot\scratch\wsl\`, outputs in `E:\DragalPilot\analysis\g70-lowspeed-20261004\`.

- Re-used: `drive_extract.py`, `lane_drift_extract.py`, `faults_events.py`, `err_timeline.py`, `irq_rates.py`, `torqued_buckets.py`.
  - `lane_drift_extract.py` gained `m.lead_*` and `cs.steer_tq` fields; existing fields are unchanged. The previous version is kept as `lane_drift_extract.session4a.py.bak`.
- New: `lowspeed_timeline.py`, `s4b_gps_extract.py`, `s4b_track_match.py`, `s4b_make_stretches.py`, `lowspeed_drives.py`, `s4b_path_diff.py`, `s4b_path_peaks.py`, `s4b_peak_state.py`, `s4b_curve_shift.py`, `s4b_initdata_params.py`.
  - `lowspeed_drives.py` adapts `lane_drift.py` and `speed_band_osc.py`. Its docstring lists the deliberate differences: no 15 m/s gate, a manual mode, 40 s runs, and 40 s Welch windows.
  - `s4b_curve_shift.py` reuses `lane_drift.py`'s section D method.
- Logs: `E:\DragalPilot\logs\s4b-*.log`.
- Environment: WSL clone at `82f58a9a8c`, Python 3.12.13, numpy 2.5.2.

Bands, as set in the kickoff:

- **Slow:** 0.05–0.3 Hz.
- **Fast:** 0.3–3 Hz.
- Peak frequencies on a band-edge bin are flagged.
- **Every slow-band peak fell on the 0.05 Hz edge bin (red spectrum), so no slow-band peak frequency is reported.**

## Results

### 1. At low speed the car executes the model's plan; no controller-specific swing (observation)

Kalman yaw-rate curvature vs the model's `desiredCurvature`, engaged:

| | S1 25–30 mph (E-a / E-b) | S2 30–35 mph (E-b) | S4 highway (E-a / E-b) |
|---|---|---|---|
| Slow band 0.05–0.3 Hz: gain / phase / coherence | 0.97 / −8° / 0.99, 0.96 / −7° / 0.99 | 0.95 / −7° / 0.99 | 1.04 / −8° / 1.00, 0.98 / −10° / 0.99 |
| 0.3–1 Hz: gain / phase / coherence | 1.28 / −32° / 0.93, 1.25 / −26° / 0.89 | 1.00 / −38° / 0.87 | 1.37 / −36° / 0.90, 1.44 / −47° / 0.84 |
| Lat-accel error sign changes per s | 1.6 / 1.1 | 0.8 | 1.7 / 1.5 |
| Saturated | 0% / 0% | 0% | 0% / 3.2% |

- **Slow band:** the car follows the plan, as it does on the highway (session 4 found gain 1.02–1.08 there).
- **0.3–1 Hz:** the actual curvature overshoots the plan by up to 44% (none in S2), with ~26–47° lag. This is **not larger at 25–35 mph than on the highway**. The absolute amplitudes are small (fast-band curvature std 2–3.4 × 10⁻⁴ 1/m).
- The higher low-speed KP (2.9 at 12 m/s, 11.5 at 5 m/s; KD 0) shows **no sign of low-speed oscillation** in these runs.
- **Fast-band lateral sway from yaw rate (0.3–3 Hz, cm):**

  | | S1 | S2 | S4 |
  |---|---|---|---|
  | Engaged | 1.37, 1.00 | 0.93 | 1.37, 1.72 |
  | Manual | 0.94, 1.44 | 0.77, 1.66 | 0.70, 0.50 |

  - At 25–35 mph, engaged lies within the range of the two manual runs.
  - On the highway, engaged is about twice manual, but it is still under 2 cm.

### 2. Slow-band path: engaged vs manual on the same road (observation, lane-line independent)

Method (`s4b_path_diff.py`):

- Each run's actual path curvature (Kalman yaw rate / v) is placed on route 0c's distance-along-road axis, using the odometer (∫vEgo) with a linear fit through the GPS matches.
- It is then refined by the shift (±20 m) that best correlates it with 0c's profile.
- For each pair of runs, the curvature difference is double-integrated over distance, in the wavelength band that corresponds to 0.05–0.3 Hz at the section speed.
- That gives the **lateral path difference between the two runs** (relative only; absolute lane position is unknown).

Results:

- Profile correlation with the reference: 0.96–0.99, except E-a in S1 (0.79).
- Odometer scale 0.998–1.000.
- Shifts ≤ 3 m.

**Slow-band path difference, std (m):**

| Pair | S1 25–30 mph, no lines | S2 30–35 mph, lines | S3 35–55 mph | S4 highway |
|---|---|---|---|---|
| Manual vs manual (human baseline) | **0.115** | **0.172** | **0.171** | **0.212** |
| E-b vs M-c / M-e | 0.159 / 0.225 | 0.176 / 0.161 | 0.293 / 0.218 | 0.144 / 0.111 |
| E-a vs M-c / M-e | 0.122 / 0.179 | — | — | 0.190 / 0.096 |
| Engaged vs engaged (E-a vs E-b) | 0.075 | — | — | 0.063 |

- **S2 (30–35 mph, with lane lines) and S4 (highway):** the engaged path differs from the human paths no more than the two human runs differ from each other.
- **S1 (25–30 mph, no confident lane lines):**
  - The engaged path differs from the human paths by 1.06–2.0× the human-to-human difference.
  - The two engaged runs agree with each other closely (0.075 m).
  - So it is a **repeatable path that differs from the human's, not random wandering.**
- **S3:** the larger engaged-vs-manual value comes mainly from one turn. It was driven with the blinker on and the wheel pressed 36% of the time, so it is not clean engaged driving and is excluded from interpretation.
- **Curve-cutting relative to the human:** the slope of path difference on road curvature is ≤ 0.015 m per 10⁻³ 1/m in magnitude in S1–S3. **At low speed the engaged car does not take curves more on the inside than the human does.**
- **Where S1 differs** (`s4b_path_peaks.py`; engaged minus the mean of the two manual runs; negative = engaged further left):
  - The largest difference is at s ≈ 437 m, at route 0c 14:17:56, at the same place in every run:
    - E-b −0.73 m;
    - E-a −0.40 m;
    - the two manual runs within 0.08 m of each other.
  - At those moments: lateral active, no steering press, no blinker, no lane lines (> 0.5: 0%), no lead (`s4b_peak_state.py`).
  - The other S1 differences are ≤ 0.5 m, and at some of them the two manual runs also disagree.
- **Visual context** at that spot (wide road camera; frame index from the route time, approximate ±1 s; `frames/S1bend_*`):
  - two-lane road with a double yellow centre line;
  - a curb on the right with **no white edge line**;
  - a **left-turn bay with painted arrows opening on the left**.
  - **Hypothesis:** with no right edge line, the model drifts toward the widening on the left. Unverified; this needs the video lane-position measurement.

### 3. Lane position where lines are confident (observation; thin data)

Method: `s4b_curve_shift.py`, the same method as `lane_drift.py` section D, v > 15 m/s, runs ≥ 15 s. With runs ≥ 30 s only 37–60 s per route remain; both are logged.

| | Engaged 0a / 0b | Manual 0c / 0e | Engaged highway, routes 6 / 7 / 8 (session 4) |
|---|---|---|---|
| Eligible time | 62 / 46 s | 105 / 77 s | 578 / 622 / 1278 s |
| Mean device position (− = left of centre) | +0.005 / −0.036 m | −0.081 / −0.049 m | −0.174 / −0.193 / −0.121 m |

- The human also sits slightly left of centre on these roads, and engaged sits no further left than the human here.
- The ~0.15–0.19 m left bias found engaged on the interstate (routes 6–8) can't be compared directly: different road, no manual run there.
- **Inside-of-curve shift vs a human: inconclusive.** There is too little eligible curvature on these roads (mean |road curvature| 0.1–0.36 × 10⁻³ 1/m), and the slopes are noisy (corr ≤ 0.5, both signs).

### 4. Plan vs outcome (observation)

Realised change vs the model's planned change over 1 s, where lines are confident (S3/S4):

- engaged: slope 0.71–0.96, corr 0.66–0.78;
- manual: slope 0.88–1.11, corr 0.71–0.85.

The model's 1 s plan predicts the human's path about as well as the engaged car's. This doesn't separate them.

### 5. Other checks (observation)

- **Steer faults:** none on any route (`steerFaultTemporary`/`Permanent` 0).
- **CPU:** mean 55–57% while engaged, p95 ≤ 61%, within baseline.
- **Real panda:** no relay malfunction. TX blocked only in the elm327 start-up window (≤ 15 per route), plus 3 in Hyundai mode on 0a (at +89 s and +367 s, both at lateral disengagements).
- **Safety replay artifact on 0b:**
  - The offline replay counted 7,247 blocked LKAS11 (0x340) messages from +112.7 s.
  - The real panda blocked **none** in Hyundai mode (`pandaStates.safetyTxBlocked`).
  - The replay also reported `safety_tick_rx_invalid`, while the real panda had `rxChecksInvalid` 0.
  - So this is a replay-state divergence (the replay's rx-check timing), not a real block. Hypothesis for the mechanism; not investigated further.
- **`torqued`:**
  - Not valid; calPerc 60 → 70; total points 6,862 → 7,039; the controller still uses the offline 4.0 / 0.07.
  - Raw estimate 4.0–4.25, friction 0.069–0.079.
  - Bucket reconstruction (`torqued_buckets.py`, routes 8 → 0e; total 7,017 vs 7,039 logged, calPerc 69 vs 70):
    - outermost negative bucket **38 / 100** (was 23);
    - −0.3…−0.2 at 261 / 300;
    - +0.3…+0.5 at 95 / 100;
    - the rest full.
  - About 62 more points are needed in the limiting bucket, roughly 1.3 h of engaged driving above 34 mph at route 8's rate.
- **Bus-1 `interruptRateCan2`:**
  - The start-up error burst on bus 1 (CAN-FD, unused by the port) happens on **every** route since the firmware change: ~35k errors and a 12.7k–19k/s interrupt peak, while the panda is still in elm327, with CAN-FD re-enabled afterwards.
  - The sticky fault bit is set only on some boots (0c, 0d; 0e inherited it from 0d's boot, because its error counter continues from 0d's 34,830). It was not set on 0a or 0b.
  - So the bit depends on whether the burst's 1 s rate crosses the 16k/s threshold. The burst itself is consistent.
  - No error increase after start-up on any route. No control effect observed.
  - Now n = 7 boots with the burst after the firmware change, vs n = 4 boots without it before. Cause still unknown.

## Interpretation (hypothesis)

> **See the follow-up at the end.** The 3 s weave the user describes is a steering-loop effect at 0.3–0.6 Hz that is present at all speeds. This section is about the slow path (< 0.3 Hz) and the comparison with the human. "No low-speed-specific oscillation" still holds; "no controller involvement" does not hold for the 3 s weave.

- On these drives at 25–35 mph, the engaged car **does not swing more than the human in the fast band**, and it **follows the model's plan in the slow band**. The controller's higher low-speed gain shows no oscillation.
- The difference from human driving is **in the path the model chooses**:
  - It appears only on the 25–30 mph section **without lane lines** (double yellow on the left, curb with no edge line on the right).
  - It is repeatable between the two engaged runs.
  - It is largest (0.4–0.7 m further left than the human) where a left-turn bay opens.
  - With lane lines (S2) and on the highway, engaged differs from the human no more than the human differs from itself.
- **Not covered:** stop-and-go behind a lead vehicle, which is the user's main complaint. In stop-and-go the lane lines are usually hidden and a lead car is present, so the model's path may behave differently from anything measured here.
- **The user's own impression of these drives isn't recorded yet.** Did the swing feel present on 0a/0b, and where? It decides whether S1's path difference is what they feel.

## Limitations

- **Small sample:** 1–2 runs per mode per section. One road loop, one afternoon, light rain on part of it (0c frame).
- Path differences are **relative between runs**. Absolute lane position at S1 is unknown, because the model had no confident lane lines. Whether the engaged path or the human path is closer to the lane centre there needs the video measurement.
- Alignment along the road is by odometer plus GPS (shifts ≤ 3 m). That's adequate for 38–230 m wavelengths, not for short ones. E-a's S1 profile correlates only 0.79.
- Lane offsets and road curvature in §3 are the model's own perception.
- Video frames are aligned approximately (frame index from route time, ±1 s). They give visual context only.

## Options (each a separate bounded change; user decision)

> **Superseded in part** by the follow-up below. The user then described the weave as ~3 s per cycle with the wheel visibly moving, which matches the 0.3–0.6 Hz steering-loop gain, not the slow path difference. Option 4 as first written ("controller changes not indicated") no longer holds. See "Proposed next step" at the end.

1. ~~No software change now.~~ For the slow path difference (S1) alone, no software change is indicated. For the 3 s weave, see the follow-up.
2. **Data:**
   - stop-and-go behind a lead, engaged plus manual on the same stretch, which is the actual complaint;
   - the user's description of where the swing is felt on 0a/0b (answered in the follow-up: no specific locations; ~3 s; wheel moves).
   - The video lane-check session can measure absolute lane position at S1, especially the turn-bay spot.
3. **Model choice** (the user's decision is to stay on the default model for now). If S1-type roads matter, a model comparison on this same loop (engaged, same direction) would be the bounded experiment. It changes `modeld` to `modeld_v2` and activates `CameraOffset`/`PlanplusControl` (session 4 source facts), so it needs its own proposal.
4. ~~Not indicated: controller or torque changes.~~ The 0.3–1 Hz overshoot turned out to be what the user describes. See the follow-up.

## Follow-up: the ~3 s weave (user report, same session)

**User description (2026-10-04):**

- occasional weaving, "rhythm about 3 seconds";
- "a few inches of left to right movement of the vehicle";
- **the wheel visibly moves back and forth**;
- no specific locations recalled;
- now some very good segments without weaving, but it is still detectable.

That is ~0.33 Hz, a steering-level oscillation. It sits right on the 0.3 Hz edge between the kickoff's two bands, so the band summaries above split it. §2 measures the slow path, not this.

### Weave band 0.2–0.6 Hz: where the gain comes from (observation)

Method: `s4b_loop_xfer.py`. Engaged frames without override or blinker, runs ≥ 30 s, 100 Hz. Welch with 20 s windows. Every link is in lateral acceleration. Values are gain / phase, with coherence ≥ 0.77.

- **A** = controller setpoint (`desiredLateralAccel`) → steering-angle lateral accel (`actualLateralAccel`, the controller's own measurement): controller + EPS.
- **B** = steering-angle lateral accel → Kalman yaw-rate lateral accel: the vehicle's response.
- **C** = setpoint → yaw lateral accel: what the car actually does relative to the request.

Log: `s4b-loop-xfer-20261004-153331.log`.

| Route (tune), speed band | A 0.1–0.2 Hz | A 0.3–0.4 Hz | A 0.4–0.6 Hz | B 0.3–0.4 Hz | B 0.4–0.6 Hz | C 0.3–0.4 Hz | C 0.4–0.6 Hz |
|---|---|---|---|---|---|---|---|
| r6 (old), 55+ mph | 1.10 / −2° | 1.15 / −27° | 1.26 / −39° | 1.07 / 0° | 1.24 / +2° | 1.29 / −30° | 1.82 / −41° |
| r7 (old), 55+ mph | 1.10 / −1° | 1.22 / −28° | 1.27 / −45° | 1.09 / +1° | 1.33 / +6° | 1.42 / −30° | 1.90 / −42° |
| r8 (new), 55+ mph | 1.04 / −5° | 1.05 / −48° | 1.14 / −59° | 1.26 / +13° | 1.35 / +16° | 1.42 / −37° | 1.73 / −45° |
| r8 (new), 35–55 mph | 1.04 / −9° | 1.00 / −30° | 1.11 / −33° | 1.10 / 0° | 1.20 / +1° | 1.12 / −31° | 1.37 / −34° |
| 0a (new), 20–35 mph | 0.96 / −13° | 1.15 / −36° | 1.19 / −37° | 1.27 / +3° | 1.29 / +1° | 1.46 / −34° | 1.57 / −37° |
| 0b (new), 20–35 mph | 0.96 / −11° | 0.96 / −19° | 1.20 / −21° | 1.08 / −5° | 1.04 / −6° | 1.05 / −24° | 1.29 / −28° |
| 0b (new), 35–55 mph | 1.22 / −18° | 1.27 / −38° | 1.31 / −43° | 1.21 / +4° | 1.24 / +8° | 1.53 / −35° | 1.65 / −37° |

- **In this band the car's actual motion is 1.05–1.9× the requested motion, lagging 24–48°,** on every route and in every speed band, before and after the tune.
  - It comes from both links:
    - the controller/EPS loop gives 0.96–1.38× with 19–59° lag;
    - the vehicle then turns 4–35% more per degree of steering than the steady-state vehicle model predicts.
  - B is ≈ 1.0 at 0.1–0.2 Hz (0.92–1.15), so the steady-state calibration (steerRatio 14.1) is right.
- **The tune fixed the low-frequency over-torque** (A at 0.1–0.2 Hz: 1.10–1.13 → 0.96–1.07, except 0b at 35–55 mph, 1.22) but **not this band.** That matches the user: "improved, but some weaving remains."
- **The control error (setpoint − measurement) peaks at 0.30–0.40 Hz (2.5–3.3 s)** on route 8 (highway) and on 0a/0b above 35 mph. These peaks are not on a band edge; the search band is 0.1–1.5 Hz. **That matches the user's 3 s rhythm.**
  - On the other bands the error peak is at the 0.1 Hz edge bin, i.e. no peak.
- **Not specific to low speed in this data.** C at 0.3–0.6 Hz is similar at 20–35, 35–55 and 55+ mph.
- **Weave episodes:**
  - `s4b_weave.py` (log `s4b-weave-20261004-153119.log`) looks for a 0.2–0.6 Hz lateral displacement envelope ≥ 2.5 cm for ≥ 6 s.
  - Engaged, on near-straight plans: the episodes show the same signature, actual/desired 1.2–1.9× with 20–45° lag.
  - In those episodes the torque P-term's band amplitude is 1.4–2.6× the total output's, so P works against the feedforward in this band.
  - **Raw episode counts don't discriminate on these curvy roads.** The manual runs score as high, because bends and turn bays also put energy into 0.2–0.6 Hz yaw.

### Source facts (`dragal/custom` @ `82f58a9a8c`)

- **The device runs `LatControlTorqueV0`** (`sunnypilot/selfdrive/controls/controlsd_ext.py` L36–46): torque cars get V0 unless `EnforceTorqueControl` is set ("FIXME-SP: revert when upstream fixes tuning issues with v1").
- **V0** (`sunnypilot/selfdrive/controls/lib/latcontrol_torque_v0.py`):
  - L79–91: `setpoint = lat_delay·jerk + expected`, which algebraically equals the **current** desired lateral accel.
  - L87–92: `error = setpoint − measurement`, where the measurement comes from the steering angle. So the error always contains the actuator delay (lagd 0.17 s). The TODO at L81 notes this.
  - L96–107: `output = ff (current desired) + KP·error + KI·∫error`.
  - L25–29: KD = 0. KP is 11.5 at 5 m/s, 3.5 at 10, 2.0 at 15 and 1.0 at 30 m/s; KI 0.3.
- **Upstream v1** (`selfdrive/controls/lib/latcontrol_torque.py`):
  - `setpoint = expected` (the request delayed by lat_delay), so the **error excludes the delay**;
  - KP 0.8 at 30 m/s, KI 0.15;
  - jerk enters only the friction input (JERK_GAIN 0.3).
- **The `EnforceTorqueControl` toggle changes more than the controller version.** It also:
  - re-runs `configure_torque_tune` (`sunnypilot/selfdrive/car/interfaces.py` L28–35, L74–76);
  - enables the torque override params (`latcontrol_torque_ext_override.py`);
  - enables `torqued`'s relaxed and custom options (`sunnypilot/selfdrive/locationd/torqued_ext.py`).

### Interpretation (hypothesis)

- The ~3 s weave the user feels is **a lightly damped oscillation of the steering loop**, not the model's path:
  - V0's proportional term acts on an error that includes the actuator delay, which gives extra gain and lag around 0.3–0.6 Hz;
  - the car's own yaw response adds 4–35% on top of that.
  - Any 0.3–0.6 Hz content in the plan, or a disturbance, is amplified ~1.1–1.9× and lags. The model then re-plans against the overshoot.
- The open-loop arithmetic agrees roughly. If the measurement is the output delayed by 0.17 s, then V0's `ff + KP·(ff − meas)` asks for ~1.5× at 0.33 Hz with ~40° lead at 12 m/s (KP 2.9), and ~1.1× at 30 m/s. This is approximate; the closed loop and EPS dynamics are not modelled.
- It is **not low-speed specific** in the data. Why the user feels it most at low speed is open. Possible reasons:
  - the higher KP at low speed;
  - lane lines that are absent more often;
  - perception;
  - stop-and-go, which is still not measured.

### Proposed next step: offline before any device change (bounded; user decision)

**Question:** would V0 with the delay removed from the error (the upstream v1 error definition), with everything else unchanged, reduce the 0.3–0.6 Hz gain on this car without hurting curve tracking?

1. **Offline only, no device access:**
   - Identify the plant from these logs: torque → steering-angle lateral accel (delay + first/second-order EPS and steering dynamics), fitted on routes 8/0a/0b and validated on held-out route 7.
   - Simulate the closed loop with logged setpoints for:
     - (a) V0 as deployed;
     - (b) V0 with `setpoint = expected` (the v1 error definition);
     - (c) upstream v1 as is.
   - Compare A/C gain and phase at 0.2–0.6 Hz, curve actual/desired, step overshoot, and error.
2. **Success criteria for proposing a device experiment:**
   - C at 0.3–0.6 Hz ≤ 1.2 with phase lag not worse;
   - curve actual/desired 0.95–1.04 (the current tune criterion);
   - no increase in mean |error| above 20%.
3. **If it passes:** a separate deployment proposal for one bounded code change on `dragal/custom`, scoped to this car, not a global KP change (CLAUDE.md §2). It would carry tests, a focused review, the same loop driven engaged with the same metrics, and a rollback.
   - Using the `EnforceTorqueControl` toggle instead is **not** recommended as the experiment, because it changes several things at once (see the source facts above).

### Result of the offline simulation (session 6, same day)

Full write-up: [2026-10-04-g70-weave-sim.md](2026-10-04-g70-weave-sim.md). Offline model evidence only; no device access.

- **It did not pass.** V0 with `setpoint = expected` (the v1 error definition) changes the 0.3–0.6 Hz gain by only −0.10 to +0.03. It adds 11–21° of lag and fails the criteria in every band. Upstream v1 is no better.
  - **No device change is proposed.** The "delay in V0's error" hypothesis above is not supported by the model.
- The identified steering plant is overdamped: a first-order-like lag with a corner at 0.2–0.4 Hz, plus 0.02–0.17 s delay and friction.
- At 35+ mph its dynamic torque gain is 1.21–1.29× what latAccelFactor 4.0 assumes. In the model, that gain mismatch, together with the lag, makes the feedforward + P overshoot in the weave band.
  - Matching the feedforward scale to it (exploratory only) cut the band gain by 0.07–0.15. C stayed above 1.2 at 35+ mph, because the vehicle link alone is 1.21–1.34 there.
- **At 20–35 mph the model under-predicts the logged 0.4–0.6 Hz gain**, so the low-speed impression stays unexplained.
