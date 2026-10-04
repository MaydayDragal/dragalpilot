# G70 2024 port: morning drives, steering tune and hands-on warnings (2026-10-04)

Software on device: `dragal/custom` @ `7e9d0755d9` (initData.gitCommit, all routes). The user drove alone, per the in-car checklist (stage C reported clean; stage D below). Evidence type: **observations from rlogs** and **confirmed source facts** (file + revision `7e9d0755d9`). No device changes were made.

## User report (2026-10-04, after the drives)

- Stage C (low speed, closed area): no issues.
- Stage D: no non-routine disengagements. "A few driver engagement alerts" that the user expected sunnypilot's hands-free behaviour to suppress. micd/soundd crashed again.
- Steering "ping-pongs" in the lane: it oversteers into curves, corrects immediately, then oversteers again.
- The user has a phone video of the steering wheel (not yet provided).

## Data

| Route | Start (EDT, GPS) | Length | Lateral engaged |
|---|---|---|---|
| `00000005--6ef1c41d0e` | 09:47:51 | 211 s | 0 s (micd/soundd down at +31.6 s) |
| `00000006--d25600146e` | 09:51:23 | 810 s | 735 s, mostly 24–35 m/s |
| `00000007--4ed1795760` | 10:05:24 | 1188 s | 947 s, incl. lateral-only at 5–21 m/s |

