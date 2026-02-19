---
stepsCompleted: [init, discovery, journeys, requirements, specifications, complete]
outputPath: 'reference/PRD.md'
---

# Product Requirements Document - AutoConvert

**Author:** Alex Liou
**Date:** 2025-12-09

---

## 1. Overview

### Vision

AutoConvert automates the conversion of vendor Excel files into a standardized 40-column template for customs reporting. Logistics staff currently process ~600 files/month at ~10 minutes each (100+ hours of repetitive, error-prone work). AutoConvert uses a configuration-driven synonym engine with deterministic heuristic matching to identify sheets, map columns, allocate weights, and produce validated output — enforcing a "Zero False Positive" policy where only fully-validated files receive SUCCESS status.

### Classification

| Attribute | Value |
|-----------|-------|
| Project Type | Greenfield |
| Product Category | CLI Tool |
| Primary Context | Internal |

### Actors

| Actor Type | Primary Goal |
|------------|--------------|
| Logistics Staff | Process vendor Excel files in batch, review results, manually handle ATTENTION/FAILED files |
| IT Admin | Add regex patterns in `field_patterns.yaml` and lookup rules to support new vendor formats |

### Success Metrics

| Metric | Target | Primary |
|--------|--------|---------|
| Processing time per file | < 30 seconds | Yes |
| Automation rate (SUCCESS without manual intervention) | ≥ 60% | Yes |
| False positive rate (bad data marked SUCCESS) | 0% | Yes |
| Output template compliance | 100% | No |
| Monthly hours recovered | ~80+ hours | No |
| Batch throughput | 20+ files per run | No |

### MVP Scope

**In Scope:**
- Configuration loading and regex validation at startup
- File discovery, .xls/.xlsx reading (read-only, data_only mode)
- Invoice and packing sheet detection via configurable regex patterns
- Column mapping with multi-row header support and merged cell handling
- Invoice number extraction (label-first with recursive search)
- Invoice and packing data extraction with stop condition detection
- Packing total row detection (keyword + implicit pattern)
- Data transformation (PO number cleaning, invoice number cleaning, code standardization)
- Weight allocation algorithm (precision detection, proportional distribution, remainder adjustment)
- Validation with three-tier status classification (SUCCESS / ATTENTION / FAILED)
- 40-column output template generation
- Batch processing with console output and file logging
- Diagnostic mode (`--diagnose`) for pattern troubleshooting
- Standalone Windows executable packaging via PyInstaller

**Out of Scope:**
- Pattern learning from corrections (v1.1)
- Vendor profile management UI (v1.2)
- Web dashboard for managers (v2.0)

---

## 2. Journeys/Workflows

### Logistics Staff: Batch Processing

1. Staff places vendor Excel files into the `\data` input folder
2. Staff double-clicks `AutoConvert.exe` (or runs `uv run autoconvert`)
3. System processes all `.xls`/`.xlsx` files, displaying real-time per-file status to console
4. System writes output templates to `\data\finished` for SUCCESS and ATTENTION files
5. System displays batch summary (counts + timing), then lists FAILED and ATTENTION files with error details
6. Staff reviews ATTENTION files for manual corrections, investigates FAILED files

### Logistics Staff: Diagnostic Mode

1. Staff encounters a FAILED file with unclear column mapping errors
2. Staff runs `AutoConvert.exe --diagnose vendor_file.xlsx`
3. System displays sheet detection results, column mapping attempts (successes and failures), and total row detection
4. System suggests regex patterns for unmatched columns based on actual header text
5. Staff provides diagnostic output to IT Admin for pattern updates

### IT Admin: Pattern Configuration

1. Admin receives diagnostic output or FAILED file report from Logistics Staff
2. Admin edits `config/field_patterns.yaml` to add/modify regex patterns
3. Admin reruns processing to verify the new pattern resolves the issue
4. Changes take effect on next application restart (no recompilation required)

---

## 3. Functional Requirements

### Configuration & Startup

**FR-001**: System loads and validates configuration at startup
- **Input:** `config/field_patterns.yaml`, `config/currency_rules.xlsx`, `config/country_rules.xlsx`, `config/output_template.xlsx`
- **Rules:**
  - Validate YAML root keys: `invoice_sheet`, `packing_sheet`, `invoice_columns`, `packing_columns`, `inv_no_cell`
  - Compile all regex patterns; halt on invalid syntax
  - Validate rules files are readable, non-corrupted, and contain no duplicate codes
  - Validate output template has 40 columns (A-AN) and header rows 1-4
- **Output:** Compiled pattern registry, currency/country lookup tables, validated template
- **Error:** ERR_001 → config file not found; ERR_002 → invalid regex; ERR_003 → duplicate lookup code; ERR_004 → malformed Excel; ERR_005 → invalid template structure. All halt with exit code 2.

### File Discovery & Input

**FR-002**: System scans the `\data` folder for Excel files
- **Input:** `\data` folder path
- **Rules:** Accept `.xls` and `.xlsx` files. Convert `.xls` to openpyxl Workbook in-memory using xlrd (no temp file). Open `.xlsx` with `data_only=True` to read calculated formula values.
- **Output:** List of workbook objects ready for processing
- **Error:** ERR_010 → file locked (skip, log, continue batch); ERR_011 → file corrupted (skip, log, continue batch)

**FR-003**: System treats the `\data` folder as read-only
- **Rules:** Source files are never modified, moved, or deleted. Output goes to `\data\finished`.

### Sheet Detection

**FR-004**: System identifies invoice sheet by matching sheet names against `invoice_sheet.patterns`
- **Input:** Workbook sheet names (stripped of whitespace and invisible characters)
- **Rules:** Case-insensitive regex matching against configured patterns
- **Output:** Identified invoice sheet
- **Error:** ERR_012 → no sheet matches invoice patterns → FAILED

**FR-005**: System identifies packing sheet by matching sheet names against `packing_sheet.patterns`
- **Input:** Workbook sheet names (stripped of whitespace and invisible characters)
- **Rules:** Case-insensitive regex matching against configured patterns
- **Output:** Identified packing sheet
- **Error:** ERR_013 → no sheet matches packing patterns → FAILED

### Column Mapping

