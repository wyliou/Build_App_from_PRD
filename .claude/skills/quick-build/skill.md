---
name: quick-build
description: Implement from PRD + architecture quickly
---

# Quick Build

Rapidly implement a project from PRD and architecture docs. Coordinates parallel subagents for speed. Main agent plans, scaffolds, and integrates — subagents write module code and tests.

**Context budget rule:** Every line that enters your context costs tokens. Minimize what you read, repeat, and inline. Delegate reading to subagents and communicate via files.

---

## Phase 1: Discover (subagent)

**Delegate discovery to a Plan subagent** to keep raw file contents out of main context.

### Subagent prompt:

```
Read the project and return a structured brief. Extract exactly what's listed below.

## Find and read these files:
- PRD: search for PRD.md, prd.md, or files containing "requirements" in docs/, project root
- Architecture: search for architecture.md, ARCHITECTURE.md, design.md in docs/, project root
- Project manifest: pyproject.toml, package.json, Cargo.toml, go.mod, etc.
- Existing source code: check src/, app/, lib/
- Test data: check if data/, samples/, fixtures/, or tests/data/ exists (path only — do NOT read file contents)

## Return this exact structure:

### File Paths
- PRD: {path or MISSING}
- Architecture: {path or MISSING}
- Manifest: {path}
- Source dir: {path}
- Test data dir: {path or NONE}

### Stack
- Language: | Test framework: | Package manager: | Dependency isolation:

### Requirements (from PRD)
For each FR: {FR_number}: {one-line description}

### Data Models (from architecture)
For each model: {name}: {fields with types, one line}

### Module Dependency Graph (from architecture)
{module} → depends on [{modules}]

### Cross-cutting Concerns
- Error handling: {strategy}
- Logging: {pattern}
- Validation: {approach}

### Existing Code Assessment
For each existing module: {module_path}: {status: complete|partial|stub} — {what's implemented}
If greenfield: "No existing code"

### Existing Tooling
- Test framework config: {path or NONE}
- Linting config: {path or NONE}
- Type checking config: {path or NONE}
- CI/CD config: {path or NONE}
```

**Gate:** If the brief reports PRD or architecture as MISSING, stop and ask the user.

---

## Phase 2: Plan (subagent → file)

**Delegate planning to a general-purpose subagent** that writes `build-plan.md` and `build-context.md`. This keeps PRD/architecture contents out of main context.

### Subagent prompt:

```
You are a software architect. Read the project docs and produce a build plan.

## Inputs
Read these files:
- PRD: {prd_path}
- Architecture: {architecture_path}
- Discovery brief: (included below)

{paste_discovery_brief_here}

## Task
Produce TWO files:

### File 1: {project_root}/build-plan.md
Contains:

#### 1. Build Config
| Key | Value |
|-----|-------|
| language | |
| package_manager | |
| test_command | |
| lint_command | |
| lint_tool | (package name to install as dev dep) |
| type_check_command | |
| type_check_tool | (package name to install as dev dep) |

#### 2. Interface Contracts
For every public function called across module boundaries:
module.function(param: Type, ...) -> ReturnType
  Called by: [modules]

#### 3. Batch Plan
Group unbuilt/incomplete modules by dependency order:
- Batch 0: [modules with no unbuilt deps]
- Batch 1: [modules depending only on batch 0]
For each module: module_path, test_path, FRs, exports, imports.

### File 2: {project_root}/build-context.md
A self-contained reference file for all subagents. Contains:
- Stack info (language, test framework, package manager)
- Error handling strategy
- Logging pattern
- All conventions (formatting, naming, return semantics)
- Side-effect ownership rules
- Test requirements (happy path, edge cases, error cases, 3-5 per function)
- Known gotchas
- Platform-specific considerations (Windows encoding, path handling, etc.)

## Rules
- Read the PRD as the source of truth
- Do NOT include raw PRD/architecture text — distill into structured sections
- Do NOT duplicate conventions in build-plan.md — they belong in build-context.md only
- Proceed quickly — this is rapid build mode
```

### After the subagent completes:

1. Read `build-plan.md` — this is your working reference.
2. Verify `build-context.md` exists (subagents will read it).
3. **Create task list** via `TaskCreate`: Scaffold → Batch 0..N → Validate → Commit. Set `addBlockedBy`.
4. **Proceed immediately** — do NOT wait for user approval.

---

## Phase 3: Scaffold (main agent)

Create the project foundation before delegating any implementation:

