---
status: complete
current_step: 4
prd_source: docs/PRD.md
prd_checksum: 94f1ee7b
product_category: CLI Tool
completed_at: 2026-02-20
---

# Architecture: AutoConvert

> Generated: 2026-02-20
> PRD: docs/PRD.md

<!--
=============================================================================
AI IMPLEMENTATION GUIDE

This document + PRD = complete implementation context.
- PRD defines WHAT (requirements with Input/Rules/Output/Error)
- Architecture defines HOW (stack, structure, patterns, specifications)

IMPLEMENTATION ORDER:
1. Install tech stack dependencies (use Build Commands)
2. Create directory structure (use src_dir/test_dir markers)
3. Set up database with schema
4. Implement modules following boundaries (use Path, Exports, Depends On)
5. Build contracts matching module assignments
6. Apply coding patterns consistently

RULES:
- Follow naming conventions exactly
- Use error codes from taxonomy
- Keep modules isolated per boundaries
- Follow logging pattern for all log output
- Respect side-effect ownership
=============================================================================
-->

---

## 1. Technology Stack

| Category | Choice | Version | Rationale |
|----------|--------|---------|-----------|
| Language | Python | 3.11+ | PRD decided — type hints, Decimal support, performance |
| Excel (xlsx) | openpyxl | 3.1.5 | PRD decided — read xlsx with data_only, merge handling |
| Excel (xls) | xlrd | 2.0.2 | PRD decided — legacy xls format support |
| YAML Parser | PyYAML | 6.0.3 | Standard Python YAML library, simple config loading |
| Data Models | pydantic | 2.12.5 | Typed data validation for entities (InvoiceItem, etc.) |
| Testing | pytest | 9.0.2 | Python standard, fixture support for test corpus |
| Linter/Formatter | ruff | 0.15.2 | Fast all-in-one linter + black-compatible formatter |
| Type Checker | pyright | 1.1.408 | Strict Python type checking |
| Packaging | PyInstaller | 6.19.0 | Mature single-file Windows exe builder (<30 MB) |
| Project Manager | uv | latest | Fast dependency resolution, venv management |

### Build Commands

| Command | Value |
|---------|-------|
| Install | `uv sync` |
| Test | `uv run pytest tests/ --tb=short` |
| Lint | `uv run ruff check src/` |
| Type Check | `uv run pyright src/` |
| Format | `uv run ruff format src/` |
| Build | `uv run pyinstaller autoconvert.spec --clean --onefile --strip` |

### Dependency Pinning Strategy

- **Decided deps (exact pin):** `openpyxl==3.1.5`, `xlrd==2.0.2`, `PyYAML==6.0.3`
- **Runtime deps (compatible range):** `pydantic>=2.12,<3`
- **Dev deps (minimum version):** `pytest>=9`, `ruff>=0.15`, `pyright>=1.1`, `pyinstaller>=6.19`

### PyInstaller Configuration

**Spec file (`autoconvert.spec`) must exclude unused stdlib modules to stay under 30 MB:**

```python
excludes = [
    'tkinter', 'unittest', 'email', 'html', 'http',
    'xml.etree', 'pydoc', 'doctest', 'asyncio',
    'multiprocessing', 'concurrent', 'xmlrpc',
]
```

**Early validation:** Run an exe size spike build before full implementation to confirm the dependency bundle (Python runtime + openpyxl + xlrd + PyYAML + pydantic-core) fits within the 30 MB budget.

---

## 2. Project Structure

<!-- src_dir: src/autoconvert/ -->
<!-- test_dir: tests/ -->

