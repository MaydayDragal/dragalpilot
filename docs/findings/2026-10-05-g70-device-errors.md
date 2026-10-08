# G70 2024: device errors during the new drives (soundd/micd, unsupported vehicle, locationd, grasp warning) (2026-10-05, session 8)

The user's partner reported, for the drives of 2026-10-04 and 2026-10-05:
- a soundd error around 06:39;
- after disabling and re-enabling sunnypilot, a "locationd" message and then "unsupported vehicle", cleared by unplugging and replugging the device;
- a locationd error on 10-04 about 2 minutes after starting the car;
- a "driver's grasp not detected" warning just before a bookmark.

The partner also stated that the car's networks were up (he was driving). All of it is analysed here from the rlogs already pulled. No device access was used.

Evidence labels:
- **Confirmed source fact:** file + revision `82f58a9a8c`.
- **Observation:** rlog, with route and time.
- **Hypothesis.**
- **Partner report.**

Times are EDT. They are route GPS start + log offset. initData's wall clock is unsynced (07-28) at a cold boot and is not used.

## Tools (all read-only, `E:\DragalPilot\scratch\wsl\sng\`)

- `s8_diag.py`: timeline per route of process states, selfdrive alerts, onroad events, cloudlog warnings/errors, bookmarks, panda safety/ignition, carParams, initData params, boot (monotonic) time. Outputs in `analysis\g70-sng-20261005\diag\<route>.txt`.
- `s8_crash_dump.py`: full crash tracebacks (log `s8-crashscan-*`).
- `s8_uptime.py`: uptime and `OpenpilotEnabledToggle` at each route start (`diag\route_uptime.txt`).
- `s8_locationd_inputs.py`, `s8_gyro_bias.py`: locationd inputs per second.
- `s8_bus_diff.py`: CAN byte changes inside a time window.
- `hands_warning_scan.py` (session 3, unchanged), run on all new engaged routes (log `s8-hands-scan-*`).

## 1. soundd and micd crash at start-up (the "soundd error")

**Observation.** On routes `03`, `05`, `13`, `16` and `18`:
- `micd` and `soundd` crash 31 s after the route starts, both with `Exception: get_stream failed after retry`. The audio stream couldn't be opened (`soundd.py` L185, `micd.py` L117).
- Each of those routes starts 19–20 s after a cold boot.
- It happened on 5 of the 21 routes on record that start within 26 s of a cold boot. It never happened on a route started later in a boot.

**Source (`82f58a9a8c`):**
- `soundd.get_stream` is `@retry(attempts=10, delay=3)` (`selfdrive/ui/soundd.py` L171; `common/utils.py` L260–275). 30 s of failed attempts, then the process dies.
- The manager does not restart a crashed process while onroad: `PythonProcess.start()` returns early while `self.proc` is set (`system/manager/process.py` L168–178). It is restarted only after the device goes offroad (`ensure_running` L225–241 stops it, the next onroad starts it).
- `selfdrived` raises `processNotRunning`. That blocks engagement (no entry) and **soft-disables an active engagement ("TAKE CONTROL IMMEDIATELY")**.

**What the partner saw (observation):**
- **Route `16`** (cold boot 06:31:41, route 06:31:59):
  - crash at 06:32:30;
  - `processNotRunning` for the whole drive;
  - the engage attempt at 06:39:30 was refused ("Process Not Running: micd, soundd").
- **Route `18`** (after the replug):
  - engaged at 06:40:51;
  - the crash at 06:41:01 forced "TAKE CONTROL IMMEDIATELY", disengaged at 06:41:04;
  - re-engage refused.
- **Route `13`** (10-04 19:06) has the same crash, followed by routes `14` (sunnypilot disabled) and `15` (re-enabled, worked).
- Disabling and re-enabling sunnypilot is a full offroad/onroad cycle, which restarts the two processes. By then the audio device is ready. That is why routes `15` and `1a` worked.

**Assessment:**
- The audio device is intermittently not ready during the first ~50 s after a cold boot. This is in upstream code and the device's audio stack, not in our port. `dragal/custom` changes only the car port, the panda safety and firmware (diff `baseline/dev-20261003..dragal/custom`).
- Upstream sunnypilot `master` has no later change; it still equals the baseline source `a5f44653d7`.
- The baseline's own parked routes `00`–`02` had no crash, but that is 3 boots, too few to compare.
- **Hypothesis, not tested:** audio hardware initialisation timing on this comma 4 (mici). The device's `/data/community/crashes/*.log` and the boot logs (`/data/media/0/realdata/boot/`, not pulled) may show more.

