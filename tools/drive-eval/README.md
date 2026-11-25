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

## Added 2026-11-20

Reading logs on the PC: `pip install pycapnp zstandard`, then set `CEREAL_DIR` to the sunnypilot checkout's `openpilot/cereal` folder and `CAR_CAPNP_DIR` to a folder holding `car.capnp` (`git show HEAD:opendbc_repo/opendbc/car/car.capnp > car.capnp` in the checkout).

| Script | Where | What it does |
|---|---|---|
| `pclog.py` | PC (imported) | `for msg in pclog.read("...rlog.zst")`: reads a comma log with pycapnp. About 0.3 s per segment. Stops quietly at a message cut off at ignition-off. |
| `gap_check.py <recordings root>` | PC | steady-following distance per gap setting (cluster bars) for each setup in `SETUPS`, against following time x speed + 6 m + extra, and the following time the measurement implies |
| `gap_safety.py <recordings root>` | PC | per setup in `GROUPS`: time-gap percentiles, shortest time to collision, strongest braking and each event under -1.5 m/s2, the set speed against the cluster, and each stop with the speed at which the stop was first requested |
| `gap_speed.py <long extract dir>` | PC | median following distance per 5 mph band for the stock cruise's closest setting and each openpilot setup, with a straight-line fit; prints a JSON line for charting |
| `render_fan_ui.py <checkout> <out.png>` | PC (Pillow) | runs `fan_indicator.py` and `long_indicator.py` with a drawing stand-in and renders the screen at several fan settings |
| `render_screen_map.py <checkout> <out.png>` | PC (Pillow, numpy) | places every driving-screen element from the real icons and fonts at the positions in the code, in seven situations, and reports any two elements that share pixels. Positions are transcribed by hand: update it when the widgets change. |

- **A following time is not a gap.** The planner's desired distance at equal speeds is time x speed + 6 m + `g70_long_stop_extra`. Check a new setting with `gap_check.py` before describing it as a distance.
- **Before adding anything to the driving screen**, run `render_screen_map.py`: an earlier change was checked against one neighbour and overlapped another.

## Added 2026-11-20 (afternoon)

| Script | Where | What it does |
|---|---|---|
| `restart_delay.py <recordings root> <route> ... [--trace]` | PC | every standstill behind a lead with openpilot longitudinal: when the lead starts, when the stop request is dropped, when the command goes positive, when the car moves and reaches 1 and 3 m/s, and the lead's head start. `--trace` prints each at 0.25 s steps. |
| `replay_quick_start.py <checkout> <recordings root> <route> ...` | PC | runs `g70_long.QuickStart` from the checkout over logged drives: where it would start, against the logged stop release, and whether the lead really left. `EARLY=0.3` enables the early stage. The car's response is the logged one. |
| `lat_state.py <lateral extract dir> <route> ...` | PC | per route: learned torque values and whether they are used, steer ratio, stiffness, angle offset, learned delay, lateral params, and basics above 60 mph |
| `sway_vs_lead.py <lateral extract dir> <long extract dir> <route> ...` | PC | lane movement above 60 mph by lead distance and by the car's own acceleration |

- **Whole-drive steering numbers depend on the route as much as on the setup.** Above 60 mph with curves included, lane movement ranged from 2.3 to 9.1 cm across drives with no relation to settings. Use the same-road section of `sway.py`, and prefer drives in the same direction at the same time of day.
- **A delay can be the car's.** Before changing what is asked, check with `restart_delay.py --trace` how long the car takes after the request.

## Added 2026-11-20 (evening)

