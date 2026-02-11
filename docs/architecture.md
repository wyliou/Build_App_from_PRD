---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
inputDocuments:
  - 'docs/prd.md'
workflowType: 'architecture'
lastStep: 8
status: 'complete'
completedAt: '2025-12-12'
lastUpdated: '2025-12-25'
architectureSyncedWithPRD: '2025-12-25'
project_name: 'AutoConvert'
user_name: 'Alex'
date: '2025-12-12'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**
66 functional requirements spanning file processing, pattern matching, data extraction, transformation, weight allocation, validation, and output generation. The system is a batch-mode CLI tool that:
- Monitors a data folder for vendor Excel files
- Uses configuration-driven regex patterns to identify sheets and map columns
- Extracts invoice and packing data with smart header detection
- Transforms data (currency/country codes, PO/invoice cleaning)
- Allocates weights proportionally with exact-match validation
- Generates standardized 40-column output templates
- Provides comprehensive logging and diagnostic capabilities

**Non-Functional Requirements:**
- **Performance:** <30s per file, 20+ file batches, <5s startup
- **Reliability:** 0% false positive rate, graceful failure handling
- **Compatibility:** Windows 10/11, .xls and .xlsx, Unicode paths
- **Maintainability:** IT admin can modify patterns via YAML
- **Distribution:** <30MB single-file executable, fully offline

**Scale & Complexity:**

- Primary domain: Desktop CLI / Data Processing
- Complexity level: Medium
- Estimated architectural components: 11 modules (see below)

### Technical Constraints & Dependencies

- **Runtime:** Python packaged via PyInstaller for Windows
- **Excel Libraries:** openpyxl (xlsx, read-only mode), xlrd (xls legacy conversion)
- **Configuration:** YAML for patterns, Excel for lookup tables
- **No External Dependencies:** Fully offline operation, no network calls
- **Read-Only Input:** Source files never modified or moved

### Cross-Cutting Concerns Identified

1. **Logging Architecture:** Dual-output (console real-time, file with timestamps), multiple verbosity levels (DEBUG/INFO/WARNING/ERROR), UTF-8 encoding with `errors='replace'` fallback for console

2. **Error Handling Strategy:** Standardized error codes (ERR_001-ERR_047, ERR_051-ERR_052, ATT_002-ATT_004), three-tier classification (SUCCESS/ATTENTION/FAILED), fail-fast on configuration errors, collect-all-errors validation pattern. **ATTENTION enhancement:** Embed row-level warnings as Excel comments in output file (e.g., cell comment on unstandardized currency showing original value)

3. **Configuration Management:** Startup validation (schema + regex compilation), lookup table loading with duplicate detection, compiled pattern registry

4. **Unicode Support:** Chinese file names, sheet names, column headers, field values throughout the pipeline

5. **Precision Handling:** Floating-point artifact prevention via cell display precision detection and controlled rounding

6. **Output Safety:** Atomic file writes (temp + rename) to prevent corrupted outputs

7. **Index Convention (0-based vs 1-based):** openpyxl uses 1-based row/column indices for cell access (`sheet.cell(row=1, column=1)`). Internal data structures (`ColumnMap`, `MergeTracker`) use **0-based indices** for consistency with Python conventions. **Conversion rule:** When reading from openpyxl, subtract 1 before storing; when writing to openpyxl, add 1 before cell access. Example:
   ```python
   # Reading: store as 0-based
   mapped_columns[field_name] = col - 1

   # Writing: convert to 1-based for openpyxl
   cell = sheet.cell(row=row, column=col_idx + 1)
   ```

### Architectural Boundaries (from ADR Analysis)

The PRD's functional requirements and error code catalog naturally cluster into 10 subsystems:

| Subsystem | Responsibility | Key FRs |
|-----------|---------------|---------|
| **Configuration** | Load & validate patterns, lookup tables | FR1, FR36 |
| **File Ingestion** | Discover files, check locks, convert xls | FR2, FR3 |
| **Sheet Detection** | Identify Invoice/Packing sheets | FR4, FR5, FR6 |
| **Column Mapping** | Header detection, regex matching, merged cells | FR7-FR14 |
| **Data Extraction - Invoice** | Invoice items, inv_no extraction | FR15-FR17 |
| **Data Extraction - Packing** | Packing items, totals detection | FR18-FR25 |
| **Transformation** | Clean & standardize values | FR26-FR28 |
| **Weight Allocation** | Proportional distribution algorithm | FR29-FR35 |
| **Validation** | Status classification, error collection | FR36-FR51 |
| **Output & Reporting** | Template generation, logging, summary | FR42-FR46, FR52-FR58, FR60-FR64 |
| **Diagnostic Mode** | Single-file troubleshooting | FR59 |
| **Integration** | Entry point, smoke testing | FR66 |

