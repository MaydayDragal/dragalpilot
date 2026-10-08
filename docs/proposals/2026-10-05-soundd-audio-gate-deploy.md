# Deployment proposal: soundd/micd longer audio retry + engagement blocked until audio is ready (2026-10-05)

**Status: DEPLOYED 2026-10-05 22:31–22:35 EDT: installed `c027a92857`, rebooted with the user's explicit OK, post-boot check passed (see the deployment record). Check drives 2026-10-06 (8 routes): gate works as designed, no soundd/micd crash (see the check-drive record).** Originally needed approval for:
- the commit on `dragal/custom`;
- the install;
- the reboot, confirmed separately at the time.

Basis:
- [change and review record](../findings/2026-10-05-soundd-audio-gate.md);
- [device-errors findings](../findings/2026-10-05-g70-device-errors.md).

## 1. The change

- **What:** one commit on `dragal/custom` on top of the installed `82f58a9a8c`, containing:
  - 5 Python files (one new: `openpilot/selfdrive/ui/soundd_ready.py`);
  - 2 new test files.
- **What it doesn't touch:** opendbc, panda safety and firmware, native code, params keys and cereal schema are all unchanged, so the panda is not reflashed. CarParams are unchanged, so torqued/paramsd/lagd caches are kept.
- **Effect on the car:**
  1. soundd and micd wait up to ~90 s for the audio device instead of 30 s.
  2. Until soundd has opened its audio stream, engaging (cruise or MADS lateral) is refused with "Process Not Running: soundd (audio starting)". Normally that's the first 25–40 s after starting the car. After that, everything behaves as today.
  3. If the audio never comes up within ~90 s, soundd still crashes and today's "Process Not Running: soundd" applies.
- **How it's deployed:** a git bundle of the commit, verified by sha256 on the device, then fetch and fast-forward. That is the same mechanism as the two earlier deployments.

## 2. Validation done (offline; no physical evidence yet)

- 80 tests OK on x86 (47 existing + 33 new), lint clean, 7/7 mutations caught.
- Focused adversarial review: no blockers or majors; all justified minor/info findings fixed.
- Details in the change record.
- **Not validated:** on-device behaviour, process replay, a full `update_events` run.

## 3. Resource impact

- **selfdrived:** while waiting (≤ ~40 s per drive), one small file read every 10 frames (10 Hz). The reviewer measured ~38–120 µs per read on x86. Nothing after the latch.
- **soundd:** one 5-byte write per start.
- **Before any active use:** measure the read cost on the device while it's inactive. One read-only timing loop over the marker path, in the install connection.

## 4. Device procedure (each step reconfirmed at the time; device inactive, current address confirmed, no other SSH session)

