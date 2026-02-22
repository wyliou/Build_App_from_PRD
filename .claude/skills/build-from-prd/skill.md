---
name: build-from-prd
description: Implement a project from PRD and architecture docs
---

# Build from PRD

You are a **Tech Lead agent**. Subagents write module code/tests. You scaffold, orchestrate batches, run gates, and fix.

**Context budget:** Minimize what enters your context. Delegate reading to subagents. Communicate via files (`build-plan.md`, `build-context.md`). Never inline what subagents can read themselves.

**Model rule:** Phase 1 Stage A (architecture) MUST use the same model as the main agent. Stage B spec-writing subagents can use `sonnet` — they distill from build-plan.md + PRD, not make architecture decisions.

**Resumption rule:** If context was compacted or session resumed (including across sessions), read `build-log.md` + task list to reconstruct current phase/batch state before continuing. The build-log tracks per-module status, so partially-completed batches can resume without re-delegating passing modules.

---

## Phase 1: Discover + Plan + Generate Module Specs

Two stages. **Stage A**: single subagent reads PRD + architecture, writes `build-plan.md` (with exports table) + `build-context.md`. **Stage B**: parallel subagents write per-module spec files using build-plan.md as reference. Do NOT read PRD/architecture yourself.

### Stage A prompt — adapt paths per project:
```
You are a software architect. Discover the project, read PRD + architecture, and produce planning files.

Find and read: PRD (docs/PRD.md), Architecture (docs/architecture.md — optional, proceed without), manifest, source dir, test data dir, config files. If PRD is MISSING, stop and report immediately.

## PRD Format Analysis

Before planning, assess: (1) FR section name and ID scheme (e.g., FR-001), (2) FR fields (Input/Rules/Output/Error + optional Depends/Priority), (3) grouping structure and priority information, (4) other available sections (Overview, Journeys, NFRs, Data Entities, Tech Constraints, Implementation Reference). Record findings in build-plan.md under a **PRD Format Notes** block (3-5 lines).

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
4. **FR to Subsystem Map** — `{requirement_id}: subsystem — acceptance criterion` (use the PRD's own identifier scheme)
5. **Side-Effect & Validation Ownership** — who logs what, who validates what; each validation rule at exactly one pipeline stage. Non-owners must NOT log or duplicate checks. For each validation error code, list the **single owning module** and add an explicit **Non-Owner Exclusion List** — modules that touch the same fields but must NOT validate them. These exclusions are copied verbatim into Stage B spec files as "DO NOT validate X — owned by Y" lines. For orchestrator modules: include a **Field Population Map** — for each validated required field, list every source that can populate it (extraction, override, fallback from ANY FR — including transformation-phase sources) and the pipeline step. Cross-check: scan ALL FRs for keywords "override", "fallback", "default", "when empty", "use X as Y" — each is a population source that must appear in the map. Validation of a field MUST be sequenced after ALL its population sources. Additionally, include a **Detection-Fallback Map** — for each field that has both a primary detection path (e.g., header pattern match) and a fallback path (e.g., data-row scan), document the sequencing constraint: the primary detection MUST NOT hard-fail (e.g., return null/None) before the fallback has a chance to run. The primary should return a partial/incomplete result that the fallback can augment, and the hard-fail check should occur only after all fallback paths have been attempted.
6. **Shared Utilities** — functions/constants needed by 2+ modules. For each: signature, placement (module path), consumers, and brief implementation note (<10 lines each)
7. **Batch Plan** — modules grouped by dependency order; each with: path, test_path, FRs, **exports table** (function signatures with param types + return types), imports, **complexity** (simple/moderate/complex). The exports table is the interface contract for Stage B spec writers.
8. **Ambiguities** — unclear/contradictory requirements

**IMPORTANT — Batch Plan Rules:**
- Minimize batch count aggressively: target ≤ ceil(total_modules / 6) batches. Single-module batches are wasteful — merge with the nearest compatible batch. Entry points and thin wrappers (e.g., `__main__`, CLI arg parsing) always merge into the last real batch.
- Two modules can share a batch if neither depends on the other. Optimize for minimum sequential gates, not minimum batch "width."
- If the PRD provides per-FR priority (Must/Should/Could), batch Must FRs earlier. If priority is absent, batch by dependency order, grouping alphabetically by capability area within each batch.
- For each module, assign complexity: **simple** (pure functions, no I/O, <5 functions), **moderate** (some I/O or state, 5-10 functions), **complex** (orchestration, many edge cases, >10 functions).

**IMPORTANT — No Conventions in build-plan.md:**
Conventions belong ONLY in build-context.md. build-plan.md must NOT duplicate them — reference build-context.md instead.

## Write {project_root}/build-context.md with:
Stack, error handling strategy, logging pattern, all conventions, all side-effect rules, test requirements (3-5 per function: happy/edge/error), known gotchas (including third-party type-stub gaps and cross-extraction consistency: functions extracting values for downstream comparison must use identical precision/rounding rules), platform-specific considerations. Include an **Index Convention Table** documenting every shared data structure that uses row/column indices — for each, state whether it uses 0-based or 1-based indexing, and name the conversion pattern (e.g., "openpyxl row = internal_row + 1"). Include a **Data Representation Consistency Table** — scan ALL FRs for any field/column that the PRD says can appear in an alternative representation (merged cells, nested structures, encoded formats, nullable wrappers, etc.). List every such field and require ALL readers (not just the FR that mentions the alternative form) to handle it. If FR-X says "field F can appear in form Z" and FR-Y reads field F without mentioning form Z, the table must flag this and the spec for FR-Y's module must handle form Z. Include a **Subagent Constraints** section with universal implementation rules (no stubs, no type redefinition, no new deps, no cross-module mocking, fixture scoping, singleton teardown, dictionary key lookups must use exact casing from the definition source, wrap all parse/conversion calls for user-supplied data in try/except — fields with optional or polymorphic content may contain unexpected types) so the delegation prompt can reference it instead of repeating them.

Do NOT write spec files — that is Stage B's job.
Rules: PRD is source of truth. Distill prose, never parameters. Be exhaustive on exports table signatures. WRITE ALL FILES and verify they exist.
```

