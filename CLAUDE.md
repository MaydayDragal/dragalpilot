# CLAUDE.md — dragalpilot project rules

Durable rules for every Claude Code session and every delegated agent/tool in this project. Source of these rules: [docs/kickoff/Startup.md](docs/kickoff/Startup.md) (verbatim original kickoff). If this file and the kickoff disagree, flag it to the user; do not silently pick one. If an `AGENTS.md` is ever added, keep it consistent with this file.

The user supplies goals. Never invent a vehicle configuration, complaint, diagnosis, or tuning target.

## 0. Session start

1. Read this file, [docs/sessions/README.md](docs/sessions/README.md) (latest handoff), [CHANGELOG.md](CHANGELOG.md), and [docs/local-storage.md](docs/local-storage.md).
2. Inspect the actual workspace (outer repo status, `sunnypilot/` branch/HEAD/status, submodule status) and continue from the checkpoint. Distinguish last-observed state from freshly confirmed state.
3. Reconfirm transient device state/address before any device access. Do not import permissions from other projects or earlier sessions.

## 1. Layout and baseline

- Outer project (this repo, `MaydayDragal/dragalpilot`): `CLAUDE.md`, `README.md`, `CHANGELOG.md`, `docs/`.
- `sunnypilot/`: clone of `https://github.com/sunnypilot/sunnypilot.git`, **gitignored by the outer repo** (not vendored, not a submodule). Its revision is recorded in [docs/baseline.md](docs/baseline.md).
- The baseline is the exact recorded `dev` commit. Never silently advance it. Upstream updates are deliberate, recorded (old → new SHA, reason, validation) in `docs/baseline.md` and the changelog.
- Customization happens on a separate local branch in `sunnypilot/`, never directly on `dev`/baseline.
- Discover layout and tooling from the checked-out revision; don't assume older openpilot/sunnypilot structure. Inspect the *pinned* submodules (e.g. `opendbc_repo`, `panda`), not current upstream.

## 2. Technical approach

- Before proposing a customization, trace input/configuration → perception/model → planning → control → vehicle interface/CAN → safety, including activation conditions, units, timing, state transitions, limits, and safety checks. Identify the responsible layer before changing it.
- Never generalize control behavior or tuning across vehicle platforms.
- Distinguish evidence types: source-level request, transmitted command, hardware acceptance, measured physical response.
- Latest dev source is a research baseline, not proof of what is installed or validated. Record installed software/models/settings/dependency identities separately when evidence appears.
- **Never bypass safety checks or widen safety limits** as a shortcut to performance.

## 3. Local-only data storage

Data root: **`E:\DragalPilot`** (see [docs/local-storage.md](docs/local-storage.md) for layout, naming, and verification).

- ALL logs, videos, frames, datasets, analysis outputs, caches, scratch, partial transfers, and temp files go under the data root. **Never in the outer repo, `sunnypilot/`, or any submodule — not even in ignored folders.** No Git LFS for data, no force-adds, no symlinks into the repo.
- Only source code, durable docs, and small curated findings live in the project.
- **RLOGS only, never QLOGS.** If rlogs are unavailable, report the gap; do not fall back.
- Group recordings by route start time in **America/New_York**, recording original timestamp, UTC offset, route/segment IDs, device ID when needed. Keep routes together across midnight; prevent collisions (including DST-repeated local times).
- Verify storage identity, availability, writability, and free space before data operations. If the data root becomes unavailable, **stop data work** — never fall back to the checkout or another disk.
- Use per-command temp/cache env vars (`TMP`, `TEMP`, `TMPDIR`, tool-specific cache vars) and explicit output paths pointing at the data root. Watch for tools that ignore them (test runners, submodule commands). No unnecessary machine-wide config changes.
- Before any commit: inspect outer repo status, `sunnypilot/` status, and relevant submodules for stray data/artifacts. Ignore rules are a backstop only.

## 4. Evidence and testing

- Label claims as: confirmed source fact (file + revision), observation (recording interval / device state), hypothesis, or unverified assumption. State limitations plainly.
- Diagnose before tuning. One bounded change at a time against the preserved baseline. Before an experiment, define question, expected behavior, comparison conditions, success and failure criteria.
- Verify source, model, config, schema, units, timestamps, and activation state before interpreting signals. Align logs/video by recorded timestamps and verified stream mappings; label approximate alignment. Missing data is unknown — not zero, not "normal".
- Prefer local analysis of existing recordings. Reproducible tools; record commands and dependency versions; reuse verified caches.
- Behavior changes/bug fixes need meaningful regression and boundary tests (activation/deactivation, resets, invalid inputs, limits, timing) plus relevant existing tests. Tests verify behavior, not mirror implementation.
- Use only the checkout's supported build/lint/test/replay/sim/safety-test tooling for the changed layer. Never invent a universal test command or claim a check ran that didn't.
- Baseline vs candidate on the same eligible inputs. Keep exploratory tuning separate from held-out validation. No causal or physical-performance claims beyond what data supports.
- Report exact commands, exit status, revision tested, and skipped/unavailable checks.
- Offline tests, replay, and review approval ≠ real-world performance ≠ deployment authorization. Distinguish source correctness, offline evidence, inactive-device verification, and user-supervised operational validation.
- Before declaring done, independently inspect final changes and evidence. An agent's completion report is not verification.

## 5. QA process

Coordinator (main session) owns verification, remediation, and the final result. Never silently drop a required round to save tokens. If reviewer tooling is unavailable, report QA as **pending** — never substitute self-review.

