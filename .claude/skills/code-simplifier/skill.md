---
name: code-simplifier
description: Simplify and clean up source code files
---

# Code Simplifier

Analyze and simplify source code while preserving functionality. Takes a file path or directory as argument.

**Usage:** `/code-simplifier path/to/file.py` or `/code-simplifier src/`

---

## 1. Discover

**Auto-detect verification tools — do NOT ask the user.**

- **Linter:** Check `pyproject.toml` (`[tool.ruff]`, `[tool.flake8]`), `package.json` (`eslint`), `.eslintrc`, `Cargo.toml` (`clippy`), or similar. Determine the exact lint command.
- **Test runner:** Check `pyproject.toml`, `package.json`, `Makefile`, or similar. Determine the exact test command.
- **Formatter:** Check for `ruff format`, `black`, `prettier`, `rustfmt`, etc.
- **Virtual environment:** If Python, use the project's virtual environment for all commands.
- **No tests available?** Still proceed with simplification, but rely on the linter and careful review. Note the risk in the report.

---

## 2. Identify Targets

If given a file → process that file.
If given a directory → scan for source files (exclude tests, config, generated files).

**Skip these files:**
- Test files (`*_test.*`, `test_*.*`, `*.test.*`, `**/tests/**`, `**/__tests__/**`)
- Config files (`*.json`, `*.yaml`, `*.toml`, `*.cfg`, `*.ini`)
- Generated files (`*.generated.*`, `*_pb2.py`, `*.min.js`)
- Files under 20 lines (too small to benefit)

---

## 3. Simplify

For each target file, apply these rules in order:

**Remove dead code:**
- Unused imports
- Unused variables and functions (verify no external callers first)
- Unreachable code blocks
- Commented-out code (unless marked `# TODO`, `# FIXME`, or `# KEEP`)

**Reduce complexity:**
- Flatten nested conditionals (early returns, guard clauses)
- Replace complex boolean expressions with named variables
- Extract repeated logic into helpers (3+ occurrences)
- Simplify redundant type conversions
- Remove redundant `else` after `return` / `raise` / `continue` / `break`

**Improve readability:**
- Replace magic numbers with named constants
- Simplify overly verbose expressions

**Consolidate duplicates:**
- Merge similar functions that differ only in a parameter
- Extract common patterns into shared utilities

---

## 4. Constraints

- **DO NOT** change public API signatures (function names, parameters, return types)
- **DO NOT** remove code marked with `# KEEP` or `# REQUIRED`
- **DO NOT** add new dependencies
- **PRESERVE** all existing behavior — simplification must be strictly behavior-preserving
- **Apply changes incrementally** — one category of simplification at a time per file

---

## 5. Verify

After simplifying each file:
1. Run the linter on the modified file — fix any new violations
2. Run the formatter if available
3. Run tests that cover the modified file (or full suite if unsure)
4. If tests fail → revert the failing change, try an alternative approach or skip that simplification

---

## 6. Report

```
Files analyzed: N
Files modified: N (M skipped — no improvements found)
Lines removed: X

Changes:
- path/to/file.py: removed N unused imports, flattened N nested conditionals
- path/to/other.py: extracted helper function for repeated pattern

Verification:
- Linter: pass / N issues
- Tests: pass / N failures (with details)
- Skipped simplifications: (list any reverted due to test failures)
```
