---
name: build-from-prd
description: Implement a project from PRD and architecture docs
---

# Build from PRD

You are a **Tech Lead agent**. Subagents write module code/tests. You scaffold, orchestrate batches, run gates, and fix.

**Context budget:** Minimize what enters your context. Delegate reading to subagents. Communicate via files (`build-plan.md`, `build-context.md`). Never inline what subagents can read themselves.

**Model rule:** The Phase 1 planning subagent MUST use the same model as the main agent (pass the `model` parameter). Interface contracts and conventions drive the entire build — this is not the place to economize.

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
3. For modified modules: spec file includes an **Existing API** section listing signatures that MUST NOT change (unless the PRD explicitly requires it)
4. Batch plan only includes new/modified modules — leave unchanged modules alone
5. Note existing conventions (naming, error handling, test patterns) in build-context.md and follow them

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
| stub_detection_command | (e.g., grep -r "raise NotImplementedError" src/ --include="*.py" -l) |
| src_dir | (e.g., src/) |
| test_dir | (e.g., tests/) |

2. **Gate Configuration** — which quality gates are active:

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
7. **Shared Utilities** — functions/constants needed by 2+ modules. For each:
   - Function signature (name, params, return type)
   - Placement (e.g., core/numeric.py, shared/helpers.py)
   - Which modules will import it
   - Brief implementation note (usually <10 lines each)
8. **Batch Plan** — modules grouped by dependency order; each with: path, test_path, FRs, exports, imports, **complexity** (simple/moderate/complex)
9. **Ambiguities** — unclear/contradictory requirements

**IMPORTANT — Batch Plan Rules:**
- Minimize batch count by merging modules whose dependencies are ALL in strictly earlier batches. Two modules can share a batch if neither depends on the other.
- Optimize for minimum number of sequential gates, not minimum batch "width."
- For each module, assign complexity: **simple** (pure functions, no I/O, <5 functions), **moderate** (some I/O or state, 5-10 functions), **complex** (orchestration, many edge cases, >10 functions).

**IMPORTANT — No Interface Contracts in build-plan.md:**
Do NOT include a full Interface Contracts section. All function signatures belong in per-module spec files only. The orchestrator reads build-plan.md; it does not need signatures (those are for subagents via spec files).

## Write {project_root}/build-context.md with:
Stack, error handling strategy, logging pattern, all conventions, all side-effect rules, test requirements (3-5 per function: happy/edge/error), known gotchas.

## Write per-module spec files to {project_root}/specs/
For EVERY module in the Batch Plan, create a file `specs/{module_name}.md` (e.g., `specs/extraction_invoice.md`) containing ONLY:
1. **Module path** and **test path**
2. **FRs** this module implements (distilled requirements, not raw PRD text)
3. **Exports** — exact function/class signatures with param types, return types, and docstring summaries
4. **Imports** — what this module imports from other modules (module path + symbol names + their signatures)
5. **Side-effect rules** — what this module owns (logging, file I/O) and what it must NOT do
6. **Test requirements** — 3-5 test cases per function (happy/edge/error) with one-line descriptions
7. **Gotchas** — any known pitfalls specific to this module

Each spec file should be **under 150 lines** — a self-contained brief that gives a subagent everything it needs without reading the full PRD, build-plan.md, or build-context.md.

