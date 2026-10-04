# Startup prompt for Claude Code

You are helping me start a new, independent sunnypilot customization project from scratch. Our work will combine source investigation, local log/video analysis, controlled experiments, and carefully validated customizations. Establish a reproducible baseline and durable working rules first. I will supply the specific goals later; do not invent a vehicle configuration, complaint, diagnosis, or tuning target.

This document is the kickoff prompt. Carry its rules into the new project's `CLAUDE.md` so they persist across Claude Code sessions. If the project also uses `AGENTS.md`, keep shared instructions consistent. Apply these rules to all tools and delegated work.

## 1. Establish the project and clone upstream

- Ask me where the new source project should live and where its separate local data storage should live. The data root must be outside every Git checkout. Do not reuse another project's paths, data, settings, or permissions without my instruction.
- Once the source destination is known, create a fresh project there. Refuse to overwrite an occupied destination or discard existing work.
- Clone the official repository, **https://github.com/sunnypilot/sunnypilot.git**, using the latest remote **`dev`** branch at the time you start, with its submodules:

  ```sh
  git ls-remote --heads https://github.com/sunnypilot/sunnypilot.git refs/heads/dev
  git clone --branch dev --recurse-submodules https://github.com/sunnypilot/sunnypilot.git sunnypilot
  ```

  Run the clone from the agreed source project directory. If `dev` is unavailable, report the problem rather than substituting another branch, an archive, or a third-party fork. This is a local source clone, not device installation.
- Verify the remote URL, branch, full commit SHA, commit date, recursive submodule revisions/status, and initial working-tree status. Record the acquisition time and timezone. Resolve incomplete submodule initialization before treating the baseline as ready.
- Preserve that exact starting revision as the reproducible baseline. Create a separate local customization branch before edits. Do not silently advance the baseline when upstream moves; record deliberate updates and their validation.
- Read the cloned revision's README, contributor instructions, build/dependency guidance, and applicable repository instructions. Discover the actual layout and supported development tools from that checkout rather than assuming an older version's structure.
- Keep project documentation separate from upstream code where practical. A simple outer project folder containing `CLAUDE.md`, `README.md`, `CHANGELOG.md`, `docs/`, and the `sunnypilot/` clone is suitable. If the outer folder is also version-controlled, explicitly choose and document how the nested clone is tracked; do not accidentally vendor a full repository.

## 2. High-level technical orientation

sunnypilot builds on comma.ai's openpilot driver-assistance software and adds configurable behavior and features. Use the official [sunnypilot repository](https://github.com/sunnypilot/sunnypilot) and the checked-out source as the authority for this project's version.

At a high level, the system combines camera/model processing, vehicle-state interpretation, planning, control, vehicle-specific interfaces and CAN messaging, safety enforcement, configuration, and user interface behavior. Vehicle integration and safety-related code may live in bundled dependencies such as opendbc; inspect the actual pinned dependency rather than assuming current upstream opendbc matches this checkout.

Before proposing a customization, trace the relevant path from input/configuration through planning and control to its output, including activation conditions, units, timing, state transitions, limits, and safety checks. Identify which layer is responsible before changing it. Do not generalize control behavior or tuning between vehicle platforms. Source-level requests, transmitted commands, hardware acceptance, and measured physical response are different forms of evidence.

Latest development source is a research baseline, not proof that it matches installed software or is validated for deployment. Record installed software, models, settings, and dependency identities separately when evidence becomes available. Do not bypass safety checks or widen safety limits as a shortcut to performance changes.

## 3. Local-only storage: ask me for the location

All downloaded logs and videos, decoded frames, raw/derived datasets, analysis outputs, caches, scratch work, partial transfers, and temporary files belong under the separate local data root I choose. **Never put these in the source repository or its submodules, even in ignored folders.** Do not use Git LFS, force-add them, or symlink datasets into the repository.

Keep source code, durable documentation, and small curated findings in the project. Configure tools explicitly so their working data and generated artifacts stay in local storage.

Use this initial storage layout, adapting only with a documented reason:

```text
<DATA_ROOT>/
  recordings/YYYY/MM/DD/HH-MM-SS__route-id/
    rlogs/segment-NNN/
    videos/front-narrow/segment-NNN/
    videos/front-wide/segment-NNN/
    videos/driver/segment-NNN/
    metadata/
  analysis/
  cache/
  scratch/
  temporary/
```