| Script | Where | What it does |
|---|---|---|
| `brake_events.py <long extract dir> <out.json> <route> ...` | PC | every substantial braking event with openpilot longitudinal (1.5 m/s2 held 0.5 s, or a slowdown to a standstill from above 15 mph): a summary line and a 4 Hz time series per event |
| `brake_plot.py <events.json> <out prefix>` | PC (matplotlib) | small-multiple pages of those events, 12 per page: speed of car and lead, gap, acceleration asked and measured |
| `plan_source.py <recordings root> <route>` | PC | which part of the planner held the request (lead plan, cruise plan, driving model), overall and per braking stretch, with the model's own request alongside |
| `replay_lead_brake.py <g70_long.py> <out.npy> <route> "<tau thr>" "<tau thr>"` | comma (offroad) | replays a route through the installed planner as installed and with a lead-braking fade setting from a not-yet-installed `g70_long.py` |
| `replay_plan_variants.py <out.npy> <route> <variant> ...` | comma (offroad) | the same for variants `jerk=<scale>` (smoothness weights) and `ahead=<s>` (plan read further ahead); `base` for none |

- **Replay before recommending a planner change.** The unchanged replay matched the log at 0.999, a 28-minute route with four variants takes about ten minutes, and it showed in advance that a change would do nothing. A replay keeps the logged gap and car response, so it can show when the planner asks, not what a different following distance would do.
- Onroad-only processes are not running while parked, so the replay loads the planner without disturbing anything; run it with `nice`.

## Added 2026-11-21

- **The car creeps at about 0.9 m/s (2 mph) against a weak braking request.** Any stop logic that waits for a lower speed lets it close on the lead. Check a stop with `gap_safety.py` (final gap, speed at the stop request) before and after changing it.
- Setup lists in `sway.py`, `gap_check.py` and `gap_safety.py` now include `e2` / `e3`.

## Added 2026-11-21 (evening)

| Script | Where | What it does |
|---|---|---|
| `mdps12_check.py <recordings root> <route> [max segments]` | PC | on the steering unit's MDPS12 frames: does the CRC8 reproduce byte 3, does the counter step by one, are bits set outside the DBC signals; on frames openpilot sent to the camera: checksum, counter, and which fields differ from the car's latest frame |

- **Logs from another branch:** copy that branch's `openpilot/cereal/*.capnp` (with `include/`) and `opendbc/car/car.capnp` to a folder and point `CEREAL_DIR` / `CAR_CAPNP_DIR` at it. Do not import `opendbc.car` and `pclog` in one process: both load `car.capnp` and Python exits without a message; dump the frames with one script and test with another.
- **Before re-sending a message, check the bits no signal covers.** MDPS12 always carries three (32-34); a re-pack from the DBC silently dropped them.
- `sway.py`: the setup list now compares our recent drives with `g70-2024-new`.

## Added 2026-11-23

- **Compare tunes in torque counts, not in factor and friction.** Both are fractions of the car's maximum torque: factor 2.5 at a 270-count limit is 108 counts per m/s2, factor 3.45 at 384 is 111. The friction snap near zero is friction x maximum / ramp width.
- **Before trying a borrowed steering model, sample its reaction to fast changes** (the lateral jerk input), not only its steady output.
- `sway.py`: the setup list now holds the standard-value tests on sunnypilot's branch.

## Added 2026-11-25

| Script | Runs on | What it does |
|---|---|---|
| `extract_pc.py <tools dir> <out dir> <rlog glob> ...` | PC | runs the per-segment extraction of `extract.py` with `pclog.py` in place of the device's log reader (set `CEREAL_DIR` / `CAR_CAPNP_DIR` for the branch that made the log; use Windows-style paths). No device needed. |
| `render_steer_bar.py <sunnypilot checkout> <out.png>` | PC | draws the bottom bar of the driving screen in steering-wheel mode by running the real `torque_bar.py` with a stand-in drawing library |
| `loopmodel.py` | PC | small-signal model of the steering loop from the identified steering (stiffness, damping, delay) and the v1 control law. **It does not reproduce the measured response** (gain 1.2-1.4 and 30-50 degrees of lag predicted at 0.2-0.45 Hz, 0.84-0.90 and 81-92 measured); kept as a record, not for choosing settings. |
| `delay_extract.py <out.npz> <rlog glob>` | PC | per route at 100 Hz: request, measured curvature, torque, raw gyroscope, calibrated yaw rate where logged, lane lines, lagd's delay |
| `delay_measure.py <label>=<file.npz> ...` | PC | the delay chain (model request, request, torque, wheel, vehicle) by cross-correlation and by cross-spectrum phase in three frequency bands, and the car's position toward the inside of curves while the request builds, holds and unwinds |
| `curve_phases.py <gyro_to_yaw.npy> "<label>=<a.npz>,<b.npz>" ...` | PC | every curve split into entry, mid-turn and exit: timing, error against the request, position toward the inside, wheel movement, torque. A label containing `270` uses that torque limit. |
| `msg_check.py <route prefix> <first seg> <last seg>` | PC | what our branch sent on a drive: SCC14 counter and checksum, MDPS12 to the camera, the camera's LKAS12 against the re-sent copy, panda and car faults |