### After Stage A completes

1. **Verify files exist** — resume subagent if any are missing.
2. **Read `build-plan.md`** — verify exports table has concrete signatures, FR mapping is complete, batch plan follows merging rules.
3. **Resolve ambiguities** — ask user if needed.

### Stage B: Parallel Spec Writing

Launch parallel spec-writing subagents — one per batch group (2-4 batches per group, use `sonnet` model). Each writes specs for its modules.

Stage B prompt template:
```
Write spec files for these modules: {module_list}

Read {project_root}/build-plan.md for exports table (your interface contract), batch plan, FR mapping, shared utilities.
Read the PRD at {prd_path} for FR details referenced by your modules.
Read {project_root}/build-context.md for conventions and subagent constraints.

For each **moderate/complex** module, write `specs/{module_name}.md` with:
1. **Module path** and **test path**
2. **FRs** — distill prose but preserve ALL concrete parameters verbatim. Enumerated format/variant lists must be preserved as individual testable items. When the PRD lists patterned examples (e.g., `*`, `**`, `***`), note the generalization rule in Gotchas.
3. **Exports** — must match build-plan.md exports table exactly, add docstring summaries
4. **Imports** — module path + symbols + which functions to call. For orchestrators: include **required call order** with rationale
5. **Side-effect rules**, **Gotchas**, **Verbatim outputs** (copy user-visible strings character-for-character from PRD)
6. **Ownership exclusions** — copy from build-plan.md's Non-Owner Exclusion List. For each error code this module touches but does NOT own, add an explicit line: "DO NOT validate/log {error_code} for {field} — owned by {owning_module}." These prevent independently-built subagents from duplicating validation logic.
7. **Test requirements** — 3-5 per function. Each enumerated format/variant MUST have its own test case.

For **simple** modules (pure functions, <5 functions), use **compact format** — single file `specs/{module_name}.md`:
Module: {path} | Tests: {test_path} | FRs: {list}
Exports: (copy from build-plan.md exports table)
Imports: {module}: {symbols}
Tests: {3-5 one-line test descriptions}
Gotchas: {any, or "None"}

Cross-validate: (a) every Import resolves to an Export in build-plan.md, (b) orchestrator call order satisfies the Field Population Map — for each required field, every population source (extraction, override, fallback from any FR) precedes the validation step that checks it, (c) when two modules extract values for downstream comparison (e.g., per-item sum vs total row), both specs prescribe identical extraction/rounding rules, (d) orchestrator call order satisfies the Detection-Fallback Map — any function that has a fallback path must NOT have its primary path hard-fail (return null/None that blocks the pipeline) before the fallback runs. The spec must explicitly note that the primary returns a partial result and the hard-fail check occurs after all fallbacks, (e) data representation consistency — for every field listed in the Data Representation Consistency Table, verify that ALL readers in ALL specs handle the alternative form (not just the module whose FR mentions it), (f) ownership exclusions — verify that no spec validates/logs an error code it doesn't own per the Non-Owner Exclusion List. Fix issues before completing.
```