- Download **RLOGS only, never QLOGS**. If RLOGS are unavailable, report the evidence gap rather than falling back to QLOGS.
- Group recordings by route start time, not download time. Ask which browsing timezone to use; record the original timestamp, timezone/UTC offset, exact route and segment identifiers, and device identifier when needed. Keep a route together even if it crosses midnight. Prevent collisions, including repeated local times.
- Separate cameras and segments. Preserve original compression and filenames where practical; verify camera-to-filename mappings against the pinned source. Record missing cameras/segments instead of assuming complete coverage.
- Record provenance, transfer completeness, sizes/hashes when available, and missing data. Verify partial downloads before promoting them to completed recordings. Do not overwrite existing recordings blindly or duplicate raw data unnecessarily.
- Verify storage identity, mount availability if applicable, writability, and free space before data operations. Once a storage device/path is agreed, stop data work if it becomes unavailable; never silently fall back to the checkout or another disk.
- Use per-command temporary/cache environment variables and explicit tool output paths. Account for tools that ignore environment settings, including test tools and submodule commands. Do not change machine-wide configuration unnecessarily.
- Before any commit, inspect the outer project's status, the sunnypilot checkout, and relevant submodules for accidental data or generated artifacts. Ignore rules are a backstop, not storage enforcement.

## 4. Evidence and testing

- Separate confirmed source facts, observations from recordings/device state, hypotheses, and unverified assumptions. Cite exact files/revisions and recording intervals where relevant. Explain limitations plainly.
- Diagnose before tuning. Preserve the unmodified baseline and compare one bounded change at a time. Define the question, expected behavior, comparison conditions, success criteria, and failure criteria before an experiment.
- Verify source, model, configuration, schema, units, timestamps, and activation state before interpreting signals. Align logs and video using recorded timestamps and verified stream mappings; label approximate alignment. Missing data remains unknown, not zero or evidence of normal operation.
- Prefer local analysis of existing recordings. Keep tools reproducible, record commands and dependency versions, and reuse verified caches rather than repeatedly decoding or downloading the same data.
- For behavior changes and bug fixes, add meaningful regression/boundary tests and run the relevant existing tests. Exercise activation/deactivation, resets, invalid inputs, limits, timing, and other affected contracts where applicable. Tests should verify behavior, not merely mirror the implementation.
- Follow the pinned checkout's supported build, lint, unit, integration, replay, simulation, and safety-test guidance as appropriate to the changed layer. Inspect available tooling before choosing commands. Do not invent a universal test command or claim unsupported checks ran.
- Compare baseline and candidate on the same eligible inputs when possible. Keep exploratory selection/tuning separate from held-out validation; do not present repeated tuning on the same examples as independent confirmation. Avoid causal or physical-performance claims that the data cannot support.
- Run required checks after fixes. Report exact commands, exit status/results, the revision tested, and any skipped or unavailable checks. Re-run broader checks when changed dependencies, failures, or unresolved risks justify them; avoid redundant repetition without a reason.
- Offline tests, replay results, and reviewer approval do not establish real-world performance or authorize device deployment. Distinguish source correctness, offline evidence, inactive-device verification, and user-supervised operational validation.
- Before saying work is complete, independently inspect the final changes and verify the evidence. An agent's completion report is not verification. Never claim a test, review, deployment, or improvement occurred when it did not.

## 5. Required project QA process

The main coordinator owns verification, remediation, and the final result. The full QA workflow has two sequential rounds. Saving tokens must not silently remove a required round.

For a small, localized change, use one adversarial reviewer focused on the changed code and its impacts instead of the full two-round process. The coordinator still verifies findings, fixes agreed defects, and runs appropriate checks. Record this as a focused review; do not claim two-round QA occurred. Larger project QA uses the full process below.

### Round 1: cooperative correctness QA

1. Work with a cooperative review agent to review correctness against the requirements.
2. Investigate findings together, remediate agreed defects, and verify the changes with appropriate checks.
3. Escalate unresolved disagreements to me with evidence and both positions. Do not silently dismiss them or resolve them by unilateral coordinator decision.
4. Finish round 1 and resolve its escalations before round 2. Identify the exact resulting source snapshot for independent review.

### Round 2: independent adversarial QA

1. Use a new reviewer, distinct from the cooperative reviewer, with fresh context and no inherited conversation history. Ask it to challenge correctness and look for failures independently.
2. Supply only the resulting code/tests, neutral task requirements, exact review snapshot, and necessary operating constraints. Do not provide cooperative QA notes, findings, discussions, remediation explanations, memory, or other review artifacts. This includes such material embedded in changelogs, handoffs, guides, prompts, or commit messages.
3. Enforce the information boundary with a clean review workspace and actual access restrictions. A fresh Claude conversation, subagent, or worktree alone does not isolate files accessible through shared filesystem/tool access. Check inherited instructions and accessible history as well. If available tooling cannot enforce isolation, disclose that limitation to me before proceeding; leave isolated QA pending rather than claiming it occurred.
4. The isolation requirement overrides normal instructions to read handoffs/guides containing cooperative QA material. Supply uncontaminated requirements and device/CPU rules separately. Code review never grants device access.
5. Independently verify every adversarial finding against code, requirements, and reproducible evidence where possible. Do not accept a finding merely because its confidence or severity label sounds convincing.
6. Remediate all findings you agree with and verify the fixes.

### One binding tiebreaker for disputed adversarial findings

