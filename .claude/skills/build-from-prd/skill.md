---
name: build-from-prd
description: Implement a project from PRD and architecture docs
---

# Build from PRD

You are a **Tech Lead agent**. Subagents write module code/tests. You scaffold, orchestrate batches, run gates, and fix.

**Context budget:** Minimize what enters your context. Delegate reading to subagents. Communicate via files (`build-plan.md`, `build-context.md`). Never inline what subagents can read themselves.

**Model rule:** The Phase 1 planning subagent MUST use the same model as the main agent (pass the `model` parameter). Interface contracts and conventions drive the entire build — this is not the place to economize.

**Resumption rule:** If context was compacted or session resumed, read `build-log.md` + task list to reconstruct current phase/batch state before continuing.

---

## Phase 1: Discover + Plan + Generate Module Specs

Delegate to a **single general-purpose subagent** (NOT Plan — Plan can't write files). It reads PRD + architecture and writes `build-plan.md`, `build-context.md`, and **per-module spec files** directly. Do NOT read PRD/architecture yourself.

Subagent prompt — adapt paths per project:
```
You are a software architect. Discover the project, read PRD + architecture, and produce planning files.

Find and read: PRD (docs/PRD.md), Architecture (docs/architecture.md), manifest, source dir, test data dir, config files. If PRD or architecture is MISSING, stop and report immediately.

## Greenfield vs Existing Codebase

If source code already exists:
1. Map existing modules and their public interfaces
2. Identify which modules need modification vs creation
3. For modified modules: spec file includes an **Existing API** section listing signatures that MUST NOT change (unless PRD explicitly requires it)
4. Batch plan only includes new/modified modules — leave unchanged modules alone
5. Note existing conventions in build-context.md and follow them

If no source code exists (greenfield): proceed normally.

## Write {project_root}/build-plan.md with these sections:

1. **Build Config** — language-agnostic command table:

| Key | Value |
|-----|-------|
| language | (e.g., python, typescript, go) |
| package_manager | (e.g., uv, npm, go) |
| test_command | (e.g., uv run pytest tests/ --tb=short) |
| lint_command | (e.g., uv run ruff check src/ --fix) |
| type_check_command | (e.g., uv run pyright src/) |
| stub_detection_pattern | (e.g., raise NotImplementedError, TODO:IMPLEMENT, panic("not implemented")) |
| src_dir | (e.g., src/) |
| test_dir | (e.g., tests/) |

2. **Gate Configuration** — auto-disable when Build Config command is empty:

| Gate | Active | Reason if disabled |
|------|--------|--------------------|
| stub_detection | yes/no | |
| lint | yes/no | |
| type_check | yes/no | (disable for dynamically typed languages without type checker) |
| integration_tests | yes/no | |
| simplification | yes/no | (disable for single-batch builds) |
| validation | yes/no | (disable if no test data) |

3. **Project Summary** — file paths, stack, existing code assessment
4. **FR to Subsystem Map** — `FR_xx: subsystem — acceptance criterion`
5. **Side-Effect Ownership** — who logs what, non-owners must NOT
6. **Conventions** — decisions multiple modules must agree on
7. **Shared Utilities** — functions/constants needed by 2+ modules. For each: signature, placement (module path), consumers, and brief implementation note (<10 lines each)
8. **Batch Plan** — modules grouped by dependency order; each with: path, test_path, FRs, exports, imports, **complexity** (simple/moderate/complex)
9. **Ambiguities** — unclear/contradictory requirements

**IMPORTANT — Batch Plan Rules:**
- Minimize batch count by merging modules whose dependencies are ALL in strictly earlier batches. Two modules can share a batch if neither depends on the other.
- Optimize for minimum number of sequential gates, not minimum batch "width."
- For each module, assign complexity: **simple** (pure functions, no I/O, <5 functions), **moderate** (some I/O or state, 5-10 functions), **complex** (orchestration, many edge cases, >10 functions).

**IMPORTANT — No Interface Contracts in build-plan.md:**
Do NOT include a full Interface Contracts section. All function signatures belong in per-module spec files only.

## Write {project_root}/build-context.md with:
Stack, error handling strategy, logging pattern, all conventions, all side-effect rules, test requirements (3-5 per function: happy/edge/error), known gotchas.

## Write per-module spec files to {project_root}/specs/
For EVERY module in the Batch Plan, create a file `specs/{module_name}.md` (e.g., `specs/extraction_invoice.md`) containing ONLY:
1. **Module path** and **test path**
2. **FRs** this module implements — distill prose but preserve ALL concrete parameters verbatim (thresholds, search ranges, patterns, priority orders, format examples)
3. **Exports** — exact function/class signatures with param types, return types, and docstring summaries
4. **Imports** — what this module imports (module path + symbol names + **which functions/methods it will call** from each import)
5. **Side-effect rules** — what this module owns (logging, file I/O) and what it must NOT do
6. **Test requirements** — 3-5 test cases per function (happy/edge/error) with one-line descriptions
7. **Gotchas** — any known pitfalls specific to this module

Each spec file should be **under 200 lines**.

**Before finishing:** cross-validate all specs bidirectionally — every Import must resolve to a source Export, AND every exported function/method must appear as a used Import in ≥1 consumer spec (orphans = missing wiring). Fix all issues before completing.

Rules: PRD is source of truth. Distill prose, never parameters. Be exhaustive on signatures. WRITE ALL FILES and verify they exist.
```

### After subagent completes

1. **Verify files exist** — resume subagent if any are missing.
2. **Read `build-plan.md`**. **Spot-check** FRs section of 2-3 complex specs — verify concrete PRD parameters (ranges, thresholds, patterns) weren't lost in distillation.
3. **Resolve ambiguities** — ask user if needed.
4. **Validate dependency graph:**
   - For each module in the Batch Plan, check that every module listed in its `imports` is in a strictly earlier batch.
   - If any violation found, re-order batches. Log to `build-log.md`.
5. **Create task list:** Scaffold → Batch 0..N → Integration Tests → Simplify → Validate → Commit, with `addBlockedBy` ordering.
6. **Initialize build log:** Write `{project_root}/build-log.md` with a header and Phase 1 completion entry.

**Gate:** If PRD or architecture MISSING, stop and ask user.

---

## Phase 2: Scaffold

**For greenfield projects:** Create directories + init files, manifest with deps, install/sync, cross-cutting infrastructure (error types, constants, models, logging config), test config + fixtures.

**For existing codebases:** Skip or minimally extend — only create new directories/files needed for new modules. Do NOT restructure existing code.

**Shared utilities:** Implement all functions listed in the **Shared Utilities** section of `build-plan.md`. These are typically small (< 10 lines each) pure functions needed by multiple modules. Implementing them now prevents subagents from independently reimplementing them.

**Gate:** Test collection dry-run (e.g., `pytest --collect-only`) must succeed with zero errors.

Log scaffold completion to `build-log.md`.

---

## Phase 3: Delegate by Batch

Process batches in dependency order. Launch all modules within a batch **as parallel synchronous Task calls in a single message**. Do NOT use `run_in_background` — the batch gate needs all results, so blocking is correct. Then run the post-batch gate.

### Model selection

Use the **complexity** field from the Batch Plan to select the subagent model:
- **simple** → `haiku` (pure functions, minimal logic)
- **moderate** → `sonnet` (some I/O, moderate logic)
- **complex** → `opus` (orchestration, many edge cases)

Pass the `model` parameter when launching the subagent.

### Delegation prompt template

Subagents read their **spec file** instead of the full PRD/plan:
```
Implement and test: {subsystem_name}
Module: {module_path} | Tests: {test_path}

Read {project_root}/specs/{module_spec}.md for your complete module specification (requirements, exports, imports, side-effects, test cases, gotchas). This is your primary reference.
Also read {project_root}/build-context.md for project conventions if needed.
EXPORTS must match the spec exactly. IMPORTS from lower batches are implemented — import and CALL every listed function/method, do NOT mock.

Constraints:
- Only modify {module_path} and {test_path}. Do NOT create stub files for other modules.
- No new dependencies. Do NOT duplicate utility functions that exist in shared modules (check imports in your spec).
- Run {test_command} {test_path} before finishing.
- Your implementation must NOT contain stubs — fully implement all functions.
- Do NOT manipulate the module/import system globally or rely on test execution order.
- All test fixtures must be scoped per-test unless explicitly configured otherwise.
- Tests must pass both in isolation AND when run with the full suite.
- Tests must verify FR acceptance criteria from your spec (including concrete parameters: ranges, thresholds, patterns), not just exercise implementation logic.
- For complex modules: also skim the PRD sections referenced in your spec's FRs to catch parameters the spec may have summarized.
```

### Post-batch gate

After ALL subagents in a batch complete:

**Step 1 — Stub detection:** (skip if gate disabled)
Search source files for `{stub_detection_pattern}`. If any found, re-delegate that module with stricter prompt. Counts as retry attempt 1.

**Step 2 — Lint + type check:** (skip disabled gates; run in parallel — they're independent)
```bash
{lint_command}
{type_check_command}
```
Fix errors before proceeding. If a fix pattern appears in ≥2 modules, IMMEDIATELY append it (with code example) to `build-context.md` so future batches avoid it.

**Step 3 — Test gate:**
- Run tests for **this batch only**: `{test_command} {batch_test_paths}`
- Then run a quick **smoke test** in first-failure-exit mode (`-x`, `--bail`, `--failfast` per language)
- Run the **full test suite** only at milestone gates: after the midpoint batch and after the final batch.

Do NOT read subagent results on success — test results are your signal.

**Step 4 — On failure:** Read only failing output. Apply the retry budget (see Recovery).

**Step 5 — Partial advancement:** If most modules pass but some fail:
1. Mark passing modules as complete.
2. Fix or re-delegate failing module(s).
3. Re-run only failing tests + smoke test.
4. Advance to next batch once all modules pass.

**Step 6 — Log:** Append batch results to `build-log.md` (pass/fail, test count, any re-delegations).

**Context rule:** Never write >30 lines of module code in main context — delegate instead.

---

## Phase 4: Integration Tests

Delegate to a subagent. Tests use real modules (no mocking internals):
1. **Boundary tests** — wire 2-3 modules, pass realistic data, verify output
2. **Full pipeline test** — synthetic input end-to-end, verify final output and that every pipeline stage executes
3. **Error propagation test** — trigger early error, verify it surfaces correctly
4. **Pipeline assumption tests** — empty upstream output, maximal output, duplicated entries

Run full test suite. Fix failures before proceeding. Log to `build-log.md`.

---

## Phase 5: Simplify

Delegate cross-module deduplication to a subagent (or run `/code-simplifier` if available). Target: duplicate helpers, constants, validation logic across independently-built modules.

**Skip condition:** Only skip if gate disabled in Build Config, OR the batch plan had a single batch. Passing tests do NOT indicate absence of duplication.

Log simplification results to `build-log.md`.

---

## Phase 6: Validate

**If test data exists** (and gate is enabled), delegate to a general-purpose subagent:
```
Run real-data-validation. Project root: {root}, PRD: {prd}, test data: {data_dir}, run: {run_cmd}, tests: {test_cmd}.
Read {project_root}/build-context.md for conventions and expected behavior.
Fix code bugs directly. Do NOT modify test data. Default assumption: code is wrong.
For every failure: inspect actual input data + cross-reference PRD before classifying as "data issue".
Cross-reference failures against PRD directly — specs may have lost parameters during distillation.
Check output for duplicate messages, inconsistent formatting, convention divergence — these are code bugs.
Write report to {project_root}/validation-report.md.
```

After: read `validation-report.md`. If code changes were made, re-run full test suite. Relay report to user.

**If no test data** (or gate disabled), run full test suite one final time and report results.

Log validation results to `build-log.md`.

---

## Build Log

Maintain `{project_root}/build-log.md` throughout all phases. Append entries for:
- Phase transitions (with phase name)
- Batch gate results (pass/fail, test count, type errors found)
- Failures and how they were resolved (fix directly vs re-delegate)
- Subagent re-delegations with reasons and attempt number
- Dependency graph re-orderings

This log survives context compaction and is the primary recovery artifact for resumed sessions. Keep entries concise — one line per event, details only for failures.

---

## Context Budget Rules

1. Avoid reading PRD/architecture in main context — subagents read them. Exception: targeted sections during Phase 6 debugging.
2. Never inline interface signatures in delegation prompts — they're in spec files.
3. Never copy subagent output into file writes — use subagents that write files directly.
4. Never read subagent results on success — run tests instead.
5. Never write >30 lines of module code in main context — delegate.
6. Minimize reading specs in main context — only spot-check FRs section during Phase 1 verification.
7. On context compaction: read `build-log.md` + task list to reconstruct state before continuing.

---

## Recovery

### Retry Budget

Each module gets a maximum of **2 re-delegation attempts** (3 total including original).

- **Attempt 1** (original): Standard delegation prompt.
- **Attempt 2** (first retry): Add explicit failure context. Emphasize the specific issue.
- **Attempt 3** (final retry): Include failing test output in prompt. Use `opus` regardless of complexity.
- **After 3 failures**: Escalate to user with diagnostic info (module name, all 3 failure reasons, spec file path).

### Recovery Table

| Problem | Action |
|---------|--------|
| Subagent returns with failing tests | Read failing output only, apply retry budget |
| Subagent left stubs | Re-delegate with explicit "fully implement" constraint (counts as retry) |
| Out-of-scope changes or extra files created | Revert/delete, re-delegate with stricter scope |
| Cross-module signature mismatch | Fix implementing module to match spec file |
| Missing dependency module | Scaffold incomplete — create init/export, re-delegate |
| Implementation diverges from PRD | Spec lossy — verify spec FRs against PRD, fix spec, re-delegate |
| Tests pass individually, fail together | Shared mutable state — check for global state, module system hacks, test ordering deps |
| Lint / type errors after batch | Fix directly; for signature mismatches, match spec files |
| Unit tests pass but real data fails | Subagent tested implementation, not spec — fix code in Phase 6 |
| Validation finds code bugs | Fix directly, re-run validation |
| Circular dependency | Move shared types to core module |
| Ambiguous requirement | Ask user — do not guess |
| Duplicate code across subagents | Phase 5 deduplication |
| Context getting large | Delegate remaining work to fewer, larger subagents |
| Spec file missing for a module | Resume Phase 1 subagent to generate it |
| Dependency graph violation | Re-order batches per Phase 1 step 4, log to build-log.md |
