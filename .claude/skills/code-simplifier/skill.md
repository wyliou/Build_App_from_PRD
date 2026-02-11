---
name: code-simplifier
description: Simplify and clean up source code files
---

# Code Simplifier

Analyze and simplify source code while preserving functionality.

## Usage

Run on a single file:
```
/code-simplifier path/to/file.ext
```

Run on a directory:
```
/code-simplifier src/
```

## Simplification Rules

### 1. Remove Dead Code
- Unused imports
- Unused variables
- Unreachable code blocks
- Commented-out code (unless marked `# TODO`, `# FIXME`, `// TODO`, `// FIXME`)

### 2. Reduce Complexity
- Flatten nested conditionals where possible
- Replace complex boolean expressions with named variables
- Extract repeated logic into helper functions (3+ occurrences)
- Simplify redundant type conversions

### 3. Improve Readability
- Replace magic numbers with named constants
- Simplify overly verbose expressions
- Remove redundant else after return/raise/throw/continue/break

### 4. Consolidate Duplicates (within files)
- Merge similar functions with minor differences
- Extract common patterns into utilities
- Remove duplicate validation logic

### 5. Cross-Module Deduplication
When running on a directory, scan for code duplicated **across** modules:
- **Identical functions** — same logic in multiple files (e.g., helper functions written independently by subagents). Consolidate into a single shared module and update all import sites.
- **Near-identical functions** — same logic with minor naming or parameter differences. Unify the signature, consolidate, and update callers.
- **Duplicate constants** — same set/dict/list/enum defined in multiple files. Move to a shared location in the most appropriate common module.
- **Shared placement** — place consolidated code in the lowest common ancestor module in the dependency graph. If no natural home exists, create a shared helpers file within the relevant package. Avoid top-level grab-bag utility files.
- **Update tests** — after moving code, update test imports accordingly. If duplicate functions had separate tests, consolidate the test cases (keep all unique assertions, remove exact duplicates).

## Constraints

- **DO NOT** change public API signatures
- **DO NOT** remove code marked with `# KEEP`, `# REQUIRED`, `// KEEP`, `// REQUIRED`
- **DO NOT** simplify test files
- **DO NOT** modify configuration files
- **PRESERVE** all existing functionality — simplification must be behavior-preserving

## Process

**Single file mode** (`/code-simplifier path/to/file.ext`):
1. Read the target file
2. Identify simplification opportunities (rules 1–4)
3. Apply changes incrementally
4. Run tests to verify no regressions
5. Report changes made

**Directory mode** (`/code-simplifier path/to/src/`):
1. Read all source files in the directory
2. **Cross-module dedup scan** (rule 5): identify functions, constants, and logic duplicated across files. Group duplicates by content similarity.
3. Consolidate duplicates into shared modules, update all import sites
4. Apply within-file simplifications (rules 1–4) to each file
5. Run the full test suite to verify no regressions
6. Report all changes made, grouped by category

## Output Format

**Single file:**
```
[filename]: N simplifications
  - Removed N unused imports
  - Flattened N nested conditionals
  - Extracted N helper functions
  - [other changes]
```

**Directory (with dedup):**
```
[CROSS-MODULE DEDUP]
  - Consolidated `helper_fn` from module_a + module_b → shared/common (2 files updated)
  - Moved SHARED_CONSTANT from module_a + module_b → core/constants (2 files updated)

[PER-FILE SIMPLIFICATIONS]
[filename]: N simplifications
  - ...

[filename]: already clean

[TESTS] All N tests passing
```
