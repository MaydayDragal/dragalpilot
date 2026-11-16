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
