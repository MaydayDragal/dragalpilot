# G70 2024: move to sunnypilot `dev` 2026-11-12, device update, first two drives (2026-11-12)

**Status:** deployed and driven twice. One device setting changed after the drives (torque override, §6); not yet driven with it.

Work was done from a different PC than the October sessions (no WSL, no `E:\DragalPilot` data root). Device identifiers (address, dongle ID, panda serial) and GPS are kept out of this repo.

Evidence labels: **source fact** (file + revision), **observation** (device or rlog), **hypothesis**.

## 1. Request (user)

1. Reset every sunnypilot modification except the car fingerprint, and move to the latest sunnypilot.
2. Then: keep the "grasp not detected" (`0x484`) fix.
3. Install on the comma, and review two drives (tune, rack/controller behaviour, one bookmarked turn, a short test of the Lateral Jerk Torque Controller).

## 2. New branch `sunnypilot/g70-fingerprint`

| Commit | Content |
|---|---|
| `d3e1a2f` | Base: upstream `dev`, "sunnypilot v2026.11.12-5016", built from master `066c0e295712` |
| `be9fe0d` | G70 2024 car port only (6 files under `opendbc_repo/opendbc/`) |
| `c4776c4` | `0x484` camera-SCC block, its safety-test edits, rebuilt `panda_h7` firmware |

Pushed to this repo as `sunnypilot/g70-fingerprint`. `sunnypilot/g70-baseline` and `sunnypilot/dragal-custom` are unchanged.

**Kept (`be9fe0d`):** `GENESIS_G70_2024` platform (`CHECKSUM_CRC8 | CAMERA_SCC`, Harness F, steerRatio 14.1), camera/radar/EPS firmware, torque override `[4.0, 2.7, 0.07]`, LKAS11 LDWS list entry, `car_list.json` and `routes.py` entries.

**Dropped:** the soundd/micd audio gate, the D2C4 deadzone and curvature low-pass, and (until step 2 of the request) the `0x484` change.

**Source facts found while porting (`d3e1a2f` vs `0b2c431d`):**
- `CarSpecs` no longer has `mass` (`opendbc/car/__init__.py`; inertia and tire stiffness are now per-mass). The October patch applies cleanly but `CarSpecs(mass=1769, …)` would raise at import and break every car. `mass` was removed; every other added line is identical to the October port.
- `fw_versions.py`, `fw_query_definitions.py` and `car_helpers.py` are unchanged, and no other platform uses the G70's firmware codes.
- `AGNOS_VERSION` is `19.9` (was `19.7`).
- The prebuilt `dev` tree ships `panda/board` sources but no `SConscript`. The pinned panda is `sunnyhaibin/panda` @ `8a16e089b885`; its `board/` is identical to the vendored one.
- `panda/board/obj` is gitignored but tracked (`git add -u`).

## 3. Panda firmware with the `0x484` change

