---
name: build-from-prd
description: Implement a project from PRD and architecture docs
---

# Build from PRD

You are a **Tech Lead agent**. Subagents write module code/tests. You scaffold, orchestrate batches, run gates, and fix.

**Context budget:** Minimize what enters your context. Delegate reading to subagents. Communicate via files (`build-plan.md`, `build-context.md`). Never inline what subagents can read themselves.

**Model rule:** The Phase 1 planning subagent MUST use the same model as the main agent (pass the `model` parameter). Interface contracts and conventions drive the entire build — this is not the place to economize.

**Resumption rule:** If context was compacted or session resumed (including across sessions), read `build-log.md` + task list to reconstruct current phase/batch state before continuing. The build-log tracks per-module status, so partially-completed batches can resume without re-delegating passing modules.

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
6. Detect existing test framework, fixtures, and patterns — new tests must follow them
7. Check for existing CI/CD, linting config, type-checking config — reuse rather than replace

If no source code exists (greenfield): proceed normally.

## Write {project_root}/build-plan.md with these sections:

1. **Build Config** — language-agnostic command table:

| Key | Value |
|-----|-------|
| language | (e.g., python, typescript, go) |
| package_manager | (e.g., uv, npm, go) |
| test_command | (e.g., uv run pytest tests/ --tb=short) |
| lint_command | (e.g., uv run ruff check src/ --fix) |
| lint_tool | (e.g., ruff, eslint, golangci-lint) — the package name to install as dev dep |
| type_check_command | (e.g., uv run pyright src/) |
| type_check_tool | (e.g., pyright, tsc) — the package name to install as dev dep |
| run_command | (e.g., uv run python -m myapp, node dist/index.js, go run ./cmd/app) |
| stub_detection_pattern | (e.g., raise NotImplementedError, TODO:IMPLEMENT, panic("not implemented")) |
| src_dir | (e.g., src/) |
| test_dir | (e.g., tests/) |
| format_command | (e.g., uv run ruff format src/, npx prettier --write src/) — leave empty if lint tool handles formatting |
| format_tool | (e.g., ruff, prettier, gofmt) — omit if same as lint_tool |

2. **Gate Configuration** — auto-disable when Build Config command is empty:

| Gate | Active | Reason if disabled |
|------|--------|--------------------|
| stub_detection | yes/no | |
| lint | yes/no | |
| type_check | yes/no | (disable for dynamically typed languages without type checker) |
| format | yes/no | (disable if no formatter or lint_tool handles formatting) |
| integration_tests | yes/no | |
| simplification | yes/no | (disable for single-batch builds) |
| validation | yes/no | (disable if no test data) |

3. **Project Summary** — file paths, stack, existing code assessment
4. **FR to Subsystem Map** — `FR_xx: subsystem — acceptance criterion`
5. **Side-Effect Ownership** — who logs what, non-owners must NOT
6. **Shared Utilities** — functions/constants needed by 2+ modules. For each: signature, placement (module path), consumers, and brief implementation note (<10 lines each)
7. **Batch Plan** — modules grouped by dependency order; each with: path, test_path, FRs, exports, imports, **complexity** (simple/moderate/complex)
8. **Ambiguities** — unclear/contradictory requirements

**IMPORTANT — Batch Plan Rules:**
- Minimize batch count by merging modules whose dependencies are ALL in strictly earlier batches. Two modules can share a batch if neither depends on the other.
- Optimize for minimum number of sequential gates, not minimum batch "width." Merge consecutive tail batches of ≤2 modules into one when dependencies allow.
- For each module, assign complexity: **simple** (pure functions, no I/O, <5 functions), **moderate** (some I/O or state, 5-10 functions), **complex** (orchestration, many edge cases, >10 functions). **Override:** If a module wraps a third-party library and must distinguish between library-internal type codes or modes (e.g., cell types, token types, status categories), classify as at least **moderate** regardless of function count — these require domain knowledge about the library's API semantics.

**IMPORTANT — No Interface Contracts in build-plan.md:**
Do NOT include a full Interface Contracts section. All function signatures belong in per-module spec files only.