**FR-006**: System maps invoice columns using regex patterns from `invoice_columns.<column>.patterns`
- **Input:** Invoice sheet header row, pattern registry
- **Rules:**
  - Multiple patterns matching same column → first pattern wins
  - Same pattern matching multiple columns → leftmost column wins
  - Whitespace in headers is normalized (newlines, tabs, multiple spaces → single space)
  - Case-insensitive matching
  - Supports multilingual headers (English + Chinese)
- **Output:** Column index mapping for 14 fields (see §7.1 for column definitions)
- **Error:** ERR_020 → required column missing → FAILED; optional column missing → continue
- **Depends:** FR-001

| Invoice Column | Required | Notes |
|----------------|----------|-------|
| part_no | Yes | |
| po_no | Yes | |
| qty | Yes | |
| price | Yes | |
| amount | Yes | |
| currency | Yes | Fallback: data-row detection (FR-008) |
| coo | Yes | |
| COD | No | Overrides coo per-row when non-empty (FR-024) |
| brand | Yes | |
| brand_type | Yes | |
| model | Yes | |
| weight | No | Not extracted; calculated by weight allocation |
| inv_no | No | Optional in data rows; fallback to header extraction (FR-012) |
| serial | No | |

**FR-007**: System maps packing columns using regex patterns from `packing_columns.<column>.patterns`
- **Input:** Packing sheet header row, pattern registry
- **Rules:** Same matching rules as FR-006
- **Output:** Column index mapping for packing fields
- **Error:** ERR_020 → required column missing → FAILED

| Packing Column | Required |
|----------------|----------|
| part_no | Yes |
| qty | Yes |
| nw | Yes |
| gw | Yes |
| pack | No |

**FR-008**: System detects currency from data row when header matching fails
- **Input:** First effective data row (skipping blank rows), current column mapping
- **Rules:**
  - Currency column matching MUST NOT hard-fail during column mapping. If no header cell matches a currency pattern, column mapping returns successfully without currency, and this fallback scan runs before any "required column missing" check for currency.
  - Scan data row for currency values: USD, CNY, EUR, RMB, JPY, GBP, HKD, TWD
  - Skip columns already matched to other fields, EXCEPT columns matched to headers containing "PRICE", "AMOUNT", "金额", or "单价" keywords
  - Leftmost currency value found wins
  - When price or amount columns contain currency codes instead of numeric values (merged header pattern), shift **each** affected price/amount column independently to its adjacent column (col+1) if it has a numeric value. Both price AND amount may need shifting in the same file — do not stop after shifting one.
- **Output:** Currency column index; adjusted price/amount column indices if shifted
- **Error:** If currency still not found after fallback → ERR_020
- **Depends:** FR-006

**FR-009**: System supports multi-row headers for both invoice and packing sheets
- **Input:** Header row, sub-header row (header_row + 1)
- **Rules:**
  - If required fields not found in primary header row, check header_row + 1 for sub-headers
  - Even when the primary header row meets the minimum match threshold, also check header_row + 1: if combining adds ≥2 new field matches, treat it as a sub-header row. This handles split headers where structural columns (e.g., Part No., Qty) are in one row and detail columns (e.g., N.W., G.W.) are in the next.
  - Sub-header cells must contain descriptive text (e.g., "N.W.(KGS)"), NOT data values
  - Currency codes (USD, CNY, etc.) in header_row + 1 are data values, not sub-headers — reject these matches
  - Cells ending with a colon (`:` or `：`) are label-value pairs (e.g., "净重：", "毛重："), not column headers — exclude them from header matching. These commonly appear on summary lines above the actual header row.
  - When sub-header is detected, data extraction starts at header_row + 2
  - When header cells are merged across multiple rows (e.g., A10:A11), data extraction must start after the deepest merge bottom row, not just header_row + 1. The merge tracker determines the actual header extent.
- **Output:** Complete column mapping using primary + sub-header rows; adjusted data start row
- **Depends:** FR-006, FR-007

**FR-010**: System handles merged cells by unmerging and propagating values
- **Input:** Sheet with merged cells
- **Rules:**
  - Capture all merge ranges before unmerging
  - Unmerge all cells on the sheet
  - String fields: propagate values from merge origin to all cells in the range (vertical, horizontal, and block merges)
  - Numeric fields (qty, price, amount, nw, gw): do NOT propagate after unmerging
  - Header-row merges: values are NOT propagated to data rows (only data-row merges propagate)
  - See §7.6 for processing order and detailed merge handling
- **Output:** Sheet with unmerged cells and propagated string values
- **Error:** ERR_046 → different part_no values share same merged NW/qty cell

**FR-011**: System validates merged weight cells in packing sheet
- **Input:** Extracted packing items, merge range tracker
- **Rules:**
  - Same part_no sharing merged NW/qty → allowed (FR-017 handles aggregation)
  - Different part_no sharing merged NW/qty → ERR_046. Validated immediately after packing extraction, before weight allocation
- **Output:** Validation pass/fail
- **Error:** ERR_046 → `Different parts ({parts}) share merged NW/qty cell (rows {min}-{max})`
- **Depends:** FR-010

### Invoice Data Extraction

**FR-012**: System extracts invoice number from sheet header area
- **Input:** Invoice sheet rows 2-15, `inv_no_cell` patterns from config
- **Rules:**
  - **Method 1 (Label match):** Find cell matching `label_patterns`, then check adjacent cells (right, right+1, below, below+1)
  - Pure label detection: cell matches label_pattern AND has < 3 alphanumeric chars after removing keywords → recursive search (max 3 levels)
  - Extended search: when adjacent cell matches `exclude_patterns`, try cell to its right, then below
  - **Method 2 (Embedded value):** Extract from cell containing both label and value using `inv_no_cell.patterns`
  - Clean extracted value (remove "INV#" and "NO." prefixes)
  - See §7.5 for extraction algorithm details
- **Output:** Invoice number string; log format: `[INFO] Inv_No extracted ({method} of '{label}'): {inv_no} at '{cell_ref}'`
- **Error:** ERR_021 → invoice number not found in header area or data columns

**FR-013**: System supports combined invoices with multiple invoice numbers per sheet
- **Input:** Invoice data rows with optional inv_no column
- **Rules:**
  - Per-row inv_no from data column takes precedence over header-extracted inv_no
  - Header inv_no (FR-012) is fallback only for items with empty inv_no in data column
- **Output:** Each invoice item has correct inv_no from either source
- **Depends:** FR-012

