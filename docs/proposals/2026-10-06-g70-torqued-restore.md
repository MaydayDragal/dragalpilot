# Proposal: restore torqued's learned state to the end of route 0x16 (2026-10-06)

**Status: DEPLOYED 2026-10-06 06:25 EDT (option A, user-chosen and authorized: "A. if complete, go ahead and install on the device and reboot when needed"). No reboot needed. Check drives 2026-10-06 (8 routes): restore confirmed (7,722 points, valid, laf 3.688 at the first start), learning continued to 8,576 points.** See the deployment and check-drive records at the end.

Basis: [reconstruction findings](../findings/2026-10-06-g70-torqued-reconstruction.md) (validation partly fails on the point count; read §4 there before deciding).

## 1. The change

- **What changes:** one device param, `LiveTorqueParameters`, replaced with the reconstructed cache:
  - file `E:\DragalPilot\analysis\g70-torqued-restore-20261005\LiveTorqueParameters_end_route16_v2b.bin`;
  - sha256 `2883e5dad34406447d4f2076f4fe2ab5e04f6a590f1490e341ba223690fa6adf`.
- **What doesn't change:** code, other params, firmware, CarParams.
- **When it takes effect:** at the next onroad start. torqued restores it if `CarParamsPrevRoute` still matches the restore key `(GENESIS_G70_2024, torque, 0.07, 4.0, 1)`.
- **Effect on driving:** controls apply the filtered values whenever the message passes its checks (`controlsd.py` L93–100).

  | Value | Today (post-MOCK cache, invalid, so the offline values) | After the restore |
  |---|---|---|
  | latAccelFactor | 4.0 | 3.688 (−7.8%) |
  | friction | 0.07 | 0.0808 |
  | latAccelOffset | 0 | −0.072 |

  These are the values the car used at the end of route 0x16. That is a record of earlier use, not evidence that they are better.
- **What is given up:** the learning since the wipe (routes 0x18 onward; 7,003 points, not valid, as pulled 2026-10-05). The script backs it up.

## 2. Validation (offline)

- Reconstruction with the checkout's unmodified torqued over routes 8–0x16. Criteria were fixed before comparing.
  - **Passes:** decay, calPerc, valid flags, filtered values (≤ 0.0016 laf), raw-fit statistics, cache timing.
  - **Fails:** the point count, 7,722 vs 7,723. The fit of the point set equals the device's within sampling noise (laf +0.0009 ± 0.0011).
- **Restore check** with the real restore path and the device's `CarParamsPersistent`: restored, valid, calPerc 100. A mismatched key or a missing PrevRoute means no restore.
- **Focused adversarial review:** see the findings doc §6.

## 3. Resource impact

- One-off, offroad only: a short Python decode and one ~170 KB param write. No processes are added and nothing runs while driving.

## 4. Device procedure (one SSH connection; device inactive and offroad; current address confirmed; no other SSH session)

Script: `E:\DragalPilot\deploy\torqued-restore-20261006\restore.sh` (payload embedded). It runs these steps in order:

1. **Pre-state:** `IsOffroad=1`, not onroad, torqued not running, HEAD `c027a92857`.
2. **Backup:** the current `LiveTorqueParameters`, `CarParamsPrevRoute` and `CarParamsPersistent` are printed as sha256 + base64 into the log on the data root, before any write.
3. **Restore-key check:** the device's own code decodes both CarParams params and must find `(GENESIS_G70_2024, torque, 0.07, 4.0, 1)`.
4. **Payload:** sha256 must match.
5. **Write:** offroad is rechecked, then `Params().put("LiveTorqueParameters", data, block=True)`. The script reads it back, compares it byte for byte, and decodes it (valid, calPerc 100, 7,722 points, laf 3.688).
6. **No reboot.**

## 5. Verification on the next drive (user drives normally; logs pulled afterwards)

- **swaglog:** "restored torque params from cache" from torqued.
- **First logged `lateralTorqueParameters`:**
  - totalBucketPoints 7,722;
  - calPerc 100, valid;
  - decay ≈ 250;
  - latAccelFactorFiltered ≈ 3.688.
- **Risk:** if that start fingerprints as `MOCK` (the 0x17 situation), the key doesn't match. torqued then starts fresh and overwrites the cache, and the restore is lost (re-run it from the same file).

## 6. Rollback

- Same procedure, writing the backed-up `LiveTorqueParameters` bytes (from the log) back with `Params().put`, offroad.
- If the backup was absent, `Params().remove("LiveTorqueParameters")`.
- No reboot.

## 7. Approval requested

1. Run `restore.sh` once, with the device inactive (address and state confirmed at the time).

## Deployment record (2026-10-06)

