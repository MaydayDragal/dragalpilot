# Torqued cache reconstruction: end of route 0x16 (2026-10-05/06, session 9)

**Status:** reconstruction done offline. **Validation partly fails** (point count off by 1 of 7,723; see §4); a post-hoc point-level check on held-out routes reproduces 95.7% of the device's points exactly, with the same fit (§6, F2). Restore check passes. Focused adversarial review done (§6). **User chose option A; deployed 2026-10-06 06:25 EDT** (see the [proposal](../proposals/2026-10-06-g70-torqued-restore.md) deployment record). **Check drives 2026-10-06:** restore confirmed on the device (first message 7,722 points, valid, decay 250, laf 3.688; G70 fingerprint on all 8 starts), see the proposal's check-drive record.

**Goal (user decision, session 8):** restore torqued's learned state on the device to how it stood at the end of route `0x16`, before the `MOCK` route `0x17` invalidated the cache ([device-errors findings](2026-10-05-g70-device-errors.md) Follow-up 3).

## 1. Why a reconstruction is needed (confirmed source facts, `c027a92857` = device `82f58a9a8c` for these files)

- The rlog `lateralTorqueParameters` messages carry no points (`torqued.py` L276–278, `with_points=DEBUG`). Points exist only in the `LiveTorqueParameters` param, written every 240 frames with points (L280–283), and that param is gone.
- `torqued.main()` (L255–283):
  - SubMaster polled on `deviceMotion`, conflated sockets (`cereal/messaging/__init__.py` SubMaster);
  - `frame` starts at −1, so the first publish **and** cache write are at frame 0;
  - `update()` times out after 100 ms and still advances `frame`;
  - inputs are handled only when `sm.all_checks()`.
- Restore (L105–134): needs `CarParamsPrevRoute` and `LiveTorqueParameters`. The restore key is (fingerprint, lateral tuning, friction, latAccelFactor, VERSION). `card.py` L163–171 copies `CarParamsPersistent` → `CarParamsPrevRoute` at each fingerprinted start. `CarParams` is cleared on every onroad transition (`params_keys.h` L23), so torqued blocks until card fingerprints.
- Controls apply the **filtered** laf / offset / friction whenever the message passes `all_checks` and `useParams` (`controlsd.py` L93–100). They do not wait for `valid`.

## 2. Inputs (observations from the rlogs; `analysis/g70-torqued-restore-20261005/inventory.json`)

- 15 routes, 8 → `0x16` in driving order, all `GitCommit 82f58a9a8c`, all with restore key `(GENESIS_G70_2024, torque, 0.07, 4.0)`.
- Torqued-relevant params are identical on all routes:
  - `LagdToggle=1`;
  - `TorqueParamsOverrideEnabled=0`;
  - `EnforceTorqueControl`, `LiveTorqueParamsToggle` and `CustomTorqueParams` absent.
- Route `0x0d` (8 s): no carParams and no torqued output, so card never fingerprinted and torqued never ran.
- Route 8 starts empty (0 points, decay 50, 4.0 / 0.07), consistent with the restore key change at the `82f58a9a8c` deployment.
- Every route's first logged `totalBucketPoints` equals the previous route's last value, so no points were lost between routes.
- Gaps: route 9 segment 4 and route `0x12` segment 8 are 0 bytes; most routes' last segment is truncated (normal at route end). No `lateralTorqueParameters` gaps over 1 s and no resets.

## 3. Method

- **Replay:** `E:\DragalPilot\scratch\wsl\torqued\s9_replay.py` drives the checkout's **unmodified** `torqued.main()` from the rlogs (x86 WSL, test shim, real Params with `PARAMS_ROOT` on the data root).
- **Harness parts:**
  - `SubMaster.update` is fed from the log (the real `update_msgs`/`all_checks` are used);
  - `PubMaster` records instead of sending;
  - realtime config is a no-op;
  - the `LiveTorqueParameters` writes are recorded;
  - the bucket RNG is seeded (it only affects the random 2,000-point subsample of the raw fit);
  - route params come from initData, CarParams from carParams, and `CarParamsPrevRoute` is set per `card.py`.
