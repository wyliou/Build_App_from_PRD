---
name: real-data-validation
description: Validate implementation against real data, classify failures as code bugs or input issues
---

# Validate Real Data

Run the tool against ALL test inputs, classify every failure, fix code bugs, report the rest.

---

## 1. Auto-Discover

**Find everything needed — do NOT ask the user.**

- **Entry point:** Search for CLI entry points (`__main__.py`, `cli.py`, `main.py`, `main.go`, `index.ts`, etc.), `pyproject.toml` scripts, `package.json` scripts, or `Makefile` targets. Determine the exact command to run the tool.
- **Test data:** Scan for input files in `data/`, `samples/`, `fixtures/`, `tests/fixtures/`, or similar. Identify the file types and count.
- **Spec docs:** Find PRD/requirements in `docs/` or project root for cross-referencing failures against requirements.
- **Expected outputs:** Check for golden/expected output files (e.g., `tests/fixtures/expected/`, `data/expected/`) for comparison.
- **Virtual environment:** If Python, use the project's virtual environment for execution.

---

## 2. Initial Run

Run the tool against ALL inputs in a single batch. Capture full output (stdout + stderr + exit code).

- If 100% pass → report summary and exit. No further steps needed.
- Otherwise → proceed to analysis.

---

## 3. Classify Failures

**Scope: ALL non-success outcomes** — not just hard errors. Warnings and degraded outputs can also indicate code bugs.

For each non-success file:

1. **Identify** — which function/phase failed? What value or condition caused it?
2. **Cross-reference spec** — does the PRD require handling this case?
3. **Classify:**

| Classification | Criteria | Action |
|----------------|----------|--------|
| **code_bug** | Logic is wrong, implementation doesn't match spec | Fix it |
| **integration_gap** | Function exists but never called in the pipeline | Wire it up |
| **delegation_gap** | Spec requires it, but it's not implemented at all | Implement it |
| **needs_deep_analysis** | Cause unclear, data-related, pattern unknown | → Step 4 |

**Signs of integration_gap:** Function is exported but has no call sites in the pipeline.
**Signs of delegation_gap:** Spec has a rule/pattern not found anywhere in the code.

---

## 4. Deep Analysis

For every `needs_deep_analysis` file — do NOT skip to `input_issue` without this step.

**4a. Extract the actual data causing failure:**
- Part mismatch → list ALL parts from both sides
- Empty field → show detected columns + actual cell values
- Weight error → show all weights + positions

**4b. Compare across files for patterns:**
```
File 1: Invoice "ABC-001" vs Packing "ABC001" (dash stripped)
File 2: Invoice "XYZ-002" vs Packing "XYZ002" (dash stripped)
→ PATTERN: Dash normalization needed
```

**4c. Pattern checklist:**
- String: case, whitespace, dashes, underscores, trailing spaces
- Prefix/suffix: "P/N:", "NO.", unit suffixes
- Type coercion: "001" vs 1, float vs int
- Encoding: unicode variants, fullwidth characters

**4d. Final classification:**

| Classification | Criteria | Action |
|----------------|----------|--------|
| **code_bug** | Pattern found, fixable in code | Fix it |
| **requires_user_action** | Pattern found, needs config/schema change | Report with suggested fix |
| **input_issue** | No pattern, genuinely unique data problem | Document only |

**Rule:** Only modify source code. Config/schema changes → `requires_user_action`.

---

## 5. Fix and Re-Run

For each `code_bug`, `integration_gap`, and `delegation_gap`:
1. Implement the fix
2. Re-run ALL files (not just the previously failing one — fixes can cause regressions)
3. Max 3 fix-rerun iterations per issue. If still failing after 3 attempts, reclassify as `needs_deep_analysis`.

---

## 6. Summary

Report final results:

```
Results: X/Y passed (Z%)

Fixed:
- Code bugs: N
- Integration gaps: N
- Delegation gaps: N

Remaining:
- Requires user action: N (pattern found, non-code fix needed)
- Input issues: N (verified unique, no code fix possible)

Details:
- Patterns fixed: <list with before/after evidence>
- Requires user action: <file: pattern + suggested fix>
- Input issues: <file: specific unique issue>
```
