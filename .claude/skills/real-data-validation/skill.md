---
name: real-data-validation
description: Validate a build against real test data and PRD requirements
---

# Real Data Validation

Validate a completed implementation against real test data and PRD requirements. Investigates every non-ideal result, fixes code bugs, and re-runs until stable.

Can be invoked standalone or delegated to by another skill (e.g., `build-from-prd`, `quick-build`).

## Inputs

Locate and read:

- **PRD**: Search for `PRD.md`, `prd.md`, or files containing "requirements" / "product requirements" in `docs/`, project root, or any reasonable location.
- **Architecture**: Search for `architecture.md`, `ARCHITECTURE.md`, `design.md`, or similar. Needed to understand module boundaries and data flow during investigation.
- **Source code**: Check `src/`, `app/`, `lib/`, or the project's established source directory.
- **Test suite**: Check `tests/` or the project's test directory.
- **Test data**: Check `data/`, `samples/`, `fixtures/`, `tests/data/`, or similar.
- **Project manifest**: `pyproject.toml`, `package.json`, `Cargo.toml`, `go.mod`, etc. to understand how to run tests and the application.

STOP if PRD, source code, or test data is missing — report what's absent.

### Build artifacts (when delegated from `build-from-prd` or `quick-build`)

Check the project root for these files — if they exist, use them instead of re-detecting:

- **`build-plan.md`**: Contains a **Build Config** table with pre-computed `test_command`, `run_command`, `src_dir`, `test_dir`, language, and package manager. Use these directly in Step 1 instead of re-detecting the stack.
- **`build-context.md`**: Contains project conventions, side-effect rules, error handling patterns, and known gotchas. Read this for context during investigation — it explains which module owns which side-effect (logging, file I/O), which prevents misclassifying ownership bugs.
- **`specs/`**: Per-module spec files with FR mappings, exports, and verbatim outputs. Useful for understanding module boundaries during investigation, but always cross-reference the **PRD directly** — specs may have lost parameters during distillation.

---

## Step 1: Baseline

1. **Detect the stack.** If `build-plan.md` exists, read the **Build Config** table for pre-computed commands (test_command, language, package_manager, src_dir, test_dir). Otherwise, detect from the project manifest. Determine the test command, run command, and dependency isolation method.
2. **Run the full test suite.** Record the pass/fail count.
   - If tests fail, fix them before proceeding. Do not investigate test data with a broken test suite.
3. **Identify the entry point** — how to execute the application against test data:
   - Check the project manifest for scripts / entry points / bin commands.
   - Look for `main` files, CLI modules, `Makefile` targets, or run scripts.
   - Read the PRD or README for usage instructions.
   - If the application is a library (not a CLI/server), identify the top-level function that processes input and write a short runner script.
4. **Smoke test** — run the application against **one** test input to verify it starts, processes without crashing, and produces output. If the smoke test fails (config errors, missing dependencies, startup exceptions), fix the blocker before running against all data. This catches environment and config issues cheaply.

---

## Step 2: Run Against All Test Data

1. **Execute the application** against every input in the test data directory. **Capture output to a file** (e.g., `> validation-run-1.log 2>&1`) for reliable parsing.
   - For **CLI/batch apps**: run the command against all input files.
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

**Scan for convention/ownership bugs** by analyzing the captured output file:
- Extract all warning/error lines, group by error code.
- Flag any error code that appears 2+ times for the same input (possible duplicate reporting).
- Flag same condition reported with different wording from different modules.
- Flag inconsistent message formatting (different prefixes, capitalization, templates).

These are **convention divergence or responsibility overlap bugs** — two modules independently detecting/reporting the same condition. If `build-context.md` exists, use its **Side-Effect Ownership** rules to quickly identify which module is the rightful owner. Classify and fix as code bugs before investigating data failures.

### Phase B: Quick triage (main agent)

For each group, do a **lightweight check** in main context before committing to deep investigation:

1. **Read the error message.** Identify the function and line where the non-ideal outcome originates.
2. **Read the failing function** (~50 lines around the failure site). Do NOT trace the entire pipeline.
3. **Quick data check** — write one **batch diagnostic script per group** (not per file). The script should process ALL files in the group and print a summary table. This is faster than individual scripts and reveals whether the issue is consistent across the group.
   - Stack-agnostic framing: write a minimal script that reads the raw input at **both** the code's failure point **and** PRD-specified locations. Use whatever tool fits the stack (openpyxl for Excel, jq for JSON, DOM parser for XML, curl for APIs, etc.).
   - Print values in **related fields** and at **PRD-specified locations** — the data may exist where the PRD says to look, not where the code currently searches.