**IMPORTANT — No Conventions in build-plan.md:**
Conventions belong ONLY in build-context.md. build-plan.md must NOT duplicate them — reference build-context.md instead.

## Write {project_root}/build-context.md with:
Stack, error handling strategy, logging pattern, all conventions, all side-effect rules, test requirements (3-5 per function: happy/edge/error), known gotchas (including library/test-framework interactions), platform-specific considerations.

## Write per-module spec files to {project_root}/specs/
For EVERY module in the Batch Plan, create a file `specs/{module_name}.md` (e.g., `specs/extraction_invoice.md`) containing ONLY:
1. **Module path** and **test path**
2. **FRs** this module implements — distill prose but preserve ALL concrete parameters verbatim (thresholds, search ranges, patterns, priority orders, format examples). Disambiguate terms that could refer to multiple fields (e.g., "codes" → specify "source keys" vs "target values"). When the PRD uses open-ended qualifiers ("etc.", "and similar", "any number of", "such as") on a list, state the **generative rule** (e.g., "any string consisting entirely of repeated asterisks"), not just the PRD's examples. For any heuristic or classifier function, include explicit **boundary definitions**: 2-3 positive examples that SHOULD match AND 2-3 negative examples that SHOULD NOT match but are close enough to be confused.
3. **Exports** — exact function/class signatures with param types, return types, and docstring summaries
4. **Imports** — what this module imports (module path + symbol names + **which functions/methods it will call** from each import)
5. **Side-effect rules** — what this module owns (logging, file I/O) and what it must NOT do
6. **Test requirements** — 3-5 test cases per function (happy/edge/error) with one-line descriptions. For classifier/heuristic functions, require at least one **negative boundary case** (input that resembles a match but must NOT match). For scoring/ranking functions, require a **minimum-qualifying case** (barely passes threshold) and an **empty candidates case**.
7. **Gotchas** — any known pitfalls specific to this module
8. **Verbatim outputs** — every user-visible string this module produces: exact log messages (with log level), print formats, error message templates, status strings. Copy these **character-for-character** from the PRD. If the PRD specifies emoji, log level, field layout, or conditional formatting, include it exactly. This section prevents distillation loss of output format requirements.

Each spec file should be **under 200 lines**.

**Before finishing:** cross-validate all specs: (a) every Import resolves to an Export, every Export is consumed by ≥1 Import (orphans = missing wiring); (b) every module's imports come from strictly earlier batches (violations = reorder batches); (c) **data field tracing** — for every field in the PRD's data model, verify it appears in the complete processing chain (extraction spec → data model spec → transformation spec → output spec); a field present in the model but absent from extraction or output is incomplete wiring. Fix all issues before completing.