### Key Architectural Decisions (Preliminary)

1. **Sequential processing** - Process files one at a time with memory cleanup (sufficient for 20-file batches)
2. **Fail-fast configuration** - Validate all config at startup, halt on errors before processing any files
3. **Collect-all validation** - Gather all errors/warnings before status classification (better diagnostics)
4. **Atomic output writes** - Write to temp file, rename on success (supports Zero False Positive policy)
5. **Compiled pattern registry** - Single compilation point at startup, reuse throughout processing

## Starter Template Evaluation

### Primary Technology Domain

**CLI Tool / Desktop Data Processing** based on project requirements analysis.

This is a batch-mode Python CLI packaged as a standalone Windows executable via PyInstaller. Not a web application, API, or mobile app.

### Starter Options Considered

| Option | Description | Assessment |
|--------|-------------|------------|
| cookiecutter-pypackage | Full Python package with tests, docs, CI | Overkill—targets pip distribution, not exe |
| python-project-template | Basic src layout with pytest | Generic—doesn't match PRD folder structure |
| **No external starter** | Build from PRD specification directly | **Best fit**—PRD defines exact structure |

### Selected Approach: PRD-Driven Structure

**Rationale for Selection:**
1. PRD already specifies exact deployment structure (`AutoConvert.exe`, `config/`, `data/`, `data/finished/`, `process_log.txt`)
2. No pip/PyPI distribution needed—single exe via PyInstaller
3. 11 modules already mapped from requirements provide clear module boundaries
4. Domain-specific structure (Excel processing, pattern matching) doesn't fit generic templates
5. PRD's folder structure is the "contract" with end users—architecture must match it

**Project Structure (Derived from PRD + Subsystems):**

```
AutoConvert/
├── src/
│   └── autoconvert/
│       ├── __init__.py
│       ├── __main__.py          # Package entry point
│       ├── main.py              # Entry point, CLI handling
│       │
│       ├── core/                # Shared foundation (cross-cutting)
│       │   ├── __init__.py
│       │   ├── errors.py        # Standardized error codes (ERR_xxx, ATT_xxx)
│       │   └── models.py        # Shared dataclasses (InvoiceItem, PackingItem, etc.)
│       │
│       ├── setup/               # Configuration subsystem (named 'setup' to avoid confusion with runtime config/)
│       │   ├── __init__.py
│       │   ├── loader.py        # YAML/Excel config loading
│       │   ├── validator.py     # Schema & regex validation
│       │   ├── registry.py      # Compiled pattern registry
│       │   └── config.py        # Config dataclass and load_all_config()
│       │
│       ├── ingestion/           # File Ingestion subsystem
│       │   ├── __init__.py
│       │   ├── discovery.py     # File scanning, lock checking
│       │   ├── workbook.py      # Workbook loading abstraction
│       │   └── converter.py     # xls → xlsx conversion
│       │
│       ├── parsing/             # Sheet Detection + Column Mapping
│       │   ├── __init__.py
│       │   ├── sheet_detector.py    # Invoice/packing sheet detection
│       │   ├── header_finder.py     # Header row detection with pattern matching
│       │   ├── column_mapper.py     # Column mapping with regex patterns
│       │   └── merged_cells.py      # Merged cell tracking & validation (FR12-FR13)
│       │
│       ├── extraction/          # Data Extraction subsystem
│       │   ├── __init__.py
│       │   ├── invoice.py       # Invoice sheet extraction
│       │   ├── packing.py       # Packing sheet extraction
│       │   ├── total_detector.py    # Total row detection logic
│       │   └── total_extractor.py   # Total value extraction
│       │
│       ├── transformation/      # Transformation subsystem
│       │   ├── __init__.py
│       │   ├── transform.py     # Main transformation orchestration
│       │   ├── cleaners.py      # PO/invoice number cleaning
│       │   └── standardizers.py # Currency/country code lookup
│       │
│       ├── allocation/          # Weight Allocation subsystem
│       │   ├── __init__.py
│       │   ├── weight.py        # Proportional allocation algorithm
│       │   └── weight_aggregator.py    # Weight aggregation utilities (if split needed)
│       │
│       ├── validation/          # Validation subsystem
│       │   ├── __init__.py
│       │   ├── rules.py         # Validation rules
│       │   ├── classifier.py    # SUCCESS/ATTENTION/FAILED classification
│       │   └── error_aggregator.py    # Error/warning aggregation
│       │
│       ├── output/              # Output & Reporting subsystem
│       │   ├── __init__.py
│       │   ├── batch.py         # Batch processing orchestration
│       │   ├── file_processor.py    # Single file processing pipeline
│       │   ├── template.py      # 40-column template population
│       │   ├── writer.py        # Atomic file writing
│       │   └── reporter.py      # Batch summary generation
│       │
│       ├── diagnostic/          # Diagnostic Mode subsystem
│       │   ├── __init__.py
│       │   ├── runner.py        # Diagnostic mode entry point
│       │   ├── formatters.py    # Output formatting for diagnostics
│       │   └── analyzers.py     # Pattern/column analysis
│       │
│       └── logging/             # Cross-cutting logging
│           ├── __init__.py
│           ├── logger.py        # Dual console/file logging
│           └── messages.py      # Standardized log message templates
│
├── tests/
│   └── ...                      # pytest structure mirroring src/
├── config/                      # Runtime config (packaged with exe)
│   ├── field_patterns.yaml
│   ├── currency_rules.xlsx
│   ├── country_rules.xlsx
│   └── output_template.xlsx
├── pyproject.toml               # Project metadata, dependencies
├── uv.lock                      # Locked dependencies
└── build_exe.py                 # PyInstaller build script
```

