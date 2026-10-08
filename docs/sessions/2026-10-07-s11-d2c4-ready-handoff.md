# Handoff: session 11 (2026-10-07): D2C4 validated offline, implemented, full QA, ready to install; next: milder variants

Written 2026-10-07 at the user's request: "Get D2C4 ready for implementation once the device becomes available. Once it is fully ready for implementation, create a handoff and a kickoff prompt for the next session to do the milder variant testing. Also write a kickoff prompt scoped just for the installation of D2C4 for when the device becomes available."

- **Main thread.** Supersedes [2026-10-07-s10b-d2c4-validation-handoff.md](2026-10-07-s10b-d2c4-validation-handoff.md).
- **Kickoffs:**
  - milder variants (next session): [2026-10-07-s11-milder-variants-kickoff.md](2026-10-07-s11-milder-variants-kickoff.md);
  - install only (when the device is available): [2026-10-07-s11-d2c4-install-kickoff.md](2026-10-07-s11-d2c4-install-kickoff.md).
- **Token usage:** no reliable cumulative figure available.
- Reconfirm everything at the next session start.

## 1. Objective

Make sunnypilot drive the user's 2024 Genesis G70 well.
- **Primary lateral complaint:** the steering wheel is "twitchy": constant small corrections on straight roads, with clear lanes.
- Weaving also matters.
- **Candidate fix:** D2C4 = `steeringAngleDeadzoneDeg` 0.4° + a causal 2 Hz desiredCurvature low-pass, car-scoped.

## 2. User instructions and decisions (this session; earlier standing rules still apply)

- "Use [the s10b kickoff]": the 4 steps (review, offline checks, implementation + QA, on-car A/B with per-action authorization), each evaluated on wheel jitter, weaving and comfort.
- Step 1 boundary: "Swap validation first".
- After the swap validation failed by 1 point on E2 tracking: **"Accept costs, test transients"**. Also: explore the CPU's advanced instruction sets for the tooling.
- After the transient red flags: **"Get D2C4 ready for implementation once the device becomes available"**, then this handoff, the milder-variant kickoff and the install-only kickoff, and a project memory update about the CPU instruction-set findings.
- **New standing rule (in CLAUDE.md §8):** the VM is dedicated to the project. Use all compute, memory and storage. Parallelize with bit-identical results where possible; a method change is a declared deviation.
- **Standing:**
  - video pulls and tool installs authorized;
  - read-only device pulls unrestricted in scope;
  - unneeded files may be deleted;
  - no targeted test re-runs for docs-only commits;
  - durable rules go into CLAUDE.md;
  - **every device change, install and reboot needs explicit per-action authorization at the time.**
- **Outer docs commit:** still not requested. Everything since `606c36b` (sessions 8–11) is uncommitted.

## 3. Exact revisions and workspace (confirmed 2026-10-07 ~13:10 EDT)

- **Baseline:** `dev` @ `0b2c431d3a…` (unchanged).
- **`sunnypilot/`:** `dragal/custom` @ **`89bbe60ab127cf71d238856a19c1e74b16bc36bd`** (local, not pushed), clean.
  - **Installed on the device:** `c027a92857` = `dragal/custom~4`.
  - New commits: `268040c361`, `8593b66148`, `66b22ef83f`, `89bbe60ab1`.
- **WSL clone** `~/src/sunnypilot`: detached at `89bbe60ab1`, clean.
- **Outer `main`** @ `606c36b` = `origin/main`, with uncommitted:
  - modified: `CHANGELOG.md`, `CLAUDE.md`, `docs/baseline.md`, `docs/local-storage.md`, `docs/sessions/README.md`, `docs/findings/2026-10-04-g70-tune-0x484-first-drive.md`, **`docs/findings/2026-10-07-g70-twitch-root-cause.md`** (session 11 errata);
  - new: the session 8–10 docs (as in the s10b handoff), plus **`docs/findings/2026-10-07-g70-d2c4-validation.md`**, **`docs/proposals/2026-10-07-g70-d2c4-deploy.md`**, and this handoff + 2 kickoffs.
- **Data root `E:`:** UniqueId `daa460f7…`, about 229 GB free.
- **Device:** **D2C4 installed 2026-10-07 13:33 EDT** (`c027a92857` → `89bbe60ab1`), rebooted, post-boot check OK at 17:36Z: `.104`, offroad, `DisableUpdates=1`, firmware unchanged. Deployment record in the proposal. Cache files show a probable drive at ~17:27Z, not pulled yet.

## 4. Completed work and evidence

All details are in [D2C4 validation findings](../findings/2026-10-07-g70-d2c4-validation.md). Evidence levels: offline model evidence plus source/test evidence. **Nothing has been validated on-car.**