- Directory structure and module init files
- Project manifest with all dependencies
- **Dev tooling:** Install lint and type-check tools from Build Config (`lint_tool`, `type_check_tool`) as dev dependencies now — do not defer to batch gates
- Install / sync dependencies
- Cross-cutting infrastructure: error types, shared constants, data models, logging config
- Shared test configuration and fixtures
- Verify the scaffold compiles / imports cleanly

**For existing codebases:** Reuse existing test framework, fixtures, linting config, and type-checking config. Only create new directories/files needed for new modules.

**Platform considerations:**
- **Windows:** Ensure UTF-8 encoding for file I/O (stdout/stderr reconfiguration if needed). Use `pathlib` for paths.
- **All platforms:** Use `pathlib` for file paths. Avoid shell-specific syntax in scripts.

**Gate:** Run a test collection dry-run (e.g., `pytest --collect-only`, `jest --listTests`). Must succeed before proceeding.

---

## Phase 4: Build by Batch (subagents)

Process batches in dependency order. **Launch all subsystems within a batch in parallel** via the `Task` tool.

### Delegation prompt template:

```
Implement and test: {subsystem_name}
Module: {module_path} | Tests: {test_path}

## Requirements
Read {prd_path} for requirements: {FR_list}.
The PRD is authoritative.

## Shared Context
Read {project_root}/build-context.md for conventions, contracts, and cross-cutting rules.

## This Module's Interfaces
### EXPORTS (signatures must match exactly):
{exported_function_signatures}

### IMPORTS (already implemented, import directly):
{imported_function_signatures}

## Constraints
- Do NOT modify files outside {module_path} and {test_path}
- Do NOT install additional dependencies
- Do NOT redefine types, classes, or dataclasses that exist in your imports — import them from the owning module
- Run tests before finishing: {test_command}
```

### Post-batch gate (main agent)

After ALL subagents in a batch finish:

1. **Do NOT read TaskOutput** for successful agents. Run the full test suite instead.
2. Run type check / lint if applicable.
3. **All must pass before starting the next batch.** If tests fail:
   - Read only the failing test output.
   - Simple fix → fix directly. Complex fix → delegate to a subagent.

**Context rule:** If you're about to write more than 30 lines of module code in main context, delegate to a subagent instead.

---

## Phase 5: Validate

**If test data exists**, delegate to a subagent:

```
Run real-data-validation. Follow the 5-step process: Baseline, Run Against All Data, Investigate Non-Ideal Results, Fix and Re-run, Report.

Project root: {root}
PRD: {prd_path}
Test data: {data_dir}
Run command: {run_cmd}
Test command: {test_cmd}

Read {project_root}/build-context.md for conventions and expected behavior.

Key principles:
- Default assumption: code is wrong, not data.
- Group failures by similarity before investigating.
- Fix likely code bugs IMMEDIATELY before investigating uncertain cases.
- Cross-reference failures against PRD directly.
- Iterate for up to 3 rounds until stable.

Write report to {project_root}/validation-report.md.
```

After it completes, read `validation-report.md` (not TaskOutput) and relay to the user.

**If no test data exists**, run the full test suite one final time and report results.

---

## Phase 6: Commit

- Use `/commit` when the user is ready.
- Do NOT auto-commit. Wait for user instruction.

---

## Context Budget Rules

1. **Never read PRD/architecture in main context.** Subagents read them; main agent works from `build-plan.md`.
2. **Never inline shared context.** Subagents read `build-context.md`.
3. **Never read TaskOutput on success.** Run tests instead.
4. **Never write >30 lines of module code in main context.** Delegate instead.
5. **Minimize fix cycles in main context.** Delegate complex fixes to subagents.

---

## Recovery

| Problem | Action |
|---------|--------|
| Subagent returns with failing tests | Read only failing output, fix or re-delegate |
| Cross-module type/signature mismatch | Fix implementing module to match contract |
| Subagent redefined types from imports | Delete duplicates, add imports — append reminder to build-context.md |
| Subagent can't find dependency module | Scaffold is incomplete — fix and re-delegate |
| Dev tools missing at batch gate | Install immediately, note in build-context.md |
| Tests pass individually but fail together | Shared mutable state — add isolation |
| Validation finds code bugs | Fix directly, re-run validation |
| Validation finds formatting bugs | Likely spec distillation loss — cross-ref PRD directly, fix code |
| Import/circular dependency error | Refactor to break the cycle |
| Context getting large | Delegate remaining work to fewer, larger subagents |
