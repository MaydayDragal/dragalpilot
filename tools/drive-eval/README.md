# drive-eval

Scripts used in November 2026 to pull steering data off the comma and compare drives. They are working tools, not a package: route lists and configuration labels are edited in the scripts.

## Two halves

**On the comma (offroad only)**, with its own Python and `LogReader`:

```sh
cd /data/openpilot
PYTHONPATH=/data/openpilot nice -n 10 /usr/local/venv/bin/python /data/tmp/ext/<script>.py <route> [<route> ...]
```

| Script | What it does |
|---|---|
| `extract.py` | One compact `.pkl` per segment in `/data/tmp/ext/`: carState, carControl, carOutput, controlsState torque state, model lane lines, learned parameters, events, bookmarks, selected params. 4 processes. |
| `canscan.py` | For a route with a bookmark: history of `0x53E` and every CAN bit with few transitions near the bookmark. |
| `lkas12_stats.py` | Frame rate and payload statistics of LKAS12 (`0x53E`) over routes. |
| `lkas12_resend_check.py` | Camera vs re-sent LKAS12 stream for one route: counts, gaps, mismatches, attention-level history. |

Copy the `.pkl` files to the PC and delete `/data/tmp/ext` afterwards. A route is `<counter>--<id>` as listed under `/data/media/0/realdata`.

**On the PC**, any Python 3.12 with numpy; no repo code is imported:

| Script | Usage | Output |
|---|---|---|
| `lib.py` | imported by the others | loads a folder of `.pkl` into 100 Hz arrays per route |
| `overview.py <dir>` | one folder | per-route settings, events, alerts, learned values |
| `win.py <scripts dir> <dir> <route> <t0> <t1> <step>` | | time series table for a window |
| `compare.py <scripts dir> <dir> ...` | | tracking by speed band, curve events, passes through a reference location |
| `weave.py <scripts dir> <dir> ...` | | straight-road spectra: lane motion, request→actual gain and lag, wheel motion, per configuration |
| `loopfit.py <scripts dir> <dir> ...` | | plant estimate (torque → lateral accel, request as instrument), small-signal controller law, fit against the measured response; writes `loopfit.pkl` |
| `candidates.py` | run where `loopfit.pkl` is | predicted gain / lag / torque activity for candidate settings |

## Definitions

