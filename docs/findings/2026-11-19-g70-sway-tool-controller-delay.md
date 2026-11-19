# G70 2024: sway tool, controller delay 0.33 s and 0.10 s, hands-on message traced, SCC11 filter exercised

Covers 2026-11-18 19:45Z to 2026-11-19 02:30Z. Drives `000000ca`–`000000cc` (controller delay 0.33 s) and `000000cd`–`000000d0` (0.10 s), all on `g70-fingerprint` @ `ee06954` with the V1 torque controller, stock gains, Lateral Jerk on, Enforce on, override 4.5 / 0.07, friction ramp 0.24, published delay fixed at 0.33 s and request smoothing `0.2 20 25`. Device identifiers and GPS are kept out of this repo.

Statements are marked as observations (measured from logs), inferences, or plans.

## 1. Summary

- **Observation:** on this car the V1 controller ping-pongs and the V0 controller wobbles, and the controller's delay setting moves a setup between the two. V1 with a 0.10 s controller delay has the ping-pong of V0 (1.0 swings per minute above 60 mph against 5.0 at 0.33 s) and also its wobble (15.2 fast swings per minute against 5.7).
- **Observation:** the 0.33 s controller delay made no measurable difference against the stock controller delay on the same roads. The first reading of `ca`–`cc` (more lane motion at 0.45–0.7 Hz, larger curve swing) compared different roads and is withdrawn.
- **Inference:** ping-pong on V1 comes from the car following the request 0.66–0.78 s late in the 0.2–0.45 Hz band; wobble on V0 and on V1 at 0.10 s comes from the car answering 0.7–1 Hz requests with 1.0–1.2 times the requested lateral acceleration.
- **Plan / state:** keep 0.10 s and lower the V1 feedback gain to 0.6 (`/data/g70_v1_gains` = `0.6 0.15`, set 2026-11-19 about 02:15Z, not yet driven).
- **Observation:** the cluster's "hands not detected" message is openpilot's own first-stage driver-monitoring alert, sent in LKAS11 `CF_Lkas_SysWarning` = 4.
- **Observation:** the SCC11 standstill-prompt filter met its first cruise-held stop: 82 s of camera `SCCInfoDisplay` 4, every frame sent to the car as 0.

## 2. The sway tool (`tools/drive-eval/sway.py`)

Runs on the PC on the extracts and writes a report page (`sway_report.html` is its template) with graphs and a map. The report holds GPS positions and is written next to the extracts, outside this repo.

Stretches used: steering active, hands off, no blinker, both lane lines seen, 12 s or longer.

| Part | Method |
|---|---|
| Swings | Lane-centre offset band-passed 0.08–1.5 Hz and cut at turning points (reversals under 3 cm ignored). Size is peak to peak, period is twice the duration. Wander: period over 5 s. Ping-pong: 2–5 s. Fast: under 2 s. Counted on straights (5 s mean of the absolute request under 0.35 m/s²) when 8 cm or larger. A train is four or more consecutive ping-pong swings. |
| Wobble | The same counting on lateral acceleration band-passed 0.5–3 Hz: swings faster than 1.6 s and 0.15 m/s² or larger. Wheel reversals of 0.15° or more per minute. |
| Who moves | The car's own sideways movement is the lateral acceleration divided by ω² in each band; "car share" is the lane-offset power it explains. |
| Loop | Per band from 20.48 s straight windows: plan stiffness (request per metre of offset), following gain and delay (request to lateral acceleration), open-loop gain and phase margin, and amplification 1 / \|1 + L\|. Estimated in closed loop from normal driving: a guide, with coherence columns. |
| Same road | Road cells of 0.001° with a heading octant. Each earlier setup is compared with the reference setup only on cells both drove above 35 mph. |
| Map | Each ping-pong swing and wobble at its position; repeat spots are cells where at least three drives, and 60 % of the drives that passed, swing on a straight. |

The 8 cm, 15 cm, 0.15 m/s² and 3 cm thresholds are choices, not derived values.

## 3. Results above 60 mph (observations)

| Setup | Straights (min) | Ping-pong /min | Wobble /min | Follow delay 0.2–0.45 Hz (s) | Follow gain 0.7–1 Hz | Largest amplification 0.2–0.45 Hz | Wheel reversals /min |
|---|---|---|---|---|---|---|---|
| V0 4.5 / 0.05 (`b5`) | 6.8 | 1.2 | 14.6 | 0.30 | 1.01 | 1.24 | 44 |
| V0 4.2 / 0.07 (`bc`–`be`) | 11.2 | 3.6 | 11.5 | 0.48 | 1.13 | 1.18 | 36 |
| V1 no smoothing (`c0`–`c3`) | 20.3 | 3.8 | 6.3 | 0.71 | 0.63 | 1.76 | 33 |
| V1 smoothing 0.2 all speeds (`c4`) | 6.9 | 3.8 | 0.8 | 0.75 | 0.47 | 1.87 | 21 |
| V1 filter 0.3 look-ahead 0.2 (`c6`, `c7`) | 9.9 | 3.6 | 1.9 | 0.78 | 0.90 | 1.87 | 30 |
| V0 smoothing 0.2 (`c8`, `c9`) | 11.1 | 2.0 | 20.8 | 0.45 | 1.22 | 1.23 | 52 |
| V1 smoothing, controller delay 0.33 (`ca`–`cc`) | 11.3 | 5.0 | 5.7 | 0.66 | 0.65 | 1.54 | 31 |
| V1 smoothing, controller delay 0.10 (`cd`–`d0`) | 5.8 | 1.0 | 15.2 | 0.53 | 1.20 | 1.81 | 48 |