- **Decision:** the user chose **option A** (end of 0x16) over option B (merge, recommended) and authorized the install, plus a reboot if needed. The user confirmed the device at `192.168.98.104`, indoors, with no SSH sessions.
- **Build:** `restore.sh` (payload sha256 `2883e5da…`, embedded copy verified).
- **Dry runs in WSL** (`sim_restore.sh`, logs `sim-restore-*.log`): restore + readback, and the rollback (backup bytes written back exactly). The first dry run passed. The device run then exposed a gap the dry run couldn't (below), so a second dry run followed the fix.
- **Attempt 1** (one SSH connection, 10:24:58–10:24:59Z; `E:\DragalPilot\logs\device-torqued-restore-20261006-062454.log`):
  - **aborted before any write**, exit 9, at the restore-key check;
  - plain `python3` over SSH is `/usr/bin/python3` without numpy;
  - backups were captured, and their hashes equal the session 8 pull.
- **Read-only check** (one connection): the manager runs `/usr/local/venv/bin/python` (→ python 3.12, numpy 2.5.1). The script now uses it (`PY`, overridable for the dry run); dry run repeated, OK.
- **Attempt 2** (one SSH connection, 10:25:42–10:25:46Z; `E:\DragalPilot\logs\device-torqued-restore-20261006-062539.log`), ssh exit 0:
  - **Pre-state:** `IsOffroad=1`, `IsOnroad` absent, `IsEngaged=0`, `GitCommit=c027a92857`, `DisableUpdates=1`, torqued not running, only this session's sshd.
  - **Backups:** `LiveTorqueParameters` `5b876dd8…` (168,192 B), `CarParamsPrevRoute` `1227321e…`, `CarParamsPersistent` `0b35e13d…`. Extracted and hash-verified to `E:\DragalPilot\deploy\torqued-restore-20261006\backup-device-20261006T102542Z\`.
  - **Restore key:** OK on both (`GENESIS_G70_2024, torque, 0.07, 4.0, 1`).
  - **Payload:** sha256 matched.
  - **Write:** `Params().put(..., block=True)`; readback equal; valid, calPerc 100, 7,722 points, laf 3.68845 / friction 0.080771 / offset −0.072296, decay 250, version 1. Param file sha256 `2883e5da…`.
- **Reboot:** not performed and not needed (torqued is onroad-only and reads the cache at its next start).
- **Rollback:** offroad, write `backup-device-20261006T102542Z/LiveTorqueParameters` back with `Params().put` using `/usr/local/venv/bin/python`.
- **Pending:** the check drive and a log pull (§5): swaglog "restored torque params from cache"; first `lateralTorqueParameters` 7,722 points, valid, decay ≈ 250, laf ≈ 3.688.

## Check-drive record (2026-10-06, session 10)

**Result: the restore took effect.** Every §5 check passes. This shows the restore happened, not that the values improve driving.

- **Data:** routes `0x1e`–`0x25` (2026-10-06 06:34–20:48 EDT; the first started 9 min after the restore), pulled read-only 2026-10-07 02:24–02:31Z. Analysis: `analysis/g70-s10-checkdrive-20261006/`, log `logs/s10-torqued-*.log` (`s10_torqued_check.py`).
- **Fingerprint:** `GENESIS_G70_2024` (exact, `fw_count` 10) on all 8 starts, so there was no MOCK start and the restore key held.
  - `CarParamsPersistent` changed hash (`0b35e13d…` → `055ff2cb…`), but only the order of `carFw` entries differs. The restore key `(GENESIS_G70_2024, torque, 0.07, 4.0)` is identical (`s10_cp_diff.py`).
- **swaglog:** `restored torque params from cache` from torqued on all 8 boots.
- **First `lateralTorqueParameters` of route `0x1e`** (9.25 s after the route starts):
  - valid, calPerc 100, useParams, version 1;
  - totalBucketPoints **7,722**;
  - decay **250**;
  - latAccelFactorFiltered **3.68844**, friction 0.08077, offset −0.0723.

  These equal the restored file (3.68845 / 0.080771 / −0.072296).
  - The first 7 messages carry `Event.valid` False. The same happens at the starts of `0x16` and `0x1d` (before the restore), so it is start-up behaviour; controls use the offline values for that ~1 s.
- **Learning continued from the restored state:** every route's first message equals the previous route's last.

  | | Points | laf filtered | friction | offset |
  |---|---|---|---|---|
  | Start of `0x1e` | 7,722 | 3.688 | 0.0808 | −0.072 |
  | End of `0x25` | 8,576 | 3.547 | 0.0816 | −0.054 |

  - Valid and calPerc 100 throughout.
  - The device's cache at the pull (`8a843369…`, 205,944 B) decodes to the end-of-`0x25` state: 8,576 points, valid; buckets −0.5…0.5: 150 / 697 / 1500 / 1500 / 1500 / 1500 / 1479 / 250.
- **Rollback** is still available (backup unchanged). It would now also discard the 854 points learned on these drives.
