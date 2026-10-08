# Handoff: session 11r (2026-10-07, parallel): remote rlog pull + first on-car A/B of D2C4

Parallel to the milder-variants session ([kickoff](2026-10-07-s11-milder-variants-kickoff.md)). Started from the [remote-pull kickoff](2026-10-07-s11-remote-pull-d2c4-ab-kickoff.md).
- **Next kickoff:** [2026-10-07-s11r-ab-followup-kickoff.md](2026-10-07-s11r-ab-followup-kickoff.md).
- **Token usage:** no reliable cumulative figure available.
- Reconfirm everything at the next session start.

## 1. Objective

- Reach the device remotely (it was out of the car at the user's partner's workplace).
- Pull rlogs only for the A drive (13:27 EDT, `c027a92857`) and the D2C4 drives.
- Confirm the install took effect.
- Run the pre-registered on-car A/B analysis (deployment proposal §6).

## 2. User instructions and decisions (this session)

- **Part 1 (research):** stop and ask before connecting. Done.
- **Authorization:** "Device is powered on and will stay on, sub is still active, not in a car and nothing is connected over SSH, all connections are authorized for this log pull. There is only 1 drive after the 13:33 install to my knowledge."
  - It covered this pull only. Any later device access needs new authorization.
- **One-time exception to the CLAUDE.md §3 video rule** (from the kickoff): no videos in this remote pull. They are recorded as gaps and must be pulled over the LAN later.
- **After the pre-registration** (the data differed from §6): "Go ahead and analyze the data we have, we should have more later. My partner is the driver so I don't have the subjective data yet, but I'm interested in the objective results that we can get."
- **Standing:** every device change, install and reboot needs explicit per-action authorization. The outer docs commit has not been requested.

## 3. Exact revisions and workspace (confirmed 2026-10-07 ~15:40 EDT)

- **`sunnypilot/`:** `dragal/custom` @ `89bbe60ab1`, clean (not touched). The WSL clone `~/src/sunnypilot` is @ `89bbe60`, clean (not touched).
- **Outer `main` @ `606c36b`,** with everything since session 8 uncommitted.
  - This session added: `docs/findings/2026-10-07-remote-ssh-proxy.md`, `docs/findings/2026-10-07-g70-d2c4-ab-onroad.md`, this handoff and its kickoff.
  - It appended to `CHANGELOG.md` and `docs/sessions/README.md`.
- **Data root `E:`:** UniqueId `daa460f7…`, about 228 GB free.
- **Device:** installed `89bbe60ab1` (D2C4), `DisableUpdates=1`, offroad on Wi-Fi at the partner's workplace at 18:59Z. `/data` 43 GB free.

## 4. Completed work and evidence

1. **Research** ([remote SSH proxy findings](../findings/2026-10-07-remote-ssh-proxy.md)):
   - ssh.comma.ai relays an end-to-end SSH session to the device's own sshd through athenad (port 22 only). It needs prime and the device online.
   - Our key is the device's only GitHub key. sunnylink has no usable client path.
2. **Pull** (findings §1):
   - 4 sequential read-only connections, 18:59–19:03Z, through the proxy. The proxy host key matched the documented fingerprint; the device host key was pinned to the LAN-recorded one.
   - **71 rlogs** (`0x26`, `0x27`, `0x28`), all sha256 MATCH, promoted to `recordings/2026/10/07/` with `PROVENANCE.md` and `GAPS.md`.
3. **Install confirmed from the logs** (findings §2):
   - `0x28` is the only D2C4 drive; deadzone 0.4 in CarParams; the configuration params are off.
   - The torqued, lagd and paramsd restores all took effect.
   - **`0x27` logged no GPS at all.**
4. **Inventory and road matching** (findings §2.3):
   - B's road and direction were also driven on A software by `0x26`, `0x1e` (dark), `0x20`, `0x22` (day) and `0x24` (dark).
   - B is below the §6 minimum: 6.6 min straight-clean, 9 curve events.