**FR-014**: System extracts per-item fields from invoice sheet
- **Input:** Invoice sheet data rows starting after header (or header + 2 if sub-header detected)
- **Rules:**
  - Extract 13 fields: part_no, po_no, qty, price, amount, currency, coo, COD, brand, brand_type, model, inv_no, serial
  - String fields: strip leading/trailing whitespace
  - Numeric fields: WYSIWYG precision with ROUND_HALF_UP rounding. qty uses cell display precision; price uses fixed 5 decimals; amount uses cell display precision
  - Strip unit suffixes (KG, KGS, PCS, EA, 件, 个) from numeric values before parsing
  - Skip leading blank rows between header and first data row
  - Skip rows where part_no contains standalone header keywords ("part no")
  - Use merge-aware reading for string fields (read from merge origin cell)
  - See §7.9 for numeric precision rules
  - **Stop conditions:** (a) part_no empty AND qty = 0 after first data row; (b) part_no contains "total" (case-insensitive); (c) part_no contains footer keywords (报关行, 有限公司, etc.); (d) any cell in columns A-J contains "total", "合计", "总计", "小计"
- **Output:** List of invoice items with extracted field values; log: `Invoice sheet extracted {N} items (rows {start}-{end})`
- **Error:** ERR_030 → empty required field; ERR_031 → invalid numeric value
- **Depends:** FR-006, FR-009, FR-010

### Packing Data Extraction

**FR-015**: System extracts packing fields from packing sheet
- **Input:** Packing sheet data rows
- **Rules:**
  - Extract: part_no, qty, nw (and gw, pack if mapped)
  - Numeric qty: round to cell display precision
  - Numeric nw (line-level): round to 5 decimal precision for allocation calculations
  - Strip unit suffixes before parsing
  - Skip leading blank rows, empty part_no rows, no-weight-data rows (qty=0 and nw=0), pallet summary rows ("plt.", "pallet"), header continuation rows
  - Use merge-aware reading for part_no
  - **Stop conditions:** (a) any cell in columns A-J contains "total", "合计", "总计", "小计"; (b) truly blank row after first data row; (c) implicit total row pattern (empty part_no with numeric NW > 0 AND GW > 0, excluding merged cell continuation rows)
  - Row processing order: check stop conditions BEFORE checking if row is blank
- **Output:** List of packing items; determines `last_data_row` for total row search
- **Error:** ERR_030 → empty required field
- **Depends:** FR-007, FR-009, FR-010

**FR-016**: System prevents double-counting of shared weight cells
- **Input:** Packing rows with shared carton weight (three recognized patterns)
- **Rules:**
  - **Merged cells:** Merged NW cell value counted only on first row of merge range; subsequent rows return 0.0 for aggregation. Weight values are NOT propagated (per FR-010).
  - **Ditto marks:** Vendors use ditto marks (`"`, `〃`, `\u201c`, `\u201d`) in NW/GW columns to indicate "same carton as above." Ditto-mark cells are treated identically to merged cell continuation rows — return 0.0 for aggregation to prevent double-counting.
  - **Blank-cell carton groups:** Vendors pack multiple PO lines into one carton and record NW/GW only on the first row of the group; continuation rows have blank (None/empty) NW/GW cells. These rows are valid data items — accept them with NW=0.0 for aggregation. Do NOT reject as missing data.
- **Output:** Correct weight totals without duplication
- **Depends:** FR-010

**FR-017**: System detects total row using two strategies
- **Input:** Packing sheet, `last_data_row` from FR-015
- **Rules:**
  - **Strategy 1 (Keyword):** Search rows `last_data_row + 1` to `last_data_row + 15` in first 10 columns for case-insensitive "total", "合计", "总计", "小计"
  - **Strategy 2 (Implicit):** If Strategy 1 fails, search same range for rows where mapped part_no column is empty AND both nw and gw columns have numeric value > 0. Exclude rows where part_no column was part of a merged range.
- **Output:** Total row number
- **Error:** ERR_032 → total row not found
- **Depends:** FR-015

**FR-018**: System extracts total_nw from total row
- **Input:** Total row, nw column
- **Rules:**
  - Strip embedded unit suffixes (KG, KGS, G, LB, LBS) before parsing
  - Preserve cell's visible precision based on `number_format` property (e.g., `0.00` → 2 decimals)
  - When format is `General` with embedded unit, strip unit before counting decimals
  - When format is `General` or empty, round to 5 decimals first to clean floating-point artifacts, then normalize trailing zeros
  - See §7.9 for precision detection details
- **Output:** total_nw as Decimal with correct precision
- **Error:** ERR_033 → total_nw is 0, negative, or non-numeric
- **Depends:** FR-017

**FR-019**: System extracts total_gw from total row area
- **Input:** Total row, gw column, rows +1 and +2 below total row
- **Rules:**
  - Extract GW from total row
  - Check +1 and +2 rows in GW column: if both have numeric values, use +2 row as final total_gw (packaging weight addition pattern)
  - Same unit stripping and precision rules as FR-018
- **Output:** total_gw as Decimal with correct precision
- **Error:** ERR_034 → total_gw is 0, negative, or non-numeric
- **Depends:** FR-017

**FR-020**: System extracts total_packets using multi-priority search
- **Input:** Total row area, column search range (A through NW column + 2, minimum 11)
- **Rules:**
  - **Priority 1 (Packet label):** Search total row +1 to +3 for labels "件数"/"件數", extract adjacent value (right, up to 3 columns) or embedded value. Adjacent values with unit suffixes (e.g., "7CTNS") should extract leading digits.
  - **Priority 2 (PLT indicator):** Search total_row - 1 or - 2 for "PLT.G"/"PLT. G" pattern, extract leading number or check adjacent cell
  - **Priority 3 (Below-total patterns):** Search total row itself and +1 to +3 below for unit-suffix patterns ("7托", "30箱", "7CTNS"), embedded Chinese patterns ("共7托"), pallet range patterns ("PLT#1(1~34)"), total-with-breakdown patterns ("348（256胶框+92纸箱）" → 348)
  - Pallet count takes priority over carton count when both appear in same text
  - Recognized carton units: 箱 (Chinese), CTN/CTNS (English, case-insensitive)
  - Supported formats: pure numeric, with unit suffix, with suffix + trailing text, embedded in PLT indicator, embedded in Chinese text
  - Validation: must be positive integer in range 1-1000
