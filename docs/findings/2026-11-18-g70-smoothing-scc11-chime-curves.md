# G70 2024: request smoothing, SCC11 re-send, attention chime, curve position, straights review (2026-11-17 evening to 2026-11-18)

**Status:** `g70-fingerprint` @ `500ba91` on the device (branch `sunnypilot/g70-scc11-filter`). Settings since 2026-11-18 ~02:50Z: **`TorqueControlTune` 0.0 (V0)**, Lateral Jerk on, Enforce on, override 4.5 / 0.07, friction ramp 0.24, published delay fixed at 0.33 s, smoothing `0.2 20 25` (0.2 s filter with equal look-ahead, none below 20 m/s, full from 25 m/s), SCC11 filter file present. **V0 with smoothing is not yet driven.** Also untested in the car: the SCC11 standstill filter (no cruise-held stop yet) and the LKAS11 chime filter (no attention warning yet).

Follows [2026-11-17-g70-crash-fix-v1-delay-creep.md](2026-11-17-g70-crash-fix-v1-delay-creep.md). SCC11 design and stages: [proposal](../proposals/2026-11-17-g70-scc11-info-display-filter.md). Scripts: [tools/drive-eval](../../tools/drive-eval/README.md). Device identifiers and GPS are kept out of this repo.

Evidence labels: **source fact**, **observation** (rlog), **offline result**, **hypothesis**, **user report**.

## 1. Drives (observations)

All V1 (`TorqueControlTune` 1.0), Enforce on, Lateral Jerk on, override 4.5 / 0.07, friction ramp 0.24, published delay fixed at 0.330 s. Times UTC.

| Route | Start | Segs | Build | Smoothing file | SCC11 |
|---|---|---|---|---|---|
| `000000c4` | 11-17 21:21 | 25 | `466c14c` | `0.2` (all speeds) | camera's copy forwarded (old firmware) |
| `000000c5` | 11-17 23:35 | 15 | `5aeff4e` | `0.2 11 20` | re-sent, pass-through |
| `000000c6` | 11-18 01:39 | 14 | `513f72b` | `0.3 20 25 0.2` | re-sent, filter file present |
| `000000c7` | 11-18 01:53 | 13 | `513f72b` | `0.3 20 25 0.2` | re-sent, filter file present |

lagd's own estimate with the published delay fixed: 0.231–0.233 s (`c4`), 0.232 → 0.236 (`c5`), 0.236 → 0.247 (`c6`, `c7`). It still rises, more slowly than with the offset.

## 2. Request smoothing

**Source facts.** `237edfd`: `LAT_SMOOTH_SECONDS` read from `/data/g70_lat_smooth`; modeld low-passes `desiredCurvature` and modeld and controlsd add the same time to the steering delay. `df21ce2`: `seconds v_lo v_hi` (m/s) ramps the smoothing with speed. `513f72b`: a fourth number sets the added look-ahead separately from the filter time. The stock modeld is in use and builds the request from the plan (`get_curvature_from_plan`); `action_t` is also a model input.

**Drive `c4`, constant 0.2 s** (request-based numbers, `compare_req.py`): above 60 mph (584 s) RMS error 0.070, lane motion 0.2–0.7 Hz 0.0237, wheel 0.125 / 0.046 (0.2–0.7 / 0.7–4 Hz), against 0.030–0.038, 0.147–0.182 and 0.068–0.090 on `c0`–`c3`. By speed, wheel rate RMS (°/s, lat active, hands off): 13.3 at 1–10 mph (38 s), 7.9 at 10–25, 8.6 at 25–45, 3.5 at 45–60, 3.2 above 60; `c1` / `c3` without smoothing: 3.3–3.7 in every band. **User: busier at low speed, much better on the highway.**

**Drive `c5`, ramp 25–45 mph:** no hands-off data below 25 mph; 25–45 mph wheel rate 5.5; above 60 mph wheel 0.7–4 Hz 0.063.

**Open-loop comparison of methods** (`plan_dump.py`, `smooth_methods.py`; route `c1`, 513 s hands-off above 60 mph, 11 straight windows of 25.6 s). The request rebuilt from the logged plan matches the logged action to 0.0003 m/s² RMS (request RMS 0.473). Relative to no smoothing:

| Method | Frame-to-frame change | Request 0.7–4 Hz | Gain 0.3–0.45 / 0.45–0.7 Hz | Phase 0.3–0.45 / 0.45–0.7 Hz |
|---|---|---|---|---|
| filter 0.2 s + look-ahead 0.2 s (stock pairing) | −51 % | −21 % | 1.10 / 1.15 | +1° / −4° |
| filter 0.3 s + look-ahead 0.3 s | −57 % | −32 % | 1.09 / 1.11 | −1° / −8° |
| filter 0.2 s + look-ahead 0.3 s | −46 % | −12 % | 1.21 / 1.31 | +9° / +3° |
| filter 0.2 s, no extra look-ahead | −62 % | −42 % | 0.90 / 0.83 | −22° / −29° |
| plan average ±0.2 s, no filter | −2 % | −3 % | 1.00 / 0.99 | 0° |
| two-stage 2 × 0.1 s + look-ahead 0.2 s | −48 % | −12 % | 1.16 / 1.25 | +2° / −3° |
| filter 0.3 s + look-ahead 0.2 s | −61 % | −39 % | 0.99 / 0.97 | −9° / −15° |
| no filter, look-ahead +0.1 s | +12 % | +20 % | 1.10 / 1.20 | +14° / +16° |

Look-ahead by itself raises the request at 0.3–0.7 Hz; this fits the busier wheel seen with the 0.15 s delay offset on V0 (11-17 findings §4). Averaging along the plan does nothing because the jitter is between frames, not within a plan.

**Drives `c6`, `c7`, filter 0.3 s + look-ahead 0.2 s above 56 mph** (straight windows above 60 mph, 307 s; `c4` with 0.2 / 0.2 in brackets, 195 s): lane RMS 1.59 / 1.14 / 1.36 / 0.71 / 0.43 cm at 0.1–0.2 / 0.2–0.3 / 0.3–0.45 / 0.45–0.7 / 0.7–1.0 Hz (2.26 / 1.20 / 1.12 / 0.80 / 0.47); wheel 0.079 / 0.073 / 0.109 / 0.069 / 0.033° (0.060 / 0.058 / 0.064 / 0.051 / 0.024); wheel peak at 0.39 Hz. The open-loop comparison suggested this pairing would stop enlarging the request at the hunting frequencies; in the car the 0.3–0.45 Hz band got worse. **Reading:** a later request costs more there than a 10–15 % larger one. Smoothing set back to `0.2 20 25` (user request).

## 3. SCC11 re-send (stage 2 of the proposal: passed) and filter (stage 3: not yet exercised)

- **Firmware (offline result):** `tools/panda-fw/build_fw.sh` reproduces the shipped `panda_h7.bin.signed` (`f99ab974…`) byte for byte from `df21ce2`. With `{0x420, 0, 8, .check_relay = true}`: `8213b0c4…`, signature `1a059f84405a5733`, +16 bytes, only `HYUNDAI_CAMERA_SCC_TX_MSGS` changed size (5 → 6 entries). Flashed at the boot after installing `5aeff4e` ("Done flashing").
- **`c5` (pass-through), `c6`, `c7` (filter file present), `scc11_resend_check.py`:** every camera SCC11 frame re-sent once (42,223 / 41,547 / 38,379), payload identical, counter step 1 throughout on the request and on the bus-0 echo, camera-to-request delay median 4.3–4.4 ms, maximum 8.2–14.9 ms, no gap above 60 ms. One 50 Hz SCC11 stream on bus 0 (the echo count equals the request count minus the six frames rejected in the 2 s before the panda enters the Hyundai mode, which the steering messages also show at every start). No `relayMalfunction`, no cruise events; `safetyRxInvalid` 0.
- **Other panda observations:** `interruptRateCan2` and `faultTemp` are set for whole drives, also on `c4` with the previous firmware. In `c5` two LKAS11 frames were rejected at 673 s, at the instant lat control switched off.
- **`SCCInfoDisplay`:** `c5` had one 26 s period of 4 (pass-through, prompt shown, user bookmark 2.7 s after it began). `c6` and `c7` had none, so the filter has not been exercised.
- `c7` start: two caught `isotp` assertions from the firmware query; fingerprint `GENESIS_G70_2024`, not fuzzy.