**Focused review** (small, localized change): one adversarial reviewer on the changed code and its impacts; coordinator verifies findings, fixes agreed defects, runs checks. Record it as a focused review, not two-round QA.

**Full QA** (larger changes), sequential:

- **Round 1 — cooperative:** review correctness against requirements with a cooperative agent; investigate, remediate agreed defects, verify. Escalate unresolved disagreements to the user with evidence and both positions. Finish round 1 and record the exact resulting snapshot (SHA) before round 2.
- **Round 2 — independent adversarial:** a new, distinct reviewer with fresh context. Supply only resulting code/tests, neutral requirements, exact snapshot, and necessary operating constraints. **Exclude all cooperative-QA material** (notes, findings, remediation explanations, memory) — including when embedded in changelogs, handoffs, guides, prompts, or commit messages. Enforce with a clean review workspace and real access restrictions; a fresh subagent/worktree alone is not isolation if shared files remain accessible. Check inherited instructions (this file, memory) and accessible history. If isolation can't be enforced, disclose to the user and leave round 2 pending. This isolation overrides instructions to read handoffs/guides. Code review never grants device access.
- Verify every adversarial finding independently against code, requirements, and reproducible evidence; don't defer to confidence labels. Fix all agreed findings and verify.
- **Single binding tiebreaker:** all disputed/partly-agreed findings go to ONE new adversarial agent (distinct from prior reviewers) with code, original findings, coordinator position, and evidence for both sides, neutrally framed, noting changes since review, still excluding cooperative artifacts. Its conclusions are binding: implement and verify. No chains of tiebreakers. Does not override device constraints.
- Record reviewed revisions, findings, verification, agreements, escalations, tiebreaker decisions, fixes, final validation. Keep cooperative records inaccessible to independent reviewers. Report completed vs pending QA stages at every handoff.

## 6. Device access (comma device)

- Local setup/analysis does **not** authorize device access, install, deploy, parameter changes, or reboot. Establish scope and current operating state first.
- **Exactly one SSH connection at a time** (SSH/SCP/SFTP/rsync all serialized; account for the user's own sessions and other tools). Reuse the connection; never open another for monitoring.
- Confirm the current address before connecting; a saved address is not current evidence.
- Establish whether the device is active — don't infer from location or SSH reachability. **While active: only pull existing logs.** Everything else waits for confirmed inactivity unless the user explicitly widens scope.
- Changes needed during a drive: coordinate with the user to put the device in forced off-road mode and confirm it is no longer controlling first.
- **Never reboot without explicit authorization for that specific reboot** (including indirect reboots). Reconfirm state first; prior authorization does not carry over.
- Device CPU/logging overhead is safety-sensitive (high-volume debug logging has previously overwhelmed a device during active control). No busy polling, expensive processing, or extra background tasks. Measure proposed device-side overhead while inactive before any active use.
- Deployment approval request must include: concrete reviewable change, validation, resource-impact assessment, rollback plan. Preserve last known-good config; record what was actually deployed. Delegation never widens authorization.
- Unknown state/authorization → continue local work, clarify before device operations. Never store credentials or private keys in project docs.

## 7. Communication and continuity

- Concise, evidence-driven updates: findings, decisions, remaining uncertainty, next action. Targeted searches/reads; don't redo completed investigation without reason.
- Persist with authorized local work; ask only for genuinely missing info or authorization.
- Maintain: `README.md` (orientation), `CLAUDE.md` (rules), `docs/local-storage.md` (storage), `docs/baseline.md` (revisions), dated `CHANGELOG.md` entry per session (including research-only sessions).
- Checkpoint during sustained work. Near compaction (or at the next logical point after one), finish the current coherent checkpoint and write a **new uniquely named handoff** plus a **separate copy-ready kickoff prompt** in `docs/sessions/` (date/topic suffix); never overwrite older pairs. Update `docs/sessions/README.md` (chronological, with Latest links) and the changelog. Don't interrupt in-flight operations to hand off.
- Soft target: fresh-session handoff around 250k–300k cumulative tokens when real usage reporting exists. Don't invent usage numbers; say when reporting is unavailable.
- Handoff contents: objective, user instructions/decisions, exact source revisions, completed work + evidence, open hypotheses/questions, workspace/branch status, running operations, artifact paths, validation + limitations, QA stages, device state and SSH connection ownership, ordered next steps. Verify it against the actual workspace before stopping.
- Kickoff prompt: read `CLAUDE.md`, latest handoff, changelog, relevant guides; state the immediate next task. No accumulated superseded instructions.
- Don't create or message other sessions without user authorization.

## 8. Host environment notes

- Host: Windows Server 2025 (QEMU VM). Shells: PowerShell 5.1 and Git Bash. See [docs/baseline.md](docs/baseline.md) for tooling status and known gaps (e.g. Linux build/test environment).
- Git commands that touch `sunnypilot/` may need `-c core.longpaths=true` per command (not set globally).
- The `dev` baseline is a bot-generated prebuilt branch: vendored deps (no submodules), committed `.so` binaries. Its source is `origin/master` at the commit named in its message (see `docs/baseline.md`).

## 9. Upstream contribution etiquette

Anything submitted upstream must follow the checkout's `docs/AI_POLICY.md`: the user must understand and test it, driving fixes need real log evidence, and AI assistance is disclosed with an `Assisted-by: Claude` trailer. PRs target `master`. Nothing is pushed or submitted upstream without the user's explicit request.