- **Output:** total_packets integer
- **Error:** ATT_002 → total_packets not found or invalid (ATTENTION, not FAILED)
- **Depends:** FR-017

**FR-021**: System logs packing totals with visible precision
- **Rules:** Format: `[INFO] Packing total row at row {row}, NW= {nw}, GW= {gw}, Packets= {packets}`. Trailing zeros removed from NW/GW display.

| Packing Total Field | Required | If Missing |
|---------------------|----------|------------|
| total_nw | Yes | ERR_033 → FAILED |
| total_gw | Yes | ERR_034 → FAILED |
| total_packets | No | ATT_002 → ATTENTION |

### Data Transformation

**FR-022**: System cleans PO numbers by removing suffix from first "-" or "/" delimiter
- **Input:** Raw po_no string
- **Rules:** Remove everything from first `-` or `/` onward
- **Output:** Cleaned po_no (e.g., `2250600556-2.1` → `2250600556`, `PO12345/1` → `PO12345`)

**FR-023**: System cleans invoice numbers by removing "INV#" and "NO." prefixes
- **Rules:** Applied at extraction time for both header area (FR-012) and data row sources

**FR-024**: System standardizes currency and country codes using lookup tables
- **Input:** Raw currency/coo/COD values, `currency_rules.xlsx`, `country_rules.xlsx`
- **Rules:**
  - COD override: when COD column exists and row's COD is non-empty, use COD value as COO before standardization
  - Placeholder values treated as empty (not triggering ATT_004): any string consisting entirely of `*` characters (e.g., `*`, `**`, `****`), any string consisting entirely of `/` characters, any string consisting entirely of `-` characters, `N/A`, `NA`, `NONE`, `NULL`
  - Normalization: try original value (uppercase, trimmed), then try with all internal whitespace removed (e.g., `MADE IN CHINA` → `MADEINCHINA`)
- **Output:** Standardized numeric codes
- **Error:** Empty currency/coo → ERR_030 (FAILED); non-empty but not in lookup → ATT_003/ATT_004 (ATTENTION)

### Weight Allocation

**FR-025**: System aggregates packing weights by part_no
- **Input:** Extracted packing items
- **Rules:** Sum weights grouped by part_no. When same part_no shares merged weight, only first row of merge contributes.
- **Output:** Dictionary mapping part_no → total weight
- **Error:** ERR_042 → part has qty but packing weight = 0; ERR_045 → total quantity for part is zero

**FR-026**: System validates packing weight sum before allocation
- **Input:** Sum of extracted packing weights, total_nw
- **Rules:** If difference > 0.1, fail immediately before any rounding or adjustment
- **Error:** ERR_047 → `Packing weights sum ({sum}) disagrees with total_nw ({total_nw}), difference: {diff}`

**FR-027**: System detects decimal precision from total_nw
- **Input:** total_nw value (already rounded per FR-018)
- **Rules:** Analyze decimal places. Minimum 2, maximum 5 (for sum matching) or 6 (for zero check).
- **Output:** Base precision N
- **Error:** ERR_033 → total_nw not a valid number

**FR-028**: System rounds packing weights and adjusts to match total_nw exactly
- **Input:** Aggregated weights per part, base precision N
- **Rules:**
  - Try precision N → if rounded sum matches total_nw, use it
  - Try precision N+1 → if match, use it; else use N+1 with last-part adjustment
  - Do NOT try N+2 for sum matching
  - If any weight rounds to zero → increase precision (N+1, N+2, ... up to max 5); stop at first precision with no zeros
  - Adjust last part's weight so sum equals total_nw exactly
  - See §7.4 for detailed algorithm steps
- **Output:** Rounded weights per part that sum to total_nw
- **Error:** ERR_044 → weight rounds to zero at max 6 decimal precision

**FR-029**: System allocates weights to invoice items proportionally
- **Input:** Rounded part weights (FR-028), invoice items with quantities
- **Rules:**
  - For each part_no: allocate weight proportionally by `item_qty / total_qty`
  - Round to line precision (packing precision + 1)
  - Assign remainder to last invoice item per part
- **Output:** Invoice items with allocated weight values
- **Error:** ERR_040 → part in invoice but not in packing; ERR_043 → part in packing but not in invoice

**FR-030**: System validates weight allocation
- **Input:** Allocated weights, total_nw
- **Rules:** Per-part allocated weight must exactly match packing total per part. Grand total must exactly match total_nw.
- **Output:** Validation pass/fail; log: `[INFO] Weight allocation complete: {total_nw}`
- **Error:** ERR_041 → `Weight allocation mismatch: allocated {allocated} != total {total_nw}`

### Validation

**FR-031**: System validates required fields in extracted invoice items
- **Input:** Extracted invoice items
- **Rules:**
  - Required fields: part_no, po_no, qty, price, amount, currency, coo, brand, brand_type, model
  - Empty = None, empty string, or whitespace-only
  - Validated AFTER extraction and BEFORE weight allocation
  - A column can have a valid header but empty data in all rows → ERR_030 (data error), not ERR_020 (mapping error)
- **Output:** Validation pass/fail per item
- **Error:** ERR_030 → empty required field at row; ERR_031 → invalid numeric value (NaN/Inf)
- **Depends:** FR-014

**FR-032**: System classifies each file into exactly one status
- **Rules:**
  - **FAILED:** Any ERR_xxx code → do NOT generate output
  - **ATTENTION:** Only ATT_002 (missing total_packets), ATT_003 (unstandardized currency), or ATT_004 (unstandardized COO) → generate output, flag for review
  - **SUCCESS:** All validations pass, no ERR or ATT codes → generate output
- **Output:** File status with emoji indicator: `✅ SUCCESS`, `⚠️ ATTENTION`, `❌ FAILED`

**FR-033**: System logs errors and warnings with codes at point of detection
- **Rules:**
  - Format: `[ERR_xxx] {message}` or `[ATT_xxx] {message}`
  - Each error/warning logged exactly once (single-point logging). Phase functions log at detection; main orchestrator does NOT re-log.
- **Depends:** FR-032

### Output Generation

**FR-034**: System generates output file for SUCCESS and ATTENTION files
- **Input:** Validated invoice items with allocated weights, packing totals, output template
- **Rules:**
  - Load fresh copy of `output_template.xlsx` for each file (preserves sheet name, formatting, styles)
  - Preserve fixed headers in rows 1-4
  - Write invoice line items starting at row 5
  - Apply fixed values (column C = "3", R = "32052", S = "320506", T = "142") for all data rows
  - Write total_gw in P5 and total_packets in AK5 (row 5 only)
  - See §7.7 for complete 40-column mapping