5. **Pre-registration** (findings §3), written before any metric. Then the **results** (findings §4, preliminary):
   - **Jitter:** jumps −42% (CI −56…−25), T −39% → **pass**. But the light-matched midday A drive `0x20` is lower than B, so the reduction is not distinguishable from day-to-day variation.
   - **Weave:** W **+18.4%** (+21.6% on the Amendment 5 masks) → **fail** (limit 15%; the CI includes 0). Lane-offset 0.05–0.7 Hz +7% (pass). Lane-offset 0.2–0.7 Hz +41% (CI +20…+65; reported).
   - **Comfort:** steering-proxy jerk −23% (pass); 20 Hz line / column 8–20 Hz pass. **IMU not evaluable** (A-primary gate r 0.775 < 0.8).
   - **Tracking:** mean error +27% (pass; CI up to +39%); curve lag +0.094 s (pass); lane offset in curves −0.006 m (pass). Overrides **pending** (no video): B has 5 press onsets in 11.4 min.
   - **Driver's assessment:** **pending** (the driver is the user's partner).
   - **Reading:** the twitch reduction and the transient costs are about the size the model predicted. The weave got worse, not better (*hypothesis:* the filter's extra phase lag in the weave band, R5, acting through the outer loop).
6. **Focused review** of the analysis script (findings §5): no blocker or major; 4 minor findings, all reporting-level and agreed; no verdict changes.

## 5. Open questions

- Is the weave increase real (one B drive, CI includes 0 for W) and caused by C4's phase lag? This bears on the milder-variants work: a higher cutoff gives less phase lag.
- Is the jitter reduction robust in daylight on the same road? It needs more B drives, ideally at the times of `0x20`/`0x22`.
- What caused B's 5 steering-press onsets? Needs the road video (deferred).
- Why did `0x27` have no GPS? Not investigated: the device-errors topic (session 8 locationd/GPS) may be relevant.

## 6. Validation limits and QA

- One B drive, at one time of day.
- A drives are from other times, mostly dark. Traffic and weather are not measured.
- No video of any kind for these routes yet.
- All verdicts are **preliminary**.
- **QA:** focused review of the analysis script done. Two-round QA n/a (no code or device change). Pull and analysis are offline/read-only evidence. Nothing here is deployment authorization.

## 7. Artifacts

| What | Where |
|---|---|
| Recordings | `E:\DragalPilot\recordings\2026\10\07\{06-26-59__00000026--6ec0a50b0c, 13-06-19__00000027--bf9faec3ff, 13-40-58__00000028--4e2298f929}` |
| Pull logs, small param files, manifests | `E:\DragalPilot\device-logs\2026-10-07_s11r_remote\`; `logs/device-pull-20261007s11r.remote.sha256`; `logs/promote-20261007s11r.log` |
| Proxy known-hosts | `E:\DragalPilot\cache\ssh\known_hosts.comma-proxy` |
| Device scripts | `E:\DragalPilot\scratch\device\{ssh_proxy_s11r.sh, list_s11r_20261007.sh, pull_rlogs_s11r_20261007.sh, pull_driver_s11r_20261007.sh}` (resumable, per-file sha256). Fix before reuse: the `pgrep` guard is a no-op in Git Bash. |
| Promotion / provenance | `E:\DragalPilot\scratch\{promote_20261007s11r.ps1, provenance_20261007s11r.sh, provenance_20261007s11r.template.md}` |
| Analysis | `E:\DragalPilot\analysis\g70-d2c4-ab-20261007\{drives, confirm, dataset, imu, gps, inventory, match, metrics}` |
| New scripts (`scratch/wsl/sng/`) | `s14_ab_confirm.py`, `s14_route_time.py`, `s14_gps_extract.py`, `s14_ab_inventory.py`, `s14_ab_match.py`, `s14_ab_metrics.py`, `s14_ab_report.py` + `run_s14_*.sh`. Shared scripts unchanged. |
| Review | `E:\DragalPilot\scratch\review-s11r\` |

- **Venvs:** checkout venv for rlog readers; `~/venvs/vid` (numba) for `s11_eval`-based scripts.
- **From Git Bash, call WSL with `MSYS_NO_PATHCONV=1`** (otherwise `/mnt/...` paths are rewritten).

## 8. Running operations

None. No background agents, no WSL jobs.

## 9. Device state and SSH ownership

- **No SSH connection open.** This session made 4 sequential proxy connections, all closed.
- The device is at the partner's workplace (last observed 18:59Z, offroad, Wi-Fi).
- Any new access needs:
  - the user's authorization;
  - a confirmed current state;
  - no other session.

## 10. Ordered next steps

1. **Video pull over the LAN** (or the proxy, if the user authorizes it) for `0x26`–`0x28` (fcamera + ecamera, per `GAPS.md`), before the deleter reaches them. Roughly 8 h of driving at 43 GB free (estimate).
2. **Collect the partner's assessment of the B drive,** verbatim (criterion 5).
3. **More B drives** on the same road in daylight; then pull them and re-run the pipeline. Pre-register the added data first; the §6 criteria stay unchanged.
4. **Decision for the user:** keep D2C4 while collecting / roll back to `c027a92857` / move to a milder variant. Share the weave/phase-lag finding with the milder-variants work.
5. **Outer docs commit** when the user asks.
