# Handoff: session 2 (2026-10-03 → 2026-10-04): WSL, tests, rlog analysis, review, deployment

Written 2026-10-04 ~00:35 EDT, after the Stage 0 deployment. The user is next running the in-car checklist without Claude. Reconfirm everything at the next session start.

## Objective

Get sunnypilot to support the user's 2024 Genesis G70 (it previously fingerprinted as MOCK/dashcam). Current phase: the port is deployed, and real-world validation is pending.

## User decisions and instructions (this session)

- Plan steps 1–3 done; step 4 (deploy) approved and executed.
- Approved: the deployment plan, the `DisableUpdates=1` param write, and the reboot (done). Future reboots still need explicit authorization each time.
- Alpha longitudinal: leave the port as upstream wrote it (no `UNSUPPORTED_LONGITUDINAL`). The user will not enable the toggle.
- The car has **Harness F** (docs entry changed accordingly).
- Undated routes go to `recordings/undated/<route-id>/` (Claude's choice, delegated by the user).
- **Don't run targeted tests for comment- or docs-only commits** (saved to memory).
- In-car stages are run by the user alone: install in the car → quick drive not engaged → if clean, a short low-speed engagement in a closed area with no traffic → if clean, collect engaged driving data. Then Claude analyses. Checklist: `docs/proposals/2026-10-04-g70-in-car-checklist.md`.
- Pushes were approved for `7cac8f6` and `0f024f7`. **Commits after `0f024f7` are local and not pushed** (push not yet answered).

## Exact revisions

- sunnypilot baseline: `dev` @ `0b2c431d3abab630df0a32f53236944855a91aa3` (unchanged).
- **`dragal/custom` @ `7e9d0755d999b22036227d61356386e230d45114`** (local only), 4 commits on the baseline:
  - `392f9b6` port
  - `5cdfe3c` EPS FW from the car
  - `f932569` route citation (comment)
  - `7e9d075` harness F (docs)
- Outer repo `main`: `origin/main` = `0f024f7`. Local HEAD is `7c7adff` plus this handoff commit (several unpushed commits).
- WSL test clone `~/src/sunnypilot`: detached at `7e9d075`, clean.

## Completed work and evidence

1. **WSL environment:** Ubuntu-24.04, disk on `E:\DragalPilot\cache\wsl\`, user `dev`, uv 0.12.23, `.venv` with Python 3.12.13. Details are in `docs/baseline.md` § WSL test environment. Limitation: the `dev` prebuilt ships AArch64 `.so` files and no `SConstruct`, so openpilot-side native tests (e.g. the NNLC test) can't run on x86.
2. **Targeted tests:**
   - `test_hyundai` failed on `392f9b6` (no EPS FW). Fixed with the car's own EPS FW.
   - On `5cdfe3c`/`7e9d075`, all pass: car_list, routes, docs, hyundai, fw_fingerprint, and Hyundai safety.
   - The car's real FW gives an exact match to `GENESIS_G70_2024` (baseline: no match). Details: `docs/findings/2026-10-03-g70-fingerprint.md`.
3. **rlog analysis** (`docs/findings/2026-10-03-g70-rlog-can.md`). All 3 routes are of the car **parked**.
   - LKAS11 checksum is CRC8 on 100% of frames.
   - Buses 0 and 2 are classic CAN, mirrored (relay not isolating). Bus 1 is a separate CAN-FD network that the port doesn't use.
   - CarState `canValid` held throughout; safety rx had 0 invalid frames out of 1.53M.
   - **The SCC origin (`CAMERA_SCC`) is unverified.**
   - rlogs promoted to `recordings/2026/10/03/17-54-05__00000000--eb903c3c31`, `.../17-55-51__00000001--ed6394b42a`, and `recordings/undated/00000002--3ea363e27d`.
4. **Focused adversarial review** (`docs/findings/2026-10-04-g70-port-focused-review.md`): no blockers or majors, 6 minor/info findings, all verified and dispositioned. **QA: focused review complete. Two-round QA not performed.**
5. **Deployment** (`docs/proposals/2026-10-04-g70-2024-deploy.md` § Deployment record): the device now runs `7e9d0755d9` with `DisableUpdates=1`. The staged baseline update in `/data/safe_staging/finalized` is inert. Artifacts and logs are in `E:\DragalPilot\deploy\g70-20261004\`.
6. Device-load baseline from the pre-deploy rlogs (onroad, parked, dashcam): CPU mean 53–82%, p95 80–88% (`device-load-baseline.log`).

## Open hypotheses and questions

- `CAMERA_SCC` correct? Test: after the drive, SCC11/12 (`0x420`/`0x421`) should appear on bus 2 only while the relay is engaged.
- Steering acceptance (EPS accepts CRC8 LKAS11), the tune (steerRatio 12.9 is a guess; torque `[2.7, 2.7, 0.11]`), and possible low-speed EPS lockout.
- Bus 1 CAN-FD network: its role is unknown.
- The NNLC model would fall back to the older G70 model. NNLC stays off.

## Device state and SSH ownership

- Device `192.168.98.104` (DHCP; reconfirm), user `comma`, key `~/.ssh/id_ed25519_dragalpilot`.
- Last observed at 04:29Z on 2026-10-04: offroad, indoors, running `7e9d0755d9`, `DisableUpdates=1`, NNLC 0, alpha long absent, `Mads=1`.
- **No SSH connection is open.** It is about to be installed in the car by the user.
- Rollback: `cd /data/openpilot && git checkout dev`, then a reboot (needs authorization). Optionally restore `DisableUpdates=0`; doing so lets the updater move off the baseline.

## Ordered next steps

1. When the user returns: confirm the device's current IP and that it's inactive (offroad), and ask what happened in each checklist stage (with times).
2. Pull the **rlogs only** of the new drives (one SSH session; verify sha256), stage them in `temporary/`, then promote them with GPS-derived start times.
3. Analyse:
   - carParams (`GENESIS_G70_2024`, not fuzzy, not dashcam); safety model/param from pandaStates
   - **the SCC bus layout with the relay engaged**
   - canValid and alerts (onroadEvents)
   - steering: requested torque (LKAS11 / carControl) vs MDPS12 measured, `steerFaultTemporary`, oscillation, lateral error
   - device load vs baseline
   - Reuse `E:\DragalPilot\scratch\wsl\{rlog_inventory,g70_replay,device_load}.py`.
4. Write the findings. Any tune change is a separate bounded change with its own review.
5. Ask about pushing the outer commits.