- **Output:** `{original_filename}_template.xlsx` in `\data\finished` folder
- **Error:** Invalid filename characters (`<>:"/\|?*`) replaced with underscores

**FR-035**: System uses original vendor filename for output (not extracted invoice number)
- **Rules:** Output filename = `{input_filename_without_extension}_template.xlsx`
- **Output:** e.g., `vendor_invoice_001.xlsx` → `vendor_invoice_001_template.xlsx`

### Result Classification & Reporting

**FR-036**: System displays real-time per-file processing status to console
- **Rules:** Suppress third-party library warnings. See §7.2 for exact console output format.

**FR-037**: System writes detailed log to `process_log.txt` in project root
- **Rules:** Format: `[HH:MM] [LEVEL] message`. Levels: DEBUG, INFO, WARNING, ERROR. UTF-8 with BOM encoding. Rewritten each run. Includes regex match details, cell-by-cell parsing, intermediate calculations at DEBUG level.

**FR-038**: System displays batch summary after all files processed
- **Rules:** Summary first (counts + timing), then FAILED files with errors, then ATTENTION files with warnings. Multiple same-code errors within a file condensed to one line with "(N occurrences)" and first encountered part_no as representative example. See §7.8 for format.

**FR-039**: System pauses at end of batch when launched via double-click (.exe)
- **Rules:** Command-line execution exits with status code (no pause) for scripting/automation

**FR-040**: Console output uses UTF-8 encoding
- **Rules:** Set `PYTHONIOENCODING=utf-8` at startup or reconfigure stdout/stderr. Use `errors='replace'` fallback.

### Diagnostic Mode

**FR-041**: System provides `--diagnose <filename>` mode for troubleshooting
- **Input:** Single Excel file path
- **Rules:**
  - Process file in diagnostic mode, do not write output
  - Show ALL attempted pattern matches (successes and failures) for sheets and columns
  - Suggest regex patterns for unmatched columns based on actual header text
  - Plain text output (no emojis) for Windows console compatibility
  - See §7.2 for diagnostic output format
- **Output:** Diagnostic report to console; exit code 0

### Integration

**FR-042**: System entry point wires to batch processor and executes full pipeline
- **Input:** Command-line arguments (optional `--diagnose <filename>`)
- **Rules:**
  - Initialize logging → load/validate config → discover files → process each file through pipeline → generate batch summary
  - Exit codes: 0 = success, 1 = failures occurred, 2 = config error

---

## 4. Non-Functional Requirements

### Performance
- **NFR-PERF-001**: Individual file processing under 30 seconds average
- **NFR-PERF-002**: Batch sizes of 20+ files without memory issues
- **NFR-PERF-003**: Startup and ready to process within 5 seconds
- **NFR-PERF-004**: Pattern matching completes within 2 seconds per sheet

### Reliability
- **NFR-REL-001**: 0% false positive rate — invalid data never marked SUCCESS
- **NFR-REL-002**: Malformed Excel files handled gracefully without crashing
- **NFR-REL-003**: Remaining files continue processing after individual file failures
- **NFR-REL-004**: Identical input files produce identical output (deterministic)

### Compatibility
- **NFR-COMPAT-001**: Runs on Windows 10 and Windows 11 without additional dependencies
- **NFR-COMPAT-002**: Processes both .xls (legacy) and .xlsx (modern) Excel formats
- **NFR-COMPAT-003**: Handles Excel files from Microsoft Excel, LibreOffice, and WPS
- **NFR-COMPAT-004**: Supports file paths with Unicode characters (Chinese folder/file names)

### Maintainability
- **NFR-MAINT-001**: IT Admin with basic regex knowledge can add patterns via YAML editing
- **NFR-MAINT-002**: Pattern changes take effect on next restart (no recompilation)
- **NFR-MAINT-003**: Log files provide sufficient detail to diagnose processing failures
- **NFR-MAINT-004**: Error messages include actionable information (file name, field name, error code)

### Distribution
- **NFR-DIST-001**: Python CLI runs via `uv run autoconvert` with Python 3.11+ and uv
- **NFR-DIST-002**: Standalone executable size under 30 MB
- **NFR-DIST-003**: Fully offline operation (no network dependencies)
- **NFR-DIST-004**: Single-file .exe distribution (no installer)
- **NFR-DIST-005**: CLI and executable provide identical functionality and interface

---

## 5. Data Entities

| Entity | Key Attributes | Related FRs |
|--------|---------------|-------------|
| InvoiceItem | part_no, po_no, qty, price, amount, currency, coo, cod, brand, brand_type, model, inv_no, serial, weight | FR-014, FR-029 |
| PackingItem | part_no, qty, nw | FR-015 |
| PackingTotals | total_nw, total_gw, total_packets, total_row | FR-018, FR-019, FR-020 |
| FieldPatternConfig | invoice_sheet, packing_sheet, invoice_columns, packing_columns, inv_no_cell | FR-001 |
| CurrencyRule | source_value, target_code | FR-024 |
| CountryRule | source_value, target_code | FR-024 |

---

## 6. Technology Constraints

**Decided (non-negotiable):**
- Language: Python 3.11+
- Package manager: uv
- Excel reading: openpyxl (`.xlsx`), xlrd (`.xls` conversion)
- Executable packaging: PyInstaller (single-file)
- Configuration format: YAML with regex support
- Lookup tables: Excel format (two columns: Source_Value, Target_Code)
- Target OS: Windows 10+ (standalone .exe, fully offline)

**Open (agent can decide):**
- Internal module structure and class hierarchy
- Logging library choice
- YAML parsing library
- Testing framework

---

## 7. Implementation Reference

### 7.1 Configuration Schema

**field_patterns.yaml** — shipped with application as read-only reference in `\config` folder.

