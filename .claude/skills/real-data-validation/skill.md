---
name: real-data-validation
description: Validate a build against real test data and PRD requirements
---

# Real Data Validation

Validate a completed implementation against real test data and PRD requirements. Investigates every non-ideal result, fixes code bugs, and re-runs until stable.

Can be invoked standalone or delegated to by another skill (e.g., `build-from-prd`, `quick-build`).

## Inputs

### Primary sources (required)

These are the **only** sources of truth for understanding requirements and classifying bugs:

- **PRD**: Search for `PRD.md`, `prd.md`, or files containing "requirements" / "product requirements" in `docs/`, project root, or any reasonable location. This is the authoritative reference for ALL investigation — what the code should do, what parameters to use, what edge cases to handle.
- **Architecture**: Search for `architecture.md`, `ARCHITECTURE.md`, `design.md`, or similar. Use this to understand module boundaries, data flow, and side-effect ownership during investigation.
- **Source code**: Check `src/`, `app/`, `lib/`, or the project's established source directory.
- **Test suite**: Check `tests/` or the project's test directory.
- **Test data**: Check `data/`, `samples/`, `fixtures/`, `tests/data/`, or similar.
- **Project manifest**: `pyproject.toml`, `package.json`, `Cargo.toml`, `go.mod`, etc. to understand how to run tests and the application.

STOP if PRD, source code, or test data is missing — report what's absent.

### Build artifacts (optional — stack detection only)

If `build-plan.md` exists, read its **Build Config** table for pre-computed commands (`test_command`, `run_command`, `src_dir`, `test_dir`, language, package manager). This saves re-detecting the stack in Step 1.

**Do NOT use build artifacts (`build-context.md`, `specs/`) for investigating failures or classifying bugs.** These are derived from the PRD and may have lost parameters during distillation — using them for investigation would inherit the same blind spots that caused the bugs. Always cross-reference the PRD and architecture directly.

---

## Step 1: Baseline

1. **Detect the stack.** Read the project manifest to determine language, package manager, test command, run command, and dependency isolation method. If `build-plan.md` exists, its **Build Config** table has pre-computed commands that can accelerate this step.
2. **Run the full test suite.** Record the pass/fail count.
   - If tests fail, fix them before proceeding. Do not investigate test data with a broken test suite.
3. **Identify the entry point** — how to execute the application against test data:
   - Check the project manifest for scripts / entry points / bin commands.
   - Look for `main` files, CLI modules, `Makefile` targets, or run scripts.
   - Read the PRD or README for usage instructions.
   - If the application is a library (not a CLI/server), identify the top-level function that processes input and write a short runner script.
4. **Smoke test** — run the application against a **simple, representative** test input to verify it starts, processes without crashing, and produces output. If the smoke test fails (config errors, missing dependencies, startup exceptions), fix the blocker before running against all data.

---

## Step 2: Run Against All Test Data

1. **Execute the application** against every input in the test data directory. **Capture all output (stdout+stderr) to a UTF-8 encoded file** (name: `validation-round-{N}.log`). Prefer batch/directory mode over per-file invocation if the app supports it — faster and catches cross-file state bugs.
   - For **CLI/batch apps**: run the command against all input files (batch mode preferred).
   - For **APIs/servers**: start the server, send requests with each test input, capture responses.
   - For **libraries**: call the entry function with each test input.
2. **Parse results programmatically.** Grep or regex the output file to extract tier counts. Do not manually read terminal output. Example approaches:
   - `grep -c "SUCCESS\|FAILED\|WARNING" output.log`
   - Count exit codes per file
   - Parse structured output (JSON, CSV) if available
3. **Classify results into outcome tiers** using whatever the application reports (e.g., SUCCESS/WARNING/FAILED, pass/warn/error, exit codes). If the application has no built-in classification:
   - **Success**: completed without errors, output looks correct.
   - **Warning**: completed but logged warnings or produced partial output.
   - **Failed**: crashed, returned error, or produced no output.
4. **Record the tier counts** — e.g., "35 success, 2 warning, 4 failed".
5. **Save the output file** — keep it for round-over-round comparison (name as `validation-round-{N}.log`).

---

## Step 3: Investigate Non-Ideal Results

### Phase A: Group + convention scan

**Group failures by similarity first** — same error message, same failing function, same missing field. Investigate one representative per group, not every individual failure.

**Scan for convention/ownership bugs** in the captured output:
- Group all warning/error lines by error code. Flag codes appearing 2+ times per input (duplicate reporting) or the same condition reported differently from different modules.
- These are responsibility overlap bugs. Check the architecture doc for module boundaries and the PRD for side-effect ownership. Fix as code bugs before investigating data failures.

### Phase B: Quick triage (main agent)

For each group, do a **lightweight check** in main context before committing to deep investigation:

1. **Read the error message.** Identify the function and line where the non-ideal outcome originates.
2. **Read the failing function** (~50 lines around the failure site). Do NOT trace the entire pipeline.
3. **Quick data check** — write one **batch diagnostic script per group** (not per file) and save for reuse in later rounds. The script should process ALL files in the group and print a summary table comparing values at the code's failure point AND at PRD-specified locations. Use whatever tool fits the stack (openpyxl, jq, DOM parser, etc.). Data may exist where the PRD says to look, not where the code currently searches.
4. **Quick PRD check** — **read** the relevant PRD section (not just grep). Compare the PRD's specified algorithm (search ranges, patterns, columns, thresholds) against the code's actual implementation. Check for fallbacks, overrides, defaults. Also check if the code makes positional assumptions (index-based computation) that break when upstream produces non-consecutive positions (skipped rows, filtered items).