**Module Size Guidelines:**
- Target: 200-400 lines per module (optimal)
- Maximum: 500 lines per module (hard limit)
- When a module exceeds 500 lines, split by responsibility

**Key Structural Decisions:**
| Decision | Rationale |
|----------|-----------|
| `core/` module | Centralizes shared errors and models |
| Split `totals.py` → `total_detector.py` + `total_extractor.py` | Separates detection logic from extraction |
| Split `processor.py` → `batch.py` + `file_processor.py` | Separates batch orchestration from single-file processing |
| Split `reports.py` → `formatters.py` + `analyzers.py` | Separates output formatting from analysis logic |

**Architectural Decisions Established:**

| Decision Area | Choice | Rationale |
|---------------|--------|-----------|
| **Language** | Python 3.11+ | PRD requirement, PyInstaller compatible |
| **Package Manager** | uv | Fast, modern, lockfile support, excellent Windows compatibility |
| **Project Layout** | src/ layout | Standard, prevents import issues |
| **Testing** | pytest | De facto Python standard |
| **Linting** | ruff | Fast, replaces flake8+isort+black |
| **Type Checking** | pyright or mypy | Catch errors before runtime |
| **Build Tool** | PyInstaller | PRD requirement for single exe |

**Note:** First implementation task should be scaffolding this structure with `uv init` and verifying basic imports.

## Core Architectural Decisions

### Decision Summary

| Category | Decision | Rationale |
|----------|----------|-----------|
| **Data Models** | Hybrid: Pydantic (config boundary) + Dataclasses (internal) | Validation at input, lightweight internal flow |
| **Error Handling** | Hybrid: Exceptions (config) + Accumulator (file processing) | Fail-fast startup, collect-all for batch |
| **Numeric Precision** | Float everywhere, controlled rounding in code | PRD's WYSIWYG principle, detect cell display precision |
| **Logging** | Standard Python logging module | Zero dependencies, dual-handler setup sufficient |
| **CLI Parsing** | argparse (stdlib) | Minimal CLI needs, no extra dependencies |

### Data Architecture

**Data Models Strategy:**
- **Pydantic models** at configuration boundary for validation (field_patterns.yaml, lookup tables)
- **Dataclasses** for internal data structures (InvoiceItem, PackingItem, PackingTotals, ProcessingResult)
- Pydantic validates untrusted external input; dataclasses carry validated internal state

**Numeric Handling:**
- Use Python `float` throughout for simplicity and performance
- Apply controlled rounding based on cell display precision (WYSIWYG)
- Precision detection from Excel cell format, not arbitrary decimals

### Error Handling Strategy

**Two-Tier Approach:**

1. **Startup Phase (Config Loading):**
   - Use exceptions for fatal errors (ERR_001-005)
   - Fail fast, halt before processing any files
   - Clear error messages with resolution guidance