```yaml
invoice_sheet:
  patterns:
    - 'pattern1'
    - 'pattern2'

packing_sheet:
  patterns:
    - 'pattern1'
    - 'pattern2'

invoice_columns:
  column_name:                     # Snake_case identifier (e.g., part_no, quantity)
    patterns:
      - 'pattern1'                 # Regex, case-insensitive
      - 'pattern2'
    type: <string|numeric|date|currency>
    required: <true|false>

packing_columns:
  column_name:                     # Snake_case with p_ prefix (e.g., p_partno, p_nw)
    patterns:
      - 'pattern1'
      - 'pattern2'
    type: <string|numeric|date|currency>
    required: <true|false>

inv_no_cell:
  patterns:
    - 'INVOICE\s*NO\.?\s*[:：]\s*(\S+)'
    - 'INV\.?\s*NO\.?\s*[:：]\s*(\S+)'
    - '发票号\s*[:：]\s*(\S+)'

  label_patterns:
    - 'No\.?\s*&\s*Date.*Invoice'
    - '^INV\.?\s*NO\.?$'

  exclude_patterns:
    - '(?i)^invoice\s*no\.?[:：]?$'
    - '(?i)^inv\.?\s*no\.?[:：]?$'
    - '(?i)^invoice\s*date[:：]?$'
```

**Rules files (Excel format):**
- `currency_rules.xlsx` — Currency name → standardized code
- `country_rules.xlsx` — Country name → standardized code
- Format: Column A = Source_Value, Column B = Target_Code, header in row 1, data from row 2

### 7.2 Console Output Format

**Startup:**
```
[INFO] =================================================================
[INFO]                     AutoConvert v{version}
[INFO] =================================================================
[INFO] Input folder:  C:\path\to\data
[INFO] Output folder: C:\path\to\data\finished
[INFO] All regex patterns validated and compiled successfully
[INFO] Loaded 2 currency rules, 55 country rules
[INFO] Found 29 xlsx file(s) to process
```

**Per-file — SUCCESS:**
```
[INFO] -----------------------------------------------------------------
[INFO] [1/29] Processing: vendor_invoice_001.xlsx ...
[INFO] Inv_No extracted (1 row below of 'No. & Date of Invoice'): L026-SM-250803 at 'F3'
[INFO] Invoice sheet extracted 83 items (rows 12-94)
[INFO] Packing total row at row 133, NW= 212.5, GW= 257.7, Packets= 92
[INFO] Packing sheet extracted 113 items (rows 14-126)
[INFO] Trying precision: 2
[INFO] Expecting rounded part sum: 212.5, Target: 212.5
[INFO] Perfect match at 2 decimals
[INFO] Weight allocation complete: 212.5
[INFO] Output successfully written to: vendor_invoice_001_template.xlsx
[INFO] ✅ SUCCESS
```

**Per-file — FAILED (errors logged at detection, before status):**
```
[INFO] -----------------------------------------------------------------
[INFO] [2/29] Processing: vendor_invoice_002.xlsx ...
[ERROR] [ERR_020] Required column(s) missing: brand_type
[ERROR] ❌ FAILED
```

**Per-file — ATTENTION (warnings logged at detection, before status):**
```
[INFO] -----------------------------------------------------------------
[INFO] [3/29] Processing: vendor_invoice_003.xlsx ...
[INFO] Inv_No extracted (below of 'No. & Date of Invoice'): ABC-123 at 'E3'
[INFO] Invoice sheet extracted 10 items (rows 12-21)
[INFO] Packing total row at row 30, NW= 50.0, GW= 60.0
[INFO] Packing sheet extracted 10 items (rows 14-23)
[WARNING] [ATT_002] total_packets not found or invalid, please verify manually in output
[INFO] Trying precision: 2
[INFO] Expecting rounded part sum: 50.0, Target: 50.0
[INFO] Perfect match at 2 decimals
[INFO] Weight allocation complete: 50.0
[INFO] Template written to: vendor_invoice_003_template.xlsx
[WARNING]⚠️ ATTENTION
```

**File log format:** `[HH:MM] [LEVEL] message` with DEBUG/INFO/WARNING/ERROR levels. Includes DEBUG-level messages for regex match details, cell parsing, and intermediate calculations.

**Diagnostic mode output:**
```
===========================================================================
                    DIAGNOSTIC MODE - vendor_file.xlsx
===========================================================================

[SHEET DETECTION]
  Invoice sheet: "發票Sheet" matched pattern: "(?i)invoice|發票"
  Packing sheet: "装箱明细" matched pattern: "(?i)pack|装箱"

[COLUMN MAPPING - Invoice Sheet]
  Header row detected at: Row 11
    part_no      (Col C) matched: "(?i)part.?no|料号" (required)
    po_no        (Col E) matched: "(?i)po.?no|订单" (required)
    currency     (Col ?) NOT MATCHED (required)
      Tried patterns: ['(?i)curr', '(?i)币种']

[SUGGESTED ADDITIONS]
  Add to field_patterns.yaml > invoice_columns > currency > patterns:
    - "(?i)货币"  # Found in header: "货币代码"

[COLUMN MAPPING - Packing Sheet]
  Header row detected at: Row 15
    part_no      (Col C) matched: "(?i)part.?no" (required)
    nw           (Col H) matched: "(?i)net.*wt" (required)
    gw           (Col I) matched: "(?i)gross" (required)

[TOTAL ROW DETECTION]
  Total row detected at: Row 95
    total_nw: 212.5
    total_gw: 257.7
    total_packets: 20
```

### 7.3 Error/Status Code Catalog

**Startup Errors (exit code 2 — halt before processing):**

| Code | Description | Cause | Resolution |
|------|-------------|-------|------------|
| ERR_001 | Config file not found | `field_patterns.yaml` missing | Restore from installation |
| ERR_002 | Invalid regex pattern | Syntax error in pattern | Fix regex in field_patterns.yaml |
| ERR_003 | Duplicate lookup code | Same code mapped to multiple values | Remove duplicate entries |
| ERR_004 | Malformed Excel file | Rules or template file corrupted | Replace corrupted file |
| ERR_005 | Template structure invalid | output_template.xlsx missing columns/headers | Restore from installation |

**File-Level Errors (FAILED):**

| Code | Description | Cause | Resolution |
|------|-------------|-------|------------|
| ERR_010 | File locked | Open in another application | Close file and retry |
| ERR_011 | File corrupted | Cannot read Excel structure | Request new file from vendor |
| ERR_012 | Invoice sheet not found | No sheet matches patterns | Add pattern or check file |
| ERR_013 | Packing sheet not found | No sheet matches patterns | Add pattern or check file |
| ERR_014 | Header row not found | No row in range 7-30 has ≥7 valid headers | Check file structure |

