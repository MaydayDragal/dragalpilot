# Focused adversarial review: GENESIS_G70_2024 port (2026-10-04)

Type: **focused review** (CLAUDE.md §5). One adversarial reviewer and coordinator verification. This is not two-round QA.

## Setup

- Reviewed: `dragal/custom` @ `5cdfe3c082180b3c7e2b1298f0a8517d1d8e435f` against baseline `0b2c431d3abab630df0a32f53236944855a91aa3`, with upstream reference opendbc `cfb743f4`.
- Reviewer: one fresh general-purpose subagent. Inputs: the diff, neutral requirements, and the raw evidence (device FW log, rlogs).
  - It was told not to read the outer `docs/`, `CHANGELOG.md`, `README.md`, `E:\DragalPilot\analysis` or the coordinator's scripts.
  - Isolation was instruction-based only, with no access restrictions. CLAUDE.md is auto-loaded into every agent's context, and the `dragal/custom` commit messages were visible (one briefly explains the EPS addition). For a focused review this is disclosed, not enforced.
- Constraints: no device access, no repo edits, own WSL worktree (removed afterwards). Scratch: `E:\DragalPilot\scratch\review-g70\`.

## Findings and dispositions

| # | Finding (reviewer severity) | Coordinator verification | Disposition |
|---|---|---|---|
| 1 | The second reference route `a6310918f9699ef5/2024-02-27--20-17-09` in `routes.py` has no traceable source (minor) | **Partly agreed.** Both routes appear in the commaai/opendbc PR #1134 description ("route with openpilot" / "route with stock system"), copy at `E:\DragalPilot\scratch\pr1134.json`. So the value is sourced. The comment did not say where it came from. | Fixed: the comment now cites PR #1134 and labels each route. `dragal/custom` @ **`f9325699ed`** (comment-only). |
| 2 | Specs (steerRatio 12.9 "guesstimate", mass 1769) and torque `[2.7, 2.7, 0.11]` are unvalidated. The upstream reference car was a 3.3T. The jerk test margin is ~4.92 vs 5.0 (minor) | Agreed. These are upstream values; the panda limits (384/3/7) are unchanged. | No code change. Needs supervised validation; carried into the deployment plan. |
| 3 | Alpha longitudinal is offered (no `UNSUPPORTED_LONGITUDINAL`/`LEGACY` flag) on an unvalidated camera-SCC platform (minor) | Confirmed in `values.py` (no flag) and `interface.py:91`. It is opt-in through the toggle. | **User decision (2026-10-04): leave the port as upstream wrote it.** The user will not enable the alpha-long toggle. This is enforced by procedure, not by code; it is carried into the deployment plan. |
| 4 | The NNLC model falls back to the older-generation `GENESIS_G70` model (non-exact, ~0.815 similarity) (info) | Confirmed: `substitute.toml` has no G70_2024 entry. The similarity figure was not re-derived. | Only applies if NNLC is enabled. Keep it off for first validation (deployment plan). |
| 5 | `CARS.md` not regenerated (info) | Not re-checked. The baseline already differs from its generator, and no test covers it. | No action. |
| 6 | The EPS FW entry restricts matches to this car's exact EPS FW (info) | Agreed. Another G70 2024 with different EPS FW won't match and will fall back to dashcam, which is fail-safe. | No action. Intended (it is required by `test_platform_code_ecus_available`). |

New item from verifying #1: the PR #1134 description says the author used **Harness F**, while the port's docs entry (upstream `cfb743f4`) says `hyundai_l`. That field affects docs and the parts list only. **Resolved 2026-10-04:** the user confirmed Harness F is installed. The docs entry was changed to `CarHarness.hyundai_f` in `dragal/custom` @ **`7e9d0755d9`** (docs-only; `car_list.json` has no harness field).

## Reviewer's independent evidence (not re-run by the coordinator unless noted)

- The diff touches only `opendbc/car` and `opendbc/sunnypilot/car`, with no `safety/` files (coordinator-confirmed in session 2).
- CarParams, CarParamsSP and torque params are identical for all 270 baseline platforms; only the new platform is added.
- LKAS11 CRC8 matched 50,151 of 50,151 frames. The bus-0 send-order pattern and the radar FW string ("RDR", not "SCC") suggest camera-SCC. This is circumstantial, not confirmation.
- Simulated TX (stock long): panda accepted 0x340 and 0x485, and all LKAS11 checksums are CRC8. With alpha long, the 0x7D0 tester-present is blocked. That is existing behaviour for classic camera-SCC cars.
- A broader unittest set (522 tests, OK) and `test_car_interfaces` (270, OK).

## Final validation (coordinator)

On `f9325699ed` (WSL clone, log `E:\DragalPilot\logs\tests-20261004-001225\`), all exit 0: `test_car_list`, `test_routes`, `test_docs`, `test_hyundai`, `test_fw_fingerprint`, `safety test_hyundai` + `test_hyundai_canfd`. The NNLC test was not run (x86 limitation, see `docs/baseline.md`).

## QA status

Focused review complete. One agreed fix is applied and verified, and one item awaits a user decision (#3). Not done: two-round QA. Real-world validation has not started.