After quick triage, classify each group into one of:
- **Likely code bug** — PRD defines behavior the code doesn't implement, or implements with wrong parameters. Fix immediately.
- **Likely data issue** — input genuinely lacks required data. Needs confirmation but low priority.
- **Uncertain** — needs deep investigation to determine.

**Dual-issue files:** If a file has both a code bug AND a data issue, track both separately. After the code bug is fixed, the data issue will remain — don't re-investigate it.

### Phase C: Fix-first loop

**Fix likely code bugs IMMEDIATELY, before investigating uncertain groups.** Then re-run (Step 4). This is critical for efficiency: one code fix often resolves multiple groups, making further investigation unnecessary.

Only proceed to deep investigation for groups that survive the re-run.

### Phase D: Deep investigation (uncertain groups only)

For groups still unresolved after the fix-first loop, investigate thoroughly:

1. **Inspect the actual input data** with a diagnostic script (reuse from Phase B if available).
2. **Cross-reference the PRD** — **read** the full PRD section for the failing feature. Check: algorithm match (search ranges, patterns, thresholds vs code), fallbacks/overrides/defaults, phase ordering, and behavior for empty/missing/malformed values. Parameter mismatches are code bugs even when "not found" seems like a data issue.
3. **Classify root cause:**
   - **Code bug** — PRD defines behavior the code doesn't implement or implements with wrong parameters. **Fix it.**
   - **Legitimate data issue** — input genuinely lacks required data and PRD defines no mechanism. **Document it.**
   - **PRD gap** — PRD doesn't cover this edge case. **Flag it.**
4. **Default assumption: code is wrong.** Only classify as "data issue" after confirming you inspected data at PRD-specified locations (not just where code searches), verified code parameters match PRD spec, checked for fallback/override/default rules, and the input genuinely cannot satisfy the requirement.

### Investigation strategy: main agent vs subagents

**Do NOT run parallel subagents AND investigate the same groups yourself.** Choose one:

- **Main agent handles all** (preferred for ≤5 groups): Faster, direct fix-first loop.
- **Delegate to subagents** (for >5 groups): Launch for uncertain groups only AFTER the fix-first loop. Do not investigate those groups yourself.

---

## Step 4: Fix and Re-run

### Fixing code

1. Fix the code bug(s) identified in Step 3.
2. **Update tests that encode buggy behavior.** After fixing code, some existing tests may fail because they tested the *old, incorrect* behavior. These are not regressions — they are tests that need updating:
   - If a test asserts the old (buggy) output, update the assertion to match the corrected behavior.
   - If a test's fixture setup assumed the buggy logic (e.g., placing data at wrong positions), update the fixture.
   - If a test fails for reasons *unrelated* to your fix, that IS a regression — investigate.

### Re-running

3. **Re-run the full test suite** to verify no regressions. All tests must pass.
4. **Predict expected delta** — before re-running, list which files should change status and the expected new tier counts. This catches incomplete fixes and unexpected side effects.
5. **Re-run against ALL test data** (not a sample — running everything gives complete comparison data). Capture output to `validation-round-{N}.log`.
6. **Compare actual vs predicted** — diff tier counts against prediction. Any mismatch (file didn't improve, or a passing file regressed) must be investigated before proceeding.

### Iteration

7. **Repeat Steps 2–4** for up to **3 rounds**. A round is "stable" when no new code bugs are found. Stop early if:
   - All results are ideal, or
   - Only legitimate data issues and PRD gaps remain (no code bugs found this round), or
   - Tier counts are identical to the previous round.
8. If round 3 still finds new code bugs, report this to the user — the codebase may need broader refactoring beyond validation scope.

---

## Step 5: Report

Write the report to `{project_root}/validation-report.md`.

```markdown
## Test Suite
{pass_count} passed, {fail_count} failed

## Data Validation Summary
| Metric | Round 1 | Round 2 | ... | Final |
|--------|---------|---------|-----|-------|
| Total inputs | N | N | ... | N |
| Success | X | X | ... | X |
| Warning | X | X | ... | X |
| Failed | X | X | ... | X |
| **Automation rate** | X% | X% | ... | X% |
| Code bugs found | X | X | ... | X |

Stabilized in round {N} of 3.

## Code Bugs Found and Fixed
### Bug {N}: {title}
- **File:** {file_path}
- **Symptom:** {what the user sees}
- **Root cause:** {why it happens}
- **Fix:** {what was changed}
- **Impact:** {how many inputs this resolved}

## Non-Ideal Results (final round)
| Input | Outcome | Classification | Explanation |
|-------|---------|----------------|-------------|
| ...   | ...     | data issue / PRD gap | ... |

## Test Updates
- {test_file}: {what was updated and why}

## Recommendations
- {actionable suggestions for data issues and PRD gaps}
```

Include:
- **Round-over-round deltas** — shows improvement trajectory. List every non-ideal result individually (even if grouped during investigation) so nothing is silently dropped.
- **Every code bug** — with symptom, root cause, fix, and impact count.
- **Test updates** — every test modified due to code fixes, with rationale.
- **Recommendations** — actionable suggestions for remaining data issues and PRD gaps.