## 2. "Unsupported vehicle" (route `17`, the MOCK fingerprint)

**Observation (route `17`, same boot as `16`):**

| Time | Event |
|---|---|
| 06:39:44 | route `16` ends: the device goes offroad (sunnypilot disabled) |
| 06:39:45 | route `17` starts with `OpenpilotEnabledToggle=0` |
| 06:39:46.8 | `card` starts the VIN/firmware query (panda in `elm327`) |
| 06:39:47.8 | **device goes offroad for 1 s** (`deviceState.started` False, panda `noOutput`), back onroad at 06:39:48.8 (sunnypilot re-enabled, per the partner) |
| 06:39:50.9 | VIN query fails; firmware query gets **1 ECU response** (normally 7, `fw_count` 10) |
| 06:39:52.0 | `car doesn't match any fingerprints` → `MOCK`, dashcam: **"Dashcam mode for unsupported car"**, then "Car Unrecognized" |
| 06:40:03 | rlog ends mid-write (unplug) |
| 06:40:11 | new boot (route `18`, uptime 19.5 s) |

- **Hypothesis, strongly supported:** re-enabling sunnypilot within ~2 s of disabling it put the device through a 1 s offroad/onroad flip while `card` was querying the ECUs. The panda went to `noOutput` (silent) in the middle of the query, the ECU replies were lost, and fingerprinting fell back to CAN-only, which can't identify this car (it fingerprints by firmware). The car's networks were up, as the partner says. **The earlier guess in [2026-10-05-g70-sng-drives.md](2026-10-05-g70-sng-drives.md) ("device started before the car's CAN was up") is wrong and has been corrected there.**
- **Consequence (source fact, in the drives doc):** the `MOCK` route made `torqued`, `paramsd` and `lagd` drop their learned state on the next drive (`card.py` `CarParamsPrevRoute`; restore-key checks in `torqued.py` / `paramsd.py` / `lagd.py`).
- **Route `19`** (06:41:24): toggled off again, then on. `card` never finished fingerprinting in its 63 s, so no carParams were logged. Route `1a` (06:42:35, same boot, uptime 144 s) fingerprinted normally and engaged.

## 3. The "locationd" message

**Observation, 10-04, route `11`** (cold boot, 18:32:41; the next route `12` is a new boot at 18:34:04, so the device was power-cycled):
- from 11.9 s on: **"locationd Temporary Error / openpilot Unavailable"** (`locationdTemporaryError`, no entry) for the rest of the route (51 s);
- `deviceMotion.inputsOK` false from the start of the filter to the end;
- carState, extrinsicsCalibration and cameraOdometry all valid; sensors OK.
- locationd logged "Observation gyroscope ignored due to failed sanity check" at 11.7–11.8 s.
  - Source: `locationd.py` L131–139: the gyro is rejected when its yaw rate minus the filter's bias differs from camera odometry by ≥ 30 × camodo std.
  - Enough rejections mark the inputs invalid (L280–330, recovery ~10 s after the rejections stop).
- **Why it never recovered is not determined.**
  - The filter's gyro-bias state is not logged (`debugFilterState` empty), so the exact check can't be recomputed.
  - Without the bias term, routes `11` and `12` show similar cross-check failure rates, yet route `12` was fine.
  - **Hypothesis:** a bad restored filter state (`LocationFilterInitialState`) or gyro bias at that cold start.
  - The power cycle cleared it.
- **10-05:** no `locationdTemporaryError` in routes `16`–`1a`. The partner's "locationd wasn't up" after re-enabling doesn't appear in the logged alerts. Candidates:
  - route `19`, where `card` never finished and selfdrived never initialised;
  - or a recollection of the 10-04 event.
  - Unresolved; the UI text isn't logged.

## 4. "Driver's grasp not detected" and the bookmark

**Observation (route `1a`):**

| Time | Event |
|---|---|
| 06:42:59 | engaged (panda `hyundai/8`, controls allowed) |
| **06:43:20–06:44:01** | camera `LFAHDA_MFC.LFA_SysWarning` = **5 then 6** for 40.1 s |
| 06:44:03 | steering override (driver touched the wheel) |
| **06:44:07** | **bookmark** ("Bookmark Saved"; `userBookmark`, `bookmarkButton`) |

