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
