# Log viewer

A single, self-contained HTML page for plotting the data in openpilot / sunnypilot rlogs.
Open [log-viewer.html](log-viewer.html) in a desktop browser (Chrome, Edge or Firefox), then drop `rlog`, `rlog.zst` or `rlog.bz2` files on it.
It needs no install or network access, and decodes everything locally in the browser tab.

It is a browser counterpart of openpilot's own viewers (`tools/jotpluggler`, `tools/plotjuggler`, `tools/cabana`). It uses the same series paths and layout format as jotpluggler.

## What it does

- **Open** one or more segments (files or a route folder). They share one timeline in seconds since the earliest `logMonoTime`, as in jotpluggler.
  Each segment repeats a few messages stamped at the route start, so time 0 is the route start even when you open later segments. The initial view, double-click and Home show the range where the data is.
  - Damaged files open as far as they can, with a warning: truncated `.zst`/`.bz2` (complete blocks only) or a cut-off last message.
  - Every pointer is checked against its own capnp segment. A message with a corrupt pointer anywhere is dropped from all series of its service, and counted. Info lists the counts and the first error.
  - zstd frames that carry a content checksum are verified (XXH64). openpilot's `rlog.zst` frames normally carry none, so those can't be checked; bzip2 blocks always carry a CRC, which is checked.
- **Browse** every service in a tree with message counts and rates. Expanding a service decodes it. The filter box matches words in paths.
- **Plot**: click or drag a field onto a plot. All plots share the time axis and the cursor.
  - Drag pans, the wheel zooms, Shift+drag zooms to a range, Ctrl+wheel zooms the value axis, and double-click shows the whole data range.
  - The legend shows each value at the cursor, using enum names where they exist.
  - Panes can be split down or right, and arranged in tabs.
- **Context**: a timeline of `carControl.latActive` / `longActive`, with optional shading of lateral-active time in every plot.
- **Logs**: `logMessage` / `errorLogMessage` entries, filterable, following the cursor. As in jotpluggler, an entry identical to the previous one (same time, text and service) is shown once.
- **Inspector**: the full decoded message of any service at the cursor.
- **CAN**: raw bytes per bus and address for `can` / `sendcan`, as `/can/<bus>/0x<ADDR>/byte<N>`. The frame index is built in the background the first time it's needed.
  - With a DBC loaded, signals appear as `/can/<bus>/<Message>/<Signal>`, with value tables (labels match the physical value).
  - Multiplexing follows jotpluggler: `m<n>` is decoded only when the switch `M` reads n; `m<n>M` (extended multiplexing) is read as `m<n>` with a warning; a multiplexed signal in a message without a switch decodes on every frame.
  - DBC lines that can't be read are listed in Info and a toast. Their signals are never attached to another message.
  - `/can/valid`, `/can/logMonoTime` and `/can/t` exist like for every service.
- **Layouts**: openpilot's 17 jotpluggler layouts are built in. Import and export use jotpluggler's JSON.
  - Supported: `derivative` and `scale` transforms, and `y_limits`.
  - Custom Python series are evaluated when they are jotpluggler's generated sample function (a one-line `return`, then jotpluggler's loop, accepted only verbatim) or a single `return` line (numpy on whole arrays, as in `math_eval.py`). The extra sources are resampled by previous-sample hold, as there.
  - The expression is parsed as a small Python subset and compiled with Python's meaning: numbers, `+ - * / **`, comparisons (chained ones in the sample function), `and`/`or`/`not` with Python truthiness (NaN is true), `abs`, builtin `min`/`max` (2+ arguments, sample function only), `np.pi`/`np.e` and elementwise `np.` functions (`abs sqrt sin cos tan arcsin arccos arctan arctan2 exp log log10 log2 floor ceil sign maximum minimum hypot radians degrees deg2rad rad2deg clip where square`).
  - Anything else is refused rather than approximated: `%`, `//`, tuples, Python globals, multi-line code, names jotpluggler doesn't define (bare `sqrt`, `math.*`), and in the whole-array form `and`/`or`/`not`, chained comparisons, `min`/`max` reductions and constant results.
  - Not supported: stateful Python series, camera panes and map panes. These are marked as unsupported rather than guessed.
  - Layouts are read as jotpluggler reads them: a node with `curves` is a pane, a split is vertical only when it says so, tabs that aren't objects are skipped, and fields of the wrong type count as absent (e.g. `"scale": null` means 1). Pane titles are shown; double-click one to rename it.
  - A layout's saved `range` is not applied, because the view fits the loaded data. Export writes the current view as each pane's `range`.
  - Colors must be `#rrggbb`. Any other value falls back to the palette.