- **Source fact** (`opendbc/dbc/generator/hyundai/hyundai_can.dbc` L1695): `LFA_SysWarning` 3 = `lfa_error`, 4 = `check_hda`, **5 = `keep_hands_on_wheel_orange`, 6 = `keep_hands_on_wheel_red`**.
- **This was the only 5/6 episode** in all new engaged routes (`10`, `12`, `15`, `18`, `1a`–`1d`). The others are levels 3 or 4. It matches the partner's report.
- Openpilot raised no alert of its own (no `steerRequired`, its LKAS11 `CF_Lkas_SysWarning` 0).
- **The panda was in Hyundai mode, so the camera's 0x485 (with the 5/6) and 0x484 were blocked** (`hyundai.h` L28–31, L311–313). A byte-level diff over all buses showed no flag-like change in any message forwarded from the camera, in what the panda received from the car, or in what openpilot sent (`diag\r1a_bus_flag_diff.txt`).
- **What this changes from session 3:**
  - The 0x484 change was judged effective on routes 8/9 (user: no dashboard warning).
  - But on those routes the camera only reported level 3 (`lfa_error`), never a hands warning. **The fix was never tested against a real hands-off escalation.**
  - Route 6 (before the fix, sunnypilot disabled) had the same 5→6, 40.1 s pattern.
- **Open question.** If the cluster showed "grasp not detected" at 06:43–06:44 (partner report), the logs don't show the path. Candidates (hypotheses):
  1. the camera or another module reaches the cluster on a network the harness doesn't intercept;
  2. a forwarded message carries it in a way the byte diff doesn't flag, e.g. a multi-value field;
  3. the cluster derives it itself, e.g. from the MDPS.
  - Settling this needs the partner's exact message/time, or a driver-camera / cluster recording.

## 5. Custom torque values (user question)

**Not overwritten.**
- The tune is in source on `dragal/custom`:
  - `override.toml` `GENESIS_G70_2024 = [4.0, 2.7, 0.07]` (latAccelFactor, max lat accel, friction);
  - `values.py` steerRatio 14.1.
- carParams on every G70 route, before and after the reset (`10`, `12`, `16`, `18`, `1a`–`1d`), shows latAccelFactor 4.000 and friction 0.070.
- What was lost is only the *learned* layer on top:
  - torqued's live estimate (it had replaced 4.0/0.07 with 3.80→3.69/0.08 while valid);
  - paramsd's steer ratio and angle offset;
  - lagd's delay.
- The controller falls back to the source tune until torqued is valid again.

## Summary of causes

| Report | Cause (label) |
|---|---|
| soundd error, can't engage / "TAKE CONTROL IMMEDIATELY" | audio device not ready → soundd/micd crash after 30 s of retries, not restarted while onroad (observation + source fact); root cause of the audio delay: hypothesis |
| unsupported vehicle | sunnypilot re-enabled ~2 s after disabling → 1 s offroad flip during the firmware query → `MOCK` (observation; mechanism strongly supported) |
| locationd (10-04) | `locationdTemporaryError` from a cold start: gyro rejected vs camera odometry, never recovered (observation); why: not determined |
| locationd (10-05) | not found in the logs |
| grasp warning before the bookmark | camera escalated keep-hands-on-wheel orange→red for 40 s (observation); how it reached the cluster despite the 0x484/0x485 blocks: open |
| torque values overwritten? | no; only the learned layer was reset (source fact + observation) |

## Practical guidance until fixed (for the user to pass on)

- If "Process Not Running: micd, soundd" appears after starting the car, park and disable/re-enable sunnypilot, **waiting at least ~10 s between the two**. This avoids the `MOCK` fingerprint, which also wipes learned calibration.
- Avoid toggling sunnypilot while the device is still fingerprinting (the first ~10 s onroad).

No software or device change is proposed yet. Candidate next steps are in the session changelog.

## Follow-up (same session): full device-log pull and deeper analysis