Collect all findings you disagree or partly agree with into a **single** re-review by another new adversarial agent, distinct from the earlier reviewers. Supply the relevant code, original findings, coordinator position, and supporting evidence for both sides with neutral framing. Identify changes since the original review and continue excluding cooperative artifacts.

This single tiebreaker is binding: accept its conclusions, implement recommended remediations, and verify them. Do not create an iterative chain of tiebreakers or reject its outcome because you still disagree. This process does not override device-access or deployment constraints.

Record reviewed revisions, findings, verification, agreements, escalations, tiebreaker decisions, fixes, and final validation. Keep cooperative records inaccessible to independent reviewers. Report completed and pending QA stages accurately at every handoff. If reviewer tooling is unavailable, report QA as pending rather than substituting coordinator self-review.

## 6. Device access and operating constraints

- Local setup and source analysis do not authorize device access, installation, deployment, parameter changes, or reboot. Establish the requested scope and current operating state before device work.
- Use **only one SSH connection at a time** for all device access. Serialize SSH, SCP, SFTP, and rsync-over-SSH, accounting for existing user sessions and other tools. Reuse the existing connection where practical; do not open another for progress monitoring. Concurrent connections can destabilize the device's SSH server.
- Confirm the current address before connecting. Wi-Fi addresses may change with DHCP; a saved address is not current evidence.
- Establish whether the device is active; do not infer inactivity from location or SSH availability. While active, **only pull existing logs**. Video/other retrieval, commands, instrumentation, and changes wait until inactivity is confirmed unless I explicitly clarify the permitted scope.
- If changes are needed during driving, coordinate with me to place the device in forced off-road mode and confirm it is no longer actively controlling before changes. A request for a change does not authorize interrupting active control.
- **Never reboot without explicit authorization for that particular reboot**, including workflows that trigger reboot indirectly. Reconfirm state before acting; previous-session authorization is not fresh reboot permission.
- Treat device CPU and logging overhead as safety-sensitive. High-volume/debug logging has previously overwhelmed a device during active control. Avoid busy polling, expensive processing, and extra background tasks. Prefer local analysis and measure proposed device-side overhead while inactive before considering active use.
- Prepare a concrete, reviewable change, relevant validation, resource-impact assessment, and rollback plan before requesting deployment approval. Preserve the last known working configuration and record what was actually deployed. Never widen authorization by delegating work.
- When operating state or authorization is unknown, continue useful local work and clarify before dependent device operations. Do not store credentials or private keys in project documents.

## 7. Communication and session continuity

- Be concise and evidence-driven. Give progress updates on findings, decisions, remaining uncertainty, and the next useful action. Use targeted searches/reads and concise tool output; do not repeat completed investigation without a concrete reason.
- Persist with authorized local work. Ask for genuinely missing information or necessary authorization, not repeated confirmation of already agreed reversible actions. Do not import permissions granted in another project.
- Maintain `README.md` for project orientation, `CLAUDE.md` for durable rules, `docs/local-storage.md` for agreed storage details, and a dated `CHANGELOG.md` entry per session, including research-only sessions.
- Keep checkpoints during sustained work. When context compaction approaches, finish and verify the next coherent checkpoint, then stop before compaction with a **new, uniquely named handoff document and a separate copy-ready kickoff prompt**. If compaction already happened, do this at the next logical handoff point. Do not interrupt an in-flight operation just to hand off or begin another long stage while preparing the handoff.
- Preserve older handoff/kickoff pairs under `docs/sessions/`; use date/topic or session suffixes to avoid collisions. Maintain `docs/sessions/README.md` with chronological records and Latest links. Update the changelog when closing a session.
- Context capacity and cumulative session usage are separate. Aim for a fresh-session handoff around 250,000–300,000 cumulative tokens when actual reporting is available; this is a soft guideline, not a reason to abandon critical work. Do not invent usage or guarantee compaction timing. State when usage reporting is unavailable.
- A handoff must capture objective, user instructions/decisions, exact source revisions, completed work and evidence, unresolved hypotheses/questions, workspace/branch status, running operations, local artifact paths, validation and limitations, QA stages, deployment/device state and connection ownership if relevant, and ordered next steps. Distinguish last-observed state from freshly confirmed state.
- The separate kickoff should direct the next session to read `CLAUDE.md`, the latest handoff, changelog, and relevant guides, then state the immediate next task. Avoid accumulating superseded instructions. Verify the handoff against the actual workspace before stopping.
- At resumed startup, inspect the actual workspace and continue from the checkpoint. Reconfirm transient device state/address before access. Do not automatically create or message other sessions unless I authorize it.

## First-session deliverable

Start by asking me for the source project directory and separate local data-storage location. Continue independent preparation while those answers are pending. Once supplied, complete the fresh `dev` clone and baseline verification, write the persistent project rules and storage guide, and give me a concise setup report with exact paths/revisions, checks performed, and any unresolved setup dependencies. Then ask what I want to investigate or customize first. Do not make runtime behavior changes during startup.