2. **File Processing Phase:**
   - Use error accumulator pattern (collect all errors/warnings per file)
   - Continue batch on individual file failures
   - Classify status (SUCCESS/ATTENTION/FAILED) after all validations complete

**ProcessingResult Structure:**
```python
@dataclass
class ProcessingResult:
    status: Literal["SUCCESS", "ATTENTION", "FAILED"]
    errors: list[str]      # ERR_xxx codes
    warnings: list[str]    # ATT_xxx codes
    output: OutputData | None
```

### Infrastructure Decisions

**Logging Implementation:**
- Standard Python `logging` module with two handlers
- Console: INFO level, `[LEVEL] message` format, UTF-8
- File: DEBUG level, `[HH:MM] [LEVEL] message` format, UTF-8 with BOM
- Log file: `process_log.txt` in project root (rewritable each run)

**CLI Implementation:**
- `argparse` for command-line parsing
- Default mode: batch process all files in `data/`
- `--diagnose <filename>`: single file diagnostic mode (FR59)
- Exit codes: 0=success, 1=failures, 2=config error (FR66)

### Dependencies Summary

**Runtime Dependencies:**
- openpyxl (xlsx read/write)
- xlrd (xls legacy read)
- pyyaml (config parsing)
- pydantic (config validation)

**Development Dependencies:**
- pytest (testing)
- ruff (linting)
- pyright (type checking)
- pyinstaller (exe building)

## Implementation Patterns & Consistency Rules

### Pattern Summary

| Category | Pattern | Enforced By |
|----------|---------|-------------|
| **Naming** | PEP 8 (snake_case functions, PascalCase classes) | ruff |
| **Error Codes** | StrEnum with range reservations | pyright |
| **Log Messages** | Helper functions in logging/messages.py | Type hints |
| **Tests** | Separate tests/ folder, mirrored structure | Convention |
| **Imports** | Absolute only, stdlib → third-party → local | ruff |
| **Type Hints** | All functions have explicit return types | pyright |
| **Dependencies** | Module DAG - no circular imports | Code review |

### Naming Conventions

**Follow PEP 8 strictly:**
- Functions/variables: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Files/modules: `snake_case.py`
- Dataclass fields: `snake_case`

### Error Code Structure

**Use StrEnum for type safety (Python 3.11+):**
```python
# errors.py
from enum import StrEnum

# Error Code Range Reservations:
# 001-009: Configuration/startup errors
# 010-019: File-level errors (lock, corrupt, missing sheets/headers)
# 020-029: Column mapping errors
# 030-039: Data extraction errors
# 040-049: Weight allocation errors
# 050-059: Output errors (template, write)
# 060-069: Reserved for future use

class ErrorCode(StrEnum):
    # Startup errors (001-009)
    CONFIG_NOT_FOUND = "ERR_001"
    INVALID_REGEX = "ERR_002"
    DUPLICATE_LOOKUP = "ERR_003"
    MALFORMED_CONFIG = "ERR_004"
    TEMPLATE_INVALID = "ERR_005"

    # File-level errors (010-019)
    FILE_LOCKED = "ERR_010"
    FILE_CORRUPTED = "ERR_011"
    INVOICE_SHEET_NOT_FOUND = "ERR_012"
    PACKING_SHEET_NOT_FOUND = "ERR_013"
    HEADER_ROW_NOT_FOUND = "ERR_014"

    # Column mapping errors (020-029)
    REQUIRED_COLUMN_MISSING = "ERR_020"
    INVOICE_NUMBER_NOT_FOUND = "ERR_021"

    # Data extraction errors (030-039)
    EMPTY_REQUIRED_FIELD = "ERR_030"
    INVALID_NUMERIC = "ERR_031"
    TOTAL_ROW_NOT_FOUND = "ERR_032"
    INVALID_TOTAL_NW = "ERR_033"
    INVALID_TOTAL_GW = "ERR_034"

    # Weight allocation errors (040-049)
    PART_NOT_IN_PACKING = "ERR_040"
    WEIGHT_ALLOCATION_MISMATCH = "ERR_041"
    PACKING_PART_ZERO_NW = "ERR_042"
    PACKING_PART_NOT_IN_INVOICE = "ERR_043"
    WEIGHT_ROUNDS_TO_ZERO = "ERR_044"
    ZERO_QUANTITY_FOR_PART = "ERR_045"
    DIFFERENT_PARTS_SHARE_MERGED_WEIGHT = "ERR_046"
    AGGREGATE_DISAGREE_TOTAL = "ERR_047"  # Pre-allocation: packing sum vs total_nw (threshold 0.1)
    
    # Output errors (050-069)
    TEMPLATE_LOAD_FAILED = "ERR_051"
    OUTPUT_WRITE_FAILED = "ERR_052"

class WarningCode(StrEnum):
    MISSING_TOTAL_PACKETS = "ATT_002"
    UNSTANDARDIZED_CURRENCY = "ATT_003"
    UNSTANDARDIZED_COO = "ATT_004"
```

