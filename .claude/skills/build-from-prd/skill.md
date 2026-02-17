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

## PRD Format Analysis

Before planning, assess the PRD structure:
1. **Identify FR section** — find the section containing functional requirements (may be named "Functional Requirements", "Requirements", "Features", "Capabilities", etc.). Note the section name.
2. **Identify FR ID scheme** — detect the identifier pattern used (e.g., FR-001, FR-AUTH-001, REQ-1, user-registration, or plain numbered headings). Use whatever scheme the PRD uses consistently.
3. **Identify FR fields** — check which structured fields each FR provides. Expected: Input, Rules, Output, Error. Optional: Depends, Priority. Note any alternative naming (e.g., "Preconditions" for Depends, "Severity" for Priority).
4. **Identify grouping structure** — FRs may be grouped under capability area headings, numbered sections, or flat lists. Note the grouping method.
5. **Check for priority information** — FRs may have explicit Priority fields (Must/Should/Could), priority at the capability-area level, or none at all.
6. **Note available sections** — list which other sections exist (Overview, Journeys, NFRs, Data Entities, Tech Constraints, Implementation Reference) by scanning headings.

Record findings in build-plan.md under a **PRD Format Notes** block (3-5 lines) so the main agent can reference them during verification.

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
5. **Side-Effect Ownership** — who logs what, non-owners must NOT
6. **Shared Utilities** — functions/constants needed by 2+ modules. For each: signature, placement (module path), consumers, and brief implementation note (<10 lines each)
7. **Batch Plan** — modules grouped by dependency order; each with: path, test_path, FRs, exports, imports, **complexity** (simple/moderate/complex)
8. **Ambiguities** — unclear/contradictory requirements

**IMPORTANT — Batch Plan Rules:**
- Minimize batch count aggressively: target ≤ ceil(total_modules / 6) batches. Single-module batches are wasteful — merge with the nearest compatible batch. Entry points and thin wrappers (e.g., `__main__`, CLI arg parsing) always merge into the last real batch.
- Two modules can share a batch if neither depends on the other. Optimize for minimum sequential gates, not minimum batch "width."
- If the PRD provides per-FR priority (Must/Should/Could), batch Must FRs earlier. If priority is absent, batch by dependency order, grouping alphabetically by capability area within each batch.
- For each module, assign complexity: **simple** (pure functions, no I/O, <5 functions), **moderate** (some I/O or state, 5-10 functions), **complex** (orchestration, many edge cases, >10 functions).

**IMPORTANT — No Interface Contracts in build-plan.md:**
Do NOT include a full Interface Contracts section. All function signatures belong in per-module spec files only.

**IMPORTANT — No Conventions in build-plan.md:**
Conventions belong ONLY in build-context.md. build-plan.md must NOT duplicate them — reference build-context.md instead.

## Write {project_root}/build-context.md with:
Stack, error handling strategy, logging pattern, all conventions, all side-effect rules, test requirements (3-5 per function: happy/edge/error), known gotchas (including third-party type-stub gaps and float comparison pitfalls), platform-specific considerations. Include a **Subagent Constraints** section with universal implementation rules (no stubs, no type redefinition, no new deps, no cross-module mocking, fixture scoping, singleton teardown) so the delegation prompt can reference it instead of repeating them.

## Write per-module spec files to {project_root}/specs/
For EVERY module in the Batch Plan, create a file `specs/{module_name}.md` (e.g., `specs/extraction_invoice.md`) containing ONLY:
1. **Module path** and **test path**
2. **FRs** this module implements — distill prose but preserve ALL concrete parameters verbatim (thresholds, search ranges, patterns, priority orders). Enumerated format/variant lists (e.g., "Supported formats: X, Y, Z") must be preserved as individual testable items, not summarized. When the PRD lists patterned examples (e.g., `*`, `**`, `***`), note the generalization rule (e.g., "any all-asterisk string") in Gotchas.
3. **Exports** — exact function/class signatures with param types, return types, and docstring summaries
4. **Imports** — what this module imports (module path + symbol names + **which functions/methods it will call**). For pipeline/orchestrator modules: include **required call order** with dependency rationale (e.g., "transform before validate — override populates fields that validation checks")
5. **Side-effect rules** — what this module owns (logging, file I/O) and what it must NOT do
6. **Test requirements** — 3-5 test cases per function (happy/edge/error). Each enumerated format/variant from the FRs section MUST have its own dedicated test case.
7. **Gotchas** — any known pitfalls specific to this module
8. **Verbatim outputs** — every user-visible string this module produces: exact log messages (with log level), print formats, error message templates, status strings. Copy these **character-for-character** from the PRD. If the PRD specifies emoji, log level, field layout, or conditional formatting, include it exactly. If the PRD does not define exact output formats for this module, write "No verbatim formats specified by PRD" and move on. This section prevents distillation loss of output format requirements.

Each spec file should be **under 200 lines**.

**Before finishing:** cross-validate all specs: (a) every Import resolves to a source Export, (b) every Export appears as an Import in ≥1 consumer (orphans = missing wiring), (c) every module's imports come from strictly earlier batches (dependency ordering), (d) orchestrator specs have a required call order where data-populating steps (transforms, overrides, fallbacks) precede validation of the fields they populate. Fix all issues before completing.

