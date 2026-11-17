# G70 2024: controlsd crash fix, USB access, V1 controller, delay creep, request smoothing (2026-11-16 evening to 2026-11-17)

**Status:** `g70-fingerprint` @ `466c14c` on the device (2026-11-17 20:42Z). Settings: `TorqueControlTune` 1.0 (V1), Lateral Jerk on, Enforce on, override **4.5 / 0.07**, friction ramp **0.24**, published steering delay **fixed at 0.33 s** (offset file 0.135 s present but ignored), request smoothing **0.2 s**. **Not yet driven** with the fixed delay or the smoothing; the last driven setup is V1, 4.5 / 0.07, ramp 0.24, offset 0.135 s (`c2`, `c3`).

Follows [2026-11-16-g70-straight-sway-loop-model.md](2026-11-16-g70-straight-sway-loop-model.md). Scripts: [tools/drive-eval](../../tools/drive-eval/README.md), [tools/live](../../tools/live/README.md). Device identifiers and GPS are kept out of this repo.

Evidence labels: **source fact**, **observation** (rlog / swaglog / device state), **offline result**, **hypothesis**, **user report**.

## 1. controlsd crash on `d833479` (fixed in `77cc8c6`)

- **User report (11-16):** "control process not running" fault at the start of the first drive on `d833479`.
- **Source fact:** `d833479` made the jerk-aware extension read `self.lac_torque.friction_threshold`, but only the upstream `LatControlTorque` (V1) got that attribute. `controlsd_ext.initialize_lateral_control` returns `LatControlTorqueV0` when `EnforceTorqueControl` is off, or when it is on and `TorqueControlTune` is 0.0 (the param default). The V0 class has no such attribute, and V0 calls the extension only while lateral control is active.
- **Observation:** the device had `EnforceTorqueControl=1`, `TorqueControlTune=0.0`, `LateralJerkTorqueController=1`. swaglog shows controlsd raising `AttributeError: 'LatControlTorque' object has no attribute 'friction_threshold'` twice, from `latcontrol_torque_v0.py` line 112 through `latcontrol_torque_jerk_aware.py` line 43, on route `000000ba`.
- **Consequence for earlier notes:** every drive up to `bf` ran `LatControlTorqueV0` with the jerk-aware extension (logged `torqueState.version` 0). The 11-16 statement that the friction-ramp knob was "used by both torque controllers" was true only for V1.
- **Fix `77cc8c6`** (pushed, installed 2026-11-16 22:33Z): the extension reads `/data/g70_friction_threshold` in its own constructor. Offline: a stubbed reproduction fails on `d833479` with a V0-like host and passes on the fix for V0 and V1 hosts, with and without the file. On the device, before the reboot, both controllers and the extension imported and the reader returned 0.28.
- **Confirmed in the car:** route `000000bc` (483 s, up to 78 mph) has 256 s of `latActive`, first active at 97 s, one controlsd pid throughout, no gap > 0.02 s in `controlsState`, no controlsd traceback. With the fix the ramp knob took effect on the V0 + jerk path for the first time.

## 2. Access from a second PC (observations)

The drives in this document were analysed on a different Windows PC from the October VM: no `E:` data root, no WSL, Python 3.13 with numpy.

- **SSH key:** the device accepted only the key registered on the GitHub account. A new ed25519 key was generated on this PC, added to the account by the user, and fetched by the device after the GitHub username was removed and re-entered in the device's SSH settings (it does not re-fetch on its own).
- **USB network (NCM) does not work with Windows:** the device's gadget exposes `ncm.0` and `ffs.adb`. Windows binds its `UsbNcm` driver and the link comes up on both ends, but no frame passes; the device kernel (4.9.103) logs `Wrong NDP SIGN` for each frame and a `dwc3` warning at enumeration. The temporary `usb0` address was removed again.
- **ADB works:** `AdbEnabled=1`, `adbd` running. With Google platform-tools, `adb forward tcp:8022 tcp:22` carries SSH over the cable (about 3 MB/s, 360 ms per command). It also works with the device powered from the car harness, where the home Wi-Fi is out of range.
- **The USB link drops:** during pulls the device disappeared from USB several times, sometimes with a reboot (uptime of a minute on return), sometimes without. `adb kill-server` / `start-server` was needed once to see it again. Pulls now fetch only files whose sha256 does not yet match the device's and retry; every file in this document was verified that way. Cause not investigated (cable, or the device powering down when parked).
- **Workflow used:** pull `rlog.zst` over USB, run `extract.py` on the parked device, copy the `.pkl` files, delete `/data/tmp/ext`. A 30-minute drive takes about 1.5 minutes to pull and under a minute to extract.

## 3. Drives (observations)