### Type Hint Requirements

**All functions must have explicit return type annotations:**
```python
# Good
def extract_invoice_items(sheet: Worksheet, config: Config) -> list[InvoiceItem]:
    ...

def log_file_progress(n: int, total: int, filename: str) -> None:
    ...

# Bad - missing return type
def extract_invoice_items(sheet: Worksheet, config: Config):
    ...
```

### Module Dependency DAG

**Import direction must follow this graph (no reverse arrows):**

```
core → (nothing - foundation module, no dependencies)
    ↑
logging → core
    ↑
setup → core, logging
    ↑
ingestion → core, setup
    ↑
parsing → core, setup
    ↑
extraction → core, setup, parsing
    ↑
transformation → core, setup
    ↑
allocation → core, extraction
    ↑
validation → core, extraction, transformation, allocation
    ↑
output → core, validation, setup
    ↑
diagnostic → core, parsing, extraction, output
    ↑
main → all (including smoketest functionality per FR66)
```

**Visual Dependency Layers:**
```
Layer 0 (Foundation):  core
Layer 1 (Services):    logging, setup
Layer 2 (Input):       ingestion, parsing
Layer 3 (Processing):  extraction, transformation
Layer 4 (Logic):       allocation, validation
Layer 5 (Output):      output, diagnostic
Layer 6 (Entry):       main
```

**Rules:**
- `core/` is the foundation - all modules may import from it
- Each subsystem exposes public API via `__init__.py`
- Internal modules (`_helpers.py`) not imported cross-subsystem
- If you need to reverse an arrow, redesign the interface
- Higher layers may import from lower layers, never the reverse

### Log Message Patterns

**Helper functions enforce PRD-compliant format:**
```python
# logging/messages.py
def log_file_progress(n: int, total: int, filename: str) -> None:
    logger.info(f"[{n}/{total}] Processing: {filename} ...")

def log_extraction(component: str, count: int, start_row: int, end_row: int) -> None:
    logger.info(f"{component} extracted {count} items (rows {start_row}-{end_row})")

def log_packing_totals(row: int, nw: float, gw: float, packets: int | None) -> None:
    msg = f"Packing total row at row {row}, NW= {nw}, GW= {gw}, Packets= {packets}"
    logger.info(msg)

def log_success() -> None:
    logger.info("✅ SUCCESS")
```

### Test Organization

**Structure:**
```
tests/
├── conftest.py              # Shared fixtures
├── test_setup/
│   ├── test_loader.py
│   └── test_validator.py
├── test_parsing/
│   ├── test_sheet_detector.py
│   └── test_column_mapper.py
├── test_extraction/
├── test_transformation/
├── test_allocation/
├── test_validation/
├── test_output/
└── fixtures/                # Sample Excel files
```

**Conventions:**
- File naming: `test_{module}.py`
- Test function naming: `test_{behavior}_when_{condition}`
- Use pytest fixtures for shared setup

### Import Style

**Absolute imports only:**
```python
# Correct
from autoconvert.setup.registry import PatternRegistry
from autoconvert.core.errors import ErrorCode

# Wrong - no relative imports
from ..setup import registry
from .loader import load_yaml
```

**Order (enforced by ruff):**
1. Standard library
2. Third-party packages
3. Local imports

### Enforcement

**Automated:**
- ruff: Naming, import order, code style
- pyright: Type checking, return types, StrEnum usage

**Manual Review:**
- Module dependency direction
- Error code range compliance
- Log message helper usage

## Project Structure & Boundaries

See **Project Structure (Derived from PRD + Subsystems)** in the Starter Template Evaluation section above for the authoritative directory structure.

### Requirements to Structure Mapping

**FR Category → Module Mapping:**