4. **Quick PRD check** — **read** the relevant PRD section (not just grep). Compare the PRD's specified algorithm (search ranges, patterns, columns, thresholds) against the code's actual implementation. Also check for fallbacks, overrides, defaults.

After quick triage, classify each group into one of:
- **Likely code bug** — PRD defines behavior the code doesn't implement, or implements with wrong parameters (search ranges, patterns). Fix immediately.
- **Likely data issue** — input genuinely lacks required data. Needs confirmation but low priority.
- **Uncertain** — needs deep investigation to determine.

### Phase C: Fix-first loop

**Fix likely code bugs IMMEDIATELY, before investigating uncertain groups.** Then re-run (Step 4). This is critical for efficiency: one code fix often resolves multiple groups, making further investigation unnecessary.

Only proceed to deep investigation for groups that survive the re-run.

### Phase D: Deep investigation (uncertain groups only)

For groups still unresolved after the fix-first loop, investigate the representative thoroughly:

1. **Inspect the actual input data** with a diagnostic script (if not already done in Phase B).
2. **Cross-reference the PRD** — **read** the full PRD section for the failing feature (not just grep for keywords). Check for:
   - **Algorithm match** — do the code's search ranges, patterns, column limits, and thresholds match the PRD? Parameter mismatches are code bugs even when "not found" seems like a data issue.
   - **Fallbacks or overrides** — does the PRD define an alternative source, default, or override for this field?
   - **Phase ordering / edge cases** — is the error firing before a required transformation? Does the PRD define behavior for empty/missing/malformed values?
3. **Classify root cause** — one of:
   - **Code bug** — the PRD defines behavior the code doesn't implement, implements with wrong parameters (ranges, patterns, thresholds), or in the wrong order. **Fix it.**
   - **Legitimate data issue** — the input genuinely lacks required data and the PRD defines no mechanism to handle it. **Document it.**
   - **PRD gap** — the PRD doesn't cover this edge case. **Flag it.**
4. **Default assumption: code is wrong.** Only classify as "data issue" after confirming:
   - You have inspected the actual input data at **PRD-specified locations** (not just where the code searches)
   - You have verified the code's search parameters (ranges, patterns, columns) match the PRD specification
   - You have checked PRD for fallback/override/default rules and verified correct implementation order
   - The input genuinely cannot satisfy the requirement through any PRD-defined mechanism

### Investigation strategy: main agent vs subagents

**Do NOT run parallel subagents AND investigate the same groups yourself.** Choose one:

- **Main agent handles all** (preferred for <=5 groups): Faster, no stale notification overhead, direct fix-first loop.
- **Delegate to subagents** (for >5 groups or very complex investigations): Launch subagents for uncertain groups only AFTER the fix-first loop. Do not investigate those groups yourself — wait for subagent results.

**Never duplicate work** — if you delegate a group to a subagent, do not also investigate it in main context.

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
4. **Re-run against all test data** to check how many issues each fix resolved. Capture output to `validation-round-{N}.log`.
5. **Compare with previous round** — diff the tier counts. Report the delta (e.g., "+2 SUCCESS, -1 ATTENTION, -1 FAILED").

### Iteration

6. **Repeat Steps 2–4** for up to **3 rounds**. A round is "stable" when no new code bugs are found. Stop early if:
   - All results are ideal, or
   - Only legitimate data issues and PRD gaps remain (no code bugs found this round), or
   - Tier counts are identical to the previous round.
7. If round 3 still finds new code bugs, report this to the user — the codebase may need broader refactoring beyond validation scope.

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
- **Round-over-round delta table** — shows improvement trajectory across rounds.
- **Every non-ideal result** — even if grouped during investigation, list each input individually so nothing is silently dropped.
- **Every code bug** — with symptom, root cause, fix, and impact count.
- **Test updates** — every test modified due to code fixes, with rationale.
- **Recommendations** — actionable suggestions for remaining data issues and PRD gaps.
