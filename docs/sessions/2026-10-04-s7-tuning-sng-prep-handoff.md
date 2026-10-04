# Handoff: session 7 (2026-10-04): controller-tuning hypotheses, stop-and-go prep, video rule

Written 2026-10-04 ~17:55 EDT. Reconfirm everything at the next session start.

## Objective

Make sunnypilot drive the user's 2024 Genesis G70 well. The current complaint is a ~3 s weave, felt most at low speed and in stop-and-go behind a lead.

This session:
- checked the weave in video;
- tested three controller-tuning levers offline;
- prepared the stop-and-go analysis and the hands-on-wheel plant input for the user's next drives.

## User instructions and decisions (this session)

- After reviewing the video results, **assess option (b) offline** while drives are pending (latAccelFactor speed scale). Done; not supported.
- **Test the damping term and the KP speed schedule.** Done; not supported.
- **Prepare the stop-and-go analysis; define hands on the wheel as a plant input.** Done.
- **New project rule:** video from both road cameras is always pulled with rlogs and organized the same way.
  - The user had asked in session 4; it had only been saved as a memory permission.
  - Now in CLAUDE.md §3 and `docs/local-storage.md`. Memory updated, plus a feedback memory: durable rules go into CLAUDE.md in the same session.
  - "Both cameras" was read as fcamera + ecamera. The driver camera stays optional (only when `RecordFront=1`); the user may say otherwise.
- **Pull authorized:** missing videos of routes 0–2. Done.
- **Commit and push, then write this handoff.** Done (`7e9499a`). This handoff and kickoff are committed and pushed separately.
- **Standing (memory):**
  - video pulls/analysis authorized, with §6 mechanics;
  - tool installs on host/WSL authorized;
  - no test re-runs for docs-only commits;
  - stay on the default driving model;
  - reboots and device changes need explicit per-action authorization.

## Exact revisions

- sunnypilot baseline `dev` @ `0b2c431d3abab630df0a32f53236944855a91aa3` (unchanged).
- `dragal/custom` @ `82f58a9a8c4af2f10d23d13fb1631deca98d4efd`: deployed, clean, unchanged this session. WSL clone the same, clean.
- **Outer repo `main`:**
  - `7e9499a`: session 7 docs (pushed): CLAUDE.md §3 rule, `docs/local-storage.md`, three new findings docs, the video-findings follow-up, changelog;
  - then the commit with this handoff, the kickoff, `docs/sessions/README.md` and the changelog line.

## Completed work and evidence

All model results are offline. "Held-out" means held-out in inputs and disturbances; the plant was fitted on the selection routes.

1. **Video weave band** ([video findings](../findings/2026-10-04-g70-video-lane-check.md), follow-up section). The 0.2–0.4 Hz lane-position motion at highway speed is confirmed independently of the model:
   - coherence 0.72–0.96, gain 0.96–1.07, phase ≤ 4°;
   - 0.2–0.6 Hz std 2.5–3.2 cm.
   - Routes 6–8, daytime highway only.
2. **latAccelFactor speed scale** ([findings](../findings/2026-10-04-g70-laf-speed-schedule.md); pre-registered):
   - selected [0.9, 1.3, 1.1] at [12.5, 20, 29] m/s;
   - held-out: ΔA −0.05 to −0.09, lag +1.4–3.2°, motion −4–5%. **Fails item 6** (a 20–35 mph step at −1.0 → +0.1%; kept as written).
   - Not robust if torqued learns 4.47. torqued alone at 4.2 gives ~40% of the effect.
   - Routes 4 and 9 were added to the simulation dataset (replay exact on 89% / 92% of cycles).
3. **Damping term and KP schedule** ([findings](../findings/2026-10-04-g70-damping-kp-schedule.md); pre-registered):
   - fast variants equal the source V0 with its PID rebuilt from the variant tables (≤ 5.5e-8);
   - selected D [0, 0.05] and KP ×[1.0, 1.0, 0.85]; combination too;
   - **all fail criterion 1** (ΔA only −0.005 to −0.083) and pass the rest.
   - Larger values fail on lag, error, low-speed curve tracking or rate-limit binding.
   - A D term would need its rate state reset at engagement: the stale `previous_measurement` gives a kick up to 3.5–4.6 m/s² at KD 0.75.
4. **Combined conclusion (model, hypothesis):** within the lag/tracking limits, V0's parameters can cut the highway weave by only ~4–5%. The peak is set by the steering plant's lag and the vehicle's yaw response. **No implementation or device change proposed.**
5. **Stop-and-go plan** ([plan](../findings/2026-10-04-g70-stop-and-go-plan.md)):
   - drive protocol D1–D4;
   - signals and episodes, curvature/angle-based, working at standstill;
   - decision rules D1–D5, thresholds provisional and changeable by the user **before** the data;
   - hands models M3a/M3b/M3c with acceptance criteria.
   - **`sng_analyze.py` dry run** on routes 4, 6–9, 0a, 0b, 0c, 0e:
     - four design amendments (A1–A4) plus a one-cycle alignment fix, all before any new data;
     - no engaged SNG episodes exist;
     - LS (20–35 mph) D1 no (0.78, CI 0.58–1.10); the EPS tracks the command (coherence 0.92).
   - **Hands feasibility:** column torque is light and leads the steering by 56–131° (a reaction signature). Its coherence with the plant residual is 0.03–0.36, so M3a alone is unlikely to close the low-speed gap. M3b is inconclusive.
