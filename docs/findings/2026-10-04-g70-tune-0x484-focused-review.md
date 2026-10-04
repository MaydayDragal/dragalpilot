# Focused adversarial review: G70 tune + camera-SCC 0x484 safety change (2026-10-04)

**QA type:** focused review (one adversarial reviewer). Two-round QA was not performed.

- **Reviewed snapshot:** `dragal/custom` `7e9d0755d9..c1806292fa` (tune, steerRatio, 0x484 safety + tests, harness fix ×2).
- **Reviewer inputs:** the diff, neutral requirements, raw evidence (torqued/paramsd values, bus-0 0x484 observation) and the test list. The reviewer was instructed not to read `docs/`, findings, handoffs or memory; this was not technically enforced. It ran read-only checks in the WSL clone, including ruff, a car-params probe and a libsafety per-config probe.
- **Not in the review:** the firmware commit `cb66129698` was made during the review. Its validation is the reproducible build (see the proposal).

## Findings and dispositions (each verified by the coordinator against the code)

| # | Severity | Finding | Verification | Disposition |
|---|---|---|---|---|
| 1 | major (evidence) | With `check_relay = true`, a 0x484 frame on bus 0 more than ~1 s after the Hyundai mode starts sets relay malfunction. That blocks **all** forwarding, including the camera's SCC/FCA, so stock ACC/AEB would stop reaching the car. The original panda #2045 blocked only in the forward hook, with no relay check. | Confirmed: `safety.h` `safety_fwd_hook` (`blocked = relay_malfunction \|\| …`) and the `stock_ecu_check` loop. This is the same exposure 0x340/0x485 already have under `check_relay`. | **Accepted with evidence** (the reviewer's condition): (a) all 5 G70 drives replayed through the new safety from the logged Hyundai-mode start: 9.10M rx, 0 invalid, **no relay malfunction**, no relay-checked address on bus 0 (`E:\DragalPilot\logs\rx-relay-replay-20261004.log`); (b) `test_models` for `HYUNDAI_KONA_2022` and `HYUNDAI_KONA_EV_2022` reference routes, including `test_panda_safety_rx_checks`: 14 tests OK (`E:\DragalPilot\logs\test-models-kona-20261004-112243.log`). Residual: a car-side 0x484 sender in an unobserved state is still possible; the failure is fail-silent. |
| 2 | minor/info | 0x484 is now TX-allowed with no content check on non-long camera-SCC. | Confirmed (probe and code). openpilot never builds 0x484; no actuation path; LKAS11 limits unchanged. | Accepted (same as upstream PR); noted in the proposal. |
| 3 | info | Blocking the camera's 0x484 may have other cluster/HDA side effects; not validated on the car. | Agreed. | Already listed as unvalidated in the proposal; part of the next drive's experiment. |
| 4 | info | Scope: only the non-CAN-FD camera-SCC non-long configs (KONA_2022, KONA_EV_2022, G70_2024); long camera-SCC, radar-SCC and legacy unchanged (probe table). | Matches the code and tests. | — |
| 5 | minor | The harness skip ("same base name") could in future hide a real cross-variant TX difference. | Agreed. | **Fixed** in `82f58a9a8c`: also requires an identical `TX_MSGS`. |
| 6 | info | The camera-SCC test now declares CLU11 on bus 2 (stricter, correct for this tree). | Agreed. | — |
| 7 | info | Torque values: torqued cache reset by design; new clip windows [2.8, 5.2] / [0.035, 0.105] contain all observed raw estimates (the old window [1.89, 3.51] would have clipped them). V0 uses the offline values until torqued is valid. The comment range was slightly off. | Agreed. | Comment **fixed** in `82f58a9a8c`. |
| 8 | info | steerRatio change has ~no effect while paramsd's learned value restores. | Agreed (already in the proposal). | — |
| 9 | info | Pre-existing: camera-SCC RX checks always include 0x391 regardless of the LDA flag. | Out of scope. | Not changed; noted. |

## Post-fix validation (`82f58a9a8c`)

All of these pass (`E:\DragalPilot\logs\tests-20261004-112317\`, `safety-cov-20261004-112506.log`):
- targeted car tests;
- full safety suite + 100% coverage;
- MISRA.

`hyundai.h` is unchanged since `c1806292fa`, so the firmware in `cb66129698` still corresponds to the code.

**QA status:** focused review complete, all findings dispositioned. Two-round QA not performed.
