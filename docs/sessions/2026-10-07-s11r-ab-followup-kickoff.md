# Kickoff prompt: D2C4 on-car A/B follow-up (videos, more B drives, driver's assessment) (copy-ready)

Use it when more D2C4 drives exist and the device can be reached.

```text
Resume the dragalpilot project at C:\Users\dre\Documents\DragalPilot\dragalpilot.

Read, in order:
- CLAUDE.md (§3 storage/recording rules, §6 device rules, §7);
- docs/sessions/2026-10-07-s11r-remote-pull-ab-handoff.md;
- docs/findings/2026-10-07-g70-d2c4-ab-onroad.md (all of it: the pre-registration §3, the preliminary results §4, the review §5);
- docs/proposals/2026-10-07-g70-d2c4-deploy.md §6 (the A/B criteria);
- docs/findings/2026-10-07-remote-ssh-proxy.md (only if the device is not on the home LAN);
- docs/local-storage.md;
- CHANGELOG.md (session 11 and 11r entries), plus whatever the milder-variants session recorded since.

State: D2C4 (89bbe60ab1) is installed; last known-good c027a92857. One B drive (0x28) was analysed. The verdict is preliminary:
- jitter passes but sits within the A day-to-day range;
- weave W +18% fails the 15% limit;
- the transient costs are as predicted;
- IMU not evaluable; overrides and the driver's assessment are pending.
The road videos of routes 0x26-0x28 were deferred (remote pull) and still have to be pulled.

Tasks (stop and ask at each device boundary; every connection needs my authorization at the time):
1. Ask me for: the device's current location/address and state; any new drives since 0x28 (who drove, when, which road); and
   the driver's (my partner's) impression of the D2C4 drives, recorded verbatim before any numbers are shown.
2. Read-only pull (one SSH connection at a time):
   - the deferred fcamera/ecamera for 0x26-0x28 (see each route's metadata/GAPS.md);
   - rlogs + both road videos for every new route after 0x28;
   - never qlogs/qcamera. Verify by sha256, promote, and update GAPS.md / PROVENANCE.md.
3. Before computing anything on new data, write an amendment to the pre-registration:
   - which new B (and A) routes qualify, with the same road matching (s14_ab_match.py) and light labelling;
   - criteria unchanged.
   Fix the reporting gaps from the §5 review:
   - per-arm CIs;
   - exact counts/minutes for the secondary rates;
   - state the W / comfort (a) run rule;
   - mark IMU not evaluable automatically when the gate fails.
   Put any code change in a new file (e.g. s15_*); never edit shared scripts in place.
4. Re-run the pipeline:
   - drive_extract, s11_dataset, s12_imu_extract, s14_gps_extract, s14_ab_match, s14_ab_metrics — runners in scratch/wsl/sng;
   - call WSL from Git Bash with MSYS_NO_PATHCONV=1.
   Also use the road video to classify B's steering-press events (criterion 4d).
5. Report against the §6 criteria (jitter, weave, comfort, tracking, driver), with limitations. Recommend keep / roll back /
   variant; I decide. No code or device changes in this session unless I authorize them separately.

If the milder-variants session is still running: no checkout/WSL-clone changes, ≤ 4 CPU workers, append-only edits of
CHANGELOG.md, docs/sessions/README.md and CLAUDE.md (re-read right before each edit).
```