Rules: PRD is source of truth. Distill prose, never parameters. Be exhaustive on signatures. WRITE ALL FILES and verify they exist.
```

### After subagent completes

1. **Verify files exist** — resume subagent if any are missing.
2-4. **Run in parallel** (these are independent reads):
   - **Spot-check** FRs section of 3 specs (1 complex, 1 moderate, 1 simple) — verify concrete PRD parameters (ranges, thresholds, patterns) weren't lost in distillation. Check that open-ended enumerations ("etc.") are expressed as generative rules, not truncated lists. Check that heuristic/classifier FRs include boundary definitions (positive + negative examples).
   - **Verify verbatim outputs** — grep the PRD for quoted strings, format examples, and message templates. For each, verify it appears in at least one spec file's **Verbatim Outputs** section. If any missing, resume subagent.
   - **FR coverage check** — verify every FR in `build-plan.md`'s FR-to-Subsystem Map appears in at least one spec file. If any unassigned, resume subagent.
   - **Data field flow check** — if the PRD defines a data model with enumerated fields (e.g., "13 per-item fields"), verify every field appears in extraction, model, AND output specs. A field present in the model but missing from extraction or output = incomplete wiring. Resume subagent to fix.
5. **Resolve ambiguities** — ask user if needed.
6. **Validate dependency graph:**
   - For each module in the Batch Plan, check that every module listed in its `imports` is in a strictly earlier batch.
   - If any violation found, re-order batches. Log to `build-log.md`.
7. **Create task list:** Scaffold → Batch 0..N → Integration Tests + Simplify → Validate → Commit, with `addBlockedBy` ordering.
8. **Initialize build log:** Write `{project_root}/build-log.md` with a header and Phase 1 completion entry.

**Gate:** If PRD or architecture MISSING, stop and ask user.

---

## Phase 2: Scaffold

**For greenfield projects:** Create directories + init files, manifest with deps, install/sync, cross-cutting infrastructure (error types, constants, models, logging config), test config + fixtures (including capture/isolation patterns for the test framework).

**For existing codebases:** Skip or minimally extend — only create new directories/files needed for new modules. Do NOT restructure existing code. Reuse existing test framework, fixtures, and configuration. If the project already has linting/type-checking config, use it.

**Dev tooling:** Install lint, type-check, and format tools listed in Build Config (`lint_tool`, `type_check_tool`, `format_tool`) as dev dependencies during scaffold. Do NOT defer this to batch gates — missing tools cause every batch to fail on the same issue.

**Shared utilities:** Implement all functions listed in the **Shared Utilities** section of `build-plan.md`. These are typically small (< 10 lines each) pure functions needed by multiple modules. Implementing them now prevents subagents from independently reimplementing them.

**Platform considerations:**
- Detect the OS from the runtime environment.
- **Windows:** Ensure UTF-8 encoding for all file I/O (stdout/stderr reconfiguration if needed). Use `pathlib` for all path handling. Add BOM markers to output files if the PRD requires Windows console compatibility.
- **All platforms:** Use `pathlib` for file paths (not `os.path` string manipulation). Avoid shell-specific syntax in scripts. Test commands should work cross-platform.

**Delegation:** For large projects (>15 modules), delegate scaffold to a subagent to save main context. Provide the Shared Utilities signatures from `build-plan.md` and the directory structure in the prompt.

**Gate:** Test collection dry-run must succeed. If scaffold includes implementations (shared utilities, error types), run their tests too.

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

Read {project_root}/specs/{module_spec}.md for your complete module specification (requirements, exports, imports, side-effects, test cases, gotchas, verbatim outputs). This is your primary reference.
Also read {project_root}/build-context.md for conventions, test patterns, and known gotchas (mandatory).
EXPORTS must match the spec exactly. IMPORTS from lower batches are implemented — import and CALL every listed function/method, do NOT mock.

Constraints:
- Only modify {module_path} and {test_path}. Do NOT create stub files for other modules.
- No new dependencies. Do NOT duplicate utility functions that exist in shared modules (check imports in your spec).
- Do NOT redefine types, classes, or dataclasses that exist in your imports — import them from the owning module.
- Run {format_command} {module_path} {test_path} && {lint_command} {module_path} {test_path} && {test_command} {test_path} before finishing.
- Your implementation must NOT contain stubs — fully implement all functions.
- Do NOT manipulate the module/import system globally or rely on test execution order.
- All test fixtures must be scoped per-test unless explicitly configured otherwise.
- Tests must pass both in isolation AND when run with the full suite.
- Tests must verify FR acceptance criteria from your spec (including concrete parameters: ranges, thresholds, patterns), not just exercise implementation logic.
- If your spec has a Verbatim Outputs section, verify your code produces those exact strings (log messages, formats, status text). Write tests for each verbatim output.
- For complex modules: also skim the PRD sections referenced in your spec's FRs to catch parameters the spec may have summarized.
- Before finishing: re-read your spec's FRs and Verbatim Outputs sections. Verify every acceptance criterion has a corresponding test, and every verbatim output is produced by your code.
```

### Post-batch gate

After ALL subagents in a batch complete:

**Step 1 — Stub detection:** (skip if gate disabled)
Search source files for `{stub_detection_pattern}`. If any found, re-delegate that module with stricter prompt. Counts as retry attempt 1.

**Step 1.5 — Scope check:**
Run `git diff --name-only` to list all files modified by this batch's subagents. Any file NOT in the batch's expected `{module_path}` or `{test_path}` list is out-of-scope. Review: additions to shared/core modules (new types, constants) are often correct — accept and note in build-log. Modifications to other modules' existing logic must be reverted and the subagent re-delegated with stricter scope.