- Pull: one read-only SSH session 2026-10-04T14:36Z, after a short read-only listing session. A third short read-only session read steering params. Device offroad and indoors (user-confirmed; `IsOffroad=1` checked in each session). rlogs + `fcamera`/`ecamera` (114 files, 3.19 GB), all sha256 MATCH vs on-device hashes. Promoted to `recordings/2026/10/04/`. No qlogs, no qcamera, no driver video (`RecordFront=0`).
- Camera-to-filename mapping verified against `openpilot/system/loggerd/loggerd.h` L98–160: `fcamera.hevc` = narrow road, `ecamera.hevc` = wide road, `dcamera.hevc` = driver.
- Scripts (on the data root, WSL clone at `7e9d0755d9`): `E:\DragalPilot\scratch\wsl\drive_extract.py` (streaming per-segment extraction + streaming copy of opendbc `replay_drive`), `lateral_metrics.py`, `hands_warning_scan.py`, `hda11_scan.py`, `window_scan.py`. Logs: `E:\DragalPilot\logs\{drive-extract,lateral-metrics,hands-warning-scan,hda11-scan,window-scan}-*`. Outputs: `E:\DragalPilot\analysis\g70-drives-20261004b\`. Route 4 (00:36 drive) was re-extracted with the same tools for comparison.

## Which lateral controller runs (confirmed source facts)

- `EnforceTorqueControl` is absent on the device, so `controlsd_ext.initialize_lateral_control` returns **`LatControlTorqueV0`** (`openpilot/sunnypilot/selfdrive/controls/controlsd_ext.py` L37–46; `.../lib/latcontrol_torque_v0.py`). The torque-param override is inactive (`latcontrol_torque_ext_override.py`: needs `EnforceTorqueControl`).
- V0: feedforward = desired lat accel − roll·g + friction term; PID with KP=1.0 at ≥30 m/s (higher at low speed), KI=0.3, KD=0. Output torque = lat accel / `latAccelFactor` (linear; `opendbc/car/interfaces.py` L215–217, no Hyundai override). The friction term is ±`friction`·`latAccelFactor`, switching across a ±0.3 m/s² error band (`opendbc/car/lateral.py` L204–212).
- Online learners and how they're used:
  - `paramsd` steerRatio and angle offset feed the vehicle model (`controlsd.py` L84–91).
  - `lagd` delay is used because `LagdToggle=1` (`sunnypilot/livedelay/helpers.py`).
  - `torqued` values are used when valid (`controlsd.py` L94–98). **When valid, `torqued` clips latAccelFactor to ±30% of the offline value** (`selfdrive/locationd/torqued.py` L26, L100–101, L238). With the port's 2.7, the most it can apply is 3.51.
- Device steering params (read 2026-10-04): `LateralJerkTorqueController=0`, `TorqueControlTune=0.0`, `TorqueParamsOverrideEnabled=0`, `LagdToggle=1`, `PlanplusControl=1.0` (neutral), `CameraOffset=0.0`, NNLC 0.

## Findings

### 1. The port's torque values are not what this car does (observation, consistent across routes)

| Estimate | latAccelFactor | friction |
|---|---|---|
| Port / carParams (offline) | **2.7** | **0.11** |
| `torqued` raw estimate, end of routes 4 / 5 / 6 / 7 | 4.07 / 3.97 / 4.47 / 4.12 | 0.067 / 0.068 / 0.072 / 0.075 |
| Curve-based, roll-corrected (achieved lat accel ÷ commanded torque in sustained curves, median), routes 4 / 6 / 7 | 3.47 / 4.73 / 4.09 | — |
| Older G70 (`GENESIS_G70`, `params.toml`), for reference only | 3.85 | 0.068 |

- `torqued` was not yet valid on any route (calPerc 39 → 56 → 64%), so the controller ran on 2.7 / 0.11 throughout.
- Consequence (inference from the V0 controller): the feedforward commands about 1.5–1.65× the torque the car needs for a given curve, and the friction term adds about 1.6× the learned friction. In curves the measured lateral accel exceeded the setpoint by ~7% (routes 6/7), and the integrator opposed the feedforward in 71–100% of sustained curves. That matches the user's "oversteers into curves, then corrects".
- Hypothesis (not yet tested): a large share of the felt ping-pong is the feedback loop repeatedly correcting an over-strong feedforward and friction term. Supporting observation: at >25 m/s the control error has a spectral peak at 0.6–0.8 Hz, with 54–70% of its power in 0.5–3 Hz (route 4: 65%).

### 2. Other learned values differ from the port's specs (observation)

- `paramsd` steerRatio: **13.9–14.3** (std ~0.1, valid) vs the port's 12.9 "guesstimate". `paramsd` is already applying its own value.
- `paramsd` steering-angle offset: about −2.3 to −3.2°. It's learned and compensated online, so this is informational.
- `lagd` lateral delay: **0.16–0.17 s** (routes 6 and 7, calPerc 100, status valid) vs `steerActuatorDelay` 0.1. lagd's value is in use.

### 3. Lane position (observation; approximate method)

- Lane-centre offset from `modelV2` lane lines (both lines prob > 0.7, v > 10 m/s, excluding 3 s after blinkers and stretches shorter than 20 s), deviation from a 10 s moving average:
  - Engaged: std 0.076–0.094 m, p95 |dev| 0.18–0.20 m.
  - Dominant frequency: about 0.1 Hz (slow wander). Only 19–26% of the power is in 0.15–0.8 Hz.
- Manual reference: only 31 s of usable manual driving (route 5): std 0.19 m. **The sample is too small to compare.**
- So the model-reported lane position shows no large fast lateral oscillation. The felt ping-pong may be mostly steering-wheel torque/angle motion rather than lane-position motion. The user's wheel video and the road videos should be reviewed against the curve times listed in `metrics_lateral.json`.

### 4. "Driver engagement" alerts: not from sunnypilot (observation)

- Driver monitoring, while lateral was active (routes 6/7): alert level 0 for 100% of samples; face detected 99.7–99.8%; wheel-touch fallback policy active <0.3%. No driver-monitoring events.
  - Source fact: DM falls back to wheel-touch only if no face is detected or the model is uncertain for 10 s (`selfdrive/monitoring/policy.py` L77, L303–304).
- openpilot never requested a hands-on warning: no `steerRequired`/`ldw` visual alerts, and `CF_Lkas_SysWarning` was 0 in every LKAS11 frame it sent.
- **The car's stock camera raised its own LFA hands-off warning** (`LFAHDA_MFC.LFA_SysWarning` on bus 2) in 4 episodes, all while openpilot was steering:
  - route 6: 09:51:54 (40 s, values 5→6), 10:00:48 (37 s, value 4)
  - route 7: 10:23:12 (35 s, value 3), 10:23:55 (19 s, value 3)
  - Two start within 0.3 s of an engagement (`pcmEnable` +564.44 → +564.6; `lkasEnable` +1067.78 → +1068.0).
- The panda blocks the camera's `0x485` from reaching the car. Which forwarded message carries the warning to the cluster is **not established**: no `HDA11_MFC` (`0x484`) field separates the episodes cleanly. Upstream PR #1134 for this car names it ("Suppress 'grasp not detected'…") and needs panda PR #2045, which stops forwarding the camera's `0x484` and lets openpilot transmit its own. **That widens the safety TX allowlist and was deliberately excluded.** Needed: the user's alert times/appearance to confirm the match.

### 5. Safety and faults (observation)

- Real panda (pandaStates): safety `hyundai` param 8; `safetyRxInvalid` 0; no faults; cumulative `safetyTxBlocked` ≤ 4 per route (routes 4, 6, 7).
- `steerFaultTemporary` while engaged: 0 on every route. Torque saturation: 0–0.15%.
- Route 7 low-speed lateral-only engagement (5–21 m/s, requests up to 189 units) ran with no EPS fault, and the real panda blocked nothing.
- **Replay limitation:** the streaming copy of opendbc `replay_drive` flagged 2,129 blocked LKAS11 and `safety_tick_rx_invalid` on route 7 during that lateral-only window. The real panda's counter shows it blocked none. The replay's MADS state doesn't follow LKAS-button engagement with cruise unavailable, so these replay blocks are a tool artifact. **Not investigated further.**

### 6. Device load and processes (observation)

- CPU mean 55.5–59.1%, p95 61–81%, max temp ~60 °C on route 5 (baseline: mean 53–82%, p95 80–88%). Within the acceptance band.
- micd/soundd exited at +31.6 s on route 5 (route 3: +31.7 s), and not on routes 4, 6, 7. Generic; not investigated.

## Follow-up (same day): user confirmation and wheel video

- **The user confirmed** that the 4 camera hands-off episodes (09:51:54, 10:00:48, 10:23:12, 10:23:55) match the alerts they saw.
- Wheel video, filed with route 6 at `recordings/2026/10/04/09-51-23__00000006--d25600146e/videos/user-phone-wheel/G70 wheel sunnypilot.mp4`: phone, 720×1280, 30 fps, 29.9 s, `creation_time` 2026-10-04T13:54:59Z (09:54:59 EDT). The user said ~09:55. It is not known whether the phone stamps the start or the end of the clip.
  - Candidate window A, 09:54:29–09:54:59 (route 6 +185 to +215 s), contains a right-hand curve at 34.8 m/s:
    - Curve entry overshoot: actual −1.55 vs desired −1.27 m/s² (+22%). The wheel went from −2.4° to +1.9° and then back to +1.1 to +1.4°.
    - Through the curve: 0.5–1° of wheel motion within each second.
  - Window B, 09:54:59–09:55:29, contains a smoother left-hand curve.
  - The frames (1 fps contact sheet, `E:\DragalPilot\analysis\g70-wheel-video-20261004\`) show small wheel rotation changes. The camera is handheld, so the video can't be aligned frame-by-frame with the logged angle. **Alignment is approximate**, and the video adds no measurement beyond the logs.

## Not established / next

- How the camera's hands-off warning reaches the cluster, and whether the user's alerts match the 4 episodes.
- Whether correcting latAccelFactor/friction removes the felt ping-pong. **A tune change is a separate, bounded change** with its own question, criteria, review and deployment approval.
- Low-speed (<5 m/s) behaviour: ~25 s engaged below 5 m/s on route 7, no faults. Still a small sample.
