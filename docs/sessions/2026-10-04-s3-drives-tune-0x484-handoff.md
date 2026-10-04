# Handoff: session 3 (2026-10-04): drives, steering tune, 0x484 safety change, deployment

Written 2026-10-04 ~12:50 EDT. Reconfirm everything at the next session start.

## Objective

Make sunnypilot drive the user's 2024 Genesis G70 well. The port works and is deployed. **Next task (user decision): investigate the slow lane-position drift (~0.1 Hz wander) that remains after the tune.**

## User decisions and instructions (this session)

- Steering tune approved and deployed: latAccelFactor 4.0, friction 0.07, steerRatio 14.1.
- The upstream panda safety change (commaai/panda#2045) was brought in "as intended by the developers", implemented as a `check_relay` TX entry for 0x484. Deployed.
- **Next round of enhancements** (user decision): replace that `check_relay` entry with a Hyundai-specific forwarding rule. It should block the camera's 0x484 without relay-malfunction detection, closer to the original panda PR.
- **Do not investigate** the sharp-curve `steerSaturated` takeover (12:02:18): the user considers it expected limit behaviour.
- The user confirmed the dashboard "grasp not detected" warning did **not** appear after the change.
- Pushes of the outer `main` were approved and done through `8786028`. `dragal/custom` stays local.
- Standing: rlogs only unless videos are requested; per-step device authorization; reboots need explicit authorization each time.

## Exact revisions

- sunnypilot baseline: `dev` @ `0b2c431d3abab630df0a32f53236944855a91aa3` (unchanged).
- **`dragal/custom` @ `82f58a9a8c4af2f10d23d13fb1631deca98d4efd`** (local only), deployed on the device. Commits after the port (`7e9d0755d9`):
  - `c895200ecb`: torque `[4.0, 2.7, 0.07]`
  - `2623b19329`: steerRatio 14.1
  - `92e72004ac`: `hyundai.h` camera-SCC (non-long) TX `{0x484, 0, 8, .check_relay = true}` + tests
  - `d2accb8980`, `c1806292fa`: test harness skips a class's own parameterized variants
  - `cb66129698`: prebuilt `panda_h7.bin.signed` sha256 `206ea19c…738d` (signature `5b8d2b33…`)
  - `82f58a9a8c`: review fixes (stricter skip: identical TX lists; comment)
- Shipped/baseline firmware: `bf8e3dab…d897d` (signature `599ef38d…`).
- Outer repo `main` = `origin/main` = `8786028` before this handoff's commit.
- WSL test clone `~/src/sunnypilot`: detached at `82f58a9`, clean. Panda source `~/src/panda` @ `74a0adc`, clean.

## Completed work and evidence

1. **Morning drives** (routes 5–7). Findings: [docs/findings/2026-10-04-g70-drives-tune.md](../findings/2026-10-04-g70-drives-tune.md).
   - The device runs `LatControlTorqueV0` (`EnforceTorqueControl` absent).
   - torqued estimated latAccelFactor ~4.0–4.5 and friction ~0.07 vs the port's 2.7/0.11.
   - The "driver engagement" alerts were the car camera's LFA hands-off warning, not sunnypilot DM.
2. **Changes**, all passing @ `82f58a9a8c` (logs `E:\DragalPilot\logs\tests-20261004-112317\`, `safety-cov-20261004-112506.log`):
   - targeted car tests;
   - full safety suite + 100% coverage;
   - MISRA;
   - negative check;
   - Kona `test_models`;
   - G70 relay replay.
3. **Firmware build**: reproducible (baseline byte-identical). Script `E:\DragalPilot\scratch\wsl\build_panda_fw.sh`; see `docs/baseline.md`.
4. **QA**: focused adversarial review ([findings](../findings/2026-10-04-g70-tune-0x484-focused-review.md)): no blockers; the major (`check_relay` relay-malfunction exposure) was accepted with evidence; 2 fixes. **Two-round QA not performed.**
5. **Deployment** (11:31–11:34 EDT): install, guarded reboot, panda flashed `599ef38d…` → `5b8d2b33…`. Record: [proposal § Deployment record](../proposals/2026-10-04-g70-tune-0x484-deploy.md).
6. **First drive after deployment** (routes 8–9). Findings: [docs/findings/2026-10-04-g70-tune-0x484-first-drive.md](../findings/2026-10-04-g70-tune-0x484-first-drive.md).
   - All tune criteria met: curve actual/desired 1.07 → 1.007; 0.5–3 Hz error share above 25 m/s 0.54–0.70 → 0.28.
   - User: ~75% better.
   - No relay malfunction. No grasp warning (user).

## Lane-drift investigation: what's known (starting point)

- Metric (`lateral_metrics.py`, `lane_position`):
  - Lane-centre offset = mean of `modelV2.laneLines[1].y[0]` and `laneLines[2].y[0]` (both prob > 0.7, v > 10 m/s, excluding 3 s after blinkers, stretches ≥ 20 s), minus its 10 s moving average.
  - Engaged std **0.076–0.094 m**, p95 |dev| 0.17–0.20 m, dominant **~0.1 Hz**. **Unchanged by the tune** (routes 6/7: 0.083/0.076; route 8: 0.077).
  - Mean offset is +0.11 to +0.17 m (sign convention not verified). Manual reference: only 31 s (too little).
- Torque tracking is good now (actual vs desired lat accel corr 0.995, best lag 0.15 s). **Hypothesis:** the wander is in the desired path (model/planner output), not the controller. Untested.
- Possibly relevant settings/state (read 2026-10-04):
  - `PlanplusControl=1.0` (neutral), `CameraOffset=0.0`, `LagdToggle=1` (lagd delay ~0.17 s, used by modeld and controls), NNLC 0, `LateralJerkTorqueController=0`.
  - paramsd angle offset −2.3 to −3.2°.
- **Not yet recorded:** which driving model is active (sunnypilot model manager; params `ModelManager_ActiveJson` etc.) and the device calibration (`CalibrationParams` / `liveCalibration` rpyCalib). Record both before interpreting.
- Data available (rlogs, `recordings/2026/10/04/`):
  - routes 4, 6, 7 (old tune) and 8, 9 (new tune);
  - road videos for routes 5–7 only (`videos/front-narrow`, `front-wide`);
  - the user's wheel video, filed with route 6.
- Extracted series: `E:\DragalPilot\analysis\g70-drives-20261004b\<route>.npz` (`mdl.*` = lane lines and `action.desiredCurvature` at 20 Hz; `lc.*` = controller at 100 Hz; `cs.*` = carState). Scripts: `E:\DragalPilot\scratch\wsl\`.
- Suggested first questions:
  - Does `modelV2.action.desiredCurvature` (or the planned path y) oscillate at ~0.1 Hz on straights while lateral is engaged?
  - Does the drift correlate with road features (curvature, lane width, lane-line probability)?
  - Is it present in manual driving as the model sees it? That needs a manual stretch from the user.
  - Is it related to calibration/offset?
- Any change (e.g. model choice, CameraOffset, a planner parameter) is a separate bounded change with its own question and criteria.

## Open items / watch list

- **`interruptRateCan2` panda fault** at startup on routes 8/9 (not before):
  - What happened: a ~3 s error burst on bus 1 (the unused CAN-FD network) while still in elm327, never repeating while driving.
  - Effect: sticky until a panda reset; no control effect (openpilot acts only on `relayMalfunction`).
  - Cause unknown. Watch on the next drives (`irq_rates.py`, `err_timeline.py`).
- `torqued` was 60% calibrated at the end of route 9 (estimate ~4.2). It may apply its own value once valid (clip 2.8–5.2). Track this, because it changes the controller between drives.
- Next round: the Hyundai 0x484 forwarding rule (safety code, tests, 100% coverage, MISRA, review, firmware rebuild with `build_panda_fw.sh`, deployment approval).
- micd/soundd crash at ~+31.6 s on some routes (3, 5); user-reported known sunnypilot bug; not investigated.
- Staging folders `temporary/device-pull-20261004{,b,c}` (~7.1 GB) were deleted 2026-10-04 with user agreement, after all 168 files were re-verified against their promoted copies. Device manifests are kept in `E:\DragalPilot\logs\device-pull-20261004*.remote.sha256`. `temporary/device-pull-20261003` (session 1) remains.

## Device state and SSH ownership

- Device `192.168.98.104` (reconfirm), user `comma`, key `~/.ssh/id_ed25519_dragalpilot`.
- Last observed 16:30Z: offroad, indoors, `GitCommit=82f58a9a8c`, `DisableUpdates=1`, panda firmware `5b8d2b33…`, NNLC 0, `Mads=1`, `RecordFront=0`. Disk 75 GB free.
- **No SSH connection open.** All sessions this day were sequential and closed.
- Rollback: `git checkout 7e9d0755d9` (or `dev`) + reboot (needs authorization); `pandad` reflashes the shipped firmware.

## QA stages

- This round's code: focused review complete. Two-round QA not performed.
- Analysis-only work needs no QA.

## Ordered next steps

1. Session start per CLAUDE.md. Confirm the workspace state above.
2. Lane-drift investigation (above), first from the existing rlogs. Record the model and calibration identity. If on-device reads are needed: user confirms IP and inactive state; read-only only.
3. Write findings. If a change is warranted, propose it as a bounded change with criteria.
4. Later: the Hyundai 0x484 forwarding-rule round; keep watching the bus-1 startup fault and torqued.