| FR Range | Category | Primary Module | Files |
|----------|----------|---------------|-------|
| FR1, FR36 | Configuration | `setup/` | loader.py, validator.py, registry.py |
| FR2 | File Discovery | `ingestion/` | discovery.py |
| FR3 | File Access & XLS Conversion | `ingestion/` | discovery.py, workbook.py, converter.py |
| FR4-FR6 | Sheet Detection | `parsing/` | sheet_detector.py |
| FR7-FR11 | Header & Column Mapping | `parsing/` | header_finder.py, column_mapper.py |
| FR12-FR14 | Merged Cells & Validation | `parsing/` | merged_cells.py, column_validator.py, weight_validator.py |
| FR15-FR17 | Invoice Extraction | `extraction/` | invoice.py |
| FR18-FR25 | Packing Extraction | `extraction/` | packing.py, total_detector.py, total_extractor.py |
| FR26-FR28 | Transformation | `transformation/` | transform.py, cleaners.py, standardizers.py |
| FR29-FR35 | Weight Allocation (incl. pre-allocation validation) | `allocation/` | weight.py, weight_aggregator.py |
| FR36-FR41 | Validation & Errors | `validation/` | rules.py, classifier.py, error_aggregator.py |
| FR42-FR46 | Output Generation | `output/` | batch.py, file_processor.py, template.py, writer.py |
| FR47-FR51 | Status Classification | `validation/` | classifier.py |
| FR52-FR58 | Error Recovery & Summary | `main.py`, `output/` | reporter.py |
| FR59 | Diagnostic Mode | `diagnostic/` | runner.py, formatters.py, analyzers.py |
| FR60-FR65 | Logging | `logging/` | logger.py, messages.py |
| FR66 | Integration & Smoke Test | `main.py`, `__main__.py` | Entry point wiring |

### Architectural Boundaries

**Module Boundaries (Public APIs only):**

| Module | Public Functions | Internal Only |
|--------|-----------------|---------------|
| `setup` | `load_config() → Config` | Pydantic models, parsing logic |
| `ingestion` | `discover_files() → list[Path]`, `open_workbook() → Workbook` | Lock checking, xls internals |
| `parsing` | `detect_sheets() → SheetInfo`, `map_columns() → ColumnMap`, `create_merge_tracker() → MergeTracker` | Header heuristics, regex internals |
| `extraction` | `extract_invoice() → list[InvoiceItem]`, `extract_packing() → list[PackingItem]`, `extract_totals() → PackingTotals` | Row iteration, cell reading |
| `transformation` | `transform_items() → list[TransformedItem]` | Cleaning regex, lookup logic |
| `allocation` | `allocate_weights() → list[AllocatedItem]` | Precision algorithm |
| `validation` | `validate_file() → list[ErrorCode]`, `classify_status() → Status` | Rule implementations |
| `output` | `generate_output() → Path`, `write_summary() → None` | Template manipulation |
| `logging` | `setup_logging() → None`, message helpers | Handler configuration |

### Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            STARTUP PHASE                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│  setup/loader.py  →  setup/validator.py  →  setup/registry.py               │
│       ↓                      ↓                       ↓                       │
│  Load YAML/Excel      Pydantic validate      Compile regex patterns          │
│                                                      ↓                       │
│                                              Config object ready             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FILE PROCESSING LOOP                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│  FOR each file in data/:                                                     │
│                                                                              │
│  ingestion/discovery.py  →  ingestion/converter.py (if .xls)                │
│           ↓                                                                  │
│  parsing/sheet_detector.py  →  parsing/merged_cells.py (capture merges)     │
│           ↓                           ↓                                      │
│  parsing/merged_cells.py (unmerge)  ←┘                                      │
│           ↓                                                                  │
│  parsing/header_finder.py  →  parsing/column_mapper.py                      │
│           ↓                           ↓                                      │
│  (filter merges by NW/qty cols)  ←───┘                                      │
│           ↓                                                                  │
│  extraction/invoice.py  ────┬──── extraction/packing.py                     │
│           ↓                 │            ↓                                   │
│  list[InvoiceItem]          │     list[PackingItem] + PackingTotals         │
│           └────────────────┴────────────┘                                   │
│                             ↓                                                │
│  transformation/cleaners.py  →  transformation/standardizers.py             │
│                             ↓                                                │
│  allocation/weight.py:                                                       │
│    1. Aggregate packing weights by part_no                                   │
│    2. PRE-ALLOCATION VALIDATION: sum vs total_nw (ERR_047 if diff > 0.1)    │
│    3. If valid: round weights + proportional allocation                      │
│                             ↓                                                │
│  validation/rules.py  →  validation/classifier.py                           │
│           ↓                      ↓                                           │
│  list[ErrorCode]          Status (SUCCESS/ATTENTION/FAILED)                 │
│                             ↓                                                │
│  output/template.py  →  output/writer.py (atomic write)                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                           BATCH COMPLETION                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│  output/reporter.py  →  Batch summary to console + log file                 │
│  main.py  →  Exit code (0=all success, 1=some failed, 2=config error)       │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Development Workflow