1. **Commit** on `dragal/custom` (Windows clone) with a WIP message.
   - Build the bundle under `E:\DragalPilot\deploy\audio-gate-20261005\` and record its sha256.
   - Dry-run install and rollback in a throwaway WSL clone first.
2. **Install (one SSH connection):**
   - pre-state: HEAD `82f58a9a8c`, clean, `IsOffroad=1`, `DisableUpdates=1`;
   - copy the bundle, check sha256, `git bundle verify`, fetch, fast-forward;
   - verify HEAD and a clean tree;
   - time the marker read (§3).
   - No reboot in this step.
3. **Reboot (separate explicit authorization).** The manager pre-imports Python modules, so the change takes effect after a restart. No panda flash is expected (firmware unchanged).
4. **Post-boot check (read-only):** `GitCommit`, `IsOffroad`, clean tree.
5. **Check drive (user):** start the car normally.
   - Expected: an engage attempt in the first ~25–40 s may show "Process Not Running: soundd (audio starting)"; after that, engagement works and alerts are audible.
   - Then pull logs: the swaglog shows `selfdrived: soundd audio stream ready at frame N`, and the rlogs show the event timeline.

## 5. Rollback

- `cd /data/openpilot && git checkout 82f58a9a8c` (or `dragal/custom~1`), then a reboot (explicit authorization).
- No firmware involved, and no cache invalidation.

## 6. Approvals requested

1. Commit the change on `dragal/custom` and prepare the bundle (no device access).
2. Install per §4.2 when the device is inactive (address and state confirmed at the time).
3. The reboot, confirmed separately at the time.

## Preparation record (2026-10-05)

- **Commit:** `dragal/custom` @ `c027a92857fab810f00a3d801ddda35f8e13c1da` (parent `82f58a9a8c`; local, not pushed). 80/80 tests at this exact revision (`s8-tests-c027-20261005-222234.log`).
- **Bundle:** `E:\DragalPilot\deploy\audio-gate-20261005\dragal-custom-c027a92857.bundle`, sha256 `a8accee31bf2eda266f6676784878ad48dc31821df79f4353b8afa68fdc94158`, prerequisite `82f58a9a8c`, embedded in `install.sh`.
- **Dry run** (WSL throwaway clone, `sim_install.sh`, log `sim-install-*.log`):
  - install → `c027a92857`, clean, firmware file unchanged `206ea19c…`;
  - overhead probe 2.5–5 µs per read (PC);
  - rollback → `82f58a9a8c`, clean.
- **Scripts for the device:** `install.sh` (no reboot), `precheck_reboot.sh` (expects HEAD `c027a92857`, firmware `206ea19c…`), `postboot_check.sh`.

## Deployment record

- **Install (§4.2), 2026-10-05 22:31 EDT (02:31:53–02:31:55Z).** User confirmed the address `192.168.98.104`, the device inactive indoors, and no other SSH session. One SSH connection, `install.sh`, ssh exit 0. Log: `E:\DragalPilot\logs\device-install-audio-gate-20261005-223151.log`.
  - Pre-state: `IsOffroad=1`, `IsOnroad` absent, `IsEngaged=0`, HEAD `82f58a9a8c`, branch `dragal/custom`, clean, `DisableUpdates=1`, firmware file `206ea19c…`. Only this session's sshd was listed.
  - Bundle sha256 `a8accee3…4158` matched; `git bundle verify` OK; fast-forward to `c027a92857`; clean; firmware file unchanged; bundle removed from `/data/tmp`.
  - Overhead (§3), measured on the inactive device: 49.0 µs/read for a missing file, 99.4 µs/read for a small existing file.
- **Reboot (§4.3), user-authorized ("Ok to restart"), 2026-10-05 22:33 EDT.** `precheck_reboot.sh` over one SSH connection: offroad, HEAD `c027a92857`, clean, `DisableUpdates=1`, no staged update pending (`.git` newer than `.overlay_init`), firmware file `206ea19c…` → all checks passed, reboot issued 02:33:13Z. Log: `E:\DragalPilot\logs\device-reboot-audio-gate-20261005-223311.log`.
- **Post-boot (§4.4), read-only**, 02:35:40Z (ping back 52 s after the reboot; `E:\DragalPilot\logs\device-postboot-audio-gate-20261005-223537.log`):
  - `GitCommit=c027a92857`, branch `dragal/custom`, clean; `IsOffroad=1`; `DisableUpdates=1`; no `updated` process; no `old_openpilot`; firmware file unchanged `206ea19c…`; `PandaHeartbeatLost` absent; `soundd_ready.py` present.
  - The marker `/dev/shm/soundd_stream_ready` is absent, as expected offroad (soundd runs onroad only). The script's exit status 2 comes from that `ls`.
  - **Panda (observation):** pandad needed 41 connect retries (SPI NACK) and found the panda in DFU/bootstub. It ran the recovery, then reported "version: bootstub … expected 5b8d2b3346f6e61e", "firmware out of date", "Done flashing", and the native pandad connected over SPI (`device-postboot-pandad*-20261005-*.log`). The image flashed is the unchanged firmware file (expected signature `5b8d2b33…`, the one deployed in session 3). The session 8 diagnostic swaglogs show the same bootstub → reflash sequence on at least two earlier boots and 28–43 retries on others, so this is existing device behaviour, not caused by this Python-only change.
- **Active:** the audio gate runs from the next onroad start. **Pending:** the check drive (§4.5) and a log pull afterwards.

## Check-drive record (2026-10-06, session 10)

**Result: works as designed on all 8 drives; no soundd/micd crash.** On-device behaviour evidence from logs only. Whether alerts were *audible* is not in the logs (no audio is recorded); that needs the driver's report.

- **Data:** routes `0x1e`–`0x25` (2026-10-06 06:34–20:48 EDT), all `c027a92857`, each a cold boot. One read-only pull 2026-10-07 02:24:57–02:31:55Z (user confirmed `.104`, inactive, indoors, no SSH session).
  - Recordings: `recordings/2026/10/06/`.
  - Swaglogs etc.: `device-logs/2026-10-06_s10_diag/`.
  - Analysis: `analysis/g70-s10-checkdrive-20261006/`.
- **swaglog (files 450–711), per boot:** `soundd stream started`, `micd stream started`, then `selfdrived: soundd audio stream ready at frame N`.
  - N is 290–2260, i.e. 2.9–22.6 s after selfdrived starts.
  - soundd took 7.2–31.3 s from start to an open stream on the 7 measurable boots (`s8_audio_timing.py`; one boot unmeasurable because of a clock jump).
  - No `get_stream failed`, no soundd/micd crash. No new crash files in `/data/community/crashes` (newest is still 2026-10-05 06:41).
- **rlogs (`drive_extract.py`, `s10_audio_rlog.py`):**
  - `processNotRunning` appears only 11.1–31.0 s after the route starts, and not at all on `0x24` (audio was ready before the first events).
  - managerState shows soundd/micd never down.
  - **Gate exercised once:** route `0x23`, an engage attempt at 14.0 s was refused with "Process Not Running: soundd (audio starting)" (noEntry, 14.0–17.0 s). Engagement at 186 s worked normally.
  - No other process alerts and no soft-disables.
- **Route `0x21` (observation + source-based hypothesis):** soundd needed 31.3 s. That is beyond the old 10 × 3 s retry window, so the old code would probably have crashed on this start (as on routes `16`/`18`).
- **Warnings:** 2 × `soundd stream over/underflow: output underflow` (L30). One also appears in the session 8 swaglogs, so it is not new.
- **Overhead:** not re-measured. The selfdrived check runs only until the latch (≤ 31 s on these drives).
