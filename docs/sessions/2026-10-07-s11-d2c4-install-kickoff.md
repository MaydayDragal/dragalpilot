> **DEPRECATED (2026-10-07): do not use.** D2C4 was installed in session 11 (13:33 EDT, `89bbe60ab1`, reboot and post-boot check OK; see the deployment record in [the proposal](../proposals/2026-10-07-g70-d2c4-deploy.md)). Kept unchanged below as the record.

# Kickoff prompt: install D2C4 on the device (copy-ready; use only when the device is available)

Scope: the installation of the prepared D2C4 change and the checks right after it. Nothing else: no new analysis, no code changes, no tuning. The milder-variant work is a separate kickoff ([2026-10-07-s11-milder-variants-kickoff.md](2026-10-07-s11-milder-variants-kickoff.md)).

```text
Resume the dragalpilot project at C:\Users\dre\Documents\DragalPilot\dragalpilot. This session's only task is to install the
prepared D2C4 change (G70 2024 steering-twitch fix) on the comma device, with my explicit authorization for each device action.

Read, in order: CLAUDE.md (especially §6 device rules), docs/proposals/2026-10-07-g70-d2c4-deploy.md (the whole proposal,
including the preparation record), docs/sessions/2026-10-07-s11-d2c4-ready-handoff.md (§3 state, §9 device), docs/local-storage.md.

1. Confirm locally, without the device:
   - outer repo state;
   - sunnypilot/ on dragal/custom @ 89bbe60ab127cf71d238856a19c1e74b16bc36bd, clean;
   - E: identity, writability and free space;
   - `sha256sum -c E:\DragalPilot\deploy\g70-d2c4-20261007\artifacts.sha256` (from that folder) passes;
   - if anything in sunnypilot/ changed since 89bbe60ab1, stop and ask me: the artifacts would have to be rebuilt and re-dry-run.
2. Ask me to confirm the device's CURRENT IP address, that it is inactive (offroad, parked, not driving) and that no other SSH
   session or tool is connected. Do not connect before that. Exactly one SSH connection at a time.
3. With my authorization for the install: run install.sh over one connection (`ssh ... 'bash -s' < install.sh`), saving the
   output to E:\DragalPilot\logs\device-install-d2c4-<timestamp>.log.
   - It aborts on its own if the device isn't in the expected state: not offroad, HEAD not c027a92857, dirty tree, unexpected
     firmware file, or NNLC / EnforceTorqueControl / LateralJerkTorqueController / TorqueParamsOverrideEnabled on.
   - On any abort, stop and report; don't work around it.
   - Report the pre-state, the bundle hash check, the new HEAD, the learned-state hashes and the filter micro-benchmark.
4. Reboot only with my separate explicit authorization at that moment: run precheck_reboot.sh (it reboots only if every check
   passes).
5. After the device is back (I confirm the address again): run postboot_check.sh (read-only), save its log and report.
6. Record everything in the proposal's deployment record, the changelog (new dated entry) and docs/sessions/README.md:
   the commands, exit statuses, log paths, and what was actually deployed.
   - Rollback (proposal §5) only if I ask, with a separate reboot authorization.
7. Then stop. The on-car A/B drives (proposal §6) are mine to drive. The log pull and analysis afterwards are a later session's
   task, with a read-only pull that I authorize at the time.
```
