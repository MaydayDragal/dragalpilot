# soundd/micd audio start-up: longer retry + engagement blocked until audio is ready (2026-10-05, session 8)

**Status:** committed on `dragal/custom` as `c027a92857` (parent `82f58a9a8c`). Tests, lint and focused review are done. Installed and active on the device since the 2026-10-05 22:33 EDT reboot. **Check drives 2026-10-06 (8 routes):** no soundd/micd crash, gate cleared 11–31 s after each start, one early engage attempt correctly refused (see the [deployment proposal](../proposals/2026-10-05-soundd-audio-gate-deploy.md) check-drive record).

Basis: [device-errors findings](2026-10-05-g70-device-errors.md) §1 and Follow-up 2. On this comma 4:
- the audio device becomes openable 25–39 s after the manager starts;
- soundd/micd give up after 10 × 3 s and are not restarted while onroad, so `processNotRunning` blocks engagement or soft-disables;
- this happened on 5 of 21 cold-boot starts.

**User decision (2026-10-05):** option B, a longer retry *plus* blocking engagement until the audio works.

## Requirements (as given to the reviewer)

1. soundd and micd retry for ~90 s (30 × 3 s) instead of 30 s.
2. Engagement, including MADS lateral, is blocked until soundd has actually opened its output stream. The block clears for the rest of the onroad session once the stream is open. If soundd later dies, `processNotRunning` applies as before.
3. No behaviour change in process replay (`REPLAY`) or simulation (`SIMULATION`).
4. No car-side behaviour change. `card.py` L293 gates its CAN output on `selfdriveInitializing`, so that event must not be used.
5. Fail closed: if readiness can't be established, engagement stays blocked, with a visible reason.
6. No native changes, no new params keys, no cereal schema changes. The device runs a prebuilt branch; Python is used as is.
7. A meaningful no-entry reason is shown.
8. Negligible device CPU (selfdrived runs at 100 Hz).

## Design

| File | Change |
|---|---|
| `openpilot/selfdrive/ui/soundd_ready.py` (new) | Marker file `<shm>/soundd_stream_ready[_<OPENPILOT_PREFIX>]` holding soundd's PID, written atomically (temp file + `os.replace`), following the existing `/dev/shm` precedent in `common/hardware/comma/modem.py`. Provides `clear()`, `mark_ready()` (fails closed; logs; removes its temp file), `is_ready(pid)` (missing or corrupt → not ready), and `audio_ready(processes, received)`. That function returns true when soundd is running and the marker holds its PID, or when soundd isn't managed or shouldn't be running; it returns false before managerState is received. |
| `openpilot/selfdrive/ui/soundd.py` | Retry `attempts=10` → `30`. `soundd_ready.clear()` when the thread starts, `soundd_ready.mark_ready()` right after the stream opens. |
| `openpilot/system/micd.py` | Retry `attempts=10` → `30`. |
| `openpilot/selfdrive/selfdrived/selfdrived.py` | `audio_pending()`: false under REPLAY/SIMULATION; otherwise checks `audio_ready` at 10 Hz and latches once ready. `process_not_running(not_running)` = real non-ignored process down **or** `audio_pending()`. It feeds the existing `processNotRunning` event, which is NO_ENTRY and SOFT_DISABLE; nothing can be engaged before the latch, so the soft-disable never fires because of the gate. |
| `openpilot/selfdrive/selfdrived/events.py` | `process_not_running_alert`: if no process is actually down, the cause is the audio gate, so the text is "Process Not Running: soundd (audio starting)". No file access. |

**Confirmed source facts (82f58a9a8c):**
- `managerState.pid` is soundd's own PID: `PythonProcess` runs `mod.main()` in its child (`system/manager/process.py` L21–37, L177).
- MADS checks NO_ENTRY before enabling, from disabled and from paused (`sunnypilot/mads/state.py` L39–40, L90–93, L116–120). Route `16` showed `processNotRunning` blocking a MADS engage.
- `processNotRunning` has no other consumers (only `selfdrived.py` and `events.py`).

**Side effects (accepted, same as for any down process):**
- While the gate is active (≤ ~40 s after onroad), the camera malfunction/frame-rate checks and the generic `commIssue` catch-all are suppressed; engagement is blocked anyway.
- If MADS entered *paused* (an enable attempted in Park/Reverse) during the window, it engages lateral silently once both gear and audio allow. That is existing MADS behaviour for any NO_ENTRY.

## Validation (offline, x86 WSL)

