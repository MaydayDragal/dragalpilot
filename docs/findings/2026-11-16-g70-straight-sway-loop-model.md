# G70 2024: six drives on factor 4.8, loop model of the straight-road sway, steering-delay offset (2026-11-16)

**Status:** `g70-fingerprint` @ `dbc2916` on the device (installed 2026-11-16 12:17Z). Device settings: Lateral Jerk on, Enforce on, override **4.5 / 0.05**, delay offset **0.12 s**. **Not yet driven.**

Follows [2026-11-13-g70-drives-daw-lkas12.md](2026-11-13-g70-drives-daw-lkas12.md). Scripts: [tools/drive-eval](../../tools/drive-eval/README.md). Device identifiers and GPS are kept out of this repo.

Evidence labels: **source fact**, **observation** (rlog), **model result**, **hypothesis**.

## 1. Recordings (2026-11-13 20:34Z to 2026-11-16 11:27Z)

`000000ad`, `ae`, `af`, `b0`, `b1`, `b4`: engaged driving on `4525e88`, Jerk 1, Enforce 1, override 4.8 / 0.07. `b2`: no lat-active time. `b3`: parked. No bookmarks, no `steerFaultTemporary`/`Permanent`.

## 2. Factor 4.8 against earlier setups (observations)

**Straight, > 60 mph** (method as on 11-13 §7):

| Config | Straight s | Lane RMS 0.2–0.3 / 0.3–0.45 Hz (cm) | gain 0.3–0.45 / 0.45–0.7 / 0.7–1.0 Hz | Lag 0.2–0.3 / 0.3–0.45 Hz | Wheel 0.45–0.7 Hz (°) |
|---|---|---|---|---|---|
| 5.0 / 0.04, standard | 307 | 1.62 / 1.48 | 1.09 / 0.92 / 0.53 | 59° / 78° | 0.067 |
| 4.5 / 0.07, jerk | 82 | 0.85 / 0.73 | 1.23 / 1.18 / 0.85 | 50° / 62° | 0.094 |
| **4.8 / 0.07, jerk** | **532** | **1.17 / 1.03** | **1.20 / 1.35 / 1.26** | **32° / 61°** | **0.129** |

- Straight, 35–60 mph, 4.8 jerk (82 s, first usable data in this band): lane RMS 1.65 / 1.48 cm, gain 1.29 / 1.20, lag 43° / 51°.
- Tracking > 60 mph: RMS error 0.061–0.067 m/s² per route (4.5 drive 0.051; first setup 0.071–0.088).
- Curve events per route: shortfall / peak 0.13–0.18 (4.5: 0.13), overshoot 0.21–0.32 m/s².
- The turn bookmarked on 11-12 was passed at 63 mph (`af`: peak request 1.07, shortfall 0.17, lane swing 0.24 m) and 34 mph (`ad`); on 11-12 it was 76 mph with a 0.61 m swing. Not comparable speeds.

Reading: with a 532 s sample the jerk controller holds about 30 % less lane motion at 0.2–0.45 Hz than the first setup, with about twice the wheel motion at 0.45–0.7 Hz. Going from 4.5 to 4.8 did not reduce the over-delivery at 0.45–1 Hz.

## 3. Controller law (source facts, `4525e88`)

- `latcontrol_torque.py`: setpoint = request delayed by `lat_delay` (lagd, about 0.19 s); error = setpoint − measurement; `ff` = undelayed request − roll + `get_friction(error + 0.3 · filtered jerk)`. `KP` 0.8 at 30 m/s, `KI` 0.15, `FRICTION_THRESHOLD` 0.2.
- `get_friction`: linear from −friction to +friction over ±0.2 m/s² of its input. In torque terms the slope is `friction / 0.2` per m/s²: **0.35 at friction 0.07**, against 0.8 / factor = 0.17 for the P term. On a straight (errors well inside ±0.2) the friction setting is the largest feedback gain.
- Jerk-aware extension (`latcontrol_torque_jerk_aware.py`, `…_ext_base.py`): same PID object, error in torque space; friction input = `0.7·(undelayed request − measurement) + 0.4·look-ahead jerk`; the 0.7 becomes 1.0 permanently the first time the look-ahead jerk is zero; the look-ahead jerk is zero unless the planned jerk keeps its sign for 1.4–2 s.
- The override factor changes the feedforward and P by its ratio but does not change the friction slope.

## 4. Loop model (model result)

`tools/drive-eval/loopfit.py`, straight windows > 60 mph, all routes `a3`…`b4` (114 windows, mean 72 mph).

**Plant, torque → lateral accel (request as instrument):**

| Hz | 0.1–0.2 | 0.2–0.3 | 0.3–0.45 | 0.45–0.7 | 0.7–1.0 | 1.0–1.5 |
|---|---|---|---|---|---|---|
| gain (m/s² per unit torque) | 3.36 | 2.16 | 1.65 | 1.59 | 1.50 | 1.05 |
| phase | −42° | −79° | −105° | −114° | −110° | −102° |

**Fit** to the measured setpoint → actual response of five configurations: best with no jerk lead in jerk mode, friction factor 1.0, standard-mode jerk gain 0.1, and **0.15 s of extra delay** (rms log error 0.24; source constants unfitted: 0.97). Lag then matches within about 10° (4.8 jerk: 15/32/61/70/73° measured, 15/38/59/66/66° predicted). Gain is under-predicted for jerk mode at 0.45–1 Hz (1.35/1.26 measured, 1.11/0.96 predicted).