Rules: PRD is source of truth. Distill, don't copy raw text. Be exhaustive on per-module signatures in spec files. WRITE ALL FILES and verify they exist.
```

### After subagent completes

1. **Verify files exist** — resume subagent if any are missing.
2. **Read `build-plan.md`** (but NOT specs — those are for subagents).
3. **Resolve ambiguities** — ask user if needed.
4. **Validate dependency graph:**
   - For each module in the Batch Plan, check that every module listed in its `imports` is in a strictly earlier batch.
   - If any violation found, re-order: move the depended-on module to an earlier batch, or merge the two batches.
   - Log any re-ordering to `build-log.md`.
5. **Cross-validate spec signatures:**
   - For each spec file's Imports section, verify the referenced function signatures match the Exports section of the source module's spec file.
   - If mismatches found, resume the Phase 1 subagent to fix the inconsistent specs before proceeding.
6. **Create task list:** Scaffold → Batch 0..N → Integration Tests → Simplify → Validate → Commit, with `addBlockedBy` ordering.
7. **Initialize build log:** Write `{project_root}/build-log.md` with a header and Phase 1 completion entry.

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

Process batches in dependency order. Launch all modules within a batch **as parallel synchronous Task calls in a single message** (do NOT use `run_in_background`). All results return together — no stale notifications, no `TaskOutput` polling needed. Then run the post-batch gate.

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
EXPORTS must match the spec exactly. IMPORTS from lower batches are implemented — import directly, do NOT mock.

Constraints:
- Only modify {module_path} and {test_path}. Do NOT create stub files for other modules.
- No new dependencies.
- Run {test_command} {test_path} before finishing.
- Your implementation must NOT contain `raise NotImplementedError` — fully implement all functions.
- Do NOT manipulate sys.modules, monkeypatch imports globally, or rely on test execution order.
- All test fixtures must be function-scoped unless explicitly session-scoped in conftest.py.
- Tests must pass both in isolation AND when run with the full suite.
- Do NOT duplicate utility functions that exist in shared modules (check imports in your spec).
```

**Why spec files?** Each spec is ~100 lines vs ~1000+ lines for PRD + build-plan + build-context. This cuts subagent input tokens by ~80%, reducing cost and improving focus. If a subagent needs broader context (rare), it can fall back to `build-context.md`.

### Post-batch gate

After ALL subagents in a batch complete:

**Step 1 — Stub detection:** (skip if gate disabled in Build Config)
```bash
{stub_detection_command}
```
If any source file (not test) contains stubs, the subagent failed to implement it. Re-delegate that module immediately with a stricter prompt emphasizing "fully implement all functions." This counts as attempt 1 of the retry budget (see Recovery).

**Step 2 — Lint gate:** (skip if gate disabled)
```bash
{lint_command}
```
Fix any errors before proceeding. Lint issues caught here are cheaper to fix than debugging test failures.

**Step 3 — Type check gate:** (skip if gate disabled)
```bash
{type_check_command}
```
Fix type errors immediately. Common issues: missing imports, wrong return types, signature mismatches between modules built by different subagents. Catching these per-batch is far cheaper than finding 29 errors after the final batch.

**Step 4 — Test gate:**
- Run tests for **this batch only**: `{test_command} {batch_test_paths}`
- Then run a quick **smoke test**: `{test_command} {test_dir} -x --timeout=30` (stop on first failure)
- Run the **full test suite** only at milestone gates: after the midpoint batch and after the final batch.

Since subagents run synchronously (not in background), their results are already available when the batch gate starts. Do NOT read individual subagent results on success — the test results are your signal.

**Step 5 — On failure:** Read only failing output. Apply the retry budget (see Recovery).

**Step 6 — Partial advancement:** If most modules in the batch pass but some fail:
1. Mark passing modules as complete.
2. Fix or re-delegate the failing module(s).
3. Re-run only the failing module's tests + the smoke test.
4. Do NOT re-run tests for already-passing modules.
5. Advance to the next batch once all modules in this batch pass.

**Step 7 — Log:** Append batch gate results to `build-log.md` (pass/fail, test count, any re-delegations).

**Context rule:** Never write >30 lines of module code in main context — delegate instead.

---

## Phase 4: Integration Tests

Delegate to a subagent. Tests use real modules (no mocking internals):
1. **Boundary tests** — wire 2-3 modules, pass realistic data, verify output
2. **Full pipeline test** — synthetic input end-to-end, verify final output
3. **Error propagation test** — trigger early error, verify it surfaces correctly
4. **Pipeline assumption tests** — empty upstream output, maximal output, duplicated entries

Run full test suite. Fix failures before proceeding. Log to `build-log.md`.

---

## Phase 5: Simplify

Run `/code-simplifier` to deduplicate across independently-built modules (duplicate helpers, constants, validation logic).

**Skip condition:** Only skip if the gate is disabled in Build Config, OR the batch plan had a single batch (no parallel subagents). Passing tests do NOT indicate absence of duplication.

Log simplification results to `build-log.md`.

---

## Phase 6: Validate