All on Enforce on, Lateral Jerk on. Times UTC.

| Route | Start | Segs | Build | Controller | Factor / friction | Ramp | Delay offset | Published delay |
|---|---|---|---|---|---|---|---|---|
| `000000ba` | 11-16 21:14 | 24 | `d833479` | V0, crashed on engage | 4.2 / 0.07 | 0.28 | 0.15 | — |
| `000000bc` | 11-16 22:57 | 9 | `77cc8c6` | V0 | 4.2 / 0.07 | 0.28 | 0.15 | 0.338–0.339 |
| `000000bd` | 11-16 23:15 | 19 | `77cc8c6` | V0 | 4.2 / 0.07 | 0.28 | 0.12 | 0.309–0.310 |
| `000000be` | 11-16 23:40 | 32 | `77cc8c6` | V0 | 4.2 / 0.07 | 0.35 | 0.12 | 0.312–0.330 |
| `000000bf` | 11-17 00:18 | 9 | `77cc8c6` | V0 | 4.5 / 0.07 | 0.28 | 0.12 | 0.330–0.331 |
| `000000c0` | 11-17 00:36 | 10 | `77cc8c6` | **V1** | 4.5 / 0.07 | 0.28 | 0.135 | 0.346–0.349 |
| `000000c1` | 11-17 11:21 | 33 | `77cc8c6` | V1 | 4.5 / 0.07 | 0.28 | 0.135 | 0.350–0.352 |
| `000000c2` | 11-17 18:32 | 20 | `77cc8c6` | V1 | 4.5 / 0.07 | 0.24 | 0.135 | 0.352–0.357 |
| `000000c3` | 11-17 19:03 | 22 | `77cc8c6` | V1 | 4.5 / 0.07 | 0.24 | 0.135 | 0.359–0.369 |

`000000bb` is a 17 s stationary dashcam-mode route. `controlsMismatch` and `canBusMissing` appear in the last second of `bc` and `bd` only (ignition off); not investigated. `espDisabled` once each in `bf`, `c2`, `c3`.

## 4. V0 results: offset, ramp, factor (observations)

**Above 60 mph, lat active, hands off** (`compare.py` method; lane and wheel are band amplitudes):

| Route | Setup | s | RMS error | Lane 0.2–0.7 Hz | Wheel 0.2–0.7 Hz | Wheel 0.7–4 Hz |
|---|---|---|---|---|---|---|
| `b5` | 4.5 / 0.05, stock ramp, +0.12 | 644 | 0.071 | 0.0323 | 0.155 | 0.110 |
| `bc` | 4.2 / 0.07, ramp 0.28, +0.15 | 158 | 0.081 | 0.0286 | 0.145 | 0.176 |
| `bd` | 4.2 / 0.07, ramp 0.28, +0.12 | 166 | 0.061 | 0.0355 | 0.184 | 0.099 |
| `be` | 4.2 / 0.07, ramp 0.35, +0.12 | 835 | 0.079 | 0.0412 | 0.229 | 0.105 |
| `bf` | 4.5 / 0.07, ramp 0.28, +0.12 | 102 | 0.059 | 0.0281 | 0.164 | 0.107 |

- **Offset 0.15 s against 0.12 s (`bc` → `bd`):** wheel motion above 0.7 Hz fell by about 45 % with 0.12 s; in `bc` the wheel peak sat at 1.07 Hz and the 1–2 Hz request was about 1.8 times that of `b5` (straight windows, 72 s). 0.15 s is too much on V0.
- **Ramp 0.35 (`be`, straight windows 82 s):** lane RMS 3.56 / 1.77 / 1.36 / 1.17 cm in the 0.1–0.2 / 0.2–0.3 / 0.3–0.45 / 0.45–0.7 Hz bands, against 1.41 / 0.93 / 0.76 / 0.77 on `b5`. More slow wander; curves unchanged. Reverted to 0.28.
- **Factor 4.2 against 4.5:** curve shortfall / peak stayed at 0.16–0.21 for 4.8, 4.5 and 4.2, so the lower factor did not improve turn-in. On `bc` the act/request gain at 0.2–0.45 Hz was 1.25–1.29 against about 1.03 on `b5`.
- **`bf`** has the lowest error and lane motion of the V0 set but only 102 s above 60 mph, two straight windows and no qualifying curve.

## 5. Neural-network lateral control: assessed offline, not enabled