- **Check `IsOffroad` before pulling logs.** A pull while the car is on adds load to a comma that is running the car.
- **Bin by 10 mph before claiming a speed effect.** Wide bands (15-30 mph against the highway) made the torque need look speed-dependent; it is flat from 35 mph up.
- **A controller's own error (`torqueState.error`) is the direct measure of how well steering follows its request**; compare it across setups before blaming the controller for lane movement.
- **Steady-state torque data cannot tell a soft centre from stiction.** A wheel held by friction shows the same flat zone.
- `sway.py`: the setup list now holds the settings tests on sunnypilot's branch (`00000013` to `00000017`).

- **Measure delay against the vehicle's yaw rate, by frequency and by speed.** The cross-correlation peak and the phase delay differ (0.20 s against 0.36 s on one drive); the phase delay at the sway frequencies is the one the planner's delay stands for.
- **A measured response delay is not a planner setting.** Raising the look-ahead to match it made the steering worse; test a timing change on the road before believing the measurement that suggested it.
- `sway.py`: the setup list now holds `00000018` and `00000019`.
- Where lane lines are missing (slow roads), measure the wheel (swings of 1 degree or more per minute, by 10 mph band) instead of lane position; `sway.py` needs both lines.
- `sway.py`: the setup list now holds `0000001a`.

## Drive quality in one command (added 2026-11-25)

`drive_quality.py` reads a drive's rlogs on the PC and prints a rated scorecard, with an HTML copy.

```
python drive_quality.py --baseline 000000d4 000000e1     # "good" means like these drives
python drive_quality.py 0000001a                         # assess a drive (several routes may be given)
python drive_quality.py --trend                          # one line per drive assessed so far
```

- Set `CEREAL_DIR` / `CAR_CAPNP_DIR` as for `pclog.py`; `DRAGAL_DATA` points at the data root (default `~/Documents/DragalPilot`). Rlogs are found under `recordings/` by route name, read in parallel and cached; about 13 s per drive the first time.
- Output goes to `<data>/analysis/quality/`: `<route>.html`, `<route>.json`, `history.jsonl`, `baseline.json`. Nothing is written to the repo and no position data is read.
- **Sections:** steering on straights per speed band (lane movement, slow and large swings, wheel movement, torque flips, the controller's tracking error); low speed without lane lines (wheel only); curves (position toward the inside on entry, mid-turn and after the exit); take-overs; speed control (hard braking, strongest braking, command flips, time gap, closest stop); messages and faults (SCC14, MDPS12, camera warnings re-sent, panda, car faults).
- **Ratings:** good = within 25 % of the baseline or better, fair = within 75 %, poor beyond, with a small floor so noise near zero is not rated. Bands with under 1.5 minutes are shown unrated. Braking, the closest following gap, stop distance and message checks use fixed limits.
- **Checked against the other tools:** on `e1` above 60 mph it gives 2.41 cm of lane movement (`sway.py` 2.3 cm in its 0.2-0.7 Hz band) and on the look-ahead drive `00000018` 1.25 large swings per minute (`sway.py` 1.25). It flags `00000018` (3 poor) against `0000001a` (1 poor) and the baseline drives.
- It does not replace `sway.py` (loop analysis, same-road comparison) or `curve_phases.py` (per-curve detail); it is the first look at a new drive.
- The baseline is whatever drives were last given to `--baseline`; ratings from different baselines are not comparable.