### After Stage B completes

1. **Spot-check** 2-3 complex specs — verify PRD parameters and enumerated format lists weren't lost. For orchestrator specs, verify call order satisfies the Field Population Map: trace each required field from its validation step backward to confirm all population sources (including cross-FR overrides/fallbacks) are sequenced earlier. Check that error short-circuits between population sources and validation don't prevent reaching later population steps.
2. **Verify ownership exclusions** — for each error code in the Non-Owner Exclusion List, grep specs for that code and confirm non-owning modules include the "DO NOT validate/log" line.
3. **Verify data representation consistency** — for each field in the Data Representation Consistency Table, grep specs for that field's reader functions and confirm all handle the alternative form.
4. **Verify verbatim outputs** — grep PRD for quoted strings/message templates; verify each appears in a spec. Resume subagent if missing.
5. **FR coverage check** — every FR in build-plan.md must appear in at least one spec.
6. **Validate dependency graph** — every import from strictly earlier batches. Re-order if violated.
7. **Create task list:** Scaffold → Batch 0..N → Integration Tests + Simplify → Validate → Commit, with `addBlockedBy` ordering.
8. **Initialize build log:** Write `{project_root}/build-log.md` with a header and Phase 1 completion entry.

**Gate:** If PRD MISSING, stop and ask user.

---

## Phase 2: Scaffold

**For greenfield projects:** Create directories + init files, manifest with deps, install/sync, cross-cutting infrastructure (error types, constants, models, logging config), test config + fixtures.

**For existing codebases:** Skip or minimally extend — only create new directories/files needed for new modules. Do NOT restructure existing code. Reuse existing test framework, fixtures, and configuration. If the project already has linting/type-checking config, use it.

**Dev tooling:** Install lint, type-check, and format tools listed in Build Config (`lint_tool`, `type_check_tool`, `format_tool`) as dev dependencies during scaffold. Do NOT defer this to batch gates — missing tools cause every batch to fail on the same issue.

**Shared utilities:** Implement all functions listed in the **Shared Utilities** section of `build-plan.md`. These are typically small (< 10 lines each) pure functions needed by multiple modules. Implementing them now prevents subagents from independently reimplementing them.

**Platform considerations:** Use the language's native path abstraction. Implement platform-specific gotchas from `build-context.md`.

**Delegation:** For large projects (>15 modules), delegate scaffold to a subagent to save main context. Provide the Shared Utilities signatures from `build-plan.md` and the directory structure in the prompt.

**Gate:** Test collection dry-run (e.g., `pytest --collect-only`) must succeed with zero errors. Verify a sample import path from the batch plan resolves.

Log scaffold completion to `build-log.md`.

---

## Phase 3: Delegate by Batch

Process batches in dependency order. Launch all modules within a batch **as parallel synchronous Task calls in a single message**. Do NOT use `run_in_background` — the batch gate needs all results, so blocking is correct. Then run the post-batch gate.

For batches with >10 modules, group related simple modules into combined tasks (2-3 per task) to reduce parallelism overhead.

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

Read {project_root}/specs/{module_spec}.md for your complete spec (requirements, exports, imports, side-effects, tests, gotchas, verbatim outputs).
Read {project_root}/build-context.md for project conventions and the Subagent Constraints section — follow all rules there.
Read source files of shared utilities (core/) you import — understand their behavior, don't reimplement.
EXPORTS must match the spec exactly. IMPORTS from lower batches are implemented — import and CALL them, do NOT mock.
The project has {passing_test_count} passing tests from prior batches — your changes must not break them.