- **Source fact:** the only model matched for `GENESIS_G70_2024` is `GENESIS_G70.json` (trained 2023-08-05), by fuzzy name match. `interfaces.py` and the UI switch off both toggles when `NeuralNetworkLateralControl` is on together with `EnforceTorqueControl` or `LateralJerkTorqueController`, and the NNLC path uses the stock friction threshold.
- **Offline result (model evaluated on the device):** for steady lateral acceleration at 60 mph the model asks for torque 0.094 / 0.177 / 0.309 at 0.5 / 1.0 / 2.0 m/s². With the learned plant factor of about 3.55 this car needs 0.141 / 0.282 / 0.563, so the model supplies 67 % / 63 % / 55 %.
- **Decision (user):** not enabled.

## 6. V1 controller (`TorqueControlTune` 1.0) with the jerk-aware extension

- **Source facts (`77cc8c6`):** V0 uses setpoint = future request (`lat_delay × jerk + expected`), PID KP 1.0 / KI 0.3. V1 uses setpoint = the request `lat_delay` ago, KP 0.8 / KI 0.15. In both, the extension recomputes error and feedforward in torque space and runs the host's PID a second time per cycle. V1 logs the delayed setpoint as `desiredLateralAccel`, so tracking error, gain and lag from the logged setpoint are **not comparable** between V0 and V1; `compare_req.py` uses `desiredCurvature × v²` for both (on V0 this equals the logged setpoint).
- **Offline result:** V1 with the extension and the car's settings ran 14 simulated seconds on the device without error. In a crude closed loop (gain 3.55, 0.2 s delay, no friction) V0 overshot a 1.5 m/s² ramp by about 30 % and V1 did not overshoot but lagged the ramp.
- **Observations, above 60 mph (request-based):**

| Route | Setup | s | RMS (req − act) | Lane 0.2–0.7 Hz | Wheel 0.2–0.7 Hz | Wheel 0.7–4 Hz |
|---|---|---|---|---|---|---|
| `bd` | V0 4.2, ramp 0.28 | 166 | 0.061 | 0.0355 | 0.184 | 0.099 |
| `bf` | V0 4.5, ramp 0.28 | 102 | 0.059 | 0.0281 | 0.164 | 0.107 |
| `c0` | V1 4.5, ramp 0.28 | 170 | 0.083 | 0.0377 | 0.147 | 0.068 |
| `c1` | V1 4.5, ramp 0.28 | 508 | 0.076 | 0.0300 | 0.182 | 0.090 |
| `c2` | V1 4.5, ramp 0.24 | 630 | 0.082 | 0.0305 | 0.156 | 0.074 |
| `c3` | V1 4.5, ramp 0.24 | 589 | 0.091 | 0.0322 | 0.172 | 0.088 |

- **Curves (request-based, medians):** V1 ramp 0.28: 10 events, peak 1.28, shortfall / peak 0.23, overshoot / peak 0.20, peak torque 0.23. V1 ramp 0.24: 20 events, peak 1.45, 0.21, 0.23, 0.28. V0 sets (`b5`, `bc`, `bd`, `be`; 3–14 events each): shortfall / peak 0.16–0.21, overshoot / peak 0.18–0.27, peak torque 0.32–0.50.
- **Straight windows above 60 mph, lane RMS (cm) by band 0.1–0.2 / 0.2–0.3 / 0.3–0.45 / 0.45–0.7 / 0.7–1.0 Hz:** V1 ramp 0.28 (174 s): 1.46 / 1.20 / 1.05 / 0.85 / 0.46, wheel 0.085 / 0.082 / 0.077 / 0.084 / 0.057°. V1 ramp 0.24 (379 s): 1.77 / 1.14 / 1.02 / 1.04 / 0.57, wheel 0.094 / 0.065 / 0.065 / 0.091 / 0.052°.
- **Reading:** V1 moves the wheel 10–35 % less above 0.7 Hz and uses less peak torque in curves, with later turn-in and higher request-tracking error; overshoot is unchanged. Ramp 0.24 against 0.28 on V1 changes lane motion at 0.2–0.45 Hz by 3–5 % (noise) with 16–21 % less wheel motion there.
- **User report:** V1 "felt better" overall and the turns "felt pretty good", with "a little bit of hunting in the straights" that "over time … seems to get worse". V1 is kept on that basis; factor 4.2 was set briefly on V1 and reverted to 4.5 before any drive.

## 7. Lane motion at 0.2–0.45 Hz does not respond to the torque settings

Across two factors (4.2, 4.5; 4.8 earlier), friction 0.05 and 0.07, ramps 0.2 / 0.24 / 0.28 / 0.35, offsets 0.12 / 0.135 / 0.15 s and both controllers, straight-road lane RMS at 0.2–0.45 Hz stayed between about 0.75 and 1.2 cm per band (ramp 0.35 worse). **Hypothesis:** the hunting is set by the loop between the driving model's lane keeping and the response delay, not by the torque controller's tuning.