```
autoconvert/
├── src/
│   └── autoconvert/
│       ├── __init__.py              # Package init, version
│       ├── __main__.py              # Entry point: python -m autoconvert
│       ├── cli.py                   # CLI argument parsing (argparse)
│       ├── config.py                # Config loading & validation (FR-002)
│       ├── models.py                # Pydantic data models (all entities)
│       ├── errors.py                # Error/warning code definitions
│       ├── batch.py                 # Batch orchestrator (FR-001, FR-003, FR-028, FR-033)
│       ├── sheet_detect.py          # Sheet detection (FR-004, FR-005, FR-006)
│       ├── column_map.py            # Header detection + column mapping + inv_no fallback (FR-007, FR-008, FR-009)
│       ├── merge_tracker.py         # Merged cell tracking & propagation (FR-010)
│       ├── extract_invoice.py       # Invoice data extraction (FR-011)
│       ├── extract_packing.py       # Packing data extraction (FR-012, FR-013, FR-014, FR-015, FR-016, FR-017)
│       ├── transform.py             # Data transformation (FR-018, FR-019, FR-020)
│       ├── weight_alloc.py          # Weight allocation pipeline (FR-021 through FR-026)
│       ├── validate.py              # Status determination (FR-027)
│       ├── output.py                # Template population & file output (FR-029, FR-030)
│       ├── logger.py                # Logging setup & console reporting (FR-031, FR-032)
│       └── report.py                # Batch summary report (FR-033)
├── tests/
│   ├── fixtures/                    # 41-file vendor test corpus
│   │   └── expected/                # Golden output files for NFR-REL-001 validation
│   ├── conftest.py                  # Shared fixtures (AppConfig, workbook factory, tmp_path output dir)
│   ├── test_models.py
│   ├── test_errors.py
│   ├── test_config.py
│   ├── test_sheet_detect.py
│   ├── test_column_map.py
│   ├── test_merge_tracker.py
│   ├── test_extract_invoice.py
│   ├── test_extract_packing.py
│   ├── test_transform.py
│   ├── test_weight_alloc.py
│   ├── test_validate.py
│   ├── test_output.py
│   ├── test_report.py
│   ├── test_batch.py
│   └── test_diagnostic.py
├── config/                          # IT Admin managed (not bundled in exe)
│   ├── field_patterns.yaml          # Sheet/column regex patterns
│   ├── output_template.xlsx         # 40-column output template
│   ├── currency_rules.xlsx          # Currency code lookup
│   └── country_rules.xlsx           # Country code lookup
├── data/                            # Auto-created at runtime (FR-001)
│   └── finished/                    # Output directory (FR-028)
├── pyproject.toml                   # Project config (deps, ruff, pyright)
├── autoconvert.spec                 # PyInstaller build spec
└── README.md
```

---

## 3. Coding Patterns

### Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Source files | snake_case | `weight_alloc.py`, `extract_invoice.py` |
| Test files | test_ prefix + snake_case | `test_weight_alloc.py` |
| Functions | snake_case | `detect_header_row()`, `allocate_weights()` |
| Classes/Models | PascalCase | `InvoiceItem`, `PackingTotals` |
| Constants | UPPER_SNAKE | `MAX_SCAN_ROW`, `HEADER_KEYWORDS` |
| Config keys | snake_case | `invoice_sheet`, `part_no` |
| Error codes | ERR_NNN / ATT_NNN | `ERR_020`, `ATT_003` (from PRD catalog) |

### CLI Response Format

```
Exit codes:
  0  — All files processed successfully (Success or Attention status)
  1  — One or more files failed (any ERR_xxx occurred)
  2  — Fatal startup error (missing config, permissions, bad arguments)

Stdout: Real-time processing logs + batch summary (per PRD FR-031, FR-033)
Stderr: Reserved for unhandled exceptions only
```

### Error Code Taxonomy

Error codes are defined in PRD Section 7. Architecture maps them to processing phases:

| Range | Phase | Codes | Short-circuits |
|-------|-------|-------|----------------|
| ERR_001–005 | Config Loading | CONFIG_NOT_FOUND, INVALID_REGEX, DUPLICATE_LOOKUP, MALFORMED_CONFIG, TEMPLATE_INVALID | Fatal — exit code 2 |
| ERR_010–014 | Sheet Detection | FILE_LOCKED, FILE_CORRUPTED, INVOICE_SHEET_NOT_FOUND, PACKING_SHEET_NOT_FOUND, HEADER_ROW_NOT_FOUND | Skip to Validation |
| ERR_020–021 | Column Mapping | REQUIRED_COLUMN_MISSING, INVOICE_NUMBER_NOT_FOUND | Collect all within phase, skip to Validation |
| ERR_030–034 | Data Extraction | EMPTY_REQUIRED_FIELD, INVALID_NUMERIC, TOTAL_ROW_NOT_FOUND, INVALID_TOTAL_NW, INVALID_TOTAL_GW | Skip to Validation |
| ERR_040–048 | Weight Allocation | PART_NOT_IN_PACKING, WEIGHT_ALLOCATION_MISMATCH, PACKING_PART_ZERO_NW, etc. | Skip to Validation |
| ERR_051–052 | Output Generation | TEMPLATE_LOAD_FAILED, OUTPUT_WRITE_FAILED | File marked Failed |
| ATT_002–004 | Warnings | MISSING_TOTAL_PACKETS, UNSTANDARDIZED_CURRENCY, UNSTANDARDIZED_COO | File marked Attention (output still generated) |