Additional constraints:
- Only modify {module_path} and {test_path}. Do NOT touch __init__.py, conftest.py, or core modules.
- Tests must verify FR acceptance criteria. Each enumerated format/variant in the spec MUST have a dedicated test case. For numeric functions: include IEEE 754 artifact values.
- If your spec has a Verbatim Outputs section, write tests verifying exact string matches.
- For pipeline/orchestrator modules: call ordering MUST match spec's required sequence — data-populating steps must precede validation of the fields they populate.
- For complex modules: also skim the PRD and review upstream dependency tests to understand expected API behavior.
- If a required import doesn't exist or has wrong signature, STOP and report — do not stub or reimplement.
- Before finishing: run `{lint_command}`, `{type_check_command}`, `{test_command} {test_path}` — fix all errors. Re-read your spec's FRs — verify every criterion has a test.
```

### Post-batch gate

After ALL subagents in a batch complete, run a **tiered gate** based on batch composition:

**Lightweight gate** (batch contains only simple-complexity modules):
- Stub detection + batch tests only. Skip lint/type-check/scope-check (subagents already ran them per-module).

**Standard gate** (batch contains moderate or complex modules, or is a milestone):
- **Stub detection:** Search for `{stub_detection_pattern}`. Re-delegate if found.
- **Scope check:** `git diff --name-only` — files outside batch's expected paths are out-of-scope. Accept additions to shared/core; revert modifications to other modules' logic.
- **Format + lint + type check:** Run in parallel. If a fix pattern appears in ≥2 modules, append to `build-context.md`.
- **Test:** Run batch tests, then smoke test (`-x`/`--bail`/`--failfast`).

**Milestone gates** (midpoint + final batch): also run the **full test suite**. At midpoint, if test data exists, run the app against 1-2 representative files to catch integration-level bugs early (pipeline ordering, format coverage gaps surface here, not in unit tests).

Do NOT read subagent results on success — test results are your signal.

**On failure:** Read only failing output. Apply the retry budget (see Recovery).

**Partial advancement:** If most modules pass but some fail:
1. Mark passing modules as complete.
2. Fix or re-delegate failing module(s).
3. Re-run only failing tests + smoke test.
4. Advance to next batch once all modules pass.

**Log:** Append batch results to `build-log.md` (pass/fail, test count, any re-delegations).

### Final-batch additional gate

After the **last batch** only:

1. **Convention compliance:** Grep source files for user-visible log/print statements. Cross-reference against PRD format specs (log levels, message formats, field layouts). Check for duplicate messages or duplicate validation logic (same condition checked/rejected from 2+ pipeline stages) and convention divergence (inconsistent formatting across modules). For each error code, grep the source tree and verify it is logged/raised from exactly one module (the owner per build-plan.md). Multiple modules logging the same error code is a cross-batch ownership violation — remove from the non-owner.
2. **Dictionary key cross-reference:** For modules that look up fields by string keys (e.g., `dict.get("field_name")`), grep all lookup keys in source files and verify each key exists in the corresponding definition source (config schema, enum, dataclass fields). Silent `None` returns from mismatched keys (e.g., `"COD"` vs `"cod"`) are invisible to tests and type checkers — this gate catches them.
3. **Index convention consistency:** For each shared data structure that uses numeric indices (row/column indices, offsets), verify that every producer and consumer agrees on the convention (0-based vs 1-based). Check variable names, docstrings, and actual usage. A variable named `*_0based` that receives a 1-based value (or vice versa) is a latent bug that only surfaces when the code path is first exercised with real data.

Fix issues found. Log to `build-log.md`.

**Context rule:** Never write >30 lines of module code in main context — delegate instead.

---

## Phase 4: Integration Tests + Simplify

Run integration tests and cross-module simplification **in parallel** — they are independent. Launch both as parallel Task calls in a single message, then run the full test suite once after both complete.

### Integration Tests (subagent)

Subagent prompt:
```
Write integration tests in {test_dir}/test_integration.py (or equivalent).
Read {prd_path} for expected end-to-end behavior and output formats.
Read {project_root}/build-plan.md for module boundaries and the pipeline flow.
Read {project_root}/build-context.md for conventions.
Read the **actual source files** of orchestrator/pipeline modules to get real function signatures — do NOT guess APIs from specs alone.
Use real modules — no mocking of internal components.