**If test data exists** (and gate is enabled), delegate to a general-purpose subagent:
```
Run real-data-validation. Project root: {root}, PRD: {prd}, test data: {data_dir}, run: {run_cmd}, tests: {test_cmd}.
Fix code bugs directly. Do NOT modify test data. Default assumption: code is wrong.
For every failure: inspect actual input data + cross-reference PRD before classifying as "data issue".
Check output for duplicate messages, inconsistent formatting, convention divergence — these are code bugs.
Write report to {project_root}/validation-report.md.
```

After: read `validation-report.md`. If code changes were made, re-run full test suite. Relay report to user.

**If no test data** (or gate disabled), run full test suite one final time and report results.

Log validation results to `build-log.md`.

---

## Phase 7: Commit

Use `/commit` when user is ready. Do NOT auto-commit.

---

## Build Log

Maintain `{project_root}/build-log.md` throughout all phases. Append entries for:
- Phase transitions (with phase name)
- Batch gate results (pass/fail, test count, type errors found)
- Failures and how they were resolved (fix directly vs re-delegate)
- Subagent re-delegations with reasons and attempt number
- Dependency graph re-orderings
- Spec signature fixes

This log survives context compaction and gives the user (and resumed sessions) full build history. Keep entries concise — one line per event, details only for failures.

---

## Context Budget Rules

1. Never read PRD/architecture in main context — subagents read them.
2. Never inline interface signatures in delegation prompts — they're in spec files.
3. Never copy subagent output into file writes — use general-purpose subagents that write files directly.
4. Never read subagent results on success — run tests instead.
5. Never write >30 lines of module code in main context — delegate.
6. Never read spec files in main context — those are for subagents only.
7. Never use `run_in_background` for batch subagents — use synchronous parallel calls.

## Subagent Launch Pattern

**Always use synchronous parallel Task calls** for batch delegation. Launch all modules in a single message without `run_in_background`. This ensures:
- All results return together in one response
- No stale completion notifications cluttering the conversation
- No need for `TaskOutput` polling or notification acknowledgment
- The main agent proceeds directly to the batch gate once all subagents finish

**Do NOT use `run_in_background: true`** for batch module subagents. The main agent has nothing useful to do while waiting (the batch gate requires all modules), so blocking is the correct behavior.

---

## Recovery

### Retry Budget

Each module gets a maximum of **2 re-delegation attempts** (3 total attempts including the original).

- **Attempt 1** (original): Standard delegation prompt.
- **Attempt 2** (first retry): Add explicit failure context from the previous attempt. Emphasize the specific issue (e.g., "Previous attempt left stubs — fully implement all functions").
- **Attempt 3** (final retry): Include the failing test output directly in the prompt. Use `opus` model regardless of complexity rating.
- **After 3 failures**: Escalate to user with diagnostic info (module name, all 3 failure reasons, spec file path). Do NOT silently retry further.

### Recovery Table

| Problem | Action |
|---------|--------|
| Subagent returns with failing tests | Read failing output only, apply retry budget |
| Subagent left a stub (`NotImplementedError`) | Re-delegate with explicit "fully implement" constraint (counts as retry) |
| Subagent created stub files for other modules | Delete the stubs, re-delegate with "only modify your assigned files" |
| Cross-module signature mismatch | Fix implementing module to match spec file |
| Missing dependency module | Scaffold incomplete — create init/export, re-delegate |
| Out-of-scope file changes | Revert, re-delegate with stricter constraints |
| Tests pass individually, fail together | Shared mutable state — check for sys.modules hacks, global state, test ordering deps |
| Lint errors after batch | Fix directly (usually unused imports or style) — fast to resolve |
| Type check errors after batch | Fix signature mismatches to match spec files |
| Validation finds code bugs | Fix directly, re-run validation |
| Circular dependency | Move shared types to core module |
| Ambiguous requirement | Ask user — do not guess |
| Duplicate code across subagents | Run `/code-simplifier` (Phase 5) |
| Context getting large | Delegate remaining work to fewer, larger subagents |
| Spec file missing for a module | Resume Phase 1 subagent to generate it |
| Dependency graph violation | Re-order batches per Phase 1 step 4, log to build-log.md |