**Pull** (user-authorized; device indoors, inactive, no SSH sessions, `.104`):
- one read-only inventory connection (23:40:57Z), then one pull connection (23:41:36–40Z);
- 636 files, 25 MB: all swaglogs (450), 31 boot logs, 7 crash logs, params, `/var/log`;
- command output: dmesg, journal, ALSA state, processes, git state of `/data/openpilot` (clean at `82f58a9a8c`);
- all sha256 MATCH;
- not pulled: `/persist` (device private keys, not needed), `safe_staging`, root-only `/var/log/btmp` and `/var/log/private`;
- stored in `E:\DragalPilot\device-logs\2026-10-05_s8_diag\` (new data-root folder, `docs/local-storage.md`);
- no routes newer than `0x1d`.

### soundd/micd: audio start-up time (observation, swaglogs)

`s8_audio_timing.py` → `analysis\g70-sng-20261005\diag\audio_start_timing.txt`. Time from the manager starting the process to its audio stream opening:

| Start | Result |
|---|---|
| Soon after a cold boot | 19.0–28.9 s (13 boots), or a crash at 30.9–31.3 s (5 boots) |
| Later in a boot (restarts) | 0.2–0.8 s |

- In the failing 10-05 boot the restart at ~73 s of uptime opened in 0.7 s. So that boot needed somewhere between ~31 and ~53 s after the process start.
- Kernel: the sound card registers ~2 s and the ADSP is up ~9 s after boot (dmesg of the current boot). The extra 10–20+ s happens after that; what the audio stack waits for isn't visible in the logs (the retry wrapper prints the exception to stdout, which isn't logged).
- **Upstream history:** comma raised the same budget 7 → 10 attempts in `5289b08bcf` "bump retry count for micd and soundd" (#36415, Oct 2025), so the slow audio start is known upstream. On this device 30 s is not always enough.

### locationd gyro (observation + source fact)

- **No filter state is restored.** `LocationFilterInitialState` is read in `locationd.py` L288 but written nowhere in the tree and absent on the device, so every boot starts with gyro bias 0 (`pose_kf.py` initial_x).
- **This device's raw gyro yaw bias at standstill** (`s8_gyro_standstill.py`, `diag\gyro_standstill_bias.txt`):
  - 0.034–0.039 rad/s (~2°/s) when the device is cooler (49–61 °C);
  - 0.026–0.031 rad/s when warm (63–71 °C).
- **The cross-check threshold** (`locationd.py` L133–139) is 30 × camera-odometry yaw std, ≈ 0.03–0.045 rad/s when driving straight.
- **Hypothesis (supported, not proven):** the bias is about the size of the threshold. The filter only learns the bias from gyro samples that pass the check. If it doesn't learn the bias early, rejections keep the input-invalid counter above its limit (`locationd.py` L280–330), so `locationdTemporaryError` persists.
  - Route `11` booted while already moving straight at speed (no standstill), which keeps the threshold tight from the first second.
  - It happened once in 21 cold boots.
- An offline replay of `locationd` on route `11` would test this. The generated filter source `pose.cpp` is in the checkout; the shipped `libpose.so` is aarch64, so it would need an x86 build outside the repo.
- The check comes from upstream `#33029` (2024). It is a validity check feeding an engagement-blocking event; widening it would be widening a safety check (CLAUDE.md §2), so it is not a candidate.

### Grasp warning, the slowdown, and "take control immediately" (observation, route `1a`, GPS clock)

Times verified against GPS: the initData clock and the GPS offset agree within 0.1 s. Camera SCC11/SCC12/LFAHDA_MFC decoded per second (`s8_scc_decode.py`, `diag\r1a_scc_decode.txt`).

| Time | Camera hands warning (0x485) | Stock cruise (SCC, camera) | Driver / openpilot |
|---|---|---|---|
| 06:43:20 | 1 → 5 (orange) | following a lead at 31–46 m, requests ±0.4–0.6 m/s² (the 74↔68 mph swings) | engaged, hands light (column torque ≤ 67) |
| 06:43:36 | 6 (red) | same | |
| 06:44:00–01 | 5 → 0 | `DriverAlertDisplay` 3 then 2 (06:44:01–02) | wheel wiggle (column torque 345–348, `steerOverride`) |
| 06:44:03 | 0 | **lead distance 45 → 15.7 m (cut-in), request −1.4 m/s²**: 74 → 63 mph by 06:44:07 | |
| 06:44:07.8 | | lead pulls away | **bookmark** |

- **The slowdown was the stock cruise braking for a car that cut in** at 06:44:03, not a hands-off response.
- **The comma device showed no "TAKE CONTROL IMMEDIATELY" in this window.** It showed it at 06:41:01 (route `18`, the soundd crash), 3 minutes earlier. The partner's account likely merges the two events.
- The car's hands-warning tone and message match the camera's 5/6 escalation. SCC11 `DriverAlertDisplay` (forwarded to the car; no value table in the DBC) changed exactly as the escalation ended. Whether the cluster shows the grasp warning through it is open.

## Follow-up 2 (same session): boot timing, offline locationd replay, cluster-alert scan

### Is the device booting slowly? (observation: boot logs + swaglogs)

