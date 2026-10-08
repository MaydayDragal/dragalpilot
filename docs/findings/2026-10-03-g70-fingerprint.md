# Genesis G70 fingerprinting: initial device inspection (2026-10-03)

Question: did the device record what is needed to fingerprint the user's G70, so that sunnypilot can run on it?

## Evidence sources

- **Device**, one read-only SSH session at `192.168.98.104`, 2026-10-04T02:35:45Z (2026-10-03 22:35 EDT). The user said the device was indoors, not in the vehicle, and not active. The device itself reported `IsOffroad=1`, `IsEngaged=0`, and no `IsOnroad` param. Script: `E:\DragalPilot\scratch\device\fp_inspect_20261003.sh`. Full output: `E:\DragalPilot\logs\device-fp-inspect-20261003.log`. No writes, restarts or file transfers.
- **Source:** the pinned `opendbc_repo` in baseline `dev` @ `0b2c431d`.
- **Upstream (web, 2026-10-03):** `commaai/opendbc` and `sunnypilot/opendbc` `master` fingerprints, commaai/opendbc PR #1134, and commaai/panda PR #2045. Copies are in `E:\DragalPilot\scratch\`.

## Confirmed device facts

- Installed software is `dev` @ `0b2c431d3abab630df0a32f53236944855a91aa3` ("2026.09.14-4885 / dev / 0b2c431"), matching the project baseline. `git status` shows no local changes. The device's remote reads `https://github.com/sunnypilot/openpilot.git`, which differs from our clone's `sunnypilot/sunnypilot.git` URL; it presumably redirects to the same repository, but that is not verified.
- `CarParamsPersistent` and `CarParamsPrevRoute` (2344 bytes each) decode to `brand=mock`, `carFingerprint=MOCK`, `dashcamOnly=true`, `fingerprintSource=can`, `fuzzyFingerprint=false`. **Fingerprinting failed and the device ran in dashcam mode.**
- VIN queried: `KMTG54SE5RU******` (serial masked; full VIN only in the local device log). Year code `R` decodes as model year 2024 under the standard VIN scheme. This decoding comes from that standard scheme; nothing in the source checks it.
- Firmware versions captured (UDS `0xF100`, buses 0 and 1, OBD multiplexing):
  - fwdCamera `0x7c4`: `\xf1\x00IK  MFC  AT USA LHD 1.00 1.02 99211-G9500 230712`
  - fwdRadar `0x7d0`: `\xf1\x00IKPE RDR -----      1.00 1.00 99110-G9600         `
  - eps `0x7d4`: `\xf1\x00IK2 MDPS R 1.00 1.03 57700G9570  4IK4R103`
  - transmission `0x7e1`: `\xf1\x00PSBG2283  E36\x00…SIK0T33XXXXXXNS0\x8d\xca\xe1P`
  - Also present: logging-only queries (combinationMeter, cornerRadar `0x7b7`, manufacturing dates) and cross-brand engine and transmission responses.
- Routes in `/data/media/0/realdata` (341 MB, 8 entries). Every segment has `rlog.zst` except as noted, along with `qlog`, `fcamera`, `ecamera` and `qcamera`. **No `dcamera.hevc` (driver video) appears in any segment.**
  - `00000000--eb903c3c31` segments 0–1 (segment 1 has rlog only)
  - `00000001--ed6394b42a` segments 0–3 (directory mtimes for segments 0–2 are 2026-10-03 21:56–21:58Z)
  - `00000002--3ea363e27d` segment 0
  - Which routes were recorded in the G70, and their real start times, are **not yet determined**. Directory mtimes are unreliable because the clock may not have been synced at boot.

## Confirmed source facts (pinned opendbc)

- Hyundai FW fingerprinting uses platform-code ECUs fwdRadar, fwdCamera and eps; fuzzy matching also checks camera date ranges (`opendbc_repo/opendbc/car/hyundai/values.py`, `match_fw_to_car_fuzzy`, ~L712–755).
- Applying the platform-code regex by hand to this car's firmware gives:

  | ECU | Code from the car | `GENESIS_G70_2020` expects |
  |---|---|---|
  | Radar | `IKPE-G9600` | `IK-G9100` / `IK-G9300` / `IK-G9000` |
  | EPS | `IK2-G9570` | `IK-G9220`, … |
  | Camera | `IK-G9500`, date 230712 | `IK-G9000`, dates ≤ 220401 |

  **No exact or fuzzy match to any G70 platform** (`GENESIS_G70`, `GENESIS_G70_2020`, `GENESIS_G70_2021_NON_SCC`). This is consistent with the device's MOCK result.