- **CSV** export of the current tab's visible curves in the visible time range. Curves without data are listed in a toast.

## Series paths

These follow `tools/jotpluggler/generate_event_extractors.py`:

- Every event adds `/<service>/valid`, `/<service>/logMonoTime` and `/<service>/t`.
  A payload field with one of those names (e.g. `lateralTorqueParameters.valid`) is renamed `/<service>/valid (payload)`. jotpluggler keeps both series under the same path, and its path lookup returns the event-level one, so the payload field can't be reached there.
- Bool, integer, float and enum fields are series. Union members appear only while set, and pointer fields only when present.
- Struct lists are indexed by position, e.g. `/modelV2/laneLines/0/y/0`.
  Scalar lists are indexed when they have at most 64 entries (jotpluggler uses 16). This makes the 33-point model and plan arrays plottable.
- Text, data, void and anyPointer fields are not series. Use the inspector for those.
- The value at the cursor is the latest logged sample at or before it, and "—" before the first sample.
  jotpluggler interpolates between samples for curves it does not draw as steps, and clamps to the first and last sample.
- Series whose wire type is integer, bool or enum are drawn as steps, ending at the last sample. jotpluggler decides by whether the values are integers.

## Schema

Decoding is driven by `schema.json`. It is generated from the pinned checkout's `openpilot/cereal/log.capnp` (which imports `car.capnp` and `custom.capnp`), and its `revision` field records the commit.
Logs from other software versions still decode: fields the schema doesn't know are skipped, and fields the log lacks read as their defaults. This is the usual capnp compatibility.
Regenerate the schema when the baseline moves (needs pycapnp, e.g. the checkout venv in WSL):

```sh
python export_schema.py ../../sunnypilot schema.json
python build.py            # writes log-viewer.html; stdlib only
```

`build.py` inlines `src/` (the decoder `logreader.js`, `bunzip2.js`, `dbc.js`, the UI `app.js`, `app.css` and `index.html`), `vendor/fzstd.umd.js` (MIT, zstd), `schema.json` and the jotpluggler layouts from the checkout.

## Tests

All tests run in WSL. Write their outputs to the data root, not here.

| Test | What it checks |
|---|---|
| `test/ref_flatten.py` + `test/digest.js` | Every series (count, times, values) from the JS decoder against an independent pycapnp walk of the same rlog. Usage is in each file. |
| `test/ref_can.py` + `test/can_digest.js` | Every DBC signal decoded by `dbc.js` against opendbc's bit extraction (`get_raw_value`), using the generated DBC opendbc itself uses. |
| `test/robustness.js` | Damaged input built from a real segment: undecodable root; out-of-bounds, double-far-to-missing-segment and cross-message pointers (the message must vanish from every series, the rest stay identical); cut multi-segment header; truncated zstd and bz2; corrupt bz2; checksummed zstd (written by python zstandard) with bit flips; DBC parser edge cases. |
| `test/smoke.js` | Headless Chromium (Playwright): open files, plot, zoom, pan, filter, layouts, logs, inspector, DBC, CAN states, custom-series semantics and sandbox, malformed layouts, tiny value ranges, dark theme and phone width. |

## Limits

- Everything stays in memory: the decompressed logs, about 1 GB for a 20-segment (19 min) route, plus what has been decoded. The CAN index adds about 0.26 GB, and every service and CAN together give about 1.55 GB (JS heap, Chromium). Load fewer segments on small machines.
- Video is not shown.
- DBC files are not bundled. opendbc generates many of them at build time, e.g. `hyundai_can_generated`; export one with `opendbc.get_generated_dbcs()`.