1. **Step 1: focused adversarial review** of the session 10 harness (§1). No blocker.
   - **Fixed in the harness:**
     - `latAccelOffset` was missing in the controller port;
     - the integrator did not start from the logged value (source fact: V0 never resets its PID);
     - A7 metrics are now computed on the quantized angle;
     - reversal and comfort metrics added;
     - independent D2/C4 reference paths.
   - **Checks:** bit-exact on 10 runs × 5 variants. Re-run: verdicts unchanged.
   - **Method findings:** tracking depends on the θ0 window; the held-out E1/E4 were reused to choose the candidates.
2. **Step 2:**
   - **2e comfort baselines** (Amendment 5):
     - the IMU validity gate failed for E3/E4: its reference was poor; the IMU agrees with the gyro;
     - the IMU is road-dominated in the twitch band (coherence with steering 0.06–0.33 above 0.7 Hz), so on-car comfort needs steering-coherent metrics;
     - the steering-proxy comfort follows the jitter;
     - the 20 Hz EPS line is engaged-only.
   - **2f:** restore keys unaffected (source facts).
   - **Amendment 6 swap validation** (E4-only plant, D2C4 tested on E2/E3):
     - twitch and comfort reductions replicate: jumps −45/−52%, T −33/−41%, W −20/−25%;
     - tracking +21.0% on E2 fails the 20% limit by 1 point.
     - The user accepted the tracking cost.
   - **Amendment 7 transients:**
     - red flags R5 (0.6 Hz phase +17–19°, from C4), R3 (slower small-step settling at 75 mph, from D2) and C3 (curve-window error +28%, lag +0.09 s; the two halves add up);
     - rise and overshoot unchanged.
   - **2c/2d:** no model for 35–55 mph or low speed; no engaged standstill data (lateral control is never active at a standstill).
3. **Step 3: implementation, tests, QA** (§3):
   - **Code:** car-scoped D2 (Hyundai interface table + `configure_torque_tune` override) and C4 (V0 `FirstOrderFilter`).
   - **Tests:** 10 new tests; 24/24 lateral tests; car suites OK; 6/6 mutants caught.
   - **Source = harness:** within 1.9e-5 counts.
   - **Full two-round QA:**
     - round 1 cooperative;
     - round 2 adversarial: one major fixed (the deadzone reset under NNLC/Enforce);
     - round 2 isolation was instruction-plus-package, remote not confirmed.
4. **Deployed 2026-10-07** (user-authorized install and reboot; [proposal](../proposals/2026-10-07-g70-d2c4-deploy.md) deployment record):
   - artifacts built at `89bbe60ab1`;
   - dry run passed, including the configuration-guard negative test;
   - on-car A/B protocol pre-registered (§6).
5. **Erratum:** session 10's angle → lateral-accel conversion ignored the understeer factor. Twitch jumps are ≈ 0.09–0.11 m/s² at 75 mph, not 0.13–0.18. The simulations are unaffected.
6. **Tooling:**
   - identification and sweeps parallelized with bit-identical results (identification 57 min → 7 min);
   - CPU instruction-set exploration: see §7.

## 5. Open hypotheses / questions