- None of these firmware strings appear anywhere in the pinned fingerprints, nor in current `commaai/opendbc` or `sunnypilot/opendbc` master (checked 2026-10-03).
- The pinned code already has `HyundaiFlags.CAMERA_SCC` and `CHECKSUM_CRC8` for non-CAN-FD Hyundai cars, and camera-SCC handling in safety (`opendbc_repo/opendbc/safety/modes/hyundai.h`). The pinned safety code has no `0x484` (HDA11_MFC) handling.

## Upstream port attempt (external, unmerged)

- commaai/opendbc **PR #1134 "HKG: Car Port for Genesis G70 2024"**: a **draft**, open since 2024-08-20, unmerged, with merge conflicts. It adds a `GENESIS_G70_2024` CAN platform with `CHECKSUM_CRC8 | CAMERA_SCC`, harness L, specs `mass=1769, wheelbase=2.83, steerRatio=12.9` (its comment calls the steer ratio a guess). It adds a torque override `[2.7, 2.7, 0.11]` and adds the car to the LKAS11 LDWS-field list.
  - Its fingerprint entry (camera and radar only) matches this car's camera and radar firmware **exactly**.
  - Its test routes are `a6310918f9699ef5/2024-02-28--14-55-10` (openpilot) and `a6310918f9699ef5/2024-02-27--20-17-09` (stock).
- It "requires" commaai/panda **PR #2045** (closed, unmerged). That PR adds `0x484` (HDA11_MFC) to the camera-SCC transmit allowlist and blocks it from forwarding, in order to suppress the "grasp not detected" warning. **This is a change to safety code and widens what the system may transmit.** It needs its own justification and review, and is not needed just to fingerprint the car.

## Assessment

- **Hypothesis (strong):** the device captured what fingerprinting needs (the VIN and the firmware of all platform-code ECUs), and rlogs exist for the drive. Getting the car recognized requires a **new `GENESIS_G70_2024` platform port**, not just firmware additions to an existing G70 platform: the 2024 model uses camera-based SCC and a new radar and EPS family.
- **Not yet verified:** that the car's CAN layout matches the PR's assumptions (SCC messages coming from the camera on bus 2, CRC8 checksums, LKAS11 and MDPS message set). This needs rlog CAN analysis, which needs a Linux toolchain and the rlogs copied locally.
- Specs, steer ratio and torque values in the PR are unvalidated for this car.

## Open questions

1. Which routes on the device were recorded in the G70, and when? (Decode `initData` and `carParams` from the rlogs.)
2. CAN bus layout from the rlogs: which addresses appear on buses 0, 1 and 2, whether SCC11/SCC12 (`0x420`/`0x421`) come from the camera, and whether the checksums are CRC8.
3. What the user's "backup option" is, and whether it is still needed.

## Update: sunnypilot `g70-2024-port-new` branch (user-supplied)

- `origin/g70-2024-port-new` @ `ed8397c6d4dd0571ad7163f89bda974503a0bb2c` (Jason Wen, 2025-08-04, "re-port over"). It is one commit on master `8cce8cf3` (2025-08-02), 3,101 commits behind master `a5f4465`, and the `dev` baseline is not an ancestor. Its only change bumps the `opendbc_repo` submodule `c6f01a60` → **`cfb743f4095225daddb0b4b060fc2257b58a6e6a`**.
- `cfb743f4` fetched from `commaai/opendbc` (head of a `g70-2024-port` branch) and kept locally as `refs/ext/g70-opendbc` in the sunnypilot clone. Diff saved at `E:\DragalPilot\scratch\g70-opendbc-cfb743f4.diff`. **It is identical to PR #1134**: same 4 files, same blob hashes. It contains no panda/safety changes.
- Dry run `git apply --check --directory=opendbc_repo` on `dev` @ `0b2c431d`: `fingerprints.py` and `values.py` apply with offsets. `hyundaican.py` (the LKAS11 car list has since gained the NON_SCC cars) and `torque_data/override.toml` (the neighbouring `HONDA_PILOT_4G` value changed) fail on context drift only. Nothing was applied.
- Status when that update was written: whether the 2024 G70's CAN layout matches the port's assumptions (rlog analysis pending), whether sunnypilot-specific integration (e.g. `openpilot/sunnypilot/selfdrive/car/car_list.json`, platform selection) needs entries, and which upstream tests (route coverage, FW format, docs) the new platform affects.

