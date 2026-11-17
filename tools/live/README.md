# live

A light live reader for steering values, written 2026-11-17. It has only been run with the car off; pulling the rlogs after a drive (see `tools/drive-eval`) turned out to be quick enough over USB that it was not needed. Treat it as untested onroad.

| Script | Where | What it does |
|---|---|---|
| `device_reader.py` | comma (piped over ssh, nothing written to the device) | samples carState, carControl, carOutput, controlsState torque state, model lane lines, lateralDelay and the learned torque values at 20 Hz and prints CSV rows; exits when the connection closes |
| `live.py --out <folder> [--adb <adb.exe>] [--host <ip>]` | PC | forwards local port 8022 to the device's ssh port with adb (or uses `--host` on Wi-Fi), saves the rows to a CSV and prints a status line every 5 s |
| `summary.py <csv> [--last S]` | PC | tracking by speed band and the straight-road band table of `drive-eval/weave.py`, at 20 Hz |

Checked: 500 rows in 25 s over USB at a steady 20 Hz; every field exists in the device's schema; about 2 % of one core with the car off (it will be higher onroad, and device load is safety-sensitive, see `CLAUDE.md` §4); the summary recovers a known gain and lag from synthetic data.