**Commands:**
- `uv sync` - Install dependencies
- `uv run pytest` - Run tests
- `uv run ruff check src/` - Lint code
- `uv run pyright src/` - Type check
- `uv run python build_exe.py` - Build executable

**Build Output:**
- `dist/AutoConvert.exe` - Single file executable (~25MB)
- `dist/` is gitignored

## Architecture Validation Results

### Coherence Validation ✅

**Decision Compatibility:**
All technology choices work together without conflicts:
- Python 3.11+ provides StrEnum, dataclasses, modern typing
- uv/PyInstaller toolchain is well-tested for Windows executables
- openpyxl + xlrd cover all Excel format requirements
- Pydantic + dataclasses hybrid is a common, well-supported pattern
- stdlib logging + argparse have zero dependency conflicts

**Pattern Consistency:**
Implementation patterns fully support architectural decisions:
- StrEnum error codes enforce type safety per decision
- Module DAG prevents circular imports per dependency structure
- Helper functions ensure PRD-compliant log formats
- Absolute imports enforced by ruff configuration

**Structure Alignment:**
Project structure enables all chosen patterns:
- src/ layout with `__init__.py` public APIs supports module boundaries
- `core/` module centralizes models.py/errors.py for cross-module sharing without cycles
- tests/ mirrors src/ enabling clear test organization
- config/ folder matches PRD deployment requirements

### Requirements Coverage Validation ✅

**Functional Requirements Coverage:**
All 66 FRs mapped to specific modules:
- FR1-FR3: Configuration and file ingestion
- FR4-FR14: Sheet detection and column mapping
- FR15-FR17: Invoice extraction
- FR18-FR25: Packing extraction
- FR26-FR28: Data transformation
- FR29-FR35: Weight allocation
- FR36-FR51: Validation and status classification
- FR52-FR58: Error recovery and batch processing
- FR59: Diagnostic mode via CLI
- FR60-FR65: Logging subsystem
- FR66: Integration and smoke testing

**Non-Functional Requirements Coverage:**
- **Performance (<30s/file, 20+ batches):** Sequential processing with memory cleanup sufficient
- **Reliability (0% false positive):** Atomic writes (temp + rename) implemented
- **Compatibility (Win 10/11, xls/xlsx):** xlrd + openpyxl + PyInstaller covers all
- **Maintainability (IT admin patterns):** YAML config, Excel lookups as specified
- **Distribution (<30MB exe):** PyInstaller single-file target achievable

**Cross-Cutting Concerns Coverage:**
- ATTENTION row-level details: Embedded as Excel comments per enhancement
- Unicode support: UTF-8 throughout, BOM for log files
- Precision: Float with controlled rounding per cell display

### Implementation Readiness Validation ✅

**Decision Completeness:**
- All critical decisions documented with specific versions (Python 3.11+, specific libraries)
- Implementation patterns comprehensive with code examples
- Consistency rules clear: StrEnum, explicit returns, absolute imports
- Module dependency DAG provides unambiguous import direction

**Structure Completeness:**
- Complete directory tree with all 50+ files defined
- All integration points specified via public APIs
- Component boundaries enforced by module `__init__.py` exports
- FR-to-file mapping table provides traceability

**Pattern Completeness:**
- Error code ranges reserved to prevent collisions
- Naming conventions fully specified (PEP 8)
- Log message helpers prevent format drift
- Import order enforced by tooling (ruff)

### Gap Analysis Results

**Critical Gaps:** None identified
- All FRs have architectural support
- All NFRs have implementation strategies
- No contradictory decisions found

**Important Gaps:** None blocking
- Example test fixtures not pre-created (normal for greenfield)
- Specific regex patterns for field_patterns.yaml not in architecture (belongs in config, not architecture doc)

**Nice-to-Have Enhancements:**
- Could add pre-commit hooks configuration in future
- Could add GitHub Actions CI workflow template
- Could add example field_patterns.yaml with common vendor patterns

### Architecture Completeness Checklist