## 4. Attention warning: text filter confirmed, chime traced to LKAS11

- **User report (`c6`, bookmark 271.4 s):** the attention-assist sound played, no message on the cluster.
- **Observation:** camera LKAS12 (`0x53E`, bus 2) status 6 with bit 44 from 266.7 to 270.7 s. The LKAS12 re-sent on bus 0 stayed at level 1 with no warning bits. This is the first Driver Attention Warning since `4525e88`, and it confirms the text filter in the car.
- **Observation:** the camera's LKAS11 (`0x340`, bus 2) had byte 1 bit 7 set from 266.6 to 270.6 s; openpilot's LKAS11 on bus 0 (sendcan and echo) carried the same bit for the same 4 s. Bit scan of the 8 s before the bookmark: on buses 0 and 2 the only other changes are the LKAS12 bits and momentary flickers on `0x475` and `0x366`.
- **Source fact:** the bit is `CF_Lkas_FcwBasReq` (15|1, receivers ABS, ESC in `hyundai_can.dbc`), and `create_lkas11` copies it from the camera's message. The 11-13 note that the camera's `0x340` byte 1 bit 7 was "already blocked by the panda" missed that copy.
- **Observation (`lkas11_daw_scan.py`, routes `c1`, `c4`–`c7`, 100 segments):** the camera set the bit on 800 frames, 400 in `c4` and 400 in `c6`; 790 with the LKAS12 warning active and 10 in the 0.1 s before it. `CF_Lkas_SysWarning` reads 15 on 358,726 of 587,105 frames (61 %), so it does not mark the warning.
- **Change `500ba91`** (installed 02:37Z): `lkas11_daw_filter` clears the bit while the camera's LKAS12 shows the warning, latches until the camera drops the bit, and holds a newly set bit for 0.2 s (20 frames) because LKAS12 is a 10 Hz message. A bit set for longer with no warning passes unchanged, since the DBC name suggests another use. G70 2024 only, no panda change. Offline: 0 frames passed for the logged timing; 380 of 400 passed when no warning accompanies the bit.
- **Hypothesis:** this bit is what sounds the chime. Not yet tested.

## 5. Curves: lane position and delivery (observations, `curve_position.py`)

Sustained curves: |request| > 0.8 m/s² for 2.5 s or more, lat active, hands off, both lane lines seen, above 35 mph. Signs checked on `c1`: lane-line y is positive to the right, and `desiredCurvature` is positive for a right curve.

| Setup | n | Inside of lane centre at entry (1 s before → 1 s after), m | Mid-curve, m | Exit (last 1 s → 1 s after), m | Swing, median, m | Delivered / requested mid-curve |
|---|---|---|---|---|---|---|
| V0, 4.5 / 0.05, delay ~0.30 (`b5`) | 10 | 0.22 → 0.36 | 0.21 | 0.18 → 0.10 | 0.42 | 1.00 |
| V0, 4.2, delay 0.31–0.34 (`bc`, `bd`, `be`) | 13 | 0.20 → 0.41 | 0.22 | 0.22 → 0.05 | 0.58 | 1.01 |
| V1, no smoothing, delay 0.35–0.37 (`c0`–`c3`) | 23 | 0.29 → 0.33 | 0.20 | 0.24 → 0.14 | 0.45 | 0.99 |
| V1, smoothing, delay 0.33 fixed (`c4`–`c7`) | 28 | 0.18 → 0.21 | 0.11 | 0.14 → 0.13 | 0.26 | 0.98 |

- The car is on the inside of the lane centre through curves on every setup, least on the last one, which also has the smallest swing. On straights it sits 0.09–0.16 m left of centre.
- Mid-curve the car delivers 97–101 % of the requested lateral acceleration on every setup (in longer stretches, 2 s+: 0.97–1.00), with the feedforward term about equal to the whole output and the integral within ±0.12 of it. The "shortfall" and "overshoot" of `compare.py` are entry and exit timing, not a lack of steady-state torque. **The 11-17/18 suggestion that the 4.5 factor leaves curves 20 % short was wrong.**
- torqued's own values on these drives: factor 3.46–3.62, friction 0.072–0.078.
- **User report:** on V1 "the turns felt pretty good".

