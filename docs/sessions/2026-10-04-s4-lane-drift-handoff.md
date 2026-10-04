# Handoff: session 4 (2026-10-04): lane-drift investigation from rlogs

Written 2026-10-04, afternoon, EDT. Reconfirm everything at the next session start.

## Objective

Make sunnypilot drive the user's 2024 Genesis G70 well. This session investigated the slow lane-position drift that remained after the tune. The next work is:

- (a) the low-speed drive data the user will collect;
- (b) optionally, a video session that independently checks the lane-position findings (kickoff [2026-10-04-s4-video-lane-check-kickoff.md](2026-10-04-s4-video-lane-check-kickoff.md)).

## User instructions and decisions (this session)

- The drift is unusual and noticeable to the user, **most noticeable in slow stop-and-go traffic**. The user will record engaged and manual low-speed drives. Protocol: [lane-drift findings § Low-speed data drive protocol](../findings/2026-10-04-g70-lane-drift.md).
- The device is mounted at the **windshield centre, ±3 mm**.
- **Stay on the default driving model** for now.
- A downstream curve correction that runs only above a minimum speed would not address the low-speed complaint (user point; agreed).
- **Standing authorizations (2026-10-04, saved in memory):**
  - Pull and analyze **all comma 4 videos** at any time. The CLAUDE.md §6 SSH, IP and state mechanics still apply.
  - **Install any helpful tools, dependencies or local vision models** on the host or WSL. Data and caches go on E:. The device is not covered.
  - Write a kickoff for a video-analysis session if useful (done).
  - Note: CLAUDE.md §0.3 ("do not import permissions from earlier sessions") conflicts with these standing grants. This was flagged to the user; CLAUDE.md is not changed yet.
- Standing from before: rlogs only (now plus videos); per-step device authorization for anything except log and video pulls; reboots need explicit authorization each time; no investigation of the 12:02:18 sharp-curve takeover.

## Exact revisions

- sunnypilot baseline `dev` @ `0b2c431d3abab630df0a32f53236944855a91aa3` (unchanged).
- `dragal/custom` @ `82f58a9a8c4af2f10d23d13fb1631deca98d4efd` (local; deployed). No code changes this session.
- Outer repo: `main` = `origin/main` @ `3d0828f` at session start. This session's doc changes are **uncommitted** unless a later commit says otherwise (check `git status`).
- WSL clones: `~/src/sunnypilot` @ `82f58a9`, `~/src/panda` @ `74a0adc`, both clean.

## Completed work and evidence

Full write-up: [docs/findings/2026-10-04-g70-lane-drift.md](../findings/2026-10-04-g70-lane-drift.md); `torqued` follow-up in [first-drive findings](../findings/2026-10-04-g70-tune-0x484-first-drive.md).

1. **Model and calibration identity.**
   - No model bundle selected. Stock `modeld` runs the built-in default (named `CD210`; ref matches the cached bundle "CD210 Model (Feb 3, 2026)"). Device `mici`, no chestnut.
   - Calibration stable: pitch ~1.2°, yaw ~−1.1°, height 1.20 m.
   - Source fact: `CameraOffset` and `PlanplusControl` are read only by `modeld_v2`, so they have no effect here.
2. **Signs (GPS-checked):** positive `desiredCurvature` = right turn; model y is right-positive; `laneLines[1]` is the left line.
3. **Drift, at v > 15 m/s:**
   - No 0.1 Hz peak. The old "0.1 Hz" was the edge of the search band; the spectrum is red.
   - Road curvature explains 64–82% of the offset variance: the car moves toward the inside of curves (~0.25–0.4 m per 1 km radius), plus a static device-left bias of 0.15–0.19 m. With the mount centred, that bias is the car's.
   - The motion is real: the lines move together and it is kinematically consistent.
   - The model plans it. The car executes it: curvature gain 1.02–1.08, phase within ±2.5°.
4. **25–30 mph vs highway:**
   - Only 54 s engaged at 25–30 mph today, all in short passes (≤ 17 s windows).
   - Fast band (0.3–3 Hz): no more oscillation than on the highway (sway 0.19 vs 1.07 cm).
   - The slow band can't be measured from this data.
5. **Model list:** 77 cached bundles, none brand-specific. The web search found no Hyundai-tuned model.
6. **`torqued`:**
   - Not valid. Its points restarted at the deployment (the cache key includes the offline torque values).
   - The bucket reconstruction matches the logged totals within 0.2%. The limiting bucket is the outermost negative-torque one (23/100, ~49 points per engaged highway hour), so ~1.5–2 more hours of similar driving above 34 mph are needed.
   - Once valid it moves latAccelFactor 4.0 → ~4.2 gradually. It learns nothing below 15 m/s.

Scripts (all on `E:\DragalPilot\scratch\wsl\`): `model_calib_identity.py`, `lane_drift_extract.py`, `lane_drift.py`, `lane_drift_spectrum.py`, `sign_check_gps.py`, `models_cache_list.py`, `lowspeed_inventory.py`, `lowspeed_windows.py`, `speed_band_osc.py`, `torqued_buckets.py`. Outputs: `E:\DragalPilot\analysis\g70-lane-drift-20261004\`. Logs: `E:\DragalPilot\logs\*-20261004*`.

## Open hypotheses / questions

- Low-speed swing: is it the model's plan (e.g. following a lead car when lane lines are weak) or the controller? Note the controller's KP rises to 2.9 at 12 m/s and 11.5 at 5 m/s, with KD 0. Untested until the low-speed data exists.
- Whether the curve-inside shift and left bias exceed human driving: needs the manual reference stretches, plus the video check.
- Downstream lane-centring correction: discussed, not designed. It is only useful above some speed and with confident lane lines.

## Device state and SSH

- No device access this session. **No SSH connection open.**
- Last observed state is unchanged from session 3: `192.168.98.104` (reconfirm), offroad, `GitCommit=82f58a9a8c`, panda `5b8d2b33…`.
- Videos on the device: unknown which still exist. Routes 3, 4, 8, 9 have no local video. Routes 5–7 have fcamera/ecamera locally.

## QA stages

Analysis only; no QA needed. The code from the previous round: focused review done; two-round QA not performed.

## Ordered next steps

The user reported the low-speed drives done (2026-10-04). Kickoffs, in order:

1. [low-speed drives](2026-10-04-s4-lowspeed-drives-kickoff.md): does the single device pull for both sessions.
2. [video lane check](2026-10-04-s4-video-lane-check-kickoff.md): starts after that pull.

1. When the user reports the low-speed drives: confirm the IP and that the device is offroad, then pull rlogs and videos. Run `speed_band_osc.py` with longer windows plus the plan-vs-execution and lane decomposition at low speed. Compare engaged vs manual.
2. Optional, in parallel: the video lane-position check (kickoff above). Only one session may hold the SSH connection at a time.
3. Once `torqued` goes valid: one check drive (applied values, curve criteria).
4. Later: the Hyundai 0x484 forwarding-rule round; watch the bus-1 startup fault.
