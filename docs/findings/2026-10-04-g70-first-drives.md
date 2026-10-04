# G70 2024 port: first drives (2026-10-04)

Software on device: `dragal/custom` @ `7e9d0755d9` (initData.gitCommit, both routes). The user's partner drove; Claude was not involved during the drive. Evidence type: **observations from rlogs** of 2 routes. This is not a validation of performance in general.

## Data

| Route | Start (EDT, GPS) | Length | Engaged | Notes |
|---|---|---|---|---|
| `00000003--6374d1c794` | 2026-10-04 00:31:30 | ~191 s | 0 s | micd and soundd died at +31.7 s → `processNotRunning` no-entry blocked engagement for the rest of the route |
| `00000004--b69c7ed33d` | 2026-10-04 00:36:45 | ~539 s | ~304 s (5 spans) | segment 9 is 0 bytes on the device |

- Pulled 2026-10-04T13:28Z: one SSH session, device offroad and indoors, rlogs only, all sha256 MATCH.
- Promoted to `recordings/2026/10/04/`. Scripts: `E:\DragalPilot\scratch\wsl\drive_analysis.py`, `drive_followup.py`.
- Logs: `E:\DragalPilot\logs\drive-analysis-20261004-093010.log`, `drive-followup-20261004.log`. Output: `E:\DragalPilot\analysis\g70-drives-20261004\`.
- User report: the micd/soundd failure is a known bug in this sunnypilot build, unrelated to the port. Their other Comma 4 usually recovers by going into and out of offroad mode. These are user statements; the logs only show the failure (route 3) and its absence (route 4).

## Findings (observations unless labelled)

1. **Fingerprint:** `GENESIS_G70_2024`, `fingerprintSource=fw`, `fuzzyFingerprint=False`, `dashcamOnly=False` on both routes. Panda safety `hyundai`, param 8, for 94–98% of samples; the rest is the elm327 fingerprinting phase at startup. carParamsSP safetyParam 6. alternativeExperience 1024 (MADS on).
2. **`CAMERA_SCC`: supported by the data (the main open question from the parked logs).** With the relay engaged, SCC11/12/13/14 and FCA11 appear on **bus 2** (camera side). Route 4: SCC11 had 26,931 frames on bus 2 vs 577 on bus 0, and the bus-0 count fits the ~2% elm327/passthrough startup window. LKAS11 and LFAHDA/HDA11 are on bus 2, while MDPS12 and CLU11 are on bus 0, matching the camera-SCC layout the port assumes.
3. **openpilot TX:**
   - All 70,424 LKAS11 frames openpilot sent have valid CRC8 checksums.
   - LFAHDA_MFC (`0x485`) is sent (`SEND_LFA`).
   - Panda rx: 0 invalid frames, no `safetyRxChecksInvalid`, no panda faults.
   - `harnessStatus=flipped` 100% of the time. The panda handles orientation itself; this is informational.
4. **Safety replay with openpilot's real TX** (opendbc `replay_drive`, the logged safety mode/param, MADS on):
   - Route 4: OK. Zero frames blocked while controls were allowed. Besides the UDS fingerprint queries, 2 LKAS11 frames were blocked while controls weren't allowed. **Not investigated.** Hypothesis: engagement-boundary timing in the replay.
   - Route 3: the replay flags 9 blocked CLU11 frames while MADS lateral was allowed. Decoded: all 229 CLU11 frames openpilot sent on route 3 were CANCEL. 220 were sent while stock cruise was on (allowed); 9 were sent just after cruise had already turned off, and the panda blocked them, which is correct per `hyundai.h` L294. They come from openpilot cancelling stock cruise while engagement was blocked by no-entry (`carcontroller.py` L165–166). Generic behaviour, not port-specific. No unsafe TX was observed.
5. **Engaged lateral (route 4):**
   - ~304 s at vEgo 2.5–32.3 m/s (mean 22.6 m/s, ≈51 mph). There was little very-low-speed engagement, so **low-speed EPS behaviour is still untested**.
   - `steerFaultTemporary`/`Permanent`: 0. Command torque never saturated. Normalized command torque p5/p95 −0.25/+0.26 (extremes −0.98/+0.81).
   - |desired − actual| lateral acceleration: mean 0.085, p95 0.24 m/s², with desired |lat accel| up to 3.5 m/s².
   - The driver was applying torque (`steeringPressed`) for ~7% of engaged frames; this includes lane-change nudges (34 lane-change events).
   - Oscillation check (near-straight driving, |desired| < 0.3 m/s², v > 10 m/s, ~148 s): steering angle std 1.47°, spectral peak 0.30 Hz, 17% of power in 0.5–3 Hz. Command torque std 0.065, peak 0.40 Hz. **No clear oscillation (preliminary**: an approximate method with no reference car). Command-torque sign flips happen ~90 times per engaged minute, but at small amplitude.
6. **CAN validity:** `canValid=false` only at ~8 s after each route start (startup); never while driving. No CAN timeouts.
7. **Device load vs pre-deploy baseline** (CPU mean 53–82%, p95 80–88%):
   - Route 4: CPU mean 56.8%, p95 79.3%; while engaged, mean 57.6%. Memory ~61%; max CPU temp 67 °C.
   - Route 3: mean 60.9%. Within the acceptance band (≤ +5 points); no thermal alerts.
8. **Alerts/events:** no port-related alerts. The events seen were normal: gear, seatbelt, park brake, overrides, lane change and calibration (route 3 started at "Calibrating 0%"). The only abnormal one is `processNotRunning` (micd, soundd) on route 3.

## Not established / next

- Low-speed (<~5 m/s) engagement behaviour, any EPS lockout, and stop-and-go.
- Steering tune quality (steerRatio 12.9 is a guess; torque `[2.7, 2.7, 0.11]`): needs more engaged data across speeds and curves, and the driver's subjective feel. The current data shows no faults or saturation and moderate tracking error. That does not show the tune is optimal.
- More engaged time. ~5 minutes is a small sample.
- Whether the micd/soundd failure correlates with anything on this device. A user-reported generic bug; not investigated.