**Step 2 — Type check:** (subagents already ran format + lint on their files)
```bash
{type_check_command} {batch_module_paths}
```
Run full `{type_check_command}` only at milestone gates (midpoint + final batch). If a fix pattern appears in ≥2 modules, IMMEDIATELY append it to `build-context.md` so future batches avoid it.

**Step 3 — Test gate:**
- Run tests for **this batch only**: `{test_command} {batch_test_paths}`
- Then run a quick **smoke test** in first-failure-exit mode (`-x`, `--bail`, `--failfast` per language)
- Run the **full test suite** at the final batch. Also at midpoint if any batch required fixes or re-delegation; otherwise skip.

Do NOT read subagent results on success — test results are your signal.

**Step 4 — On failure:** Read only failing output. Apply the retry budget (see Recovery).

**Step 5 — Partial advancement:** If most modules pass but some fail:
1. Mark passing modules as complete.
2. Fix or re-delegate failing module(s).
3. Re-run only failing tests + smoke test.
4. Advance to next batch once all modules pass.

**Step 6 — Convention check (final batch only):** Grep source files for duplicate log messages and convention divergences (formatting, capitalization). Fix any found.

**Step 7 — Log:** Append batch results to `build-log.md` (pass/fail, test count, any re-delegations, convention fixes).

**Context rule:** Never write >30 lines of module code in main context — delegate instead.

---

## Phase 4: Integration Tests + Simplify

Run integration tests and cross-module simplification **in parallel** — they are independent. Launch both as parallel Task calls in a single message, then run the full test suite once after both complete.

### Integration Tests (subagent)

Subagent prompt:
```
Write integration tests in {test_dir}/test_integration.py (or equivalent).
Read {project_root}/build-plan.md for module boundaries and the pipeline flow.
Read {project_root}/build-context.md for conventions and expected output formats.
Use real modules — no mocking of internal components.

Write tests in these categories (unit tests already cover per-module edge cases and errors — focus on cross-module behavior):
1. **Boundary tests** (3-5) — wire 2-3 adjacent modules, pass realistic data, verify output. Focus on data handoff points between subsystems. Include at least one error input per boundary. Include at least one test per pipeline with **structural irregularities** the PRD mentions (e.g., non-consecutive indices, gaps from filtered/skipped rows, missing optional fields, mixed types in a column).
2. **Full pipeline tests** (3-5) — synthetic input end-to-end, verify final output structure and content. Include happy path, empty/minimal input, and one error-triggering input.
3. **Output format** (2-3) — verify end-to-end output matches expected formats. Check field order, delimiters, headers, encoding.

Run {test_command} {test_dir}/test_integration.py before finishing.
```

### Simplify (subagent)

Delegate cross-module deduplication to a subagent (or run `/code-simplifier` if available). Target: duplicate helpers, constants, validation logic across independently-built modules.

Subagent prompt (if not using `/code-simplifier`):
```
Simplify and deduplicate across the codebase at {src_dir}.
Read {project_root}/build-plan.md for module boundaries.

Look for:
1. **Duplicate constants** — same magic numbers, keyword lists, or threshold values in 2+ modules. Extract to a shared constants module.
2. **Duplicate helper functions** — similar utility functions across modules. Extract to a shared utils module.
3. **Copy-pasted logic** — same algorithm implemented slightly differently in 2+ places. Consolidate into one.

Constraints:
- Do NOT change any public API signatures (function names, parameters, return types).
- Do NOT change behavior — only restructure. All existing tests must still pass.
- Prefer extracting to existing shared/core modules over creating new files.
- Run {test_command} after changes to verify nothing breaks.
```

**Skip condition:** Skip if gate disabled, OR ≤2 batches. Passing tests do NOT indicate absence of duplication.

### After both complete

Run the **full test suite**. Fix any failures before proceeding. Log both results to `build-log.md`.

---

## Phase 5: Validate

**If test data exists** (and gate is enabled), delegate to a **general-purpose subagent** that invokes the `/real-data-validation` skill. The subagent MUST use the same model as the main agent (pass the `model` parameter) — validation requires deep PRD cross-referencing and code fixes, which need full capability.