**Candidates (jerk mode), predicted lag at 0.2–0.3 / 0.3–0.45 / 0.45–0.7 Hz and torque per unit request at 0.45–0.7 / 0.7–1.0 Hz:**

| Setting | Lag | Torque activity |
|---|---|---|
| 4.8 / 0.07 | 38° / 59° / 66° | 0.70 / 0.64 |
| 4.5 / 0.07 | 37° / 59° / 66° | 0.72 / 0.66 |
| 4.5 / 0.05 | 43° / 67° / 76° | 0.65 / 0.60 |
| 4.5 / 0.04 | 46° / 72° / 82° | 0.62 / 0.56 |
| 4.5 / 0.04 + derivative feedforward 0.2 s | 40° / 63° / 69° | 0.67 / 0.65 |
| 4.5 / 0.04 + derivative feedforward 0.4 s | 34° / 54° / 58° | 0.75 / 0.79 |

- Lower friction: less torque activity, more lag. Derivative feedforward: less lag, more torque activity. **No torque-parameter setting lowers both** in this model.
- The fitted extra delay and the measured 60–70° at 0.3–0.7 Hz say the response is later than the 0.18–0.19 s lagd estimates.

**Hypothesis:** shifting the plan time at the model gives phase lead without adding gain, so it can pay for a lower friction setting. A 0.12 s shift is worth 9° at 0.2 Hz, 16° at 0.375 Hz, 25° at 0.575 Hz if the outer loop sees it in full.

**Source facts on the delay path:** the device runs the default model (`ModelManager_ActiveBundle` empty), i.e. `selfdrive/modeld/modeld.py`, which uses `sm['lateralDelay'].lateralDelay` directly; `LagdToggle` / `LagdToggleDelay` only reach `modeld_v2`. `LAT_SMOOTH_SECONDS` shifts the plan time and smooths by the same amount, so it is not a lead.

## 5. Change `dbc2916`: steering-delay offset

- `sunnypilot/livedelay/helpers.py`: `read_lat_delay_offset()` reads `/data/g70_lat_delay_offset` (one number, seconds, clamped 0…0.25; missing or unreadable → 0).
- `selfdrive/locationd/lagd.py`: the offset is added to the published `lateralDelay.lateralDelay`. The `LiveDelay` cache keeps the learner's own estimate and `lateralDelayEstimate` is unchanged. Consumers: modeld (plan time), controlsd (setpoint delay, jerk time), torqued (point alignment).
- No file → stock behaviour. Read once when lagd starts (each drive).
- Python only; panda firmware unchanged (`f99ab974…`).
- Checked: both files parse; reader edge cases; `py_compile` on the device. **Not driven; no tests run.**

Side effect to watch: torqued aligns its points with the published delay, so its raw estimates may shift.

## 6. Device record (2026-11-16, user-authorized)

- 11:58Z read-only: offroad, `4525e88`, clean. Extraction of 157 segments and LKAS12 scans.
- 12:17Z: bundle `4525e88..dbc2916` (sha256 `def84536…`, verified on the device); guards passed; `g70-fingerprint-prev` → `4525e88`; fast-forward; wrote `/data/g70_lat_delay_offset` = `0.12`; override factor 4.8 → **4.5**, friction 0.07 → **0.05**; reboot.
- After the restart: `dbc2916`, clean, offroad, no alerts. lagd runs only onroad, so the applied offset first shows in the next drive's `lateralDelay` (expected about 0.30 s).

**Why these three together:** 4.5 because 4.8 gave nothing over it and was slightly weaker in curves; friction 0.05 to cut the small-error gain (slope 0.35 → 0.25) and with it the wheel motion; the 0.12 s offset to pay back the lag the lower friction costs. To isolate: delete the file (offset), or set friction back to 0.07.

## 7. LKAS12 / other observations in these drives

- Re-send worked on every route (about 89,000 frames, 0–2 mismatches per route, except below). The camera's status never went under 3: **the warning block is still untested.**
- `b4`, 635.0–640.3 s (car started during the recording): the camera sent `0120ffff080dff00`, `0100ffff080dff00`, `01004141080d4b00`, i.e. bit 43 set with status 5. The filter treats any of bits 43–47 as a warning, so it cleared bit 43 for 54 frames. Bit 44 is the one seen with "take a break". **The filter should be narrowed to status 6 / bit 44** (not done yet).
- `espDisabled` (`TCS11.TCS_PAS == 1`) in `ad`, `ae`, `af`, `b0`, `b4`: short groups at standstill after starting and at 69–76 mph shortly after; in `ae` one fell while lat active → "TAKE CONTROL IMMEDIATELY / Electronic Stability Control Disabled". Cause not established.
- `faultTemp` panda status in six of eight recordings.

## 8. Open

- Drive on the new settings: ≥ 10 min of straight highway > 60 mph and some curves; compare lane motion, lag, wheel motion, curve shortfall; confirm the logged delay.
- If turn-in comes too early or the car cuts curves, lower the offset.
- Narrow the LKAS12 filter. Speed-limit sign on the cluster still unreported.
- `espDisabled` cause; `faultTemp`; opendbc tests never run on this branch.