## 6. Straights: review of all setups with 150 s or more (observations)

Straight windows above 60 mph, lane RMS in cm:

| Setup | 0.1–0.2 Hz | 0.2–0.3 Hz | 0.3–0.45 Hz | 0.45–0.7 Hz |
|---|---|---|---|---|
| V0, 4.8 / 0.07 (`b0`, `b1`, `b4`) | 1.78 | 1.06 | 0.79 | 0.90 |
| V0, 4.5 / 0.05, +0.12 s (`b5`) | 1.41 | 0.93 | 0.76 | 0.77 |
| V1, ramp 0.28, +0.135 s (`c0`, `c1`) | 1.46 | 1.20 | 1.05 | 0.85 |
| V1, ramp 0.24, +0.135 s (`c2`, `c3`) | 1.77 | 1.14 | 1.02 | 1.04 |
| V1, fixed 0.33 s, smoothing 0.2 / 0.2 (`c4`) | 2.26 | 1.20 | 1.12 | 0.80 |
| V1, fixed 0.33 s, smoothing 0.3 / 0.2 (`c6`, `c7`) | 1.59 | 1.14 | 1.36 | 0.71 |

- V1 has about 30 % more lane motion at 0.2–0.45 Hz than V0. V1 has lower feedback gains (KP 0.8 / KI 0.15 against 1.0 / 0.3) and compares the measurement with the request one delay ago.
- The largest band on every setup is 0.1–0.2 Hz, with the lane-offset peak at 0.15 Hz each time. **Hypothesis:** that is the natural frequency of the model's lane-keeping loop.
- Not moving the 0.2–0.45 Hz band: factor, friction, friction ramp (0.35 raised slow wander), smoothing strength. Worse: a later request (0.3 / 0.2). More look-ahead raises the request there (§2).
- Different roads throughout; a fixed test route would tighten every comparison in this document.

## 7. Next path (plan)

1. **V0 with the current smoothing** (set 2026-11-18, one param): V0 had the lowest 0.2–0.45 Hz lane motion and a busy wheel; smoothing now handles the wheel separately. Watch curve entry, where V0 moved further to the inside, and steering below 45 mph, where there is no smoothing.
2. If straights improve and curves hold, keep it. If curves get worse, return to V1 and raise its feedback gains part-way toward V0's (code change).
3. Leave factor, friction, ramp and the delay value alone unless turn-in feels early or late.
4. Drive one fixed route for comparisons.

## 8. Device record (2026-11-17 21:00Z to 2026-11-18 03:00Z, user-authorized)

| Time (UTC) | Change |
|---|---|
| 11-17 23:10 | install `df21ce2`, `/data/g70_lat_smooth` = `0.2 11 20`, reboot |
| 11-17 23:24 | install `5aeff4e` (SCC11 re-send + panda firmware `8213b0c4…`), reboot, panda flashed |
| 11-18 00:11 | `/data/g70_scc11_filter` created |
| 11-18, before `c6` | smoothing `0.2 20 25` |
| 11-18 01:29 | install `513f72b`, smoothing `0.3 20 25 0.2`, reboot |
| 11-18 02:37 | install `500ba91`, smoothing `0.2 20 25`, reboot; `g70-fingerprint-prev` → `513f72b` |
| 11-18 ~02:50 | `TorqueControlTune` 1.0 → 0.0 |

`/data/tmp/ext` was created and removed for each extraction. Rollback to the previous panda firmware: `df21ce2`.

## 9. Open

- V0 with smoothing; the SCC11 filter at a cruise-held stop (proposal stage 3, including whether the ESC uses `SCCInfoDisplay`); the chime filter at the next attention warning.
- lagd's estimate still rising with the published delay fixed.
- USB dropouts and reboots while parked; `interruptRateCan2`; the cluster speed-limit question from 11-16.
- No tests run for any commit on `sunnypilot/g70-scc11-filter`; `sunnypilot/g70-fingerprint` on GitHub is still `df21ce2`.