- **Straight:** 5 s moving mean of the request within ±0.35 m/s², hands off, lat active, no blinker, both lane-line probabilities > 0.5.
- **Spectra:** Hann windows of 20.48 s, 50 % overlap, averaged auto- and cross-spectra; band values are sums over the band.
- **Lane position:** mean of model lane lines 1 and 2 at their first point.
- **Gain / lag:** logged `desiredLateralAccel` (the controller's delayed setpoint) → `actualLateralAccel`.

## Limits

- The loop model is linear and small-signal. It reproduces measured gains to roughly ±0.2 and, after fitting one extra delay (0.15 s), the lag to roughly ±10°. It under-predicts the jerk-aware controller's gain at 0.45–1 Hz. Use it to rank directions, not to predict numbers.
- Comparisons between drives are on different roads and days unless stated.

## Added 2026-11-16

| Script | Where | What it does |
|---|---|---|
| `speedlimit_nav_vs_camera.py <route> ...` | comma | seconds by (nav limit from `0x544`, camera LKAS12 fields, re-sent sign) |
| `speedlimit_sources.py <route>` | comma | sunnypilot map source validity and a sample of the speed-limit resolver |
| `hda11_vs_nav.py <route> ...` | comma | camera `0x484` payloads against the nav limit and LKAS12 sign |
| `esp_events.py <scripts dir> <dir> ...` | PC | when `espDisabled` events occur (speed, lat active) |

## Added 2026-11-17

| Script | Where | What it does |
|---|---|---|
| `compare_req.py <scripts dir> <dir> ...` | PC | `compare.py`'s tracking and curve tables with the request taken as `desiredCurvature × v²`, so V0 and V1 drives can be compared |

- **V0 and V1 log different setpoints.** `LatControlTorqueV0` logs the future request as `desiredLateralAccel`; the upstream controller (`TorqueControlTune` 1.0) logs the request one steering delay ago. Error, gain and lag from `compare.py` and `weave.py` are not comparable across the two; lane and wheel motion are.
- **Pulling over USB.** With platform-tools, `adb forward tcp:8022 tcp:22` and ssh to `127.0.0.1:8022` (use `-o HostKeyAlias=<the device's known_hosts name>`). The link drops at times: take the device's `sha256sum` list first, fetch only files that do not match yet, and repeat until all match.
- `weave.py` now skips routes that are not in the loaded folders.

## Added 2026-11-18

| Script | Where | What it does |
|---|---|---|
| `bookmark_bits.py <route> [window]` | comma (piped, read-only) | CAN bits that change before every chosen bookmark (`BOOKMARKS=1,3,4`) and are otherwise quiet; history of SCC11 `SCCInfoDisplay` |
| `scc11_roundtrip.py <route> ...` | comma (piped) | every logged camera SCC11 payload decoded and re-packed from the DBC, plus the effect of the standstill-prompt filter |
| `scc11_resend_check.py <route>` | comma (piped) | camera SCC11 against what openpilot requested and what the panda sent: counts, counter steps, spacing, delay, payload equality, panda state, events |
| `lkas11_daw_scan.py <route> ...` | comma (piped) | camera LKAS11 frames by `CF_Lkas_FcwBasReq`, `CF_Lkas_SysWarning` and LKAS12 attention warning |
| `plan_dump.py <route>` | comma (piped, result to stdout as `.npy`) | per model frame: speed, flags, published delay, logged action, lane lines, plan yaw and yaw rate |
| `smooth_methods.py <file.plan.npy> ...` | PC | rebuilds the request from the logged plan as modeld does and compares smoothing and look-ahead variants (open loop) |
| `curve_position.py <scripts dir> <dir> ...` | PC | lane position at curve entry, mid-curve and exit, swing, and delivered / requested lateral acceleration |

"Piped" means `ssh ... 'cd /data/openpilot && PYTHONPATH=/data/openpilot /usr/local/venv/bin/python - <args>' < script.py`: nothing is written on the device.

- **Signs:** model lane-line `y` is positive to the right (the left line is negative), and `controlsState.desiredCurvature` is positive for a right curve (correlation with `steeringAngleDeg` −0.93 on `c1`).
- **Echo sources in `can`:** `src` 128 + bus is a frame the panda put on that bus, forwarded frames included; `src` 192 + bus is a frame openpilot asked for that the panda rejected.

## Added 2026-11-19

| Script | Where | What it does |
|---|---|---|
| `sway.py <dir> ...` | PC | sway, ping-pong and wobble report per setup: swing and train counts, who moves, loop estimate per band, same-road comparison, verdict. Writes `sway-latest.html` and a dated copy (graphs and a map) to `../sway` beside the extracts and opens it. `NO_OPEN=1`, `SWAY_OUT=<folder>`, `BASE="<setup label>"`. Edit `SETUPS` for new drives (at most 8). |
| `sway_report.html` | | template of that report; the data is inserted by `sway.py` |
| `bookmark_context.py <route> ...` | comma (piped, read-only) | for every bookmark: openpilot alerts, HUD alert, hands-on state and every field of LKAS11, LFAHDA_MFC, HDA11_MFC, LKAS12 and MDPS12 that changed in the `WIN` seconds before it, as the camera sent them and as they went to the car |

- **The report holds GPS positions.** It is written outside the repo; do not copy it in. Its map background is fetched from OpenStreetMap while it is open.
- **Reading the verdict:** ping-pong with a long follow delay means the controller waits too long; wobble with a follow gain at or above 1 at 0.7-1 Hz means the car over-answers fast requests.

## Speed control (longitudinal), added 2026-11-19

| Script | Where | What it does |
|---|---|---|
| `extract_long.py <route> ...` | comma (offroad, writes `/data/tmp/extl/*.pkl`) | per segment: carState and carControl at 20 Hz, radarState lead, openpilot's longitudinal plan, the model's lead, the camera's SCC11 / SCC12 / FCA11 decoded at 25 Hz, GPS. About 0.7 MB per segment; 300 segments take about 10 minutes, so run it in the background for many routes. |
| `long_baseline.py <dir> [route ...]` | PC | following gap per setting, comfort, hard braking, speed see-saw, set-speed holding, stops and restarts, driver take-overs, warnings, and openpilot's planner against the stock cruise's request. Route arguments limit it to those routes. |
| `long_trace.py <route> <t0> <t1> [step]` | comma (piped, read-only) | time trace of speed control: speeds, set speed, engagement, acceleration command and plan, plan source, lead, with every cruise button press, event change and alert change |

- With stock longitudinal, `a_req` in `long_baseline.py` is the car's own cruise request. With openpilot longitudinal it is still the camera's SCC12, which is no longer what drives the car; use `carControl.actuators.accel` (in the `cc` rows of the extract) for what was commanded.
- `sway.py` now has three speed bands (20-45, 45-60, above 60 mph). Its `SETUPS` list is limited to eight; older setups were removed from it as newer ones were added (their numbers are in the findings).

## Added 2026-11-19 (evening)

| Script | Where | What it does |
|---|---|---|
| `long_scan.py <route> ...` | comma (piped, read-only) | per route: alerts, fault and mismatch events, panda TX-blocked count and samples with `longActive` but controls not allowed, the lead-departure bit as the camera sent it and as it went to the car, cluster gap bars, every engagement with the buttons that led to it, and true / cluster / set speed while holding speed |
| `replay_planner.py` | comma (piped, read-only) | feeds the logged messages of a route to the installed `LongitudinalPlanner` and prints logged against replayed acceleration target and stop request, and the cluster-speed ratio. The route, segments and times are set at the bottom of the file. |
| `replay_fault.py` | comma, against a scratch copy of `opendbc` in `/data/tmp/st` with `libsafety.so` built there | replays the CAN traffic of the cruise fault (`d7`) through the panda safety code: when controls are allowed, and whether the rejected SCC12 frames are accepted |
| `render_gap_ui.py <sunnypilot checkout> <out.png>` | PC (needs Pillow) | runs the real `long_indicator.py` widget code with a drawing stand-in and renders the 536 x 240 comma screen for each gap setting, with zooms and the three-bar layout for comparison |

- **Panda safety tests on the comma:** copy `opendbc_repo/opendbc` to `/data/tmp/st/opendbc`, overlay changed files with LF line endings, build `safety/tests/libsafety/libsafety.so` with gcc (flags in the 2026-11-19 cruise-fault findings, section 4), and run `python -m unittest opendbc.safety.tests.test_hyundai` with `PYTHONPATH=/data/tmp/st`. The whole suite takes about 4 minutes. Remove `/data/tmp/st` afterwards. Run it for every change under `opendbc/safety`.
- **Before changing how openpilot longitudinal engages or disengages**, check the panda's rule for the same button (`hyundai_common_cruise_buttons_check`): if openpilot engages and the panda does not allow controls, SCC12 is rejected and the car raises a cruise fault that stays until it is restarted.