- Build: Arm GNU Toolchain 13.2.Rel1 for Windows (gcc 13.2.1, the version in `uv.lock`; zip sha256 matched Arm's published value), flags copied from the pinned `SConscript`, DEBUG build, committed `obj/gitversion.h` (`DEV-unknown-DEBUG`) and `obj/cert.h`. Signing re-implemented from `board/crypto/sign.py` (`SETLEN=1`, debug key).
- **Reproduction check (observation):** the same build of the unchanged source gives `panda_h7.bin.signed` byte-for-byte equal to the shipped file (sha256 `e37312f4…`). The signer alone also reproduces the shipped signed file from the shipped `main.bin`.
- **Modified build:** sha256 `529f9e2c…`, signature starts `7f1a57d0bb075216`, +16 bytes. The only symbol whose size changed is `HYUNDAI_CAMERA_SCC_TX_MSGS` (3 → 4 entries); the new entry decodes as `0x484`, bus 0, len 8, `check_relay = true`. Bootstub untouched.
- Windows note: the toolchain must sit on a short path (MAX_PATH breaks its newlib includes).

**Not validated:** no opendbc car or safety tests were run on `be9fe0d`/`c4776c4` (no Linux environment on this PC). Checks were static: AST parse, `CarSpecs` keyword check, TOML/JSON parse, firmware strings compared with October.

## 4. Device update (comma four, "mici")

Access: SSH over the LAN with a new key for this PC (added to the GitHub account; the device re-reads keys only when the GitHub username is re-entered). ADB was enabled on the device but was not listening on the network and did not enumerate over USB.

| Time (UTC) | Step |
|---|---|
| 13:50 | Pre-state (read-only): `g70-baseline` @ `c027a92857`, clean, offroad, AGNOS 19.7, **`DisableUpdates=0`**, `/data/safe_staging/finalized` = `0b2c431d` (inert), 8.9 GB free |
| 13:52 | Self-contained git bundle (161 MB, sha256 `5bda4458…`, verified on the device). Guards (offroad, not engaged, expected HEAD, clean) passed. `git fetch` → local branch `g70-fingerprint`, checkout `c4776c4`. `g70-baseline` kept for rollback |
| 13:53 | Guarded reboot. The launcher started the AGNOS updater; on the comma four it waits for "next" → "download & install" |
| 14:00 | Back on AGNOS 19.9. pandad found the panda in DFU, flashed recovery, then flashed the firmware ("Done flashing", no mismatch) |
| 14:04 | `DisableUpdates=1` (user-approved), guarded reboot |
| 14:06 | Post-boot: `c4776c4`, clean, offroad, no offroad alerts, `updated` not running. pandad: `version: DEV-unknown-DEBUG, signature 7f1a57d0bb075216, expected 7f1a57d0bb075216` |

**Why `DisableUpdates=1` (source fact, `hardwared.py` L354, `updated.py` L325):** with updates enabled, the update check looks for the current branch on `origin` (sunnypilot), which does not have it. `LastUpdateTime` was 2026-10-04, so `Offroad_ConnectivityNeeded` was set, and that alert blocks going onroad unless `DisableUpdates` or `SnoozeUpdate` is set.

**Log-reading notes:** swaglog messages are under `msg$s`; boot-time timestamps read 2026-07-28 until the clock syncs, so order by swaglog file number. One `sunnylinkd` certificate error at first boot came from that clock ("certificate is not yet valid").

Rollback: on the device (offroad) `git checkout g70-baseline`, reboot. The launcher then flashes AGNOS 19.7 again.

## 5. Two drives on `c4776c4` (observations)

Extraction ran on the device while offroad (its own `LogReader`, 4 processes, `nice`), 46 segments, compact per-segment files copied to the PC. Routes by device counter:

| Route | UTC | Length | Notes |
|---|---|---|---|
| `000000a3` | 17:51 | 610 s | drive 1, part 1 |
| `000000a4` | 18:02 | 143 s | drive 1, **`LateralJerkTorqueController=1`** (toggle needs offroad, so the device restarted) |
| `000000a5` | 18:05 | 507 s | drive 1, part 3, **bookmark at 307.8 s** |
| `000000a6` | 18:24 | 1204 s | drive 2 |

**Fingerprint and safety:** `carFingerprint = GENESIS_G70_2024`, `fuzzyFingerprint = false`, `dashcamOnly = false`, safety `hyundai` param 8. No `steerFaultTemporary`/`Permanent` samples in any route.

**Settings in effect (initData params):** `EnforceTorqueControl=1`, `CustomTorqueParams=1`, **`TorqueParamsOverrideEnabled=1` with `TorqueParamsOverrideLatAccelFactor=5.0`, `TorqueParamsOverrideFriction=0.04`**, `NeuralNetworkLateralControl=0`, `LagdToggle=1`, `Mads=1`. So the car was driven on 5.0 / 0.04, not the code's 4.0 / 0.07. `lateralTorqueParameters` shows filtered 5.0 / 0.04 with `useParams` false.

**Learned values during these drives:**

| Quantity | Value |
|---|---|
| torqued raw latAccelFactor | 3.95–4.02 |
| torqued raw friction | 0.064–0.072 |
| Steady-state fit of torque vs roll-compensated lateral accel (no friction term, so biased high) | 4.8 (\|LA\|>0.3), 4.6 (>0.6), 4.35 (>1.0) |
| paramsd steerRatio | 14.7–15.2 (code 14.1) |
| lagd lateral delay | 0.177–0.189 s |

**Controller arithmetic (observation):** `output = −(p + i + f) / latAccelFactor` with the override's 5.0, e.g. `p −0.51, i 0.01, f −1.55 → 0.41`.

**Tracking, hands off, lat active (100 Hz):**

| Route | Speed band | s | RMS error (m/s²) | desired→actual lag (s) | lane-centre std (m) | saturated |
|---|---|---|---|---|---|---|
| a3 | 35–60 mph | 102 | 0.105 | 0.17 | 0.19 | 0 % |
| a3 | >60 mph | 112 | 0.076 | 0.35 | 0.10 | 0 % |
| a4 (jerk ctrl) | >60 mph | 130 | 0.084 (des − act) | 0.24 | 0.17 | 0 % |
| a5 | >60 mph | 314 | 0.089 | 0.38 | 0.12 | 0 % |
| a6 | 35–60 mph | 81 | 0.167 | 0.25 | 0.15 | 0.6 % |
| a6 | >60 mph | 564 | 0.072 | 0.18 | 0.15 | 0 % |

- EPS torque follows the command: correlation 0.95–0.98 for \|command\| > 0.1; the command was rate-limited about 1 % of the time.
- Torque command direction reverses about 42 times per second in every band (same order as October's twitch findings; not re-analysed).

**Bookmarked turn (`a5`, 298–308 s, ~76 mph):** desired lateral accel went −0.8 → −1.75 m/s² in about 1 s. Actual lagged with error up to −0.51 m/s²; lane centre moved from +0.44 m to −0.13 m; then overshoot (+0.32 m/s² at 303.5 s) and a smaller repeat at 306–307 s. Peak torque 0.41 of the limit, not saturated, no driver torque.

**`steerSaturated` (`a6`, 98 s, ~43 mph):** "take control / turn exceeds limit". Desired lateral accel reached −3.1 m/s², above the platform's `maxLateralAccel` 2.7; torque 0.82–0.84; lane centre +0.51 m then −0.30 m. This is a limits alert, same lag-then-overshoot shape.

**Lateral Jerk Torque Controller (`a4`):** real tracking (desired − actual) is the same as the standard controller on comparable highway (0.084 vs 0.073–0.089 m/s²). Its logged `error` reads about 5× smaller because it is scaled differently. 130 s on one road is too little to rank it.

**Hypothesis:** with latAccelFactor 5.0 against a measured ~4.0–4.3, the feedforward sends roughly 10–20 % less torque than the car needs, which adds to the short turn-in. The 0.2–0.4 s lag is separate and will remain.

**Open:**
- pandaStates showed `faultStatus = faultTemp` in parts of `a4`–`a6` and `safetyTxBlocked` up to 4. Not investigated.
- "Grasp not detected": the user has not reported on it for these drives; not checked in the logs.
- No video review of the bookmarked turn.

## 6. Setting changed after the drives (user-approved, 2026-11-12)

On the device, offroad: `TorqueParamsOverrideLatAccelFactor` 5.0 → **4.0**, `TorqueParamsOverrideFriction` 0.04 → **0.07** (read back; `TorqueParamsOverrideEnabled` stays 1). Not yet driven. Comparison target: the same turn at a similar speed.