- **v1 failed** (`validation_v1.json`): it modelled iterations before the first deviceMotion as exact 100 ms timeouts, and it delivered messages with no receipt delay.
- **v2** (Amendment 1 in `TOLERANCES.md`):
  1. **Schedule locked to the logged publish times.** The device ran exactly 5 iterations between consecutive publishes, the 5th on the last deviceMotion < 40 ms before the publish. The device's publish *times* steer the schedule; their *content* is used only for validation. This makes criterion A1 true by construction.
  2. **Receipt delay of 0.7 ms**, calibrated on route 8's first 400 s only. Publish windows whose point increments disagree: 25 at 0 ms → 1 at 0.7 ms (of 1,596). Everything else is held out.
- **v2b:** v2 with blocking setup writes. Content-identical to v2 for every route's cache, so the run is deterministic.

## 4. Validation (criteria fixed before comparing: `TOLERANCES.md`; result `validation_v2b.json`)

| Criterion | Result |
|---|---|
| A2 route 8 start | pass |
| D2 calPerc, D3 valid / Event.valid, D4 useParams / maxResets, D5 decay | pass on all routes (decay and valid flags: 0 differences at every publish) |
| S1 filtered laf / friction / offset | pass; max \|Δ\| 0.0016 / 0.00004 / 0.00022 |
| S2 raw fits vs seed noise | pass |
| C2 decay of each route's last cache vs next route's start | pass on all 4 routes where it applies (confirms the cache write timing) |
| C3 filtered values carried across routes | pass |
| **D1 totalBucketPoints** | **FAIL** on all routes: route 8 wanders −4…+1 and ends −4; route 9 ends −1; routes a…0x16 are **−1 at every publish** (about 17,000 publishes, so every add decision there matched) |
| **C1 point totals carried across routes** | **FAIL**: −4 after route 8, −1 at every later transition |
| **Output point count** | **FAIL**: 7,722 vs 7,723 |

- **Cause of the D1/C1 failures (diagnosis):** a few borderline add decisions in routes 8 and 9. They depend on whether a carOutput/carControl message published < ~1 ms after a deviceMotion was read in the same iteration. That is the device's scheduling jitter, which the logs don't record. The point *values* (interpolated steer) are subject to the same jitter, so a byte-exact copy of the device's points is not recoverable from rlogs.
- **Equivalence of the fit (route 0x16):** no points were added during route 0x16, so its 1,820 logged raw estimates are subsample fits of the device's exact point set. Replay minus device, mean raw estimates (`replay_v2/fit_compare.json`):
  - laf +0.0009 ± 0.0011 (device 3.616);
  - friction −0.00003 ± 0.00004 (device 0.0834);
  - offset −0.00015 ± 0.00014 (device −0.0964).

  None of these differences stands out from sampling noise. Routes c, e and 0x13 agree the same way.

## 5. Output

- **File:** `E:\DragalPilot\analysis\g70-torqued-restore-20261005\LiveTorqueParameters_end_route16_v2b.bin`, sha256 `2883e5dad34406447d4f2076f4fe2ab5e04f6a590f1490e341ba223690fa6adf`. It is the replay's last cache write in route 0x16 (frame 8880).
- **Contents:**
  - valid, calPerc 100, version 1, useParams, decay 250;
  - filtered laf 3.68845 / friction 0.080771 / offset −0.072296;
  - device's last logged values: 3.68754 / 0.080817 / −0.072577;
  - 7,722 points; buckets −0.5…0.5: 114 / 493 / 1500 / 1500 / 1500 / 1500 / 885 / 230.
- **Restore check** (`restore_check_v2/restore_check.json`; real `TorqueEstimator.__init__` and Params; device `CarParamsPersistent` sha256 `0b35e13d…` as both CarParams and PrevRoute):
  - restored, with filtered values and decay exact and points identical row for row;
  - valid, calPerc 100;
  - boundary cases: PrevRoute with a different laf → not restored; no PrevRoute → not restored.
- **Not device-specific:** the Event `logMonoTime` comes from the replay machine's clock; torqued ignores it on restore.

