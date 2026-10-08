# Handoff: session 8 (2026-10-05): new drives, device errors, audio fix, torque-restore plan

Written 2026-10-05 ~22:25 EDT, near context compaction. Reconfirm everything at the next session start.

## Objective

Make sunnypilot drive the user's 2024 Genesis G70 well. Session 8:
1. pulled and analysed the partner's drives (stop-and-go plan);
2. investigated the device errors the partner reported;
3. built, reviewed and committed an audio start-up fix;
4. researched the car's own hands-off warning.

**Next session's main task:** reconstruct the torque-learning state (torqued) as it was at the end of route `0x16`, validate it, and restore it on the device. The user decided this; it needs device authorization at the time. Secondary: install the audio fix if not already done.

## User instructions and decisions (this session)

- Stop-and-go D-rule thresholds kept as written. The drives were done by the user's partner; coverage classified from data.
- **New rule (CLAUDE.md §3):** unneeded files may be deleted once no longer useful (verified duplicates, superseded temp/scratch; never promoted recordings or the only copy; note data deletions in the changelog).
- **New rule (CLAUDE.md §6):** read-only pulls from the device are unrestricted in scope (any file/log/param/command output). Other §6 rules unchanged. Secrets stay on the data root. Memory `video-pull-authorization` points to it.
- **Audio:** option B, a longer retry *plus* blocking engagement until audio works. Then: **"commit / deploy the audio fix"** (2026-10-05 ~22:15 EDT). Committed and dry-run; the device install was **not** run yet, because CLAUDE.md §6 requires the current address and inactive state to be reconfirmed, and the reboot needs its own explicit OK. Asked at the end of the session; see the device section.
- **Gyro / locationd error:** deferred unless it happens again.
- **Grasp warning:** research done (owner's manual). The user is considering the settings workflow. The user had *not* excluded replacing SCC11; that was my framing, corrected in the docs; assessed as not advisable.
- **Torque restore:** restore torqued to its state **at the end of route `0x16`** (before the `MOCK` route `0x17` wiped it). Use a new session: calculate, test, then restore.
- **Standing (memory):** video pulls authorized; tool installs on host/WSL authorized; no test re-runs for docs-only commits; durable rules go into CLAUDE.md the same session; reboots and device changes need explicit per-action authorization.

## Exact revisions

- Baseline `dev` @ `0b2c431d3a…` (unchanged).
- **`sunnypilot/` `dragal/custom` @ `c027a92857fab810f00a3d801ddda35f8e13c1da`** (local commit, not pushed). Parent `82f58a9a8c4af2f10d23d13fb1631deca98d4efd`, which is what the device runs. The commit is the audio fix (7 files, +395/−3).
- WSL test clone `~/src/sunnypilot`: detached at `c027a92857`, clean (fetched from the Windows clone, remote `win`).
- Outer repo `main` @ `606c36b` = `origin/main`, with **uncommitted** session 8 docs:
  - modified: `CLAUDE.md`, `CHANGELOG.md`, `docs/baseline.md`, `docs/local-storage.md`, `docs/findings/2026-10-04-g70-tune-0x484-first-drive.md`;
  - new findings: `2026-10-05-g70-sng-drives.md`, `2026-10-05-g70-device-errors.md`, `2026-10-05-soundd-audio-gate.md`;
  - new proposal: `docs/proposals/2026-10-05-soundd-audio-gate-deploy.md`;
  - this handoff and kickoff, and `docs/sessions/README.md`.
  - The user has not asked for an outer commit yet.

## Completed work and evidence (details in the findings docs)

1. **Pull** of 15 new routes `0x0f`–`0x1d`: rlog + fcamera + ecamera, 420 files, all sha256 MATCH, promoted with provenance. Gap: route `0x12` segment 8 is 0 bytes.
2. **Stop-and-go analysis** ([sng-drives](../findings/2026-10-05-g70-sng-drives.md)):
   - coverage: highway well covered; 2 engaged SNG episodes, 4 manual, little steady 20–35 mph;
   - SNG D1/D5: insufficient data;
   - LS pooled: D1 no, D5 no;
   - the plant model holds at 35+ mph on new held-out drives.
3. **Device errors** ([device-errors](../findings/2026-10-05-g70-device-errors.md), Follow-ups 1–5):
   - **soundd/micd crash:** the audio device opens 25–39 s after manager start; the 30 s retry expires on early starts (5 of 21). OS boot itself is normal (31 boot logs).
   - **`MOCK` route `0x17`:** sunnypilot was re-enabled ~2 s after disabling; the 1 s offroad flip broke the firmware query. As a result torqued/paramsd/lagd dropped their caches on the next drive (`card.py` `CarParamsPrevRoute`; restore keys in `torqued.py` L105–142, `paramsd.py`, `lagd.py`).
   - **locationd (route `0x11`):** a 16-sample gyro rejection burst plus very slow counter decay (~100 s). The x86 replay matches the device 42/42 s with the burst injected; the trigger is unexplained. The gyro-bias hypothesis was rejected.
   - **Grasp warning:** the car's own LFA/HDA was on, switched on by the Driving Assist (cruise MAIN) button on the highway. It ran its hands-off chain → HDA cancel → "Driver's grasp not detected. Driving speed will be limited", carried in forwarded SCC11. The slowdown is most consistent with a cut-in.
   - **Car LFA vs sunnypilot:** they ran in parallel; the panda blocked all camera LKAS11 frames, and the MDPS followed sunnypilot (correlation 0.96).
   - **Owner's manual (IK/2024):** LFA has no settings toggle (button-only). HDA can be deselected under Setup > Vehicle > Driver Assistance > Driving Convenience.
4. **Audio fix** `c027a92857` ([change record](../findings/2026-10-05-soundd-audio-gate.md)):
   - retry 30 × 3 s;
   - `/dev/shm` PID marker;
   - selfdrived raises `processNotRunning` until soundd's stream is open ("soundd (audio starting)").
   - **Validation:** 80/80 tests at `c027a92857` (log `s8-tests-c027-20261005-222234.log`); 7/7 mutations caught; focused adversarial review, no blockers, fixes applied.
   - **Deploy prep:** bundle sha256 `a8accee31bf2eda266f6676784878ad48dc31821df79f4353b8afa68fdc94158`; `install.sh` (bundle embedded, firmware hash must stay `206ea19c…`); WSL dry-run install and rollback OK (`sim-install-*.log`); `precheck_reboot.sh`, `postboot_check.sh`. All in `E:\DragalPilot\deploy\audio-gate-20261005\`.
5. **Tooling (data root):**
   - x86 test harness `cache\x86-openpilot\` (params, msgq, visionipc builds; `shim\sitecustomize.py`; `run_s8_tests.sh <tag> <unittest modules>`);
   - x86 locationd build `cache\x86-locationd\`;
   - WSL apt installs: `libeigen3-dev`, `libzmq3-dev`.

## Torque restore: what is known (for the next session)

- **Target state:** the torqued cache at the end of route `0x16` (2026-10-05 06:31–06:39 EDT; manual driving, so no new points, but the filter kept evolving).
  - Logged values at the end of `0x16` (`drive_extract` `ltp.*`): **calPerc 100, valid, latAccelFactor filtered 3.688 (raw 3.569), friction filtered 0.081, totalBucketPoints 7,723**, useParams.
  - torqued went valid during route `0x12` (~50 s in). laf 3.80 → 3.69 over routes `12`–`16`.
- **Why it must be reconstructed:**
  - The rlog `lateralTorqueParameters` messages are published without points (`torqued.py` L276–279, `with_points=DEBUG`, DEBUG off).
  - The points only exist in the param `LiveTorqueParameters` (cached every 240 frames ≈ 60 s with points, L281–283). The `MOCK` route overwrote it.
- **The device's current cache** (pulled 23:41Z, `E:\DragalPilot\device-logs\2026-10-05_s8_diag\data\params\d_tmp\LiveTorqueParameters`, decoded with `scratch\wsl\sng\s8_decode_ltp.py`):
  - valid False, calPerc 59, 7,003 points, laf filtered 4.0 (raw 4.12), friction 0.07 (raw 0.068), decay 50, version 1;
  - buckets −0.5..−0.3: 18/100 and −0.3..−0.2: 243/300 are the limiting ones.
- **Last full restart of torqued** (empty cache): the 2026-10-04 ~11:31 EDT deployment of `82f58a9a8c` (restore key changed with the new laf/friction). So the replay covers **all routes from route 8 (`11-41-17__00000008--03a89eb4e2`) through `0x16`, in driving order:**

  8, 9, a, b, c, d (undated, 8 s, between c and e), e, f, 10, 11, 12, 13, 14, 15, 16.

  - Rlogs for all are on the data root.
  - Known gaps: route 9 seg 4 and route `0x12` seg 8 are 0 bytes (route ends).
  - Earlier reconstruction (`scratch\wsl\torqued_buckets.py`, approximate) matched the logged totals within 0.2%.
- **Restore key** (`torqued.py` L137–142): (carFingerprint, lateralTuning type, friction, latAccelFactor, VERSION), compared between `CarParamsPrevRoute` and the current CarParams. It must still be (GENESIS_G70_2024, torque, 0.07, 4.0, 1). A future `MOCK` start would break it again.

## Open hypotheses / questions

- The locationd burst trigger (deferred).
- Whether deselecting HDA keeps the car's LFA off with the Driving Assist button (supervised test pending, user/partner).
- Stop-and-go weave: still not demonstrated or ruled out (needs the drive protocol's data).
- Why the audio device takes 25–40 s (not visible in the logs).

## Workspace, artifacts, running operations

- **No running operations. No SSH connection open.** No background agents.
- **Analysis:** `E:\DragalPilot\analysis\g70-sng-20261005\` (`drives\`, `lane\`, `regimes.json`, `sng_*.json`, `plant\`, `video\`, `diag\`, `locationd_replay\`).
- **Device data:** `E:\DragalPilot\device-logs\2026-10-05_s8_diag\` (swaglogs, boot logs, params, `/var/log`, command output).
- **Scripts:** `E:\DragalPilot\scratch\wsl\sng\` (`s8_*.py`, `run_s8_*.sh`, `build_x86_*.sh`), `scratch\device\{inventory,pull_new,pull_diag}_*.sh`, `scratch\promote_20261005s8.ps1`, owner's-manual pages in `scratch\manual-g70\`.
- **Logs:** `E:\DragalPilot\logs\s8-*`, `s5-s8-*`, `device-pull-20261005s8.*`, `promote-20261005s8.log`.
- **Staging:** `temporary\device-pull-20261005s8\` and `…s8b\` hold manifests only (tars deleted).

## Validation and limitations

- Audio fix:
  - validated offline only: unit/behaviour tests on x86 with a test-only native shim;
  - no full `update_events` run, no process replay, no on-device run;
  - device overhead of the marker read is to be measured during install (PC: 2.5–5 µs).
- Analyses: see the findings docs. Model results are labelled; alignment is GPS-verified for route `1a`.

## QA stages

- **Audio fix:** focused adversarial review done, fixes verified (80/80, mutations). Two-round QA not performed.
- **Analyses and docs:** not applicable.
- **Torque reconstruction tool (next session):** at least a focused review before the restore.

## Device state and SSH

- Last observed **2026-10-05T23:41:40Z**: `192.168.98.104`, indoors and not in the car (user), `IsOffroad=1`, `IsEngaged=0`, `GitCommit=82f58a9a8c`, uptime 1:12, no other SSH session.
- Connections this session: 22:35Z pull, 23:40Z inventory, 23:41Z diagnostics pull. All closed; read-only.
- **Installed:** `82f58a9a8c` (the audio fix is NOT installed). Firmware file `206ea19c…`.

## Ordered next steps

1. **Session start:**
   - read the kickoff files;
   - confirm the workspace: outer `main` with the uncommitted docs; `dragal/custom` @ `c027a92857`; WSL clone clean at `c027a92857`;
   - confirm E: (UniqueId, writable, free space).
2. **Audio install (if the user confirms the device address and inactive state):** `install.sh` over one SSH connection → verify HEAD `c027a92857`, clean, firmware unchanged, overhead line. Then the reboot **only with explicit authorization at the time** (`precheck_reboot.sh`), then `postboot_check.sh`. Record it in the proposal's deployment record and the changelog.
3. **Torque reconstruction (offline):**
   1. Write a replay that runs the checkout's `TorqueEstimator` (`openpilot/selfdrive/locationd/torqued.py`, unmodified, via the x86 shim) over the routes listed above, reproducing `main()`:
      - poll on `deviceMotion`;
      - only the latest message per subscribed service (`carControl`, `carOutput`, `carState`, `extrinsicsCalibration`, `deviceMotion`, `lateralDelay`) per iteration, gated on all checks;
      - `TorqueEstimatorExt.update_use_params`;
      - publish every 5 frames;
      - cache `get_msg(with_points=True)` every 240 frames.
   2. At each route start, construct a new estimator that restores from the previous route's last cache and that route's CarParams, through the real restore path. Patch `Params` to serve `CarParamsPrevRoute` / `LiveTorqueParameters` from memory; never touch the device.
   3. **Validate per route** against the logged `lateralTorqueParameters`: totalBucketPoints, calPerc, valid/useParams, raw and filtered laf/friction/offset, decay. Define the tolerances before running. Report gaps (the 0-byte segments).
   4. **Output:** the serialized `LiveTorqueParameters` (Event bytes, version 1, points) as cached at the last 240-frame mark of route `0x16`, plus its decoded summary, under `E:\DragalPilot\analysis\g70-torqued-restore-<date>\`.
   5. Check that the output decodes with the checkout's own restore code, i.e. `TorqueEstimator.__init__` with it as the cache and the current CarParams as both CP and `CarParamsPrevRoute`, gives the expected filtered values and calPerc 100.
   6. **Focused adversarial review** of the replay and the evidence.
4. **Restore proposal and approval:**
   - What changes: from the next drive, the controller uses laf ~3.69 / friction ~0.081 instead of 4.0/0.07.
   - Backup: the current `LiveTorqueParameters`, `CarParamsPrevRoute`, `CarParamsPersistent`.
   - Procedure: device offroad (torqued is onroad-only, so no race); write via the device's `Params().put("LiveTorqueParameters", …)`, which is atomic; verify sha256; check `CarParamsPrevRoute` still matches the restore key.
   - Rollback: put the backup back.
   - Verification on the next drive: swaglog "restored torque params from cache"; `lateralTorqueParameters` valid and calPerc 100 from the start.
   - Ask for explicit authorization; one SSH connection; no reboot needed.
5. Update the changelog, `docs/sessions/README.md`, and write a new handoff and kickoff at the end.
6. **Later:** the HDA-deselected supervised drive and log pull; the outer docs commit when the user asks; and, still carried over, the Hyundai 0x484 forwarding-rule round.