**Column Mapping Errors (FAILED):**

| Code | Description | Cause | Resolution |
|------|-------------|-------|------------|
| ERR_020 | Required column missing: {field} | Header not matched | Add pattern for vendor's format |
| ERR_021 | Invoice number not found | No inv_no in header or data | Check file for inv_no location |

**Data Extraction Errors (FAILED):**

| Code | Description | Cause | Resolution |
|------|-------------|-------|------------|
| ERR_030 | Empty required field: {field} | Required field empty in data row | Vendor file incomplete |
| ERR_031 | Invalid numeric value: {field} | Non-numeric in qty/price/amount | Check for text in numeric columns |
| ERR_032 | Total row not found | No TOTAL keyword or numeric pattern | Check packing sheet structure |
| ERR_033 | Invalid total_nw | 0, negative, or non-numeric | Verify packing total row |
| ERR_034 | Invalid total_gw | 0, negative, or non-numeric | Verify packing total row |

**Weight Allocation Errors (FAILED):**

| Code | Description | Cause | Resolution |
|------|-------------|-------|------------|
| ERR_040 | Part not in packing | Part in invoice but not packing | Verify part numbers match |
| ERR_041 | Weight allocation mismatch | Allocated sum ≠ total_nw | Check weight data entry |
| ERR_042 | Zero packing weight | Part has qty but weight = 0 | Ensure part has weight in packing |
| ERR_043 | Packing part not in invoice | Part in packing but not invoice | Verify part numbers match |
| ERR_044 | Weight rounds to zero | Weight too small at max 6 decimal precision | Weight value too small |
| ERR_045 | Zero quantity for part | Total qty = 0, cannot allocate | Verify qty values in invoice |
| ERR_046 | Different parts share merged weight | Different part_no in same merged NW cell | Vendor must separate weight cells |
| ERR_047 | Packing sum mismatch | Extracted sum differs from total_nw by > 0.1 | Check for missing rows or wrong total |

**Attention Codes (output generated, flag for review):**

| Code | Description | Cause | Resolution |
|------|-------------|-------|------------|
| ATT_002 | Missing total_packets | Cannot extract packet count | Manually verify in output |
| ATT_003 | Unstandardized currency: {value} | Value not in currency_rules.xlsx | Add mapping or correct in output |
| ATT_004 | Unstandardized COO: {value} | Value not in country_rules.xlsx | Add mapping or correct in output |

### 7.4 Weight Allocation Algorithm

**Step 1 — Precision Detection:**
- Input: `total_nw` (rounded per FR-018 cell format precision)
- Analyze decimal places from rounded value
- Output: base precision N (minimum 2, maximum 5)
- Example: `45.23` → 2, `1.955` → 3, `100.0` → 2

**Step 2 — Weight Aggregation:**
- Sum packing item weights grouped by part_no
- When same part_no shares merged weight, only first row contributes
- Validate: no zero or negative aggregated weights

**Step 3 — Pre-Allocation Validation:**
- Compare sum of extracted packing weights against total_nw
- If difference > 0.1, fail with ERR_047 (catches data issues before rounding)

**Step 4 — Precision Determination:**
- For sum matching: Try N → if perfect match, stop. Try N+1 → if match, stop. Else use N+1 with remainder adjustment. Do NOT try N+2.
- For zero check: If any weight rounds to zero at current precision → increase (N+1, N+2, ... up to max 5). Stop at first precision with no zeros.

**Step 5 — Rounding & Adjustment:**
- Round all part weights to determined packing precision using ROUND_HALF_UP
- If any rounds to zero, increase precision (per step 4)
- Adjust last part's weight so sum equals total_nw exactly

**Step 6 — Proportional Allocation:**
- For each part_no: find matching invoice items, calculate total quantity
- Allocate weight proportionally: `weight = total_weight × (item_qty / total_qty)`
- Round to line precision (packing precision + 1) using ROUND_HALF_UP
- Assign remainder to last invoice item per part

**Step 7 — Validation:**
- Per-part: allocated weight must exactly match packing total for that part
- Global: grand total must exactly match total_nw

**Required log messages (exact format):**
- `[INFO] Trying precision: {try_precision}`
- `[INFO] Expecting rounded part sum: {rounded_sum}, Target: {grand_total}`
- `[INFO] Perfect match at {try_precision} decimals`
- `[INFO] Can't find perfect match at {base_precision+1} decimals, but use it with part adjustment`
- `[INFO] Adjusting last part weight to match total_nw`
- `[WARNING] Packing weight is rounded to zero for part '{part_no}', need to change to {packing_precision+1} decimals`
- `[INFO] Weight allocation complete: {total_nw}`

**Precision summary:**
| Level | Precision |
|-------|-----------|
| total_nw | N (base, from value) |
| Packing weights | N or N+1 (dynamic) |
| Invoice item weights | packing precision + 1 |

### 7.5 Invoice Number Extraction Algorithm

**Method 1 — Label Match (primary):**

1. Scan rows 2-15 for cells matching `inv_no_cell.label_patterns`
2. For each label match, check adjacent cells in order: right, right+1, below, below+1
3. For each adjacent cell, evaluate in this priority:
   - **(a) Pure label check:** If cell matches label_pattern AND is a pure label → recursive search from that cell (max 3 levels)
   - **(b) Exclude pattern check:** If cell matches exclude_pattern → extended search (right, then below)
   - **(c) Valid value check:** If cell passes validation → return as invoice number

**Pure label detection:** A cell is "pure label" if it matches a label_pattern AND has < 3 alphanumeric characters remaining after removing keywords. Keywords must be removed in length-descending order (longest first) to prevent partial matches.

- Keywords: "invoice", "inv", "no", "number", "date", "&", "of", plus punctuation and whitespace
- Removal order: `sorted(LABEL_KEYWORDS, key=len, reverse=True)`
- Example: "INVOICE NO：" → remove "invoice" → " NO：" → remove "no" → " ：" → 0 chars → IS pure label

**Extended search:** When adjacent cell matches exclude_patterns (e.g., date values), try cell to its right, then cell below.

**Method 2 — Embedded Value (fallback):** Extract from cells containing both label and value using `inv_no_cell.patterns` regex capture groups.

**Log format:** `[INFO] Inv_No extracted ({method} of '{label}'): {inv_no} at '{cell_ref}'`
- Methods: "embedded", "1 cell right", "2 cells right", "1 row below", "2 rows below", "nested label of '{nested_label}'"