## 6. Focused adversarial review (one independent general-purpose agent, snapshot v2b; script hashes `SNAPSHOT_v2b_scripts.sha256`)

The reviewer confirmed:
- the harness semantics;
- the route order and initial state;
- the restore at every route start (the cache read equals the previous route's last cache sha at all 13 transitions);
- no unlogged points after truncated segments;
- the validator's indices and formulas.

| # | Finding (severity) | Verification / disposition |
|---|---|---|
| F1 | The post-wipe cache (routes 0x18–0x1d, 7,003 points) is real device learning that a restore would discard. A merge through torqued's own `add_point` gives the state torqued would hold had 0x17 not been MOCK (major) | **Agreed.** Checked against the source: add decisions don't depend on bucket contents; buckets are FIFO. Merge fit computed (§7). **Escalated to the user as a choice** (§7). |
| F2 | Point content is never validated; 6,000 points sit in full buckets that D1/C1 can't see (major) | **Agreed; check run (post-hoc, held out).** Same harness over 0x18–0x1d from an empty cache vs the device's actual cache: 6,702 of 7,003 points exact; 300/301 differ, 246 of them the same iteration with steer differing by a median 0.00008. Full-set fit laf 4.1242 vs 4.1239, friction 0.07022 vs 0.07024, offset equal. |
| F3 | The restore check was run on the v2 file, not v2b (minor) | **Fixed:** re-run on the v2b file (`restore_check_v2b/`), PASS (all 6 checks). The reviewer's own re-run also passed. |
| F4 | D4 doesn't check `version`; S1/D5/C2/C3 are vacuous on routes 8–0x11 (valid False, filters frozen); S2 counts n < 10 as a pass (minor) | **Agreed; recorded.** The output's version is 1. No S2 case had n < 10 (minimum 11). |
| F5 | Only 8 publish windows mismatch (route 8: 6, route 9: 2); an increment-matching fix is feasible (info) | **Agreed; not done.** It would fix counts but not the value jitter. Available if the user wants an exact count. |
| F6 | Questions 1–2 hold (info) | — |
| F7 | The output is restorable. The next start must fingerprint G70. It is a behaviour change, so §6 approval applies; re-pull the device state before writing (info) | **Agreed:** in the proposal. |

QA stage: **focused review done.** Findings verified; F3 fixed; F1 escalated to the user. Two-round QA not performed.

## 7. Options for what to restore (user chose A, 2026-10-06)

Full-set TLS fits use the same formula as `estimate_params`, over all points:

| Option | Points | Fit laf / offset / friction | Notes |
|---|---|---|---|
| **A**: end of 0x16 (as decided in session 8) | 7,722 (reconstructed) | 3.616 / −0.096 / 0.0835 | Filtered 3.688 / −0.072 / 0.0808. Discards the 7,003 newer points. |
| **B**: merge (A + the device's current points, through `TorqueBuckets.add_point` in cache order) | 8,665, valid, calPerc 100 | 3.656 / −0.021 / 0.0846 | Central buckets are exact device data from 0x18–0x1d; outer buckets come mostly from A. Filtered values still to be chosen (A's values, then convergence with a ~21 min time constant at decay 250, or a counterfactual replay). |
| Device today | 7,003 (exact), not valid, calPerc 59 | 4.124 / −0.015 / 0.0702 | Controls use the offline 4.0 / 0 / 0.07 until it becomes valid (outer buckets −0.5…−0.3: 18/100, −0.3…−0.2: 243/300). |

## 8. Limitations

- Offline only. The reconstructed points equal the device's in count to within 1 of 7,723, and in fit to within sampling noise; they are not byte-identical.
- The receipt delay is a calibrated harness parameter.
- Restoring discards whatever the device learned after the wipe (routes 0x18–0x1d: 7,003 points, not valid when pulled on 2026-10-05).
- From the next drive, controls would use laf 3.688 / friction 0.0808 / offset −0.072 instead of 4.0 / 0.07 / 0. These are the values the car drove with at the end of route 0x16 (valid since route 0x12). That is a record of earlier use, not evidence of performance.