6. **Video pull, routes 0–2:**
   - 12 files, 309 MB; one read-only SSH session 21:44:53Z; device `IsOffroad=1`, `IsEngaged=0`, `GitCommit=82f58a9a8c`, no newer routes;
   - all sha256 MATCH; promoted; provenance appended.
   - **Every local route now has rlogs + fcamera + ecamera for every segment that has them on the device.** Recorded gaps: route 0 segment 1 (no video), route 1 segment 3 (0-byte videos), route 4 segment 9 and route 9 segment 4 (0-byte).

## Open hypotheses / questions

- **Low-speed and stop-and-go weave: unexplained.** Candidates:
  - the plan following a lead when lines are weak (session 5 video observation; D3);
  - closed loop through the model (D5);
  - steering/hands dynamics at low speed (M3c stage 2, M3b);
  - the request itself.
- **Whether the user's felt weave is beyond their own driving** at low speed: D1 on the new drives. On the existing LS data: no.
- **The C ≤ 1.2 criterion** is likely unreachable through the steering loop (the vehicle link alone is 1.2–1.3).
- **Car-scoped plumbing for V0 gains** (not needed unless a future change passes).

## Workspace, artifacts, running operations

- **No running operations. No SSH connection open.**
- **Scripts** (`E:\DragalPilot\scratch\wsl\`):
  - `vid\vid_weave_band.py`;
  - `s7\` (latAccelFactor), `s8\` (D/KP), `sng\` (stop-and-go, hands);
  - `scratch\device\pull_videos_r012_20261004s7.sh`, `scratch\promote_20261004s7.ps1`.
- **Outputs** (`E:\DragalPilot\analysis\`): `g70-video-weave-band-20261004\`, `g70-laf-sched-20261004\`, `g70-damping-kp-20261004\`, `g70-sng-prep-20261004\`.
- **Logs** (`E:\DragalPilot\logs\`): `vid-weave-band-*`, `s7-*`, `s5-s7-*`, `s5-s8-*`, `s8-*`, `sng-*`, `promote-20261004s7.log`.
- **Staging:** `E:\DragalPilot\temporary\device-pull-20261004s7\` holds `pull.tar` (309 MB duplicate of the promoted files), manifests and the pull log. **Ask the user before deleting the tar.**
- Data root: E: UniqueId OK, ~238 GB free at the pull.

## Validation and limitations

- Every simulator variant was checked against the checkout's source classes (exact or ≤ 6e-8).
- The selection rules and criteria were applied mechanically, as pre-registered. Results are model evidence only:
  - single-input plant, constant per band, no outer loop;
  - no held-out 20–35 mph data.
- Two scorer/alignment bugs were found and fixed during the session (recorded in the findings); no verdict changed.

## QA stages

- Analysis and docs only; no code changes in `sunnypilot/`. QA not applicable.
- Code from earlier rounds: focused review done; two-round QA not performed.

## Device state and SSH

- Last observed 2026-10-04T21:44:53Z: `192.168.98.104`, `IsOffroad=1`, `IsEngaged=0`, `GitCommit=82f58a9a8c`, `GitBranch=dragal/custom`, `RecordFront=0`, no other SSH session.
- Connection closed (ssh exit 0). No device changes made.

## Ordered next steps

1. **Waiting on the user's drives** (plan section 1: D1 stop-and-go engaged, D2 the same by hand, D3 steady 20–35 mph, D4 optional highway).
   - Before the data: the user may adjust the provisional D-rule thresholds.
2. **When the drives are done:**
   - confirm the device address and state (§6), one SSH connection;
   - pull **rlogs + fcamera + ecamera** for all new routes;
   - verify, promote, write provenance.
3. **Extract the new routes:**
   - `drive_extract.py` + `lane_drift_extract.py` into `analysis\g70-sng-<date>\`;
   - then `sng_analyze.py` and report D1–D5;
   - frame sheets for the episodes.
4. **If D3 gave clean 20–35 mph runs ≥ 30 s:**
   - `s5_dataset.py` → session 6 plant check held out at 20–35 mph;
   - then the hands models (M3c stage 2 first, then M3b).
5. Ask about deleting `temporary\device-pull-20261004s7\pull.tar`.
6. Later: the Hyundai 0x484 forwarding-rule round; keep watching the bus-1 start-up burst; one check drive once torqued goes valid.