Subagent prompt:
```
Invoke the /real-data-validation skill using the Skill tool, then follow its instructions to completion.

Project root: {root}

The skill will independently discover PRD, architecture, source code, test data, and project manifest. It uses PRD + architecture as its sole source of truth for investigation — do not point it at build-plan.md or specs/ for understanding requirements.
```

After: read `validation-report.md`. If code changes were made, re-run full test suite. Relay report to user.

**If no test data** (or gate disabled), run full test suite one final time and report results.

Log validation results to `build-log.md`.

### Completion

After validation (or final test suite if no test data):

1. **Summary to user** — report final test count, validation results (if applicable), and any remaining issues or recommendations.
2. **Build artifact cleanup** — inform the user that `build-plan.md`, `build-context.md`, `specs/`, and `validation-round-*.log` are build artifacts. Ask whether to keep them (useful for future reference and resumption) or clean up.
3. **Mark all tasks complete** in the task list.

---

## Build Log

Maintain `{project_root}/build-log.md` throughout all phases. Append entries for:
- Phase transitions (with phase name)
- Batch gate results (pass/fail, test count, type errors found, **per-module pass/fail**)
- Convention compliance gate results
- Failures and how they were resolved (fix directly vs re-delegate)
- Subagent re-delegations with reasons and attempt number
- Dependency graph re-orderings

This log survives context compaction and is the primary recovery artifact for both mid-session and cross-session resumption. Keep entries concise — one line per event, details only for failures. Include per-module status in batch entries so partially-completed batches can resume without re-delegating passing modules.

---

## Context Budget Rules

1. Avoid reading PRD/architecture in main context — subagents read them. Exception: targeted sections during Phase 5 debugging.
2. Never inline interface signatures in delegation prompts — they're in spec files.
3. Never copy subagent output into file writes — use subagents that write files directly.
4. Never read subagent results on success — run tests instead.
5. Never write >30 lines of module code in main context — delegate.
6. Minimize reading specs in main context — only spot-check FRs and Verbatim Outputs during Phase 1 verification.
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
| Out-of-scope changes (other module logic) | Revert changes to other modules, re-delegate with stricter scope |
| Out-of-scope additions (shared types/constants) | Review — if type belongs in core/shared, accept and note in build-log; otherwise revert |
| Subagent redefined types from imports | Delete duplicates, add imports, fix tests — append "no type redefinition" reminder to build-context.md |
| Cross-module signature mismatch | Fix implementing module to match spec file |
| Missing dependency module | Scaffold incomplete — create init/export, re-delegate |
| Implementation diverges from PRD | Spec lossy — verify spec FRs against PRD, fix spec, re-delegate |
| Heuristic/classifier has wrong boundaries | Spec FRs lacked boundary definitions — add positive+negative examples to spec, re-delegate. Append boundary to build-context.md |
| Open-ended pattern truncated to fixed set | Spec distilled "etc." to enumeration — fix spec to state generative rule, re-delegate |
| Data field exists in model but not extracted/output | Incomplete pipeline wiring — trace field through extraction→model→output specs, fix gaps, re-delegate affected modules |
| Phase 5 finds formatting/output bugs | Spec distillation lost verbatim strings — cross-ref PRD directly, fix code, append missing format strings to build-context.md so future batches avoid same issue |
| Tests pass individually, fail together | Shared mutable state — check for global state, module system hacks, test ordering deps |
| Lint / type errors after batch | Fix directly; for signature mismatches, match spec files |
| Dev tools missing at batch gate | Install immediately, append to build-context.md gotchas so it doesn't recur |
| Unit tests pass but real data fails | Subagent tested implementation, not spec — fix code in Phase 5 |
| Validation finds code bugs | Fix directly, re-run validation |
| Circular dependency | Move shared types to core module |
| Ambiguous requirement | Ask user — do not guess |
| Duplicate code across subagents | Phase 4 deduplication |
| Context or subagent prompt too large | Have subagents read files (build-plan.md, build-context.md) instead of receiving inline content |
| Spec file missing for a module | Resume Phase 1 subagent to generate it |
| Dependency graph violation | Re-order batches per Phase 1 step 5, log to build-log.md |
