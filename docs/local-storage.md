# Local data storage

Agreed with user on 2026-10-03. This file is the authority for where non-source data lives.

## Data root

| Item | Value |
|---|---|
| Path | `E:\DragalPilot` (Git Bash: `/e/DragalPilot`). The user specified `E:\dragalpilot`; NTFS is case-insensitive and the pre-existing folder is spelled `DragalPilot`. |
| Volume | Label `Data1`, NTFS, fixed disk, `\\?\Volume{daa460f7-6194-4c7c-b122-387d13a3adff}\` |
| Disk | Disk 1, `QEMU QEMU HARDDISK` (virtual disk), bus SAS, no serial reported |
| Capacity at setup | 274,860,077,056 bytes total, ~274.75 GB free (2026-10-03) |
| State at setup | Folder existed and was empty (0 files). Layout created and write test passed on 2026-10-03. |
| Recording timezone | `America/New_York` (route grouping; the UTC offset is always recorded too) |

The data root is outside every Git checkout. Source checkouts are at `C:\Users\dre\Documents\DragalPilot\dragalpilot` (outer repo) and `...\dragalpilot\sunnypilot` (upstream clone).

## Pre-flight check (before any data operation)

1. Volume `E:` is present and its UniqueId matches the value above:
   `Get-Volume -DriveLetter E | Select UniqueId,SizeRemaining`
2. `E:\DragalPilot` exists and is writable (create and delete a probe file in `temporary/`).
3. There is enough free space for the planned operation.
4. If any check fails, **stop data work** and report. Never fall back to C:, the checkout, or another disk.

## Layout

```text
E:\DragalPilot\
  recordings/YYYY/MM/DD/HH-MM-SS__<route-id>/
    rlogs/segment-NNN/
    videos/front-narrow/segment-NNN/
    videos/front-wide/segment-NNN/
    videos/driver/segment-NNN/
    metadata/
  recordings/undated/<route-id>/   same inner layout; start time unknown (see Recording rules)
  analysis/       derived datasets, plots, reports (per-investigation subfolders)
  cache/          reusable decoded/converted data, tool caches
    wsl/Ubuntu-24.04/ext4.vhdx   WSL test environment disk (venv, uv cache, test clone; see docs/baseline.md)
  scratch/        throwaway working files
  temporary/      partial transfers, staging before verification
  deploy/         deployment artifacts (bundles, dry-run logs, device pre/post-state) per deployment
  logs/           tool/transfer/clone logs (added at setup: keeps command logs out of the repo and out of the recordings tree)
  device-logs/    non-route device data pulled read-only (swaglogs, boot/crash logs, params, /var/log, command output), one
                  folder per pull: YYYY-MM-DD_<session>_<tag>/ with the device paths kept, plus the manifest and verify files.
                  May contain secrets (tokens in params): never copy into the repo or docs. Added 2026-10-05.
```

`logs/`, `deploy/` and `recordings/undated/` depart from the kickoff layout. The reasons are given beside them above.

## Recording rules

- **RLOGS only, never QLOGS.** If an rlog is unavailable, record the gap in `metadata/` and report it. Do not substitute the qlog.
- **Rlogs and both road-camera videos are pulled together** (user rule, 2026-10-04; CLAUDE.md §3).
  - **What:** every pull of a route's rlogs also pulls `fcamera.hevc` and `ecamera.hevc` for the same segments, in the same connection.
  - **Where:** they are promoted into the same route folder (`rlogs/segment-NNN/`, `videos/front-narrow/segment-NNN/`, `videos/front-wide/segment-NNN/`), with one provenance record covering all three.
  - **Gaps:** a video missing on the device (deleted, not recorded, 0 bytes) is listed per segment and camera in `metadata/`. The rlogs are still promoted.
  - `qcamera.ts` is never pulled. `dcamera.hevc` only when recorded (`RecordFront=1`) and useful.
- **Route folder** uses the route **start** time in America/New_York, not the download time: `recordings/YYYY/MM/DD/HH-MM-SS__<route-id>/`.
  - A route that crosses midnight stays in its start-date folder.
  - Because `<route-id>` is in the folder name, two routes with the same local time (e.g. the repeated hour when DST ends) cannot collide.
  - **Undated routes** (no GPS fix and an unsynced device clock, so the start time can't be determined) go to `recordings/undated/<route-id>/` with the same inner layout. `metadata/` records whatever time bounds can be inferred and how. Never guess a date to fit the dated tree. If the time is established later, move the folder into the dated tree and record the method. Convention added 2026-10-03 (user delegated the choice).
  - `metadata/` records the original timestamp, the UTC offset, exact route and segment identifiers, the device identifier when needed, and how the start time was determined.
- **Segments and cameras** are kept separate. Original compression and filenames are preserved.
  - The mapping from camera to filename (e.g. which file is the narrow road, wide road, and driver camera) **must be verified against the pinned sunnypilot source before first use**, and the result recorded here. Status: **verified 2026-10-04** against `openpilot/system/loggerd/loggerd.h` L98–160 @ `7e9d0755d9`: `fcamera.hevc` → `videos/front-narrow/`, `ecamera.hevc` → `videos/front-wide/`, `dcamera.hevc` → `videos/driver/` (recorded only when `RecordFront=1`). `qcamera.ts` is a low-res copy of the narrow road view and is not pulled.
- **Provenance:** for each recording, `metadata/` holds the source (device or connect), transfer method, date, file sizes, hashes where available, and a list of missing segments and cameras. Missing data is recorded as missing, never assumed complete.
- **Transfers** land in `temporary/` first. Each file is checked for completeness (size and hash where possible) before it is promoted into `recordings/`. Existing recordings are never overwritten blindly, and raw data is not duplicated without reason.
- **Cleanup** (user rule, 2026-10-05; CLAUDE.md §3): files that are no longer useful may be deleted without asking, e.g. a staging `pull.tar` and staged copies once the promoted files are hash-verified, or superseded scratch/temp files. Small manifests and logs (`pull.log`, `remote.sha256`, `local-verify.txt`) are kept as provenance. Promoted recordings and the only copy of anything are never deleted this way. Data-file deletions are noted in the changelog.

## Tool configuration

- Set temp and cache variables per command, pointing into the data root. Example (Git Bash):
  `TMP=/e/DragalPilot/temporary TEMP=/e/DragalPilot/temporary TMPDIR=/e/DragalPilot/temporary XDG_CACHE_HOME=/e/DragalPilot/cache <cmd>`
- Give tools explicit output paths. Watch for tools that ignore these variables (test runners, submodule build scripts, pip/uv caches) and confirm where they actually write.
- Do not change machine-wide configuration to achieve this.

## Before every commit

Inspect `git status` in the outer repo, in `sunnypilot/`, and in the relevant submodules for stray data or generated artifacts. `.gitignore` is a backstop only.