## 8. The delay estimate creeps while the offset is set (observation, hypothesis)

| Routes | Offset (s) | lagd's own estimate (s) | Published delay (s) |
|---|---|---|---|
| `b0`, `b1`, `b4` | 0 | 0.174–0.179, flat | same |
| `b5` | 0.12 | 0.174 → 0.188 | 0.294 → 0.307 |
| `bc`, `bd` | 0.15, 0.12 | 0.188 → 0.192 | 0.338, 0.310 |
| `be` | 0.12 | 0.192 → 0.210 | 0.312 → 0.330 |
| `bf`, `c0`, `c1` | 0.12, 0.135 | 0.210 → 0.217 | 0.330 → 0.352 |
| `c2`, `c3` | 0.135 | 0.217 → 0.233 | 0.352 → 0.369 |

- The estimate was flat without the offset and has risen on every drive since, never falling.
- **Hypothesis:** the offset makes the model plan further ahead, lagd then measures a longer request-to-response lag and raises its estimate, which moves the horizon out again.
- The learned torque values did not drift in the same way (factor 3.44–3.61, friction 0.070–0.078).
- Drive-to-drive lane motion does not rise monotonically with the delay. Within the three V1 drives the later half had 17–22 % more lane motion and 25–50 % more wheel motion at 0.2–0.7 Hz, but those halves are short (22–82 s).

## 9. Changes `237edfd` and `466c14c` (2026-11-17, user request)

- **`237edfd`: request smoothing.** `LAT_SMOOTH_SECONDS` in `selfdrive/modeld/modeld.py` (stock 0.0) is read from `/data/g70_lat_smooth`, clamped to [0, 0.3] s. modeld low-passes `desiredCurvature` with it and, as upstream intends for this constant, modeld and controlsd both add it to the steering delay; controlsd imports the value from modeld. The device runs the stock modeld (`ModelManager_ActiveBundle` empty). At 0.2 s the filter passes 0.94 / 0.80 / 0.63 of the request at 0.3 / 0.6 / 1.0 Hz, and the added look-ahead returns more phase than the filter costs.
- **`466c14c`: fixed published delay.** When `/data/g70_lat_delay_fixed` exists, lagd publishes that value (clamped to [0.1, 0.5] s) as `lateralDelay` and ignores the offset. The learner keeps running; `lateralDelayEstimate` and the cached `LiveDelay` stay raw. **Source fact:** `LagdToggle` off does not achieve this, because the stock modeld plans with the published value either way.
- **Checked:** files compile; reader edge cases; on the device each new value was loaded by the daemons' own modules before the reboot; after the reboot the tree is clean and the only tracebacks are certificate-date errors from athenad / sunnylinkd. Not driven; no tests run.
- With 0.33 s fixed and 0.2 s smoothing the model plans about 0.53 s ahead (plus frame and action delay).

## 10. Device record (2026-11-16 22:33Z to 2026-11-17 20:42Z, user-authorized)

| Time (UTC) | Change |
|---|---|
| 11-16 22:33 | install `77cc8c6` (bundle, sha256-checked, fast-forward), `g70-fingerprint-prev` → `d833479`, reboot |
| 11-16, before `bd` | delay offset 0.15 → 0.12 |
| 11-16 23:38 | friction ramp 0.28 → 0.35 |
| 11-17, before `bf` | ramp → 0.28, override factor 4.2 → 4.5 |
| 11-17, before `c0` | `TorqueControlTune` 0.0 → 1.0, delay offset 0.12 → 0.135 |
| 11-17, after `c1` | factor 4.5 → 4.2 (not driven), then back to 4.5 with ramp 0.28 → 0.24 |
| 11-17 ~20:30 | install `237edfd`, `g70-fingerprint-prev` → `77cc8c6`, `/data/g70_lat_smooth` = 0.2, reboot |
| 11-17 20:42 | install `466c14c`, `g70-fingerprint-prev` → `237edfd`, `/data/g70_lat_delay_fixed` = 0.33, reboot |

`/data/tmp/ext` was created and removed for each extraction. No other writes.

## 11. Open

- Drive the fixed delay and the smoothing; both changed at once, so a second drive with one of the two files removed is needed to separate them.
- Whether lagd's estimate keeps rising with the published delay fixed (it is still logged as `lateralDelayEstimate`).
- Plain V1 with Lateral Jerk off has never been driven.
- `bf` (V0, 4.5 / 0.07, ramp 0.28) was never given a long drive.
- Cause of the USB dropouts; `controlsMismatch` / `canBusMissing` at ignition off in `bc`, `bd`.
- Camera video for `ba`–`c3` was not pulled. The cluster speed-limit question from 11-16 §11 is untouched.