- **x86 test harness** (new, outside the repo): `E:\DragalPilot\cache\x86-openpilot\`. It contains x86 builds of `libparams_c.so`, `msgq.ipc_pyx` and `visionipc_pyx`, compiled from the checkout's own sources with the venv's bundled capnproto/json11 plus apt `libzmq3-dev` (`build_x86_openpilot_shim.sh`), and a `sitecustomize.py` shim loaded only via `PYTHONPATH` by `run_s8_tests.sh`.
- **Baseline on the unchanged `82f58a9a8c`:** 47 existing tests (soundd, selfdrived alerts/state machine/alert manager, MADS state machine/steering mode): **OK** (log `s8-tests-baseline-20261005-211903.log`).
- **Candidate** (after the review fixes): **80 tests OK** = 47 existing + 33 new (`test_soundd_ready.py`, `test_audio_gate.py`; log `s8-tests-candidate3-20261005-213333.log`). `ruff check` clean (ruff 0.16.3); `codespell` clean; `ty check` clean on the new module.
- **New tests cover:**
  - marker path and prefix;
  - missing, stale, corrupt and overwritten markers;
  - write failure (fails closed, no temp file left);
  - `clear()`;
  - `audio_ready` for every process state;
  - soundd clears first and marks only after the stream opens (never if it fails);
  - the 30 × 3 s budget for soundd and micd (success on attempt 30, give-up after 90 s);
  - the gate (pending until ready, managerState missing, latch, stale marker, 10 Hz check, REPLAY/SIMULATION bypass);
  - the `processNotRunning` decision (gate, ignored processes, real crash);
  - the alert text (gate, real crash, crashed soundd listed once, no marker read).
- **Mutation check** (WSL clone, each reverted, files verified identical afterwards; `mutate_s8_audio2.sh`). All 7 mutations make tests fail:
  - retry 30 → 10;
  - gate disabled;
  - crashed soundd treated as ready;
  - marker written before the stream opens;
  - gate removed from the decision;
  - alert text unchanged;
  - no clear on start.
- **Not covered:** a full `SelfdriveD.update_events` run (no existing test constructs `SelfdriveD`; it needs CarParams and live messaging), process replay, and any on-device run.

## Focused review (CLAUDE.md §5)

One independent adversarial reviewer (general-purpose agent). It was given the uncommitted diff, the requirements above and the test command, and was told not to modify the checkouts.
- **Verdict: no blockers or major defects.** It confirmed the placement, the `card.py` independence, MADS honouring the block, the PID semantics, fail-closed behaviour, and 73/73 tests passing at that point.

| # | Finding (severity) | Disposition |
|---|---|---|
| 1 | Alert text changed under REPLAY/SIMULATION: the callback read the marker directly (minor, confirmed) | **Fixed:** the callback no longer reads the marker; "audio starting" is shown only when no process is down, which can't happen under REPLAY/SIMULATION. Test `test_no_marker_lookup_in_replay`. |
| 2 | Alert text vs gate could disagree (≤ 90 ms blank text; stale-marker text) (minor) | **Fixed** by the same change. |
| 3 | Callback read the file at 100 Hz in MADS paused state (minor) | **Fixed:** no file access in the callback. |
| 4 | Gaps: `update_events` wiring, mark-after-stream ordering, REPLAY callback (minor) | **Partly fixed:** decision extracted to `process_not_running()` and tested; ordering and REPLAY-callback tests added; mutations M4/M5 now caught. A full `update_events` test is still not done (see above). |
| 5 | A corrupt marker would raise `UnicodeDecodeError` in selfdrived (info) | **Fixed:** `is_ready` catches `ValueError` too. Test added. |
| 6 | Marker left behind under test prefixes; temp file leaked on write failure (info) | Temp leak **fixed** (test added). Prefix markers are removed by the tests' teardown; on device there is no prefix. |
| 7 | PID reuse could validate a stale marker (info, speculative) | **Hardened:** soundd clears any old marker at start. |
| 8 | Diagnostics suppressed while pending; a permanent "audio starting" text if the marker can't be written (info) | Accepted (documented above). A write failure is logged with `cloudlog.exception`. |
| 9 | MADS silent engage when the gate clears after a paused enable (info) | Existing MADS behaviour; documented; reported to the user. |
| 10 | `soundd_ready.py` must be deployed with the other files (info) | Covered by deploying one commit (proposal). |

QA stage: **focused review done; fixes applied and verified** (80/80, mutations). Two-round QA not performed.