### Logging Pattern

**Two outputs, configured in `logger.py`:**

| Target | Format | Levels | Purpose |
|--------|--------|--------|---------|
| Console (stdout) | `[{LEVEL}] {message}` | INFO, WARNING, ERROR | Real-time user feedback (FR-031) |
| File (`process_log.txt`) | `[{HH:MM}] [{LEVEL}] {message}` | DEBUG, INFO, WARNING, ERROR | Full audit trail (FR-032) |

**What gets logged:**

| Level | What | Example |
|-------|------|---------|
| ERROR | All ERR_xxx codes with context | `[ERROR] [ERR_020] REQUIRED_COLUMN_MISSING: 'qty' not found in Invoice sheet` |
| WARNING | All ATT_xxx codes with context | `[WARNING] [ATT_003] UNSTANDARDIZED_CURRENCY: 'RMB' not in lookup table` |
| INFO | Processing milestones, status | `[INFO] [1/20] Processing: vendor_file.xlsx ...` |
| DEBUG | Regex matches, cell values, calculations | `[DEBUG] Header row: 9 (score: 8 non-empty cells)` |

**Diagnostic mode** (`--diagnostic`): Console level set to DEBUG for single-file verbose output (FR-034).

### Error Propagation Convention

Two patterns used consistently across the codebase:

| Pattern | When | Mechanism | Example |
|---------|------|-----------|---------|
| **Raise immediate** | Single fatal error that stops the current phase | `raise ProcessingError(ERR_012, ...)` | Sheet not found, total row missing, weight mismatch |
| **Collect-then-report** | Phase where all problems should be reported at once | Return result object with `.errors: list[ProcessingError]` | Column mapping (report all missing columns), extraction validation |

**Convention:** batch.py wraps every module call in `try/except ProcessingError` AND inspects result objects for `.errors` lists. This ensures both patterns are handled uniformly at the orchestrator level.

### Side-Effect Ownership

| Side Effect | Owner Module | Non-owners Must |
|-------------|-------------|-----------------|
| Excel file reads | `batch.py` | Receive workbook object from batch orchestrator |
| Output file writes | `output.py` | Call `output.write_template()` |
| Directory creation | `batch.py` | Call through batch setup (FR-001, FR-028) |
| Console logging | `logger.py` | Use `logging.getLogger(__name__)` with shared config |
| File logging | `logger.py` | Use `logging.getLogger(__name__)` with shared config |
| Config file reads | `config.py` | Call `config.load_config()` |

---

## 4. Module Boundaries