- Is D2C4's transient cost noticeable on the road (0.09 s extra lag in curve entries, +28% curve-window error), and does it change the lane position? This can only be answered on-car.
- **Milder variants** (next session's task): can a smaller deadzone and/or a higher cutoff keep most of the twitch reduction with less transient cost? A constraint from the source facts: the 2 Hz filter alone adds atan(0.6/fc) of phase lag at 0.6 Hz. Keeping R5 (≤ 15°) needs fc ≳ 2.5 Hz, given D2's own 1–2°.
- **Data independence:** no logged era is untouched by candidate selection any more.
  - E1/E4 were used for D2C4's design.
  - E2/E3 were used for its swap evaluation, not its selection; any variant choice made on them uses them up.
  - The on-car A/B is the independent test.
- 35–55 mph and low speed are not modelled; stop-and-go is not covered (never active at a standstill).
- The 20 Hz EPS pulse source is unresolved (carried over).
- Carried over: HDA-deselected drive; stop-and-go protocol; the 0x484 forwarding-rule round.

## 6. Validation limits and QA stages

- **D2C4 code `89bbe60ab1`:**
  - full two-round QA done (round 2 isolation caveat: enforced isolation not confirmed);
  - offline/source/test evidence only;
  - not installed, not validated on-car, not authorized for deployment.
- **Offline model:**
  - a single-input stick-slip plant at 55+ mph, with logged requests replayed (no outer loop) and no tyre/yaw dynamics;
  - adequacy validated on held-out eras;
  - the curve regime is not identified, and θ0 is built from the logged angle.

## 7. Artifacts

**Docs:**
- [validation findings](../findings/2026-10-07-g70-d2c4-validation.md) (§1 review, §2 pre-registrations and results, §3 implementation and QA);
- [deployment proposal](../proposals/2026-10-07-g70-d2c4-deploy.md);
- root-cause findings (errata).

**Data (`E:\DragalPilot\analysis\g70-d2c4-20261007\`):**

| Folder / file | Contents |
|---|---|
| `imu/` | 23 routes |
| `comfort/` | baselines, gate diagnostic |
| `rerun_v2/` | session 10 results on the fixed harness |
| `plant_cl_e4/` | E4-only plant |
| `a6/` | swap validation |
| `a7/` | transients, plus the exploratory split |
| `inventory.json` | engaged-data inventory |
| `source_replay*.json` | source vs harness |
| `qa/` | the step 1 reviewer's work, round 1 probes, round 2 package |

**Deploy:** `E:\DragalPilot\deploy\g70-d2c4-20261007\` (bundle, `install.sh`, `precheck_reboot.sh`, `postboot_check.sh`, templates, `mk_install.sh`, `sim_install.sh`, `artifacts.sha256`, dry-run log).

**Scripts (`E:\DragalPilot\scratch\wsl\sng\`):**

| Group | Scripts |
|---|---|
| Harness (fixed; `*.s10.py.bak` = session 10 originals) | `s11_*` |
| IMU, comfort, gate | `s12_imu_extract.py` (+ `run_s12_imu.sh`), `s12_comfort.py`, `s12_gate_diag.py` |
| Summaries | `s12_summary_v2.py`, `s12_summary_a6.py` |
| Amendment 7 | `s12_transient.py`, `s12_curves.py` (env `S12_VARIANTS` for other variants) |
| Inventory, profiling | `s12_inventory.py`, `s12_profile.py` |
| Implementation checks | `s12_source_replay.py`, `s12_mutations.sh`, `s11_replay_check.py`, `s11_par_check.py` |
| Runners | `run_s11_rerun_v2.sh`, `run_s11_a6.sh`, `run_s11_car_tests.sh`, `run_s8_tests.sh` (x86 shim), `run_s10_vid.sh` |

- **Parallel use:** `s11_plant_cl.py` (objective over 6 processes), `s11_eval.py` (per route), `s11_robust.py` (per perturbation). Outputs are byte-identical to serial; set `S11_SERIAL=1` for serial evals.
- **Logs:** `E:\DragalPilot\logs\s10-s11*`, `s11-*`, `s8-tests-s11-*`, `s8-tests-mut-*`.
- **CPU/instruction-set exploration:** see §7.1 and project memory.
- **Disposable** (kept as listed earlier): `temporary/s9-*`, `temporary/vidwheel-tmp`, `temporary/tmp*.so`. Keep `temporary/s11-smoke` (cited by the root-cause findings).
- **Also left for the user:** empty folders `C:\Program Files\Git\mnt\e\DragalPilot\analysis\g70-d2c4-20261007\imu`, created by a mis-launched runner. The safety check blocked removing `/mnt`.

### 7.1 CPU instruction-set exploration

Done; details in project memory `cpu-simd-tooling` and the agent's logs `logs/s10-s13-*`.

- **CPU:** Zen 5, 6 vCPUs, full AVX-512. numba already targets `znver5`.
- **The closed loop is latency-bound:** about 5 ns per Euler substep (a divide chain), about 70 ns per sample, scalar.
  - The earlier "1.4 µs/sample" profile was a JIT warm-up artifact.
- **Real hot spot:** θ0 was recomputed over the whole route for every run (80% of the time).
- **`s13_sim.py`:** a windowed θ0, numba `sosfiltfilt` and O(n) `jumps_hold`.
  - Drop-in for `s11_eval.simulate` / `s11_plant_cl.objective(_par)`.
  - **About 11× serial and 8× with 6 processes, bit-identical** (11,414 checks; re-run by the coordinator: 0 mismatches).
  - **Not yet wired into the s11/s12 scripts.** Adopt it next session, with a before/after byte-identical output check.
- **AVX-512 lanes across independent sims** (`s13_simd2.py`): 2.9× per core, bit-exact. Useful for variant grids and perturbation sweeps; a prototype only.
- **FMA/fastmath:** no effect on any metric. Not used.
- **Accuracy:** 10 substeps bias ≤ 2% on jumps, ≤ 0.6% on other metrics; 40 converged. Changing the substep count needs a re-fit of both plants.

## 8. Running operations

None. No background agents, no WSL jobs.

## 9. Device state and SSH ownership

- No SSH connection is open. This session made three sequential connections (install, reboot precheck, post-boot), all closed.
- Before any device access the user must confirm the current address, the inactive state and the scope (CLAUDE.md §6).

## 10. Ordered next steps

1. **Next session (milder variants, offline):** follow the milder-variant kickoff.
2. **Done in session 11 (D2C4 installed).** The install-only kickoff is no longer needed. Next device step: the user's A/B drives (proposal §6).
3. **After the user's A/B drives:**
   - read-only pull (rlogs + both road videos + phone wheel videos), authorized at the time;
   - analysis against the pre-registered A/B criteria (proposal §6).
4. **Outer docs commit** when the user asks.