- **The OS boot is consistent and not slow.** The 31 boot logs each embed that boot's journal with monotonic timestamps (`bootlog.cc` L30–31; decoded by `s8_bootlogs.py`, `diag\bootlog_milestones.txt`).
  - Every boot: ADSP (audio DSP) out of reset at 7.4–9.9 s; `comma.service` at 7.0–9.5 s; `multi-user.target` and the boot-log snapshot (manager start) at 10.6–14.9 s.
  - Failing and good boots look the same.
- **The audio becomes usable much later than the rest of the system:**
  - systemd reaches `sound.target` at 25.6 s (the one boot log whose journal runs that long) and ~28 s in the current boot's syslog;
  - from the swaglogs, the audio stream first opens 25–39 s after the manager starts, i.e. roughly 37–55 s of uptime.
- **What decides a crash:**

| | soundd started after manager start | Audio stream open after manager start |
|---|---|---|
| 13 good starts | 6.5–12.4 s | 25.3–38.7 s |
| 5 crash starts | **5.6–6.3 s** | (deadline expired at ~36–37 s) |

  - The crashes are the earliest starts, when the car is already on at boot and onroad begins at once, combined with an audio-ready time in the upper part of its normal range.
  - So the device isn't slow to boot. The audio path takes 25–40 s after manager start on this device and software, and the 30 s retry window is measured from soundd's start.
  - The logs don't show what the audio path waits for (journal at 1 s resolution, no exception text).

### Offline locationd replay (model of the device code; route `11`)

- **Set-up:**
  - x86 builds of the checkout's generated pose filter and rednose `EKF_sym_pyx`, compiled from the checkout's sources into `E:\DragalPilot\cache\x86-locationd\` (`build_x86_locationd.sh`; `libeigen3-dev` 3.4.0 installed in WSL for this);
  - `s8_locationd_replay.py` drives the unmodified `LocationEstimator` with the logged messages and reproduces `main()`'s validity logic: one iteration per cameraOdometry, drained sensors, latest-only SubMaster services, the same counters/limits/decay;
  - on-device-only modules (messaging, Params, realtime) stubbed.
- **Fidelity:** replay vs logged `deviceMotion.inputsOK`, per second: **route `12` 172/172 s, route `1a` 176/176 s.**
- **The gyro-bias hypothesis is rejected.**
  - The cross-check uses the camera-odometry std after `CAM_ODO_ROT_STD_MULT` = 10, so the threshold while driving is ~0.3 rad/s, not ~0.03 (my earlier estimate left out the ×10).
  - The replayed filter learns the ~0.036 rad/s bias within a second and rejects no gyro sample on route `11` (0 of ~4,000).
- **Persistence explained:**
  - with the 16 logged gyro rejections injected at 11.70 s, the replay matches the logged `inputsOK` in **42/42 s**;
  - the counter starts at 16 against a limit of 9.5 and decays by ×0.95 per 10 s of good samples (`calculate_invalid_input_decay`, `INPUT_INVALID_RECOVERY` 10 s), so recovery would have taken **~100 s** (until ~1:53 into the drive);
  - the power cycle at 51 s ended the route first.
- **Trigger: not explained.** The 16 rejections (0.15 s at 11.7 s) don't occur in the replay from the logged inputs, with either initialisation timing. The device filter's state at that moment isn't logged.
- **Observation about the design (source fact):** a single short burst of ≥ 10 bad samples blocks engagement for ~100 s because the decay is per good sample. That is upstream behaviour (`#33029`). Changing it would relax a validity check (CLAUDE.md §2), so it is not proposed.

### Cluster-alert scan (observation, all 26 recorded routes; `s8_alert_scan.py`, log `s8-alert-scan-*`)

- **A full camera hands-off sequence happened twice**, both with sunnypilot steering and the panda in Hyundai mode:

| Route | Level 5→6 | At 40 s |
|---|---|---|
| 6 (10-04 09:51:54) | 40.0 s | `HDA_SysWarning` = 2 (`highway_drive_assist_system_cancelled`) 5 s + SCC11 `DriverAlertDisplay` = 3 for 1.6 s; steering press within 3 s |
| `1a` (10-05 06:43:20) | 40.0 s | the same; lead 43.5 → 13.8 m (cut-in) just after |