| Module | Path | Test Path | Responsibility | Implements | Exports | Depends On |
|--------|------|-----------|----------------|------------|---------|------------|
| models | `src/autoconvert/models.py` | `tests/test_models.py` | Pydantic data models for all entities | — | `InvoiceItem`, `PackingItem`, `PackingTotals`, `ColumnMapping`, `FileResult`, `BatchResult`, `AppConfig`, `FieldPattern` | — |
| errors | `src/autoconvert/errors.py` | `tests/test_errors.py` | Error/warning code definitions and exception classes | — | `ErrorCode`, `WarningCode`, `ProcessingError`, `ConfigError` | — |
| logger | `src/autoconvert/logger.py` | — | Logging setup for console + file output | FR-031, FR-032 | `setup_logging()`, `setup_diagnostic_logging()` | — |
| config | `src/autoconvert/config.py` | `tests/test_config.py` | Load and validate all configuration files | FR-002 | `load_config()` | models, errors |
| merge_tracker | `src/autoconvert/merge_tracker.py` | `tests/test_merge_tracker.py` | Track merged cell ranges, unmerge sheets, propagate values | FR-010 | `MergeTracker` | models |
| sheet_detect | `src/autoconvert/sheet_detect.py` | `tests/test_sheet_detect.py` | Identify Invoice and Packing sheets by keyword matching | FR-004, FR-005, FR-006 | `detect_sheets()` | models, errors, config |
| column_map | `src/autoconvert/column_map.py` | `tests/test_column_map.py` | Detect header row, map columns via regex, extract inv_no from header area | FR-007, FR-008, FR-009 | `detect_header_row()`, `map_columns()`, `extract_inv_no_from_header()` | models, errors, config |
| extract_invoice | `src/autoconvert/extract_invoice.py` | `tests/test_extract_invoice.py` | Extract per-item fields from Invoice sheet | FR-011 | `extract_invoice_items()` | models, errors, merge_tracker |
| extract_packing | `src/autoconvert/extract_packing.py` | `tests/test_extract_packing.py` | Extract packing items, detect total row, extract totals (NW, GW, packets). **Split note:** if >400 lines, extract FR-014–017 into `extract_totals.py` — public exports are already separated. Keep `_extract_total_packets()` as private function to isolate FR-017 complexity. | FR-012, FR-013, FR-014, FR-015, FR-016, FR-017 | `extract_packing_items()`, `validate_merged_weights()`, `detect_total_row()`, `extract_totals()` | models, errors, merge_tracker |
| transform | `src/autoconvert/transform.py` | `tests/test_transform.py` | Currency/country code conversion, PO number cleaning | FR-018, FR-019, FR-020 | `convert_currency()`, `convert_country()`, `clean_po_number()` | models, errors, config |
| weight_alloc | `src/autoconvert/weight_alloc.py` | `tests/test_weight_alloc.py` | Full weight allocation pipeline: aggregate, validate, determine precision, round, allocate proportionally | FR-021, FR-022, FR-023, FR-024, FR-025, FR-026 | `allocate_weights()` | models, errors |
| validate | `src/autoconvert/validate.py` | `tests/test_validate.py` | Determine final file status from accumulated errors/warnings | FR-027 | `determine_file_status()` | models, errors |
| output | `src/autoconvert/output.py` | `tests/test_output.py` | Populate 40-column output template and write to finished directory | FR-029, FR-030 | `write_template()` | models, errors, config |
| report | `src/autoconvert/report.py` | `tests/test_report.py` | Format and print batch summary report | FR-033 | `print_batch_summary()` | models |
| batch | `src/autoconvert/batch.py` | `tests/test_batch.py` | Orchestrate batch processing: folder setup, file scanning, per-file pipeline, status collection | FR-001, FR-003, FR-028 | `run_batch()`, `process_file()` | models, errors, config, sheet_detect, column_map, merge_tracker, extract_invoice, extract_packing, transform, weight_alloc, validate, output, logger, report |
| cli | `src/autoconvert/cli.py`, `src/autoconvert/__main__.py` | `tests/test_diagnostic.py` | CLI argument parsing, entry point. `__main__.py` is trivial: `from autoconvert.cli import main; main()` — enables `python -m autoconvert` and PyInstaller entry point. | FR-034 | `main()`, `parse_args()` | batch, config, logger |

### Import Graph