No trains above 60 mph except 1.2 % of the time on `bc`–`be`. The 35–60 mph band has too little hands-off straight driving on most setups to compare.

### Same road

Against `ca`–`cc` (controller delay 0.33 s), each pair on the road both drove:

| Earlier setup | Shared (min) | Ping-pong /min (it / `ca`–`cc`) | Wobble /min (it / `ca`–`cc`) |
|---|---|---|---|
| V0 4.5 / 0.05 | 10.3 | 1.7 / 4.4 | 14.7 / 5.0 |
| V1 no smoothing | 21.1 | 4.1 / 4.6 | 6.5 / 5.9 |
| V1 smoothing 0.2 all speeds | 9.5 | 3.4 / 3.6 | 2.6 / 3.4 |
| V1 filter 0.3 look-ahead 0.2 | 13.8 | 4.0 / 5.8 | 2.4 / 6.6 |
| V0 smoothing 0.2 | 16.1 | 1.9 / 5.4 | 21.8 / 5.9 |

Against `cd`–`d0` (0.10 s): the 0.33 s drives on 7.6 shared minutes have 5.3 ping-pong swings per minute against 2.7, and 7.2 wobble swings against 15.2.

### Reading

- **Observation:** the published-delay-plus-look-ahead that V1 waits before comparing the car with the request sets the follow delay: 0.75 s at 0.53 s (`c4`), 0.66 s at 0.33 s, 0.53 s at 0.10 s; V0, which does not wait, 0.30–0.48 s.
- **Observation:** follow gain at 0.7–1 Hz rises as that delay falls: 0.47, 0.65, 1.20; V0 1.0–1.2.
- **Inference:** the two faults trade through one setting, so a middle delay would land between them. Lowering the feedback gain at the short delay is the attempt to break the trade. It is not known how much of the 0.7–1 Hz over-response is feedback and how much is feed-forward and friction compensation.
- **Observation:** the map has 14 repeat spots. **Inference:** sway there is from the road or its markings.
- **Caveat:** `cd`–`d0` have 5.8 min of hands-off straights above 60 mph.

## 4. Cluster message "hands not detected" (observation)

Bookmark in `cb` at 320 s, while slowing to a stop.

| Time before the bookmark | Event |
|---|---|
| 4.36 s | openpilot alert "Touch Steering Wheel: No Face Detected" (`driverUnresponsive1`), HUD visual alert `steerRequired` |
| 4.35 s | LKAS11 sent to the car: `CF_Lkas_SysWarning` 0 → 4 |
| 1.70 s | alert cleared, `CF_Lkas_SysWarning` 4 → 0 |

The camera's own LKAS11 and LFAHDA_MFC did not change in that window. `tools/drive-eval/bookmark_context.py` prints these changes for any bookmark. Not changed: the message could be withheld for this first stage only; openpilot's screen would still show it.

## 5. SCC11 (observations)

- `cb`: cruise enabled 228 s, camera `SCCInfoDisplay` 4 for 82 s (4116 frames); all requested frames carry 0 and differ from the camera frame in byte 0 only. Requested / camera 1.0000, echoed / requested 1.0000, counter steps all 1, no gap over 60 ms.
- `ca`: no standstill; re-send identical to the camera on all 54520 frames.
- Whether the cluster stayed quiet and the car pulled away normally is not visible in the logs and has not been confirmed by the driver.

## 6. Device record (user-authorized)

| When (UTC) | Change |
|---|---|
| 2026-11-18 about 22:30 | `/data/g70_lat_ctrl_delay` 0.33 → 0.10 |
| 2026-11-19 about 02:15 | `/data/g70_v1_gains` created: `0.6 0.15` (stock 0.8 / 0.15; replaces the high-speed end of the gain schedule, full from 30 m/s, blending in from 15 m/s) |

Build unchanged (`ee06954`). No tracebacks from controlsd, modeld, lagd, card or pandad on any of the seven drives.

## 7. Open

- Drive with gain 0.6: targets are wobble near 6 per minute with ping-pong staying near 1.
- LKAS11 chime filter still untested (no attention-assist event).
- `controlsMismatch` at the start of `c9`, `interruptRateCan2` / `faultTemp`, and the cluster speed-limit issue are untouched.
- `adb` is not installed permanently on the PC.