Rules: PRD is source of truth. Distill prose, never parameters. Be exhaustive on signatures. WRITE ALL FILES and verify they exist.
```

### After subagent completes

1. **Verify files exist** — resume subagent if any are missing.
2. **Read `build-plan.md`**. **Spot-check** FRs section of 2-3 complex specs — verify concrete PRD parameters (ranges, thresholds, patterns) and enumerated format/variant lists weren't lost in distillation. For orchestrator specs, verify the required call order matches PRD data flow.
3. **Verify verbatim outputs (best-effort)** — grep the PRD for quoted strings, format examples, and message templates (e.g., `"SUCCESS"`, `"FAILED"`, log format patterns). If the PRD contains such strings, verify each appears in at least one spec file's **Verbatim Outputs** section and resume the subagent to add any missing. If the PRD does not specify exact output formats, skip this check.
4. **FR coverage check** — verify every FR in `build-plan.md`'s FR-to-Subsystem Map appears in at least one spec file's FRs section. If any FR is unassigned, resume the subagent to assign it to the appropriate module.
5. **Resolve ambiguities** — ask user if needed.
6. **Validate dependency graph:**
   - For each module in the Batch Plan, check that every module listed in its `imports` is in a strictly earlier batch.
   - If any violation found, re-order batches. Log to `build-log.md`.
7. **Create task list:** Scaffold → Batch 0..N → Integration Tests + Simplify → Validate → Commit, with `addBlockedBy` ordering.
8. **Initialize build log:** Write `{project_root}/build-log.md` with a header and Phase 1 completion entry.

**Gate:** If PRD or architecture MISSING, stop and ask user.

---

## Phase 2: Scaffold

**For greenfield projects:** Create directories + init files, manifest with deps, install/sync, cross-cutting infrastructure (error types, constants, models, logging config), test config + fixtures.

**For existing codebases:** Skip or minimally extend — only create new directories/files needed for new modules. Do NOT restructure existing code. Reuse existing test framework, fixtures, and configuration. If the project already has linting/type-checking config, use it.

**Dev tooling:** Install lint, type-check, and format tools listed in Build Config (`lint_tool`, `type_check_tool`, `format_tool`) as dev dependencies during scaffold. Do NOT defer this to batch gates — missing tools cause every batch to fail on the same issue.

**Shared utilities:** Implement all functions listed in the **Shared Utilities** section of `build-plan.md`. These are typically small (< 10 lines each) pure functions needed by multiple modules. Implementing them now prevents subagents from independently reimplementing them.

**Platform considerations:** Use `pathlib` for all file paths. The planning subagent documents platform-specific gotchas (encoding, BOM, path separators) in `build-context.md` — implement them here.

**Delegation:** For large projects (>15 modules), delegate scaffold to a subagent to save main context. Provide the Shared Utilities signatures from `build-plan.md` and the directory structure in the prompt.

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

Read {project_root}/specs/{module_spec}.md for your complete spec (requirements, exports, imports, side-effects, tests, gotchas, verbatim outputs).
Read {project_root}/build-context.md for project conventions and the Subagent Constraints section — follow all rules there.
EXPORTS must match the spec exactly. IMPORTS from lower batches are implemented — import and CALL them, do NOT mock.

Additional constraints:
- Only modify {module_path} and {test_path}.
- Tests must verify FR acceptance criteria. Each enumerated format/variant in the spec MUST have a dedicated test case. For numeric functions: include IEEE 754 artifact values.
- If your spec has a Verbatim Outputs section, write tests verifying exact string matches.
- For pipeline/orchestrator modules: call ordering MUST match spec's required sequence — data-populating steps must precede validation of the fields they populate.
- For complex modules: also skim the PRD to catch parameters the spec may have summarized.
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

After the **last batch** only: grep source files for user-visible log/print statements. Cross-reference against PRD format specs (log levels, message formats, field layouts). Check for duplicate messages (same condition reported from 2+ locations) and convention divergence (inconsistent formatting across modules). Fix issues found. Log to `build-log.md`.

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
1. **Boundary tests** (3-5) — wire 2-3 adjacent modules, pass realistic data, verify output. Focus on data handoff points between subsystems.
2. **Full pipeline tests** (2-3) — synthetic input end-to-end, verify final output structure and content. Include a case where an earlier stage populates a field that a later stage validates (e.g., override/fallback fills a required field).
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
- Run {test_command} after changes to verify nothing breaks.
```

**Skip condition:** Only skip if gate disabled in Build Config, OR the batch plan had a single batch. Passing tests do NOT indicate absence of duplication.

### After both complete

Run the **full test suite**. Fix any failures before proceeding. Log both results to `build-log.md`.

---

## Phase 5: Validate

**If test data exists** (and gate is enabled), delegate to a **general-purpose subagent** that invokes the `/real-data-validation` skill. The subagent MUST use the same model as the main agent (pass the `model` parameter) — validation requires deep PRD cross-referencing and code fixes, which need full capability.

Subagent prompt:
```
Invoke the /real-data-validation skill using the Skill tool, then follow its instructions to completion.

Project root: {root}

Build artifacts available (the skill knows how to use these):
- {root}/build-plan.md — Build Config with test_command, language, package_manager
- {root}/build-context.md — conventions, side-effect ownership, known gotchas
- {root}/specs/ — per-module spec files with FR mappings and verbatim outputs
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
8. Keep glob/grep queries targeted — use specific patterns, limit results with `head_limit`, avoid listing large directories (e.g., 40+ files).
9. Keep main agent messages concise — short status updates, not verbose explanations.
10. Use `/compact` mid-session if context exceeds ~60% between phases.

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
| Unit tests pass but real data fails | Subagent tested implementation, not spec — fix code in Phase 5 |
| Circular dependency | Move shared types to core module |
| Ambiguous requirement | Ask user — do not guess |
| Duplicate code across subagents | Phase 4 deduplication |
| Context getting large | Delegate remaining work to fewer, larger subagents |
| Spec or dependency missing | Resume Phase 1 subagent or fix scaffold; re-delegate |
| Dependency graph violation | Re-order batches per Phase 1 step 6, log to build-log.md |