```
cli → batch (run_batch)
cli → config (load_config)
cli → logger (setup_logging, setup_diagnostic_logging)

batch → config (AppConfig)
batch → models (FileResult, BatchResult)
batch → errors (ProcessingError)
batch → sheet_detect (detect_sheets)
batch → column_map (detect_header_row, map_columns, extract_inv_no_from_header)
batch → merge_tracker (MergeTracker)
batch → extract_invoice (extract_invoice_items)
batch → extract_packing (extract_packing_items, validate_merged_weights, detect_total_row, extract_totals)
batch → transform (convert_currency, convert_country, clean_po_number)
batch → weight_alloc (allocate_weights)
batch → validate (determine_file_status)
batch → output (write_template)
batch → report (print_batch_summary)

config → models (AppConfig, FieldPattern)
config → errors (ConfigError)

sheet_detect → config (AppConfig)
sheet_detect → models (SheetPair)
sheet_detect → errors (ProcessingError)

column_map → config (AppConfig)
column_map → models (ColumnMapping)
column_map → errors (ProcessingError)

merge_tracker → models (MergeRange)

extract_invoice → models (InvoiceItem)
extract_invoice → errors (ProcessingError)
extract_invoice → merge_tracker (MergeTracker)

extract_packing → models (PackingItem, PackingTotals)
extract_packing → errors (ProcessingError)
extract_packing → merge_tracker (MergeTracker)

transform → config (AppConfig)
transform → models (InvoiceItem)
transform → errors (ProcessingError)

weight_alloc → models (InvoiceItem, PackingItem, PackingTotals)
weight_alloc → errors (ProcessingError)

validate → models (FileResult)
validate → errors (ErrorCode, WarningCode)

output → config (AppConfig)
output → models (InvoiceItem, PackingTotals)
output → errors (ProcessingError)

report → models (BatchResult)
```

**Graph verification:** Acyclic. Leaf modules: `models`, `errors`, `logger`. Orchestrator: `batch`. Entry point: `cli`.

**Module Rules:**
- Each module owns its FRs completely
- Cross-module calls go through exported interfaces only
- Side effects respect ownership table (Section 3)
- `batch.py` is the only module that orchestrates the per-file pipeline sequence

---

## 5. Contracts

### CLI Commands

#### autoconvert

- **FR:** FR-001, FR-002, FR-003, FR-004–FR-030, FR-031, FR-032, FR-033
- **Module:** cli → batch
- **Args:** (none required)
- **Flags:** (none for batch mode)
- **Stdin:** N/A
- **Stdout:** Real-time per-file processing logs (FR-031) + batch summary report (FR-033). Format defined in PRD Section 7.
- **Stderr:** Unhandled exceptions only
- **Exit Codes:** `0: all files Success or Attention`, `1: one or more files Failed`, `2: fatal startup error (config missing, permissions)`

#### autoconvert --diagnostic \<filename\>

- **FR:** FR-034
- **Module:** cli → batch
- **Args:** `<filename>` — single Excel file to process (required)
- **Flags:** `--diagnostic` — enable verbose DEBUG-level output to console
- **Stdin:** N/A
- **Stdout:** Step-by-step diagnostic output: sheet detection matches, header row scores, column mapping regex matches, extraction details, transformation details, weight allocation steps, validation results
- **Stderr:** Unhandled exceptions only
- **Exit Codes:** `0: file Success or Attention`, `1: file Failed`, `2: fatal startup error`

### Inter-Module Data Flow Contracts

#### cli → config: Configuration Loading

- **Provider function:** `load_config() → AppConfig`
- **Data flow:** Reads `config/field_patterns.yaml` + 3 Excel config files → returns `AppConfig` with compiled regex patterns, lookup tables, template reference
- **Error propagation:** `ConfigError` with ERR_001–ERR_005 → cli catches and exits with code 2

#### cli → logger: Logging Setup

- **Provider function:** `setup_logging()` / `setup_diagnostic_logging()`
- **Data flow:** Configures Python `logging` module with dual handlers (console + file). Diagnostic mode sets console to DEBUG.
- **Error propagation:** N/A (best-effort, non-blocking)

#### batch → sheet_detect: Sheet Identification

- **Provider function:** `detect_sheets(workbook, config) → SheetPair`
- **Data flow:** Workbook sheet names + config patterns → identified Invoice + Packing sheet references
- **Error propagation:** `ProcessingError` with ERR_012/ERR_013 → batch records error, short-circuits to validation

#### batch → column_map: Column Mapping

- **Provider function:** `detect_header_row(sheet, sheet_type, config) → int`
- **Provider function:** `map_columns(sheet, header_row, sheet_type, config) → ColumnMapping`
- **Provider function:** `extract_inv_no_from_header(sheet, config) → str | None`
- **Data flow:** Sheet data + config patterns → header row number → column index mapping; inv_no fallback from header area
- **Error propagation:** `ProcessingError` with ERR_014/ERR_020/ERR_021 → batch records errors, short-circuits