### 7.6 Merged Cell Processing

**Processing order (must follow exactly):**

1. **Initialize merge tracker:** Create tracker AND capture all merge ranges immediately (before any other operations)
2. **Unmerge all cells:** After this, non-origin cells are empty
3. **Find headers & map columns:** Detect header row, map column indices
4. **Extract data with merge-aware reading:** When reading string field values, check if cell was part of a merged range; if yes, read from merge origin (top-left cell)
5. **Propagate if needed:** Optionally call bulk propagation for string fields

**String field propagation (all directions):**
- Vertical: A10:A15 → value in A10 propagates to A11-A15
- Horizontal: L21:M21 → value in L21 propagates to M21
- Block: B5:D8 → value in B5 propagates to all cells in range

**Header vs data merge distinction:**
- Merges starting at or before header row = header formatting → NOT propagated to data rows
- Merges starting after header row = data merges → values ARE propagated
- `propagate_string_values()` must receive the `header_row` parameter (detected after unmerging)

**String fields that propagate (invoice):** part_no, po_no, currency, coo, brand, brand_type, model, serial, inv_no
**String fields that propagate (packing):** part_no
**Numeric fields that do NOT propagate:** qty, price, amount (invoice); qty, nw, gw (packing)

**ERR_046 validation example:**
```
Packing Sheet (before unmerging):
┌─────────┬──────────┬────────┬─────────┐
│ Row     │ Part No. │ Qty    │ NW (KG) │
├─────────┼──────────┼────────┼─────────┤
│ Row 23  │ 490DLF00 │ 200    │         │
│         │          │        │  770.84 │ ← NW merged across rows 23-25
│ Row 24  │ 490DPY10 │ 5018   │         │
│ Row 25  │ 490DPY10 │ 750    │         │
└─────────┴──────────┴────────┴─────────┘

Problem: 770.84 kg spans 2 different parts (490DLF00, 490DPY10).
Error: [ERR_046] Different parts (490DLF00, 490DPY10) share merged NW/qty cell (rows 23-25)
```

### 7.7 Output Template Schema

**40-column mapping (A-AN):**

| Column | Field | Source | Notes |
|--------|-------|--------|-------|
| A | part_no | Invoice | Part number |
| B | po_no | Invoice | Cleaned PO number |
| C | FIXED | Fixed: `"3"` | Exemption method |
| D | currency | Invoice | Standardized numeric code |
| E | qty | Invoice | Quantity |
| F | price | Invoice | Unit price |
| G | amount | Invoice | Total amount |
| H | coo | Invoice | Standardized country code |
| I-K | [Reserved] | — | Empty |
| L | serial | Invoice | Item serial |
| M | weight | Allocation | Net weight |
| N | inv_no | Invoice | Invoice number |
| O | [Reserved] | — | Empty |
| P | total_gw | Packing | **Row 5 only** |
| Q | [Reserved] | — | Empty |
| R | FIXED | Fixed: `"32052"` | Destination region |
| S | FIXED | Fixed: `"320506"` | Admin code |
| T | FIXED | Fixed: `"142"` | Destination country |
| U-AJ | [Reserved] | — | Empty (16 columns) |
| AK | total_packets | Packing | **Row 5 only** |
| AL | brand | Invoice | Brand name |
| AM | brand_type | Invoice | Brand specification |
| AN | model | Invoice | Model number |

- Rows 1-4: Fixed headers (preserved from template)
- Data rows start at row 5, one per invoice line item
- total_gw (P5) and total_packets (AK5) written only in first data row

### 7.8 Batch Summary Format

```
[INFO] ===========================================================================
[INFO]                    BATCH PROCESSING SUMMARY
[INFO] ===========================================================================
[INFO] Total files:        29
[INFO] Successful:         27
[INFO] Attention:          1
[INFO] Failed:             1
[INFO] Processing time:    72.39 seconds
[INFO] Log file:           C:\path\to\process_log.txt
[INFO] ===========================================================================
```

**FAILED files section (after summary):**
```
[ERROR] FAILED FILES:
[ERROR] --------------------------------------------------------------------------
[ERROR] * vendor_file_1.xlsx
[ERROR]     [ERR_043] Part 'ABC123' in packing sheet not found in invoice (10 occurrences)
[ERROR] * vendor_file_2.xlsx
[ERROR]     [ERR_020] Required column missing: brand_type
[ERROR] --------------------------------------------------------------------------
```

**ATTENTION files section:**
```
[WARNING] FILES NEEDING ATTENTION:
[WARNING] ------------------------------------------------------------------------
[WARNING] * another_vendor_1.xlsx
[WARNING]     [ATT_002] total_packets not found or invalid, please verify manually in output
[WARNING] ------------------------------------------------------------------------
```

Condensing rules: Multiple same-code errors within a file → one line with "(N occurrences)" and first encountered part_no as representative example.

### 7.9 Numeric Precision Rules

**ROUND_HALF_UP method:** 0.5 always rounds up (e.g., 0.125 → 0.13, not 0.12).
Implementation: `round(value * 10^decimals + 1e-9) / 10^decimals` (epsilon trick for floating-point).

**Cell format precision detection:** Read cell's `number_format` property, count zero placeholders (`0`) after decimal point. Ignore currency symbols, separators, brackets. Matches: `0.00`, `#,##0.00`, `_($* #,##0.00_)`.

**Field-specific precision:**

| Field | Precision Rule |
|-------|---------------|
| Invoice qty | Cell display precision |
| Invoice price | Fixed 5 decimals |
| Invoice amount | Cell display precision |
| Packing nw (line-level) | Fixed 5 decimals (high precision for allocation) |
| total_nw | Cell visible precision via number_format |
| total_gw | Cell visible precision via number_format |

**Floating-point artifact elimination:** When format is `General` or empty, round to 5 decimals to clean artifacts (e.g., `77.22000000000001` → `77.22`), then normalize trailing zeros.

**Embedded unit precision:** When format is `General` and value has embedded unit (e.g., "4.95KG"), strip unit before counting decimals. "4.95KG" → strip → "4.95" → 2 decimals (NOT 4).

**Unit suffix stripping:** Strip KG, KGS, PCS, EA, 件, 个 from numeric values before parsing (applies to both invoice and packing extraction).