- `DriverAlertDisplay` = 3 occurs **only** at these two moments. Value 2 appears as isolated 1 s blips (routes 4, 9, b, a), unrelated to hands warnings.
- `HDA_Chime` never set.
- **Interpretation (hypothesis, strongly supported):**
  - The camera's own LFA/HDA keeps monitoring hands while sunnypilot steers. When its hands-off timer runs out (40 s, orange → red), it cancels HDA and raises a cluster alert with a chime.
  - The orange/red stages are carried in 0x485, which the panda blocks, so the driver doesn't see them.
  - The final cancel alert goes out in **SCC11** (`DriverAlertDisplay` = 3), which is forwarded because the camera's SCC drives the stock cruise. That is how "grasp not detected" plus the tone reached the driver despite the 0x484/0x485 blocks.
  - The partner's wheel wiggle came as, or right after, the alert appeared.
- Blocking SCC11 isn't possible without taking over stock longitudinal messages, so any fix needs a different approach (e.g. keeping the camera from timing out). Not designed yet.

## Follow-up 3 (same session): user decisions and the camera hands-off timer

**User decisions (2026-10-05):**
- audio: option B (longer retry plus blocking engagement until audio works); implemented and focused-reviewed, see [soundd audio gate](2026-10-05-soundd-audio-gate.md), not deployed;
- gyro: deferred unless it happens again;
- grasp warning: research how to keep the camera from timing out without touching cruise-control messages.

**Partner's account matched (route `1a`):** alert tone and "driver's grasp not detected" = the camera's HDA cancel at the end of its 40 s hands-off sequence (SCC11 `DriverAlertDisplay` = 3). The slowdown = stock cruise braking for a cut-in. The wheel wiggle = 06:44:01–03. "Take control immediately" = 06:41:01 on route `18` (soundd crash), not this event.

### When does the camera run its hands-off timer? (observation; `s8_lfa_scan.py`, `s8_lfa_state.py`, all 26 routes)

- **Correction:** `selfdriveStateSP.buttonsPressed` is a bitmask by ButtonType (`button_state_tracker.py` L17; `car.capnp` ButtonEvent.Type). 256 = bit 8 = `mainCruise`. At 06:42:58.74 on route `1a` the partner pressed **cruise MAIN**, not the LFA button. That press both engaged sunnypilot lateral (`MadsMainCruiseAllowed` = 1, `mads.py` L165–167) and switched on the car's own LFA/HDA (0x485 `LFA_Icon_State` 0 → 2, `HDA_Icon_State` 0 → 2).
- **Sequence on route `1a`:**
  - camera LFA on (green) at 06:42:58;
  - hands-off orange (5) at 06:43:20 and red (6) at 06:43:35;
  - LFA icon blinking (3), then off (0), with `HDA_SysWarning` = 2 at 06:44:01;
  - the camera's LFA stays off afterwards while sunnypilot keeps steering.