**✅ Requirements Analysis**
- [x] Project context thoroughly analyzed (66 FRs, 19 NFRs)
- [x] Scale and complexity assessed (Medium - 10 subsystems)
- [x] Technical constraints identified (offline, Windows, Unicode)
- [x] Cross-cutting concerns mapped (logging, errors, precision)

**✅ Architectural Decisions**
- [x] Critical decisions documented with versions
- [x] Technology stack fully specified (Python 3.11+, uv, PyInstaller)
- [x] Integration patterns defined (module DAG, public APIs)
- [x] Performance considerations addressed (sequential processing)

**✅ Implementation Patterns**
- [x] Naming conventions established (PEP 8)
- [x] Structure patterns defined (StrEnum, dataclasses)
- [x] Communication patterns specified (return types, module APIs)
- [x] Process patterns documented (error accumulator, atomic writes)

**✅ Project Structure**
- [x] Complete directory structure defined (50+ files)
- [x] Component boundaries established (11 modules with public APIs)
- [x] Integration points mapped (data flow diagram)
- [x] Requirements to structure mapping complete (FR table)

### Architecture Readiness Assessment

**Overall Status:** READY FOR IMPLEMENTATION

**Confidence Level:** High
- All 66 FRs traceable to code locations
- Zero critical gaps identified
- Patterns aligned with technology choices
- No contradictory decisions

**Key Strengths:**
- Clear module boundaries prevent AI agent conflicts
- StrEnum error codes provide compile-time safety
- Module DAG eliminates circular import risk
- FR-to-file mapping enables precise story creation
- Atomic writes support Zero False Positive requirement
- Merged cell handling properly isolated in dedicated module (FR12-FR13)

**Areas for Future Enhancement:**
- CI/CD pipeline (GitHub Actions) when needed
- Pre-commit hooks for team development
- Performance profiling after initial implementation
- Additional vendor pattern examples as discovered

### Implementation Handoff

**AI Agent Guidelines:**
- Follow all architectural decisions exactly as documented
- Use implementation patterns consistently across all components
- Respect project structure and module boundaries
- Respect module dependency DAG - no reverse imports
- Use StrEnum for all error/warning codes
- Add explicit return types to all functions
- Refer to this document for all architectural questions

**First Implementation Priority:**
1. Scaffold project structure with `uv init`
2. Create `pyproject.toml` with all dependencies
3. Implement `errors.py` with StrEnum codes
4. Implement `models.py` with core dataclasses
5. Implement `setup/` subsystem (foundation for all others)

## Architecture Completion Summary

### Workflow Completion

**Architecture Decision Workflow:** COMPLETED
**Total Steps Completed:** 8
**Date Completed:** 2025-12-12
**Document Location:** docs/architecture.md

### Final Architecture Deliverables

**Complete Architecture Document**
- All architectural decisions documented with specific versions
- Implementation patterns ensuring AI agent consistency
- Complete project structure with all files and directories
- Requirements to architecture mapping
- Validation confirming coherence and completeness

**Implementation Ready Foundation**
- 5 core architectural decisions made (data models, error handling, numeric precision, logging, CLI)
- 7 implementation patterns defined (naming, error codes, type hints, module DAG, log messages, tests, imports)
- 11 architectural modules specified
- 66 functional requirements fully supported

**AI Agent Implementation Guide**
- Technology stack with verified versions (Python 3.11+, uv, PyInstaller)
- Consistency rules that prevent implementation conflicts
- Project structure with clear boundaries
- Integration patterns and communication standards

### Development Sequence

1. Initialize project with `uv init`
2. Set up development environment per architecture
3. Implement core foundations (errors.py, models.py)
4. Build setup/ subsystem first (all others depend on it)
5. Implement subsystems following module DAG order
6. Maintain consistency with documented rules

### Quality Assurance Checklist

**Architecture Coherence**
- [x] All decisions work together without conflicts
- [x] Technology choices are compatible
- [x] Patterns support the architectural decisions
- [x] Structure aligns with all choices

**Requirements Coverage**
- [x] All 66 functional requirements are supported
- [x] All non-functional requirements are addressed
- [x] Cross-cutting concerns are handled
- [x] Integration points are defined

**Implementation Readiness**
- [x] Decisions are specific and actionable
- [x] Patterns prevent agent conflicts
- [x] Structure is complete and unambiguous
- [x] Examples are provided for clarity

---

**Architecture Status:** READY FOR IMPLEMENTATION

**Next Phase:** Begin implementation using the architectural decisions and patterns documented herein.

**Document Maintenance:** Update this architecture when major technical decisions are made during implementation.