Write tests in these categories:
1. **Boundary tests** (3-5) — wire 2-3 adjacent modules, pass realistic data, verify output. Focus on data handoff points; when adjacent modules extract values for comparison, verify identical precision.
2. **Full pipeline tests** (2-3) — synthetic input end-to-end, verify final output structure and content. Include a case where the primary source of a required field is EMPTY and only a cross-FR override/fallback populates it — this catches validation-before-population ordering bugs.
3. **Error propagation** (3-5) — trigger errors at different pipeline stages, verify they surface correctly to the caller with proper error codes/messages.
4. **Edge cases** (3-5) — empty input, minimal valid input, maximal input, duplicate entries, missing optional fields.
5. **Output format** (2-3) — verify end-to-end output matches PRD-specified formats. Check field order, delimiters, headers, encoding.

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
- After extracting/renaming, grep the entire {src_dir} for old names to catch dangling references. Zero old references must remain.
- When moving a tested function/constant to a shared module, ensure its test coverage moves too.
- Run {test_command} after changes to verify nothing breaks.
```

**Skip condition:** Only skip if gate disabled in Build Config, OR the batch plan had a single batch. Passing tests do NOT indicate absence of duplication.

### After both complete

Run the **full test suite**. Fix any failures before proceeding. Log both results to `build-log.md`.

---

## Phase 5: Validate

**If test data exists** (and gate is enabled), invoke the `/real-data-validation` skill **directly** — do NOT delegate skill invocation to a subagent (skill expansion + project context can exceed subagent context limits).

If the skill is unavailable, validate manually:
1. Execute `{run_command}` against test data directory
2. Categorize results (SUCCESS / ATTENTION / FAILED), cross-ref error codes against PRD
3. For failures indicating code bugs (not data issues): fix, re-run tests, re-validate (max 3 rounds)

After: if code changes were made, re-run full test suite. Relay results to user.

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
- Context compaction events (for cross-session recovery)
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
8. Keep glob/grep queries targeted — use specific patterns, limit results with `head_limit`, avoid listing large directories (e.g., 40+ files).
9. Keep main agent messages concise — short status updates, not verbose explanations.
10. Avoid reading large generated files (logs, outputs) — use targeted grep or tail instead.
11. Use `/compact` between phases — especially after Phase 1, midpoint of Phase 3, and before Phase 5.

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
| Subagent fails tests or leaves stubs | Read failing output only, apply retry budget. For stubs, emphasize "fully implement" |
| Out-of-scope changes to other modules | Revert logic changes; accept additions to shared/core if appropriate, note in build-log |
| Subagent redefined imported types | Delete duplicates, add imports — append reminder to build-context.md |
| Cross-module signature mismatch | Fix implementing module to match spec file |
| Implementation diverges from PRD | Spec lossy — verify spec FRs against PRD, fix spec, re-delegate |
| Phase 5 finds output/format bugs | Cross-ref PRD directly, fix code, append missing formats to build-context.md |
| Tests pass individually, fail together | Shared mutable state — check global state, singleton teardown, test ordering deps |
| Unit tests pass but real data fails | Cross-extraction inconsistency, spec parameter loss, or pipeline ordering — verify extraction rules match across modules, check PRD parameters against code, check Field Population Map for validation-before-population |
| Circular dependency | Move shared types to core module |
| Ambiguous requirement | Ask user — do not guess |
| Duplicate code across subagents | Phase 4 deduplication |
| Context getting large / subagent prompt too long | Delegate to fewer, larger subagents; run steps directly if skill expansion exceeds subagent limits |
| Spec or dependency missing | Resume Phase 1 subagent or fix scaffold; re-delegate |
| Dependency graph violation | Re-order batches per Phase 1 step 6, log to build-log.md |
| Dict key casing mismatch (e.g., "COD" vs "cod") | Grep all `.get("...")` and `["..."]` lookups, cross-reference against definition source (config, enum, dataclass). Silent None returns are invisible to tests — add targeted test for the lookup path |
| Index convention mismatch (0-based vs 1-based) | Trace the value from producer to all consumers, verify naming and arithmetic are consistent. Check both production code and test fixtures — tests using the wrong convention mask the bug |
| Primary detection blocks fallback (hard-fail before fallback runs) | Check Detection-Fallback Map in build-plan.md. Fix primary to return partial result; move hard-fail check after fallback |
| Validation fires before transformation populates field | Field Population Map violation — validation must be sequenced after ALL population sources (extraction + override/fallback FRs). Move validation call to after the last population step in orchestrator. Check for error short-circuits between population and validation that prevent reaching the population step |
| Duplicate validation from independently-built subagents | Check Non-Owner Exclusion List in build-plan.md. Remove the duplicate from the non-owning module. Add "DO NOT validate X — owned by Y" to spec and build-context.md to prevent recurrence |
| Alternative data representation handled by some readers but not others | Check Data Representation Consistency Table. When any FR says a field can appear in an alternative form, ALL readers of that field must handle it — not just the module whose FR mentions it |
| Parse/conversion crash on unexpected data types | Wrap parse calls in try/except for user-supplied fields. Fields with optional or polymorphic content may contain unexpected types not specified in the PRD |