| Car's own LFA icon | sunnypilot-engaged time with this icon state | Hands-off level 5/6 frames (whole routes, engaged or not) | Level 3/4 frames (whole routes) |
|---|---|---|---|
| on (2/3) | ~140 s (routes 6, `1a`, `18`) | **1,986** (routes 6, `1a`, and `e`, where sunnypilot was disabled and the car's own LFA steered) | 46 |
| off (0) | ~9,900 s | **0** | 56,325 |

- **The hands-off escalation happens only while the car's own LFA is on.** It is a driver-monitoring feature of the car's lane-following, which isn't steering (sunnypilot replaces its LKAS11).
- **What switches the car's LFA on:**
  - cruise main on: routes 5, 6, `16`, `18`, `1a`, `1b`;
  - the LFA button: many drives;
  - toggles without a nearby press (likely its own availability logic): routes a, e, 10, 1b, 1c.
  - In most drives it ended up off while sunnypilot steered, which is why the timer almost never ran.

### Options to keep the camera from timing out

| Option | What | Assessment |
|---|---|---|
| A. Car setting | Turn off the car's own Lane Following Assist (and, if separate, Highway Driving Assist steering) in the car's driver-assistance settings, so cruise main doesn't switch it on. | No software change. **Needs a supervised test:** does MADS still engage (main / SET / LFA button), does sunnypilot steer normally, does the LFA icon stay off, and do the hands-off sequence and HDA cancel disappear? Menu names on the 2024 G70 not verified. |
| B. Driving habit | When the green steering-wheel LFA icon shows, the car's own hands monitor is running. Normal light hands-on torque resets it. A quick double press of the LFA button toggles the car's LFA (and MADS) off and on. | Works today. Not a fix. |
| C. Send a hands-on signal to the camera | Block MDPS12 to the camera and send a copy with added column torque. | **Rejected:** defeats the car's driver-monitoring function (CLAUDE.md §2). |
| D. Filter the main button to the camera | Keep the camera from seeing cruise main. | **Rejected:** the camera runs stock cruise (camera SCC); this would break cruise. |
| E. Own SCC11 without `DriverAlertDisplay` | Block the camera's SCC11 (0x420) at the panda and send a copy with the field cleared every frame. | **Not advisable** (see Follow-up 4). This was not excluded by the user: "without touching the cruise messages" was my framing of the research question, corrected 2026-10-05. |

**Recommendation:** option A as a supervised settings experiment, with logs pulled afterwards. Option B in the meantime.

## Follow-up 4 (same session): 2024 G70 owner's manual, revised reading, and the SCC11 option

### Owner's manual (Genesis web manual, model code IK = G70, 2024, en_US)

Pages saved in `E:\DragalPilot\scratch\manual-g70\` (from `https://ownersmanual.genesis.com/full_webhelp/IK/2024/en_US/`, TOC `data/tocData.json`):

| Page | What it says (quoted or close paraphrase) |
|---|---|
| Smart Cruise Control operation (`id06c00b1e8e3`) | "Press the **Driving Assist** button to turn on Smart Cruise Control." Press again to turn it off; a long press = Manual Speed Limit Assist. |
| Highway Driving Assist operation (`topic_nmf_3xl_w5b`) | HDA operates when driving on a highway main road and turning HDA on with the Driving Assist button, or when entering a highway main road while LFA and SCC are operating. **Hands-off:** "Keep hands on steering wheel" message (stage 1), red wheel plus audible (stage 2), then "**Highway Driving Assist (HDA) system canceled**", then the **Driving Speed Limit**: "**Driver's grasp not detected. Driving speed will be limited**", audible continuously; it helps you drive below 40 mph, decelerates, can't accelerate automatically. It cancels when the driver grabs the wheel again, presses the Lane Driving Assist button, operates +/−/the switch, or presses a pedal. |
| Highway Driving Assist settings (`id6f2777d4246`) | **Setup > Vehicle > Driver Assistance > Driving Convenience > Highway Driving Assist** turns HDA on or off; the setting is kept after restart; "only change the Settings after parking". |
| Lane Following Assist operation (`id15ebf5c6be0`) | Turned on and off **only with a short press of the Lane Driving Assist button** (a long press toggles Lane Keeping Assist). Its own hands-off stages end in "Lane Following Assist (LFA) canceled". |
| Lane Following Assist settings (`id18264a5f9b7`) | **Only Warning Methods. There is no on/off setting for LFA**, which confirms the partner's point. |

### Revised reading of route `1a` (observation + manual)

- **The sequence matches the manual's HDA chain exactly.**
  - The Driving Assist (cruise) button was pressed on the highway at 06:42:58, so **HDA** started: HDA and LFA icons green.
  - Hands-off stage 1 at 06:43:20 and stage 2 at 06:43:35.
  - **"HDA system canceled"** at 06:44:01 (0x485 `HDA_SysWarning` = 2).
  - SCC11 `DriverAlertDisplay` = 3 at 06:44:01–02 is most likely the Driving Speed Limit message, "**Driver's grasp not detected**…". It is in a forwarded SCC message, and the speed limit is an SCC function. Hypothesis, strongly supported: the partner's wording is the manual's.
- **The slowdown:**
  - SCC requested −1.4 m/s² at 06:44:03–07 with the lead at 45 → 15.7 m, closing at 2.4 m/s, i.e. a cut-in. From 06:44:08 it requested acceleration again, back to 69 mph before any pedal input (gas from 06:44:19).
  - The Driving Speed Limit "can't accelerate automatically", so it was cancelled almost at once, by the wheel grab at 06:44:01–03.
  - The braking is most consistent with the cut-in. A brief speed-limit contribution can't be ruled out from the logs.
- **This supersedes** the earlier wording in Follow-up 2/3 that the final alert was a generic "HDA cancel alert".

### Workflow to keep the car's own hands-off monitor from running (to be confirmed in a supervised test)

1. **Parked, car on:** Setup > Vehicle > Driver Assistance > Driving Convenience > **deselect Highway Driving Assist**. It's kept across restarts. LFA can't be switched off in settings, and doesn't need to be.
2. **Engage with the Driving Assist (cruise) button only.** sunnypilot lateral engages with it (`MadsMainCruiseAllowed` = 1), and with HDA deselected the car should start Smart Cruise only, without its own LFA.
3. **Don't press the Lane Driving Assist (LFA) button while driving.** That button toggles the car's own LFA (with its own hands-off chain ending in "LFA canceled") *and* toggles sunnypilot lateral, so the two can end up in opposite states. The scan shows this happening (the car's LFA turning on from that button while sunnypilot was not engaged).
4. **Check:** the green steering-wheel (LFA) and HDA icons should stay off while sunnypilot steers. If the wheel icon appears, the car's own monitor is running; normal light hands-on torque resets it.
5. **What to confirm on the test drive:**
   - sunnypilot engages and steers normally with HDA deselected;
   - no green LFA/HDA icons;
   - no hands-off sequence.

   Then pull logs. Unverified until then: that the Driving Assist button no longer starts LFA when HDA is deselected.

### Option E (replace SCC11) assessed: not advisable

- **What it would take:**
  - a panda safety change: add 0x420 SCC11 to the camera-SCC TX allowlist with relay check, so the panda blocks the camera's SCC11. That widens the safety TX allowlist (CLAUDE.md §2) and needs a firmware rebuild and flash;
  - an opendbc change: sunnypilot re-sends the camera's SCC11 every 20 ms with `DriverAlertDisplay` cleared, keeping its counter and timing;
  - safety tests.
- **Why not:**
  1. **A new failure mode on longitudinal control.** If sunnypilot stops sending (process crash, lag, start-up), the panda keeps blocking the camera's SCC11, and the stock cruise loses its message while driving. Today sunnypilot doesn't touch cruise at all.
  2. **It would only hide the message.** The HDA cancel and the Driving Speed Limit deceleration are carried out by the camera's SCC12, so the car would still slow toward 40 mph, but silently. Stopping that would mean taking over SCC12, i.e. sunnypilot longitudinal control, which is out of scope.
  3. **It suppresses a driver-facing warning**, and the cause can be removed at the source with the HDA setting.
- **Conclusion:** technically possible, but more risk and less benefit than the settings route.

## Follow-up 5 (same session): do the car's own LFA and sunnypilot run in parallel, and do their commands conflict?

`s8_lkas_conflict.py` on route `1a`, 06:42:50–06:44:29 (output `diag\r1a_lkas_conflict.txt`). Intel bit order per `hyundai_can.dbc`: LKAS11 `CR_Lkas_StrToqReq` 16|11 −1024 and `CF_Lkas_ActToi` 27|1; MDPS12 `CR_Mdps_OutTq` 52|12 ×0.1 −204.8 and `CF_Mdps_ToiActive` 13|1.

- **They ran in parallel for 63 s** (06:42:58–06:44:01, the car's LFA icon green).
  - The camera's own LKAS11 (bus 2) had `ActToi` = 1 and requested **−36 to −117 counts** (always left).
  - sunnypilot's LKAS11 requested **+65 to −84**. During the first ~12 s it was in the **opposite direction** (e.g. 06:43:00: camera −61, sunnypilot +20).
  - The camera's request correlates only 0.32 with sunnypilot's (1 s means, n = 100).
- **Only sunnypilot's command reached the steering:**
  - 0x340 frames by source in Hyundai mode: camera bus 9,976, sunnypilot echo 9,939, **car side 0**. The panda blocked every camera LKAS11 frame (`HYUNDAI_COMMON_TX_MSGS` 0x340 `check_relay`).
  - The MDPS output torque follows sunnypilot (correlation **0.96**) and not the camera (0.40). `ToiActive` = 1 throughout.
- **Interpretation:**
  - The camera's LFA steers "open loop": its commands never take effect, so its request drifts large. That is harmless to the steering.
  - It **cannot** conflict at the actuator while the panda is in Hyundai mode. When the panda isn't in Hyundai mode (start-up, sunnypilot disabled), sunnypilot sends nothing, and only the car's own system steers.
  - A camera 0x340 on the car side while sunnypilot transmits would trip the panda's relay-malfunction check (`check_relay`) and disable controls. None was seen here or in session 3's safety replay.
- **The real interaction is indirect.**
  - Because the car's LFA/HDA thinks it is steering, it runs its own hands-off chain. Its end actions go out in messages that *are* forwarded: the HDA cancel / Driving Speed Limit via SCC11/SCC12 (Follow-up 4).
  - So the car can warn and limit speed based on a system that isn't steering.
  - sunnypilot's LKAS11 copies some non-torque fields from the camera's LKAS11 (e.g. FCW/HBA states, `hyundaican.py` L15–30); torque and `ActToi` are sunnypilot's own.
- The same parallel state occurred on routes 6 (~62 s) and `18` (~14 s) (Follow-up 3 scan). It doesn't affect the weave analysis, because the camera's commands never reach the MDPS.