## Update: port tests and FW replay (session 2, 2026-10-03 ~23:15 EDT)

Environment: WSL 2 Ubuntu 24.04 test clone, Python 3.12.13, `.venv` from `tools/setup_dependencies.sh` (see `docs/baseline.md`). Tests ran with `python -m unittest <module>` from `opendbc_repo/` (the opendbc tests are unittest-based).

1. **On `392f9b6ea9`:** `opendbc.car.hyundai.tests.test_hyundai` **failed** in `test_platform_code_ecus_available (car_model='GENESIS_G70_2024')`. Non-CAN-FD Hyundai platforms must list EPS FW for fuzzy fingerprinting, and the upstream port lists only camera and radar. Log: `E:\DragalPilot\logs\tests-20261003-231530\`.
2. **Fix, commit `5cdfe3c082`:** added `(Ecu.eps, 0x7d4, None): [b'\xf1\x00IK2 MDPS R 1.00 1.03 57700G9570  4IK4R103']`. This is the car's own UDS response, identical on buses 0 and 1 in `device-fp-inspect-20261003.log`. The fix is evidence from one car, not an invented value.
3. **On `5cdfe3c082`, all exit 0** (log `E:\DragalPilot\logs\tests-20261003-231709\`):

   | Suite | Result |
   |---|---|
   | `opendbc.sunnypilot.car.tests.test_car_list` | OK. The hand-written `car_list.json` entry equals the generator output. |
   | `opendbc.car.tests.test_routes` | OK |
   | `opendbc.car.tests.test_docs` | OK (162 subtests skipped by design: non-upstream cars and comma body) |
   | `opendbc.car.hyundai.tests.test_hyundai` | OK (2 skipped) |
   | `opendbc.car.tests.test_fw_fingerprint` | OK (15 tests, 148 subtests skipped) |
   | `opendbc.safety.tests.test_hyundai`, `test_hyundai_canfd` | OK (354 skipped: base-class/feature skips). This is a regression check only; safety is unchanged. |
   | NNLC `test_fingerprint` (openpilot side) | **Not run.** The `dev` prebuilt ships an AArch64 `libparams_c.so` and no `SConstruct`, so the test cannot import on x86. It has no G70_2024 case. |

4. **FW replay** (`E:\DragalPilot\scratch\wsl\fp_replay.py`, log `E:\DragalPilot\logs\fp-replay-20261003-231836.log`): all 19 `carFw` entries from `CarParamsPersistent`, plus the captured VIN, run through `match_fw_to_car`.
   - Baseline `0b2c431d3a`: no match in exact, fuzzy or combined mode. This matches the device's MOCK result.
   - Candidate `5cdfe3c082`: **exact match `GENESIS_G70_2024`**. Fuzzy-only mode also resolves uniquely to `GENESIS_G70_2024`.
   - Scope: this is source-level evidence about fingerprint *resolution* only. It says nothing about whether the platform's CAN and control assumptions are correct for this car.

Still open: rlog CAN verification (SCC source bus, checksum, LKAS11/MDPS12), specs and torque values, the `0x484` question, QA.

## Update: component lineage of the 2024 G70 (session 13ws, 2026-10-07; user question)

**User question:** the 2024 G70 is a "V1.5" of Hyundai's ADAS, with components from a newer generation. Is the controller in use specific to the 2023 and older G70s? Do the EPS and radar match another car, whose comma settings could help?

**Source facts** (`dragal/custom` @ `89bbe60ab1`, opendbc in the checkout):
- `GENESIS_G70_2024` is its own platform (`values.py` L601–605), separate from `GENESIS_G70` / `GENESIS_G70_2020` (2018–2023).
  - It has its own fingerprint, specs (steerRatio 14.1 learned on this car), flags `CHECKSUM_CRC8 | CAMERA_SCC`, torque override (this car's torqued values), the D2 deadzone, and the session 3 `0x484` safety change.
- **Shared with dozens of classic-CAN Hyundai/Kia/Genesis platforms:**
  - the steering controller path (`hyundai/carcontroller.py`, `hyundaican.py` LKAS11 at 100 Hz);
  - the default `CarControllerParams` (STEER_MAX 384, +3/−7 per 10 ms; `values.py` L20–56).
  - The source says STEER_MAX should not exceed "the maximum value that the stock LKAS will request" for a car. That has not been measured for this car.

**Fingerprint search for the same parts** (observation; checkout, current `commaai/opendbc` and `sunnypilot/opendbc` master, web; 2026-10-07):
- **No other car has the same EPS or radar.**
  - The part numbers are G70-specific ("G9"). Parts listings give 99110-G9600 for the 2024–2026 G70 only.
  - Upstream has no G70 2024 platform (PR #1134 is unmerged).
- **EPS** `IK2 MDPS R … 57700G9570  4IK4R103`: its firmware format (no hyphen in the part number, suffix `4IK4R103`) matches **no** entry in any fingerprint database checked. Every other rack-type EPS (older G70 `4I4VL…`, Stinger `4C2VL…`, Sonata/K5 `4DNAP…`) uses older schemes. So it is a new EPS family with no comma reference.
- **Radar** `IKPE RDR -----  99110-G9600`: the `RDR -----` format appears **only** on CAN-FD-generation cars (EV6, Ioniq 5, Ioniq 6, GV60, Kona EV 2nd gen, Niro 2nd gen, K8 HEV, Staria). All classic-CAN cars, including every older G70 and Stinger, report `SCC`.
- **Bus 1 decoded** (`s16_ws_bus1.py`, route `0x20` segment 6, `logs/s13ws-bus1-*`): all 20 addresses on the 2024's separate CAN-FD bus match opendbc's CAN-FD DBC exactly in address and frame size (`dbc/generator/hyundai/_hyundai_canfd_common.dbc`, `hyundai_canfd.dbc`):
  - 19 `FRONT_RADAR` messages (`0x201`, `0x210`–`0x21f`, `0x240`, `0x251`; 20 Hz);
  - `ADRV_0x51` (100 Hz).
  - **No steering (EPS) message is on that bus.**

**Reading:**
- The 2024 G70 carries the **CAN-FD-generation front radar** (the same message protocol as the CAN-FD cars above) on its own CAN-FD bus. Steering and cruise control stay on classic CAN. That fits the user's "V1.5" description.
- **For steering**, nothing transfers from another car:
  - the EPS is unique among known fingerprints;
  - it is commanded only through classic LKAS11, which the stock camera also uses (CRC8 confirmed, session 2);
  - CLAUDE.md §2 forbids generalising control tuning across platforms anyway.
  - The steering friction model used for the twitch work was fitted to this car's own logs, so it already reflects this EPS and rack.
- **For the radar**, the match is useful later: opendbc already decodes this radar's messages (lead/track data for longitudinal work). It isn't used by the port today.
- **Open (read-only, offline):** the stock camera's maximum LKAS11 torque request vs STEER_MAX 384; what `ADRV_0x51` carries on this car and which unit sends it.

Sources (web): [hyundaipartsdeal G70 steering gear listings](https://www.hyundaipartsdeal.com/oem-2021-hyundai-genesis_g70-steering_gear_box.html), [partrequest G70 cruise control components](https://www.partrequest.com/catalog/cruise-control-components/genesis/genesis-g70), [commaai/opendbc fingerprints](https://raw.githubusercontent.com/commaai/opendbc/master/opendbc/car/hyundai/fingerprints.py), [sunnypilot/opendbc fingerprints](https://raw.githubusercontent.com/sunnypilot/opendbc/master/opendbc/car/hyundai/fingerprints.py).

### Torque limits and `ADRV_0x51` (session 13ws, 2026-10-07; read-only, all 500 logged segments; exploratory)

Scripts: `E:\DragalPilot\scratch\wsl\sng\s16_ws_lkas_adrv.py`, `s16_ws_adrv_decode.py`, `s16_ws_adrv_scale.py` (checkout venv). Outputs: `analysis/g70-weave-twitch-sim-20261007/platform/`. Logs: `logs/s13ws-lkas-adrv-*`, `s13ws-adrv-decode-*`, `s13ws-adrv-scale-*`. Signal layouts are from opendbc's `hyundai_can.dbc` (LKAS11, MDPS12) and `_hyundai_canfd_common.dbc` (ADRV_0x51).

**Torque limits** (counts of 384; observation):

| | Stock camera's own LKAS11 (bus 2, CF_Lkas_ActToi = 1) | Our LKAS11 (sendcan) |
|---|---|---|
| Active time | 8.8 min (52,635 frames); speeds 0–35 m/s (median 19.8) | about 62% of all frames |
| Max \|request\| | **218** (highway ≥ 24.6 m/s: 153) | **384** (331 frames, all < 24.6 m/s; highway max 331) |
| p99 / p99.9 \|request\| | 136 / 195 | 186 / 315 |
| Largest same-sign step up / down per 10 ms | **7 / 6** (mostly 1–2; ≥ 5 in 26 up-steps) | **3 / 7** (the panda and controller limits) |

- **Limits in force** (source facts): `CarControllerParams` and panda `HYUNDAI_STEERING_LIMITS` are 384 / +3 / −7 for this car. That is the default; the 2024 is in no reduced-limit list.
- The upstream rule ("find the maximum value that the stock LKAS will request; if < 384, add your car to this list"): the stock maximum seen here is **218**, but only over 8.8 min of mostly gentle stock activity. So it is a lower bound on what the stock system can request, not its maximum. Not conclusive.
- **The stock system ramps torque up faster than we may:** up to 7 per 10 ms vs our 3. Our rising torque sits at the +3 rate limit in 67% of rising steps (372,893 of 557,378), so torque build-up is rate-limited most of the time. The simulator already models this limit.
- Raising the up-rate would widen a safety limit (CLAUDE.md §2: not as a shortcut). Lowering STEER_MAX is conservative but needs evidence of the stock maximum in sharp curves.
- MDPS12 while engaged: CR_Mdps_OutTq |p99| 6.4, max 16.7 (DBC units). Driver column torque range ±650.

**`ADRV_0x51`** (bus 1, 100 Hz; exploratory decode on route `0x20` segments 3–9, scales fitted on segment 6):
- Bytes 0–1 are the checksum and byte 2 the counter (opendbc defines only these). Byte 3 is constant 0x09. Bytes 10–11 and 16–31 are constant (byte 28 = 0x10).
- **Bytes 6–7 (int16 LE) = steering angle:** 10.006 counts per degree, r 0.9998, about 0.03 s after carState. **Resolution 0.1°**, the same as the car's angle sensor, so there is **no finer angle**.
- **Bytes 4–5 (int16 LE) = yaw rate:** −5,769 counts per rad/s (about 0.01 deg/s per count), r −0.998 vs the device gyro, about 0.07 s later. *This car reports carState.yawRate = 0, so this is the first yaw-rate source on the car's own buses.*
- **Bytes 8–9 = vehicle speed:** about 0.01 m/s per count, r 0.999, scale 3% off vEgo (a different speed source; *hypothesis*).
- Bytes 12–15 vary too: weak correlations with yaw and lateral acceleration; byte 14 relates to model lead probability (r −0.89). Not identified.
- **Correction (session 15cm, 2026-10-07):** "the first yaw-rate source on the car's own buses" is wrong. **ESP12 (0x220, bus 0, 100 Hz) carries the ESC's yaw rate and lateral acceleration** (`hyundai_can.dbc` L1228–1242: YAW_RATE 13 bits, 0.01, −40.95 deg/s; LAT_ACCEL 11 bits, 0.01, −10.23 m/s²). The Hyundai `carstate.py` doesn't read them.
  - Observation, all routes ([comfort-metrics findings](2026-10-07-g70-comfort-metrics.md) §1): ESP12's yaw rate matches the calibrated device gyro (r −0.996…−0.9998, scale 1.00–1.01, 30–40 ms behind it). ADRV_0x51's yaw rate is ESP12's relayed 30 ms later.
- **Reading (hypothesis):** `ADRV_0x51` is the ADAS unit re-broadcasting chassis data (angle, yaw rate, speed), slightly delayed, onto the radar's CAN-FD bus. It is the same role this message plays on CAN-FD cars, where openpilot must keep sending it after disabling the ADAS unit. The sending unit on this car is not identified. It carries no steering command and no finer steering information.

### Raising the +3 per 10 ms torque-rise limit (session 13ws, 2026-10-07; user question; exploratory)

**User:** if this car's hardware has a different limit, "logically we should be operating under the same rules… properly configuring the software for this unique car".

**How the rate limits are set** (source facts, opendbc in the checkout):
- `car/tests/test_lateral_limits.py` (ISO 11270) requires for every torque car:
  - up-jerk = (STEER_DELTA_UP / STEER_MAX) × 50 × MAX_LAT_ACCEL_MEASURED / 0.5 ≤ 3.0 m/s³ (2.5 + 0.5 tolerance);
  - down-jerk ≤ 5.0 m/s³.
  - The rates are set by this lateral-jerk rule, not by the stock system's ramp. Only STEER_MAX follows the stock system ("max stock LKAS request").
- For `GENESIS_G70_2024`, MAX_LAT_ACCEL_MEASURED is 2.7 (`torque_data/override.toml`; an unverified value from the upstream port; comma's measured value for the older `GENESIS_G70` is 2.35, `params.toml`).
  - Up-jerk: 2.1 m/s³ at +3 (now), 2.8 at +4, 3.5 at +5, 4.9 at +7. **Only +4 would still pass.**
  - Down-jerk at −7 is 4.92 (limit 5.0).
- The panda safety limit (`safety/modes/hyundai.h`, 384 / 3 / 7) would have to change too: a safety-code change, a panda firmware build, and full QA.

**Simulated impact** (`s16_ws_dup.py`; `platform/dup/dup.json`, `logs/s13ws-dup-*`; output-stage rise limit as a parameter, bit-identical at 3; E2 / E3, change vs A0 at +3):

| Variant | E4 plant: jumps / T / 0.2–0.4 Hz lag / tracking | E2+E3 plant: jumps / lag |
|---|---|---|
| A0 at +4 | +2 / +4%, +1…+2%, −0.6 / 0.0°, −0.3…−0.6% | +2 / +2%, −0.4 / −0.6° |
| A0 at +5 | +2 / +4%, +1…+2%, −0.5 / −0.3°, −0.3…−0.7% | +7 / +6%, −1.0 / −0.7° |
| A0 at +7 | +4 / +7%, +2…+3%, −0.8 / −0.5°, −0.7…−1.0% | +3 / +6%, −0.7 / −0.9° |
| D2C4 at +3 → +7 | jumps −45 / −52% → −43 / −49%; lag +16.5 / +17.6 → +16.3 / +18.8° | no material change |
| F7d at +3 → +7 | jumps −40 / −42% → −40 / −38%; lag +3.4 / +4.6 → +2.9 / +4.1° | no material change |

**Reading (model):**
- Raising the rise limit changes the twitch and the weave very little. With today's controller it makes the twitch slightly worse (jumps +2…+7%) and the weave-band lag marginally better (≤ 1°).
- The limiter is active in many rising steps (§ above), but the steps are small, and the hold-and-jump timing is set by steering friction and delay, not by the ramp rate.
- So a faster rise is not a fix for either complaint. A higher limit would also fail comma's lateral-jerk rule above +4.
- **What "configuring for this car" does point to:** measuring this car's MAX_LAT_ACCEL_MEASURED, which today is a guess. If it is higher than 2.7, comma's rule would require **lower** rates (for example, the −7 down-rate fails 5.0 m/s³ for any value above 2.74).
