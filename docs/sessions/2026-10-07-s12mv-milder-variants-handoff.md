# Handoff: session 12mv (2026-10-07): weave modelling and milder twitch fixes after the first on-car D2C4 A/B (offline)

Started from the [milder-variants kickoff](2026-10-07-s11-milder-variants-kickoff.md) (updated after session 11r). Ran alongside the A/B follow-up session ([kickoff](2026-10-07-s11r-ab-followup-kickoff.md)), if that one was started.
- **Next kickoff:** [2026-10-07-s12mv-weave-attribution-kickoff.md](2026-10-07-s12mv-weave-attribution-kickoff.md).
- **Token usage:** no reliable cumulative figure available.
- Reconfirm everything at the next session start.

## 1. Objective

Find, offline, a twitch fix that keeps most of D2C4's reduction without making weave worse and with less transient cost. On the car (one D2C4 drive), weave got worse, which the model had not predicted. So weave had to be modelled first.

## 2. User instructions and decisions (this session)

- "Use [the milder-variants kickoff] as your kickoff prompt."
- **Candidate set:** "All 9 as proposed" (MV1–MV9). **Red flags:** "Red flags reported only" (they rank candidates, they don't fail them).
- **Standing:**
  - no device access in this session;
  - no change to `sunnypilot/` or the WSL clone;
  - no in-place edits of shared scripts, ≤ 4 CPU workers, append-only edits of shared docs (parallel-session rules);
  - every device change, install and reboot needs explicit per-action authorization;
  - the outer docs commit has not been requested.

## 3. Exact revisions and workspace (confirmed at session start ~16:05 EDT and again at handoff ~16:55 EDT)

- **`sunnypilot/`:** `dragal/custom` @ `89bbe60ab127cf71d238856a19c1e74b16bc36bd`, clean, not touched. **WSL clone** `~/src/sunnypilot` @ `89bbe60ab1`, clean, not touched.
- **Installed on the device:** `89bbe60ab1` (D2C4), per session 11r's last observation. Last known-good: `c027a92857`.
- **Outer `main`** @ `606c36b`, with everything since session 8 uncommitted. This session:
  - added `docs/findings/2026-10-07-g70-milder-variants.md`, this handoff and the next kickoff;
  - appended Amendment 8 (§4) to `docs/findings/2026-10-07-g70-d2c4-validation.md`;
  - appended to `CHANGELOG.md` and `docs/sessions/README.md`.
- **Data root `E:`:** UniqueId `daa460f7…`, about 228 GB free.

## 4. Completed work and evidence

All details are in the [milder-variants findings](../findings/2026-10-07-g70-milder-variants.md) and [Amendment 8](../findings/2026-10-07-g70-d2c4-validation.md#4-amendment-8-session-12mv-milder-variants-after-the-first-on-car-ab-written-2026-10-07-before-any-run).

1. **Exploratory semantics** (fit-set routes; §1):
   - lane lines are y-right;
   - the logged request is the model's output;
   - about half of the lane offset's weave band is real car motion;
   - the request follows the lane offset with a ~50° lead.
2. **Step 2a log check** (pre-registered; §3.1):
   - **B's request weaves 32% more** in 0.2–0.7 Hz (CI +13…+51%, above every A drive);
   - the full-band wheel lag is not significantly larger (−6.9°, CI includes 0);
   - **pre-registered reading: an exogenous request change, not attributable to D2C4.**
   - B's request jitter band (0.7–4 Hz) is 20% lower, so part of the on-car twitch reduction came with a calmer request.
3. **Step 3 plant check on `0x28`** (§3.2):
   - D2C4 fails adequacy on hold (+0.117 / +0.141): the real drive twitched more than predicted.
   - The model over-predicts D2C4's added weave-band lag (+22° vs +7° observed).
4. **Step 2b outer-loop model** (§3.3): the ARX policy model is not adequate (14.9% of the held-out weave band explained, criterion ≥ 20%). So the declared phase-lag proxy (2c) was used.
5. **Amendment 8 grid** (§3.4–3.6):
   - **no candidate passes**; all fail the weave proxy (15–19° of added weave-band lag, 67–87% of D2C4's; bound 25%);
   - MV2, MV3 and MV7 meet twitch + tracking;
   - every candidate except MV7 drops R5 and C3, and the no-filter deadzones have about half D2C4's curve lag.
   - All harness checks bit-exact or identical.
   - **Exploratory split:** in context, D2 alone adds 12–13° and C4 alone about 10°. The deadzone matters as much as the filter.
6. **Recommendation** (findings §4): keep D2C4 while the A/B follow-up collects data. If weave is confirmed worse, MV3/MV2 halve the transient cost but are expected to weave about as much; the rollback is the other option.
7. **Focused review** of the analysis scripts (findings §5): no blocker or major; θ0 cache key fixed (results unchanged); 2a full-band phase difference is −5.6° with whole-run Welch (reported −6.9°); no verdict changes.

## 5. Open hypotheses / questions

- Is B's weave increase caused by D2C4 or by the day/road/request? It needs more same-road daylight B drives, with the step 2a M1/M4/M5 metrics re-run on them.
- Does a twitch reduction of 40–60% necessarily cost 15–20° of small-signal weave-band lag (hypothesis, model)? Would the car show it? D2C4 showed only +7° on one drive.
- An adequate outer-loop model: try instrumental-variable identification, lane lags ≥ 1 frame, or heading from the full lane-line geometry.
- Carried over: 20 Hz EPS pulse source; 35–55 mph and low speed not modelled; stop-and-go; why `0x27` had no GPS; HDA-deselected drive; 0x484 forwarding-rule round.

## 6. Validation limits and QA

- **All results are offline model evidence or log observations.** Nothing was validated on the car; nothing authorizes a deployment.
- The weave criterion is a proxy. The plant over-predicts D2C4's hold. No logged era is untouched by candidate selection.
- **QA:** focused review of this session's analysis scripts, see findings §5. Two-round QA does not apply (no product code change).

## 7. Artifacts

| What | Where |
|---|---|
| Outputs | `E:\DragalPilot\analysis\g70-milder-variants-20261007\{explore, 2a, 3, 2b, a8}\` (`a8/`: `grid.json`, `summary.json`, `transient_2a.json`, `curves_2b.json`, `split_exploratory.json`) |
| Scripts (new, `E:\DragalPilot\scratch\wsl\sng\`) | `s15_mv_2a.py`, `s15_mv_3.py`, `s15_mv_arx.py`, `s15_mv_var.py` (harness extension), `s15_mv_check.py`, `s15_mv_grid.py`, `s15_mv_transient.py`, `s15_mv_curves.py`, `s15_mv_summary.py`, `s15_mv_split.py`, exploratory `s15_mv_semantics.py`, `s15_mv_lane_semantics.py`, `s15_mv_peek.py`, `s15_mv_show.py`; runners `run_s15_mv*.sh` (`run_s15_mv.sh <tag> <script> args` is the generic one) |
| Logs | `E:\DragalPilot\logs\s12mv-*` |
| Review | `E:\DragalPilot\scratch\review-s12mv\` |

- Shared scripts are unchanged. `s15_mv_var.install()` monkeypatches `s11_eval` in-process only.
- **Tool note:** `s12_transient.run()` ignores `fr_dz_shift`. Use `s15_mv_transient.py` for continuous-deadzone variants.

## 8. Running operations

None at handoff: no background agents, no WSL jobs (checked ~16:55 EDT).

## 9. Device state and SSH ownership

No device access and no SSH connection in this session. Device state as last observed by session 11r (offroad at the partner's workplace, 18:59Z). Any access needs the user's authorization, a confirmed current address and state, and no other session.

## 10. Ordered next steps

1. **User decision** on the recommendation (keep D2C4 / roll back / prepare MV3 or MV2).
2. **A/B follow-up session** (if not done): pull videos and new B drives, the driver's assessment.
3. **Then the next kickoff:** re-run step 2a on the new B drives (pre-registered unchanged) to attribute the weave; optionally a v2 outer-loop identification.
4. **Outer docs commit** when the user asks.

## 11. Update after the user's question on weave attribution (2026-10-07, end of session)

- **User:** "An increase of 32% being caused by the same exact model on the same stretch of roadway on a clear day is illogical. Are we sure this is the case?"
- **Exploratory follow-up** ([findings §6](../findings/2026-10-07-g70-milder-variants.md)):
  - speed is not the explanation;
  - on the exact same road samples, B's request, wheel and lane weave are above every A drive;
  - against the light-matched midday drive `0x20`: request +9%, wheel +21%, lane +30%.
- **Revised reading:** step 2a's "exogenous" reading was too blunt, because the request sits inside the closed loop. **D2C4 is the most likely cause of the weave increase.** It is one drive, and the date and traffic are not excluded.
  - B's calmer twitch-band request was probably daylight (matches `0x20`).
- **This supersedes items 2, 6 and 10.1 above, and the "keep D2C4" recommendation loses its main support.**
  - The user's decision is now between **rolling back to `c027a92857`** and keeping D2C4 for more A/B data, with weave as a known likely cost.
  - The MV variants are expected to weave too (Amendment 8: 67–87% of D2C4's small-signal weave-band lag).
  - A twitch fix that doesn't slow small corrections is an open design question; the model found none among MV1–MV9.

## 12. Weave root cause (2026-10-07, end of session; [findings §7–8](../findings/2026-10-07-g70-milder-variants.md))

- **User:** "I'd rather find a logical defensible root cause for the weave in D2C4 because it seems to have addressed a lot of the other concerns."
- **Pre-registered log decomposition.** On B the logged setpoint is post-filter, so the request → setpoint step is C4 alone and setpoint → wheel is the rest.
  - **At 0.2–0.4 Hz (the car's ~3 s weave band):** B's wheel lags the request 18° more (CI excludes 0): 8° from C4 (exactly as designed) and 10° after it (the deadzone, small-signal). The small-amplitude response is weaker and later.
  - Wheel time in holds 40% → 59%; tracking-error weave +18%, twice as coherent with the lane offset.
  - **The stick-slip model predicts the same split at 0.2–0.4 Hz** (C4 7°, D2 9–10°, together 17–18°). It over-predicts at 0.4–0.7 Hz.
- **Reading:** D2C4 removes about 18° of phase margin from the lane-keeping loop at its weave frequency, roughly half from each part. Verdicts: H1 supported, H2 partial, H0 not favoured. One B drive.
- **Next steps** (replacing §10.2–3):
  1. **Decide whether to run an on-car isolation**: a D2-only build (drop the C4 table entry) and a C4-only build (deadzone 0), each on the same road in daylight. Each needs the code change, tests, QA, artifacts and per-action device authorization.
  2. Offline: design and pre-register candidates that keep the twitch reduction while giving back phase at 0.2–0.4 Hz (e.g. a phase-lead term in that band, or a smaller small-signal deadzone effect), ranked on the **0.2–0.4 Hz** lag, where the model now matches the car.