#### batch → merge_tracker: Merge Cell Processing

- **Provider function:** `MergeTracker(sheet)` — captures merges, unmerges sheet, provides lookup
- **Data flow:** Sheet with merged cells → unmerged sheet + merge metadata for extraction modules
- **Error propagation:** N/A (preprocessing, no business errors)

#### batch → column_map → extract_invoice: Invoice Number Resolution

- **Orchestration (batch.py owns this logic):**
  1. Check `ColumnMapping` for `inv_no` column (from FR-008 column mapping)
  2. If no inv_no column → call `extract_inv_no_from_header(sheet, config)` (FR-009 fallback)
  3. Pass resolved `inv_no` value to `extract_invoice_items()`
- **Data flow:** Column mapping result + optional header scan → resolved inv_no string

#### batch → extract_invoice: Invoice Extraction

- **Provider function:** `extract_invoice_items(sheet, column_map, merge_tracker, inv_no) → list[InvoiceItem]`
- **Data flow:** Unmerged Invoice sheet + column mapping + resolved inv_no → list of structured invoice item records
- **Error propagation:** `ProcessingError` with ERR_030/ERR_031 → batch records errors

#### batch → extract_packing: Packing Extraction + Totals

- **Provider function:** `extract_packing_items(sheet, column_map, merge_tracker) → tuple[list[PackingItem], int]`
- **Provider function:** `validate_merged_weights(packing_items, merge_tracker) → None`
- **Provider function:** `detect_total_row(sheet, last_data_row, column_map, merge_tracker) → int`
- **Provider function:** `extract_totals(sheet, total_row, column_map) → PackingTotals`
- **Data flow:** Unmerged Packing sheet → packing items + last_data_row → validated merges → total row → NW/GW/packets
- **Error propagation:** `ProcessingError` with ERR_030–034/ERR_046/ATT_002 → batch records errors/warnings

#### batch → transform: Data Transformation

- **Provider function:** `convert_currency(items, config) → list[InvoiceItem]`
- **Provider function:** `convert_country(items, config) → list[InvoiceItem]`
- **Provider function:** `clean_po_number(items) → list[InvoiceItem]`
- **Data flow:** Invoice items + lookup tables → items with standardized currency codes, country codes, cleaned PO numbers
- **Error propagation:** ATT_003/ATT_004 warnings recorded (non-blocking, values preserved as-is)

#### batch → weight_alloc: Weight Allocation

- **Provider function:** `allocate_weights(invoice_items, packing_items, packing_totals) → list[InvoiceItem]`
- **Data flow:** Invoice items + packing items + totals → invoice items with `allocated_weight` field populated
- **Error propagation:** `ProcessingError` with ERR_040–048 → batch records errors

#### batch → validate: Status Determination

- **Provider function:** `determine_file_status(errors, warnings) → FileResult`
- **Data flow:** Accumulated error/warning lists → final status (Success/Attention/Failed)
- **Error propagation:** N/A (this module resolves errors into status)

#### batch → output: Output Generation

- **Provider function:** `write_template(invoice_items, packing_totals, config, output_path) → None`
- **Data flow:** Validated invoice items + totals + template → populated 40-column output file
- **Path construction (batch.py owns this):** `output_path = data/finished/{input_filename}_template.xlsx` — batch.py constructs the full path and passes it to output.py. output.py never constructs paths.
- **Error propagation:** `ProcessingError` with ERR_051/ERR_052 → batch records error

#### batch → report: Batch Summary

- **Provider function:** `print_batch_summary(batch_result) → None`
- **Data flow:** BatchResult with all file statuses → formatted console summary
- **Error propagation:** N/A (reporting is non-blocking)

---

## 6. Database Schema

N/A — CLI tool with in-memory processing only. All 7 data entities (InvoiceItem, PackingItem, PackingTotals, ColumnMapping, MergeTracker, FileResult, BatchResult) are pydantic models held in memory during batch execution. No persistent storage.

---

## 7. Environment Variables

N/A — No environment variables required. All configuration is file-based:

| Config File | Path | Purpose |
|-------------|------|---------|
| `field_patterns.yaml` | `config/` | Sheet/column regex patterns (FR-002) |
| `output_template.xlsx` | `config/` | 40-column output template (FR-029) |
| `currency_rules.xlsx` | `config/` | Currency code lookup table (FR-018) |
| `country_rules.xlsx` | `config/` | Country code lookup table (FR-019) |

---

## 8. Testing Strategy

### Three-Tier Test Structure

| Tier | Type | Scope | Count (est.) | Speed | When |
|------|------|-------|-------------|-------|------|
| 1 | **Unit** | Pure logic: Decimal rounding, stop conditions, regex matching, PO cleaning, weight allocation math | ~80-100 | Fast (<10s) | Every commit |
| 2 | **Component** | Single module + real Excel fixtures: sheet detection, column mapping, extraction against known sheets | ~40-60 | Medium (<30s) | Every commit |
| 3 | **Integration** | Full pipeline: 41 corpus files end-to-end, compare output against golden files | 41 | Slow (~2-3 min) | Before release |

### Golden Output Files (NFR-REL-001)

`tests/fixtures/expected/` contains one golden output file per corpus file. Integration tests compare generated output cell-by-cell against golden files. **Without golden files, Zero False Positive cannot be validated.**

### Fixture Strategy

- **Unit tests:** Minimal in-memory workbooks (3-5 rows) created via openpyxl in `conftest.py` factory. Never use full corpus files for unit tests.
- **Component tests:** Small purpose-built `.xlsx` fixture files targeting specific module behaviors (unusual headers, merged cells, edge-case stop conditions).
- **Integration tests:** Full 41-file corpus from `tests/fixtures/`.

### conftest.py Shared Fixtures

- `app_config` — loaded `AppConfig` from test config files
- `make_workbook()` — factory function to create minimal in-memory workbooks with specified sheets, headers, and data rows
- `tmp_output_dir` — `tmp_path` based output directory for write tests

### High-Risk Test Areas

| Module | Risk | Minimum Test Cases |
|--------|------|-------------------|
| merge_tracker | Silent data corruption if wrong — all extraction depends on it | Horizontal merge, vertical merge spanning data rows, data-area vs header-area distinction, weight field first-row-only rule |
| weight_alloc | Decimal precision cascade with ROUND_HALF_UP and epsilon trick | 15+ cases: exact match at N, match at N+1, remainder adjustment, zero-check escalation, epsilon edge cases |
| column_map (FR-007) | Header row heuristics with magic-number thresholds | Corpus files with unusual header positions, metadata rows above header, low cell density |
| extract_packing | Stop condition ordering (check stop BEFORE blank) differs from invoice | Files with intermixed blank rows above total row, implicit total row detection |

---

## 9. Implementation Order

### Batch Sequence (Critical Path)

| Batch | Modules | Depends On | Parallelizable |
|-------|---------|------------|----------------|
| 0 | `models.py`, `errors.py`, `logger.py` | — | Yes (all leaf, zero deps) |
| 1 | `config.py`, `merge_tracker.py` | Batch 0 | Yes (independent) |
| 2 | `sheet_detect.py`, `column_map.py` | Batch 1 (config) | Yes (independent) |
| 3 | `extract_invoice.py`, `extract_packing.py` | Batch 1 (merge_tracker) | Yes (independent) |
| 4 | `transform.py`, `weight_alloc.py` | Batch 0 (models, errors) | Yes (independent) |
| 5 | `validate.py`, `output.py`, `report.py` | Batch 0 (models) | Yes (independent) |
| 6 | `batch.py` | Batches 1-5 (orchestrator) | No — must wait for all |
| 7 | `cli.py`, `__main__.py` | Batch 6 | No — entry point last |

**Batches 2-5 can run in parallel** — they all feed into batch.py but don't depend on each other.

**Bottleneck:** Batch 3 (extraction modules) — most complex business logic, most debugging time.

**Early spike:** Run a PyInstaller exe size build after Batch 0-1 to validate <30 MB budget before investing in full implementation.

---

## 10. Legacy Integration

N/A — Greenfield project. No legacy systems to integrate with.
