# Handoff: session 9 (2026-10-05/06): audio fix installed, torqued reconstructed and restored

Written 2026-10-06 ~06:35 EDT at about 270k tokens of context (handoff point, CLAUDE.md §7). Reconfirm everything at the next session start.

## Objective

Make sunnypilot drive the user's 2024 Genesis G70 well. This session:
1. installed the soundd/micd audio fix;
2. reconstructed torqued's learned state at the end of route `0x16` offline;
3. restored it on the device.

Both device changes now need a check drive and a log pull.

## User instructions and decisions (this session)

- **Audio install:** confirmed address `.104`, device inactive indoors, no SSH sessions → install. Then "Ok to restart" → reboot (done).
- **"Yes, begin"** the torqued reconstruction.
- **Restore target: option A** (end of `0x16`), with authorization to install and to reboot if needed ("A. if complete, go ahead and install on the device and reboot when needed. device is indoors, on .104 and no ssh sessions are active").
  - My recommendation was B (merge with the device's post-wipe points); the user chose A.
  - Done; no reboot needed.
- **Standing (memory / CLAUDE.md):** video pulls and tool installs authorized; read-only device pulls unrestricted; unneeded files may be deleted (§3); no test re-runs for docs-only commits; durable rules into CLAUDE.md the same session; device changes and reboots need explicit per-action authorization.
- **Outer docs commit:** not requested yet; everything since `606c36b` is uncommitted.

## Exact revisions

- Baseline `dev` @ `0b2c431d3a…` (unchanged).
- `sunnypilot/` `dragal/custom` @ **`c027a92857`** (local, not pushed), clean. WSL clone `~/src/sunnypilot` at `c027a92857`, clean.
- **Device:** `c027a92857` (audio fix), firmware file `206ea19c…` (panda signature `5b8d2b33…`), `LiveTorqueParameters` sha256 `2883e5da…` (restored).
- Outer `main` @ `606c36b` = `origin/main`, with **uncommitted** session 8 + 9 docs:
  - modified: `CHANGELOG.md`, `CLAUDE.md`, `docs/baseline.md`, `docs/local-storage.md`, `docs/sessions/README.md`, `docs/findings/2026-10-04-g70-tune-0x484-first-drive.md`;
  - new: findings `2026-10-05-*` (3) and `2026-10-06-g70-torqued-reconstruction.md`;
  - new: proposals `2026-10-05-soundd-audio-gate-deploy.md` and `2026-10-06-g70-torqued-restore.md`;
  - new: the session 8 and 9 handoff/kickoff pairs.

## Completed work and evidence

1. **Audio fix installed and active** ([proposal](../proposals/2026-10-05-soundd-audio-gate-deploy.md) deployment record).
   - `install.sh` 02:31Z: ff `82f58a9a8c` → `c027a92857`, clean, firmware unchanged; marker-read overhead 49–99 µs on the device.
   - Guarded reboot 02:33Z.
   - Post-boot check OK.
   - Panda came up in bootstub and pandad reflashed the same image. The session 8 swaglogs show the same on earlier boots, so it's existing behaviour.
2. **Torqued reconstruction** ([findings](../findings/2026-10-06-g70-torqued-reconstruction.md)). Data: `E:\DragalPilot\analysis\g70-torqued-restore-20261005\`. Scripts: `E:\DragalPilot\scratch\wsl\torqued\`.
   - Replay of the unmodified `torqued.main()` over routes 8–0x16. Criteria in `TOLERANCES.md`, fixed before comparing, plus Amendments 1 and 2.
   - **v1 failed.** v2b: schedule locked to the logged publish times, 0.7 ms receipt delay calibrated on route 8's first 400 s.
   - **v2b passes** everything except **D1/C1 and the output count**: 7,722 vs 7,723 points.
   - Post-hoc held-out check (routes 0x18–0x1d vs the device's actual cache): 6,702 of 7,003 points exact; full-set fit laf 4.1242 vs 4.1239.
   - Restore check passes (v2b file).
   - **Focused adversarial review done:** F1 (merge option) escalated → user chose A; F2 check run; F3 fixed.
3. **Torqued restore on the device** ([proposal](../proposals/2026-10-06-g70-torqued-restore.md) deployment record).
   - Attempt 1 aborted before writing: `python3` over SSH lacks numpy. Fixed to `/usr/local/venv/bin/python` (noted in `docs/baseline.md`).
   - Attempt 2 10:25:42Z: backups captured; restore key OK; write + byte-equal readback; valid, calPerc 100, 7,722 points, laf 3.688 / friction 0.0808 / offset −0.072, decay 250.
   - Backups: `E:\DragalPilot\deploy\torqued-restore-20261006\backup-device-20261006T102542Z\` (the previous cache `5b876dd8…`, 7,003 post-wipe points).

## Open hypotheses / questions

- Whether the restored params help or hurt driving: no evidence yet (this is a record of earlier use, not of performance).
- Option B (merge) remains available from the same files if wanted later.
- Carried over: HDA-deselected supervised test; stop-and-go weave (needs protocol data); locationd burst trigger; why audio takes 25–40 s; the 0x484 forwarding-rule round.

## Running operations, SSH, device

- **No running operations, no SSH connection open, no background agents.**
- **Device last observed 10:25:46Z:** `.104`, `IsOffroad=1`, `IsEngaged=0`, `GitCommit=c027a92857`, `DisableUpdates=1`, indoors.
- **SSH connections this session** (all serialized, closed):
  - 02:31Z install (write);
  - 02:33Z reboot;
  - 02:35–02:40Z post-boot and pandad log reads (4, read-only);
  - 10:24Z restore attempt 1 (aborted);
  - interpreter check (read-only);
  - 10:25Z restore attempt 2 (write).

## Validation limits and QA stages

- **Audio fix:** offline tests + focused review (session 8); post-boot check; no on-device behaviour evidence yet.
- **Torqued:** offline replay, a focused review, and a byte-equal on-device write/readback. The point count fails the pre-registered criterion by 1. Two-round QA not performed for either.

## Artifacts

- `deploy\audio-gate-20261005\`; `deploy\torqued-restore-20261006\` (`restore.sh`, template, `sim_restore.sh`, sim logs, backups, payload copy).
- Logs: `logs\device-install-audio-gate-*`, `device-reboot-*`, `device-postboot-*`, `device-torqued-restore-*`, `s9-*`.
- Scratch: `temporary\s9-restore-sim\`, `s9-review\` (review scratch), `s9-tmp\` (empty). All disposable.

## Ordered next steps

1. **Session start:** read the kickoff files. Confirm the outer repo (uncommitted docs), `dragal/custom` @ `c027a92857`, the WSL clone, and E: (UniqueId `daa460f7…`, writable, free space).
2. **After the user's next drive:** the user confirms address and state; then a read-only pull (rlogs + both videos + swaglog) of the new route(s). Check:
   - **Audio:** swaglog `selfdrived: soundd audio stream ready at frame N`; any "Process Not Running: soundd (audio starting)" only in the first ~40 s; no soundd crash.
   - **Torqued:** swaglog "restored torque params from cache"; first `lateralTorqueParameters` totalBucketPoints 7,722, valid, calPerc 100, decay ≈ 250, laf ≈ 3.688. The start must fingerprint G70 (not MOCK).
3. Record the results in both proposals and the changelog. Rollback paths are in each proposal.
4. Outer docs commit when the user asks.
5. Carried over (session 8 list): HDA-deselected supervised drive; stop-and-go protocol data; the 0x484 forwarding-rule round. Optionally delete `temporary\s9-restore-sim`, `s9-review` and `s9-tmp` (disposable; note in the changelog).
