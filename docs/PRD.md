# Product Requirements Document - AutoConvert

**Author:** Alex Liou
**Date:** 2025-12-09
**Last Updated:** 2026-01-25

## Executive Summary

AutoConvert is a Python CLI tool (with standalone Windows executable distribution) that automates the conversion of vendor Excel files into a standardized template for customs reporting. Currently, logistics staff manually process ~600 files per month, spending approximately 10 minutes per file—totaling 100+ hours of repetitive, error-prone work monthly.

The tool monitors a designated input folder, intelligently identifies invoice and packing sheets, maps columns using semantic similarity matching, applies business rules (currency/country codes, weight allocation), and outputs standardized templates with real-time Success/Attention/Failed status reporting.

### What Makes This Special
**The Deterministic Heuristic Engine:** Unlike standard scripts that break when a column moves or header row changes, `AutoConvert` uses a configuration-driven synonym engine to deterministically identify sheets and map columns. It strictly enforces data integrity with a "Zero False Positive" policy—if it's not 100% right, it doesn't pass.


## Project Classification

**Technical Type:** Python CLI Tool + Standalone Windows Executable
**Domain:** Logistics & Operations
**Complexity:** Medium

### Distribution Formats

AutoConvert is distributed in **two formats**:

1. **Python CLI Tool** (`uv run autoconvert`)
   - For development, testing, and scripting/automation workflows
   - Requires Python 3.11+ with uv package manager
   - Supports all command-line arguments and flags
   - Used during development and by technical users

2. **Standalone Windows Executable** (`AutoConvert.exe`)
   - For end-user distribution to logistics staff
   - Single-file .exe packaged via PyInstaller (<30 MB)
   - No Python installation or dependencies required
   - Windows 10+ compatible, fully offline operation
   - Double-click execution with pause-at-end for user review

Both formats share identical functionality and command-line interface.

### Domain Context
The project operates in a high-volume logistics environment where vendor data variability is the primary challenge. Accuracy is paramount over speed; a wrong weight calculation or PO number causes downstream shipping errors. The system must handle local files immutably.


## Success Criteria

1.  **Time Compression:** Reduce processing time per file from 10 minutes to **< 30 seconds**.
2.  **Automation Rate:** System successfully processes **≥60%** of vendor files without manual intervention.
3.  **Fail-Safe Trust:** The system achieves **0% False Positives**. A file is ONLY marked "Success" if all required data is valid.
4.  **Standardization:** 100% of generated output files meet the strict template validation rules (codes, formats).

### Business Metrics
* **Hours Recovered:** Target saving ~80+ hours/month.
* **Throughput:** Batch process 20+ files in a single run.
* **Error Reduction:** Elimination of manual data entry typos and calculation errors.

## Product Scope

### MVP - Minimum Viable Product

1. **Batch Processing Engine** - Python CLI tool + one-click .exe (<30 MB), processes input folder, Windows 10+
2. **Input:** Read-only access to `\data` folder containing vendor Excel files.
3. **Sheet Detection** - Configuration-based pattern matching for Sheets (Invoice + Packing) using Regex.
4. **Intelligent Column Mapping** - Configuration-based pattern matching 13 per-item fields using Regex.
5. **Invoice Sheet Extraction** - Extract Invoice data from invoice sheet.
6. **Packing Sheet Extraction** - Extract Packing data items from packing sheet. Detect total row, retrieve total_nw, total_gw, total_packets.
7. **Data Transformation** - Currency/country codes, invoice number cleaning, PO number cleaning
8. **Weight Allocation** - Part-level proportional allocation with validation
9. **Output Generation** - 40-column template population, Generate standardized files in `\data\finished`
10. **Transparency:** Real-time console logs + file logging and Batch Summary (Success/Attention/Failed).
11. **Diagnostic Mode:** Command-line flag `--diagnose <filename>` for troubleshooting pattern matching issues, showing which regex patterns matched/failed and suggesting additions to user configuration.
12. **Integration & Smoke Test:** Wire all modules to main entry point and validate end-to-end processing with real data files.

### Growth Features (Post-MVP)

 Phase | Feature | Value |
|-------|---------|-------|
| v1.1 | Pattern learning from corrections | Improve automation rate over time |
| v1.2 | Vendor profile management UI | Reduce IT dependency |
| v2.0 | Web dashboard for managers | Visibility into automation stats |


## Innovation & Novel Patterns

### The Deterministic Matcher
Instead of "AI" guessing, we use strict synonym lists defined in `\config\field_patterns.yaml`.
* **Sheet Identity:** Identified by presence of certain key words in sheet name.
* **Column Mapping:** Columns mapped via Regex matches against the config list.
* **Binary Validation:** If a required synonym is missing, the file fails immediately.


## Project Type Requirements (Console App)

### Project-Type Overview

AutoConvert is a **batch-mode CLI tool** available as both a Python module and a standalone Windows executable. It follows a "run and done" pattern with a pause at the end when launched directly (double-click .exe), designed for logistics staff who process vendor files in batches.

### Execution Methods

| Method | Command | Use Case |
|--------|---------|----------|
| Python CLI | `uv run autoconvert` | Development, testing, scripting |
| Python CLI | `uv run autoconvert --diagnose file.xlsx` | Diagnostic mode |
| Executable | `AutoConvert.exe` (double-click) | End-user batch processing |
| Executable | `AutoConvert.exe --diagnose file.xlsx` | End-user diagnostic mode |

## Folder Structure

```
AutoConvert/
├── AutoConvert.exe           # Standalone executable (for end-users)
├── config/                   # Configuration folder
│   ├── field_patterns.yaml   # Column mapping patterns (regex-based)
│   ├── currency_rules.xlsx   # Currency name → code mappings
│   ├── country_rules.xlsx    # Country name → code mappings (COO)
│   └── output_template.xlsx  # 40-column template file
├── data/                     # Processing folder
│   ├── [input files here]    # Vendor Excel files to process
│   └── finished/             # Completed output files
└── process_log.txt           # Log file
```

### Command Structure

**Execution Model:**
- **Double-click .exe:** Processes all files, displays results, pauses at end for user to review console output before closing
- **Command-line execution:** Runs to completion, exits with status code (no pause - for scripting/automation)

### Configuration Schema

**field_patterns.yaml** (Located in `\config` folder) - Shipped with application as read-only reference
- **Update Safety:** Application updates can add new default patterns without overwriting user customizations
- **Format:** YAML with **Regex** support.
- **Validation:** System compiles Regex at startup; halts on syntax errors.
- **Structure:**
    ```yaml
  invoice_sheet:
    patterns:
      - 'pattern1'                # Primary pattern
      - 'pattern2'                # Alternative pattern

  packing_sheet:
    patterns:
      - 'pattern1'                # Primary pattern
      - 'pattern2'                # Alternative pattern

  invoice_columns:
    column_name:                   # Snake_case identifier (e.g., part_no, quantity)
      patterns:                    # List of regex patterns (case-insensitive matching)
        - 'pattern1'               # Primary pattern
        - 'pattern2'               # Alternative pattern
      type: <data_type>            # string | numeric | date | currency
      required: <true|false>       # Is this field mandatory for extraction?

  packing_columns:
    column_name:                    # Snake_case identifier with p_ prefix (e.g., p_partno, p_nw)
      patterns:                    # List of regex patterns (case-insensitive matching)
        - 'pattern1'               # Primary pattern
        - 'pattern2'               # Alternative pattern
      type: <data_type>            # string | numeric | date | currency
      required: <true|false>       # Is this field mandatory for extraction?

  # Invoice number extraction from header area (rows 2-15)
  inv_no_cell:
    patterns:
      - 'INVOICE\s*NO\.?\s*[:：]\s*(\S+)'   # INVOICE NO: 12345
      - 'INV\.?\s*NO\.?\s*[:：]\s*(\S+)'    # INV NO: 12345, INV. NO.: 12345
      - '发票号\s*[:：]\s*(\S+)'            # 发票号：12345

    # Label patterns - value is in adjacent cell (right or below)
    label_patterns:
      - 'No\.?\s*&\s*Date.*Invoice'         # No. & Date of Invoice
      - '^INV\.?\s*NO\.?$'                  # INV NO (without colon)

    # Exclude patterns - reject extracted values matching these (label text captured as value)
    exclude_patterns:
      - '(?i)^invoice\s*no\.?[:：]?$'       # "Invoice No", "Invoice No.", "Invoice No:", "Invoice No："
      - '(?i)^inv\.?\s*no\.?[:：]?$'        # "Inv No", "INV NO:", "Inv. No."
      - '(?i)^invoice\s*date[:：]?$'
    ```

**Rules files (Excel format):**
- `currency_rules.xlsx` - Currency name → standardized code
- `country_rules.xlsx` - Country name → standardized code
- **Format:** Two columns (A: Source_Value, B: Target_Code), with header row in row 1. Data starts from row 2.

### Output Formats

| Output Type | Format | Detail Level | Timestamp |
|-------------|--------|--------------|-----------|
| **Console** | Real-time text | Detailed processing steps + batch summary | No |
| **File log** | Text file | Same as console with timestamps | `[HH:MM] [LEVEL]` |
| **Output files** | Excel (.xlsx) | Populated 40-column template → `data/finished/` | N/A |

## Console Output Format

> **Implementation:** See FR60-FR64 for logging requirements. This section defines the exact output format.

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

**Per-file processing (MUST follow this exact format for EVERY file):**

**SUCCESS example:**
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

**FAILED example - errors logged IMMEDIATELY when detected, before FAILED status:**
```
[INFO] -----------------------------------------------------------------
[INFO] [2/29] Processing: vendor_invoice_002.xlsx ...
[ERROR] [ERR_020] Required column(s) missing: brand_type
[ERROR] ❌ FAILED
```

**ATTENTION example - warnings logged IMMEDIATELY when detected, before ATTENTION status:**
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

**IMPORTANT: Errors and warnings MUST be logged at the moment they are detected, NOT after the final status is determined.**

**File log format:** More detailed than console, with `[HH:MM] [LEVEL]` prefix. Includes `[DEBUG]` level messages for troubleshooting (regex match details, cell-by-cell parsing, intermediate calculations).


## Functional Requirements

### System Setup & Input (FR1-FR3)

* **FR1:** System loads configuration patterns and validates root keys.
  - Loads `config/field_patterns.yaml`
  - Validates root keys: `invoice_sheet`, `packing_sheet`, `invoice_columns`, `packing_columns`, `inv_no_cell`
  - Validates all Regex patterns at startup; halts with error if invalid.

* **FR2:** System scans the `\data` folder for valid Excel files (.xls, .xlsx).
  - Converts legacy .xls files to openpyxl Workbook in-memory using xlrd library (no temp file created)
  - Original .xls file remains untouched (read-only policy)
  - Opens Excel files with `data_only=True` to read calculated formula values

* **FR3:** System treats the `\data` folder as **Read-Only** (never modifies or moves source files).
  - Checks if a file is locked (open in Excel) before reading. If locked, **skip and log errors** (do not crash).

### Structure Detection & Column Mapping (FR4-FR14)

* **FR4:** System identifies **Invoice Sheet** by scanning for `invoice_sheet.patterns`. The sheet name of vendor file may contain white spaces or invisible characters, need to strip first.

* **FR5:** System identifies **Packing Sheet** by scanning for `packing_sheet.patterns`. The sheet name of vendor file may contain white spaces or invisible characters, need to strip first.

* **FR6:** **Sheet Missing:** If `Invoice Sheet` or `Packing Sheet` is missing, status = **FAILED**. Log specific error.

* **FR7:** System can detect header row position (from row 7 to row 30) based on non-empty cell count (≥7 non-empty for the first 13 columns).
  - **Column scan limit:** First 13 columns are scanned for header detection.
  - **Cell count threshold:** Minimum 7 valid headers required.
  - **Start row:** Detection starts from row 7 to handle files with headers in early rows.
  - **Placeholder filtering:** Cells containing "Unnamed" prefix (e.g., "Unnamed: 1", "Unnamed: 2") are treated as empty and excluded from the count. These artifacts occur when files are processed by pandas or similar tools.
  - **Metadata row filtering:** Rows containing metadata labels (Tel:, Fax:, Cust ID:, Contact:, Address:) are deprioritized in favor of actual header rows.
  - **Header pattern matching:** Rows with recognized header keywords (qty, n.w., g.w., part no, amount, price, quantity, weight, 品牌, 料号, 数量, 单价, 金额, 净重, 毛重, 原产, country, origin, brand, model, description, unit, currency, coo) are prioritized.
  - **Data value filtering:** Rows with 3+ cells containing data-like values (pure numbers, decimal numbers, alphanumeric codes like "SG24701") are deprioritized. This prevents data rows from being mistakenly identified as header rows.
  - **Note:** After unmerging, non-first rows of merged cells are empty and won't trigger false header detection.

* **FR8:** System can map 14 vendor columns to standardized fields using regex patterns from `invoice_columns.<column_name>.patterns`.
  - **Column scan range:** Column mapping scans columns A through Z (1-26) to accommodate vendor files with fields spread across many columns. This differs from FR7's 13-column limit which only applies to header ROW detection (cell counting for row identification).
  - Multiple patterns matching same column -> first pattern wins
  - Same pattern matching multiple columns -> leftmost column wins
  - **Merged header currency detection:** When currency column is not found via header pattern matching, the system scans the **first effective data row** (skipping blank rows, see FR17 logic) for currency values (USD, CNY, EUR, RMB, JPY, GBP, HKD, TWD):    - Columns already matched to other fields are skipped, EXCEPT columns matched to headers containing "PRICE", "AMOUNT", "金额", or "单价" keywords
    - This handles merged header patterns where "UNIT PRICE" or "AMOUNT" spans multiple sub-columns with currency code in one and numeric value in another
    - Example: "UNIT PRICE" merged across col D-E, header pattern matches col D to `price`, data row has "USD" in col D and "0.142" in col E → currency detection finds "USD" in col D and maps currency to col D (col D is not skipped because its header contains "PRICE")
    - The leftmost currency value found in the data row wins
  - **Merged header price/amount column adjustment:** When price or amount columns contain currency codes instead of numeric values (merged header pattern), the system adjusts the column mapping:
    - If price column data row value is a currency code (USD, CNY, etc.) AND adjacent column (col+1) has a numeric value → shift price mapping to col+1
    - Same logic applies to amount column
    - Example: "UNIT PRICE" merged across col D-E, header pattern matches col D to `price`, data row has "USD" in col D and "0.142" in col E → price column is adjusted from col D to col E
    - This ensures price/amount values are correctly extracted as numbers, not currency codes
  - **Implementation (CRITICAL):** The `map_columns()` function MUST integrate both currency fallback detection AND price/amount column adjustment:
    1. First, attempt header pattern matching for all columns including currency
    2. If currency column is NOT found via header matching, call `detect_currency_from_data()`
    3. Call `_adjust_numeric_columns_for_currency()` to shift price/amount columns when they contain currency codes
    4. This must happen BEFORE returning errors for missing required columns
    - This ensures currency detection and price/amount column adjustment are always attempted within the column mapping phase

| Column     | Required | Notes |
|------------|----------|-------|
| part_no    | Yes      | |
| po_no      | Yes      | |
| qty        | Yes      | |
| price      | Yes      | |
| amount     | Yes      | |
| currency   | Yes      | |
| coo        | Yes      | |
| COD        | No       | |
| brand      | Yes      | |
| brand_type | Yes      | |
| model      | Yes      | |
| weight     | No       | **Mapped for diagnostic/completeness only** — no data is extracted from this column. Weight values come solely from allocation (FR31-FR36). `map_columns` maps the header so diagnostic mode (FR59) can report its presence, but the column index is never used for data extraction. |
| inv_no     | No       | Optional in data rows; fallback to header extraction (FR15) |
| serial     | No       | |

* **FR9:** System supports multi-row headers for both invoice and packing sheets.
  - **Multi-row header support:** If required fields are not found in the primary header row, system checks header_row + 1 for sub-headers
    - Packing sheet example: Header row has "WEIGHT(KGS)" merged across col F-G, sub-row has "N.W.(KGS)" in col F and "G.M.(KGS)" in col G → nw maps to col F, gw maps to col G
  - **Implementation (CRITICAL):** Both invoice and packing sheets MUST use `map_columns_with_subheader()` function:
    - Invoice sheet: uses `map_columns_with_subheader(sheet, header_row, registry, "invoice")`
    - Packing sheet: uses `map_columns_with_subheader(sheet, header_row, registry, "packing")`
    - The function checks for any missing required fields in sub-header row
  - **Sub-header vs Data Row Distinction (CRITICAL):** When checking header_row + 1 for sub-headers, the system must distinguish between actual sub-header text and data values:
    - **Valid sub-header:** Descriptive text like "N.W.(KGS)", "G.M.(KGS)", "数量", "Unit" - these are column labels
    - **NOT a sub-header:** Currency codes (USD, CNY, EUR, RMB, etc.), country names (China, USA), numeric values, part numbers - these are data values
    - **Currency column special case:** If the currency column is "filled" by matching a currency CODE pattern (e.g., `^USD$`) rather than a header pattern (e.g., `(?i)^currency$`), the match must be rejected as a sub-header. Currency code patterns are for data row fallback detection (FR8), not header detection.
    - **Implementation:** When a cell value matches a currency code (USD, CNY, EUR, RMB, JPY, GBP, HKD, TWD), do NOT count it as filling a missing column for sub-header detection purposes
    - **Example:** Header row 11 has no currency column. Row 12 has "USD" in column D (a data value). The system must NOT treat row 12 as a sub-header just because "USD" matches the `^USD$` pattern.
  - **Data extraction start row (CRITICAL):** When multi-row headers are used (sub-header detected), data extraction MUST start at `header_row + 2`, not `header_row + 1`. The sub-header row (header_row + 1) contains unit labels, not data.
    - Example: Header at row 12, sub-header at row 13 → data extraction starts at row 14
    - This applies to BOTH invoice and packing sheets

| Column  | Required | Notes |
|---------|----------|-------|
| po_no   | Yes      | **Header detection only** — `po_no` contributes to cell count in FR7 header row detection but its data values are never extracted or used from the packing sheet. |
| part_no | Yes      | |
| qty     | Yes      | |
| nw      | Yes      | |
| gw      | Yes      | |
| pack    | No       | |

* **FR10:** System can match columns using case-insensitive pattern matching.
  - Normalizes whitespace in column headers before pattern matching
  - Collapses newlines, tabs, and multiple spaces to single spaces
  - Example: `"Net WT\nKGS"` → `"Net WT KGS"`, `"Part  No"` → `"Part No"`

* **FR11:** System can support multilingual column headers (English + Chinese)

* **FR12:** System can handle merged cells by unmerging
  - **Default behavior:** For numeric fields, values are NOT propagated after unmerging
    - Invoice sheet: qty, price, amount
    - Packing sheet: qty, nw, gw
  - **String field propagation (CRITICAL):** For non-numeric fields, values ARE propagated from the origin cell (top-left) of merged ranges to ALL cells in the merge range:
    - Invoice sheet: part_no, po_no, currency, coo, brand, brand_type, model, serial, inv_no
    - Packing sheet: part_no (for row identification)
    - **Implementation Note:** ALL string fields must be propagated, not just part_no. Example: If "品牌类型" (brand_type) column has merged cells spanning rows 20-21, the value in row 20 must propagate to row 21. Missing propagation causes empty field values in extracted data.
  - **Propagation directions:** Values propagate from the origin cell to ALL cells within the merged range:
    - **Vertical merges:** Same column, multiple rows (e.g., A10:A15) → value in A10 propagates to A11-A15
    - **Horizontal merges:** Same row, multiple columns (e.g., L21:M21) → value in L21 propagates to M21
    - **Block merges:** Multiple rows AND columns (e.g., B5:D8) → value in B5 propagates to all cells in range
    - Example: "品牌" and "品牌类型" columns merged horizontally (L21:M21) with value "无品牌" in L21 → M21 (brand_type) receives "无品牌"
  - **Multi-row header handling:** Header cells may span multiple rows for visual formatting (e.g., header at row 23 merged with row 24). When propagating merged cell values to data rows:
    - **Header merges:** Merges that START at or before the header row are considered header formatting and their values are NOT propagated to data rows
    - **Data merges:** Only merges that START after the header row (data rows) have their values propagated
    - Example: Header "Part No." merged across rows 23-24 (header row is 23) → row 24 is blank after unmerging, not filled with "Part No."
    - Example: Data value "ABC123" merged across rows 25-26 (both are data rows) → row 26 gets value "ABC123" propagated
    - **Implementation (CRITICAL):** `propagate_string_values()` MUST receive the `header_row` parameter (detected AFTER unmerging). Without this parameter, the function cannot distinguish header merges from data merges, causing header values like "Part No." to be incorrectly propagated to data rows and extracted as data items.
  - Detect embedded currency in price/amount column (merged cell pattern)
  - **Processing order (CRITICAL - must follow exactly):**
    1. **Initialize MergeTracker:** Create tracker AND capture all merge ranges immediately on initialization (before any other operations). The tracker must auto-capture merges in `__init__()` to ensure merge information is available.
    2. **Unmerge all cells:** Call `unmerge_all()` on the sheet. After this, non-origin cells of merges will be empty.
    3. **Find headers & map columns:** Detect header row and map column indices.
    4. **Extract data with merge-aware reading:** When reading string field values during extraction:
       - Check if the cell was part of a merged range using the tracker
       - If yes, read the value from the merge origin (top-left cell), NOT from the current cell
       - This ensures rows that were part of a vertical merge get the correct value even though their cells are now empty after unmerging
    5. **Propagate if needed (OPTIONAL):** `propagate_string_values()` is an **optional convenience** that may simplify code by writing values into cells before extraction. It is **not required** if merge-aware reading (step 4) is properly implemented. Step 4 (merge-aware reading) is the **required** mechanism.
  - **Implementation Note:** The extraction code MUST handle merged cells explicitly. Simply unmerging is NOT sufficient - the extraction must either read from origins (step 4, required) or propagate values first (step 5, optional convenience).

* **FR13:** System validates merged weight cells in packing sheet:
  - **Same part_no sharing merged NW/qty:** Allowed (same part can span multiple rows with shared weight). See FR22 for aggregation handling.
  - **Different part_no sharing merged NW/qty:** Error ERR_046 - weight cannot be properly allocated when different parts share the same merged weight cell
  - **Validation timing (CRITICAL):** ERR_046 is checked immediately after packing item extraction, BEFORE weight allocation. This provides a clear root cause error instead of the downstream ERR_042 (zero weight) symptom.
  - **Header-area merge exclusion (CRITICAL):** Only check merges that START after the header row (data-area merges). Merges at or before the header row are metadata/formatting (e.g., shipper address block merged across the NW column) and must be ignored. This extends the same header-vs-data merge distinction established in FR12.
  - **Processing order:** Capture all numeric merges BEFORE unmerging → Unmerge sheets → Find headers & map columns → Extract packing items → **Validate merged weight cells (ERR_046, data-area only)** → Total row detection → Weight allocation
  - **Weight aggregation:** When same part_no shares merged weight, only the first row of the merge contributes to weight sum (FR22) to prevent double-counting

  **Concrete Example - ERR_046 Scenario:**
  ```
  Packing Sheet (before unmerging):
  ┌─────────┬──────────┬────────┬─────────┐
  │ Row     │ Part No. │ Qty    │ NW (KG) │
  ├─────────┼──────────┼────────┼─────────┤
  │ Row 23  │ 490DLF00 │ 200    │         │
  │         │          │        │  770.84 │ ← NW cell merged across rows 23-25
  │ Row 24  │ 490DPY10 │ 5018   │         │
  │ Row 25  │ 490DPY10 │ 750    │         │
  └─────────┴──────────┴────────┴─────────┘

  Problem: The merged NW cell (770.84) spans 3 rows containing 2 DIFFERENT part numbers:
    - Row 23: 490DLF00
    - Rows 24-25: 490DPY10

  The system cannot determine how to split 770.84 kg between 490DLF00 and 490DPY10.

  Error: [ERR_046] Different parts (490DLF00, 490DPY10) share merged NW/qty cell (rows 23-25)
  ```

  **Why ERR_046 before ERR_042:** Without this validation, rows 24-25 would have NW=0 after unmerging (only row 23 retains the value), causing the downstream error ERR_042 "Part '490DPY10' has qty but packing weight=0". ERR_046 identifies the root cause (merged cell with different parts) rather than the symptom (zero weight).

* **FR14:** **Error:** If a *Required Column* is missing, log specific error. If an *Optional Column* is missing, process continues.

### Data Extraction - Invoice (FR15-FR17)

* **FR15:** Invoice Number Extraction (Smart Label-First Strategy)

  **Pattern Definitions (field_patterns.yaml):**
  - `inv_no_cell.label_patterns`: Patterns to identify label cells (e.g., "Invoice No", "No. & Date of Invoice")
  - `inv_no_cell.patterns`: Patterns for embedded value extraction (label + value in same cell)
  - `inv_no_cell.exclude_patterns`: Patterns to reject non-invoice-number values (dates, label text, serials)

  **Method 1 (Label match):** Scan rows 2-15 for label patterns, then check adjacent cells
  - Find cell matching `inv_no_cell.label_patterns`
  - Check adjacent cells in order: right, right+1, below, below+1
  - **Adjacent cell evaluation priority:**
    1. **Pure label check (FIRST):** If cell matches label_pattern AND is a pure label → trigger recursive search from that cell
    2. **Exclude pattern check (SECOND):** If cell matches exclude_pattern → trigger extended search (right, then below)
    3. **Valid value check (THIRD):** If cell passes validation → return as invoice number

  **Pure Label Detection (CRITICAL):**
  - Purpose: Distinguish between label text and embedded invoice numbers
  - A cell is a "pure label" only if: (a) matches a label_pattern, AND (b) has < 3 alphanumeric characters remaining after removing keywords ("invoice", "inv", "no", "number", "date", "&", "of", punctuation, whitespace)
  - Pure labels: "Invoice No", "Invoice No:", "No. & Date of Invoice" → trigger **recursive search** (full 4-position scan)
  - Embedded values: "INVOICE NO. 6825090212", "Invoice No: ABC12345" → treated as invoice number values (not labels)
  - Example: E2="No. & Date of Invoice" → E3="Invoice No" (pure label) → recursive search from E3 → F3="NT251212001" (found)
  - **Recursion depth limit:** Maximum 3 levels of nesting to prevent infinite loops
  - **Implementation (CRITICAL - Keyword Removal Order):** When removing keywords to check if cell is pure label, keywords MUST be removed in length-descending order (longest first). This prevents partial matches where shorter keywords match inside longer ones.
    - Example: Keywords = {"invoice", "inv", "no", ...}
    - Text = "INVOICE NO："
    - WRONG order: Remove "inv" first → "oice no：" → "oice ：" → 4 chars remain → NOT pure label (BUG!)
    - CORRECT order: Remove "invoice" first → " no：" → " ：" → 0 chars remain → IS pure label ✓
    - Implementation: `sorted(LABEL_KEYWORDS, key=len, reverse=True)`

  **Extended Search (for excluded values):**
  - When adjacent cell matches `exclude_patterns` (e.g., "Date：", "2025-12-15 00:00:00")
  - Try cell to its right, then cell below
  - Each extended cell is also checked for pure labels or valid values

  **Method 2 (Embedded value):** Extract from cell containing both label and value
  - Uses `inv_no_cell.patterns` to match invoice number within label text
  - Example: "INVOICE NO.: 6825090212" → extract "6825090212" if it matches pattern
  
  **Logging:**
  - Format: `[INFO] Inv_No extracted ({method} of '{label}'): {inv_no} at '{cell_ref}'`
  - `{method}`: "embedded", "1 cell right", "2 cells right", "1 row below", "2 rows below", "nested label of '{nested_label}'"
  - Example: `[INFO] Inv_No extracted (nested label of 'Invoice No'): NT251212001 at 'F3'`

* **FR16:** System can handle combined invoices with multiple invoice numbers per sheet (via inv_no column in data rows)
  - **Priority (CRITICAL):** Per-row `inv_no` from data column takes precedence over header-extracted `inv_no`
  - **Fallback:** Header-extracted `inv_no` (FR15) is only used for items that have empty `inv_no` in the data column
  - **Implementation:** Extract per-row inv_no during item extraction, then only assign header inv_no to items where `item.inv_no` is empty
  - Example: File has header inv_no "F625081578" and data column with "F625081578" (rows 1-6) and "F625081579" (rows 7-16) → output preserves per-row values, not header value for all rows

* **FR17:** System can extract 13 per-item fields from invoice sheet (part_no, po_no, qty, price, amount, currency, coo, COD, brand, brand_type, model, inv_no, serial)
  - **Note:** weight is NOT extracted from invoice sheet; it is calculated by weight allocation (FR31-FR36)
  - **String fields:** Strip leading/trailing whitespace
  - **Field-Specific Precision + ROUND_HALF_UP (CRITICAL):** Numeric fields use defined decimal precision with ROUND_HALF_UP rounding:
    - **qty:** Use cell's displayed precision
    - **price:** Use fixed 5 decimal precision
    - **amount:** Use fixed 2 decimal precision
  - **ROUND_HALF_UP (rounding method):** 0.5 always rounds up (e.g., 0.125 → 0.13, not 0.12). Implementation uses epsilon trick: `round(value * 10^decimals + 1e-9) / 10^decimals` to avoid floating-point issues where 0.19995 is stored as 0.19994999...
  - **Cell format precision detection:** Read cell's `number_format` property, extract decimal places from format string (e.g., `0.00` → 2 decimals, `0.0000` → 4 decimals). If format is `General`, use fixed 5 decimals.
  - **Floating-point artifact elimination:** This rounding eliminates artifacts (e.g., `77.22000000000001` → `77.22`, `0.19995` with 4-decimal format → `0.2`)
  - **Unit suffix stripping:** Strip common unit suffixes (KG, KGS, PCS, EA, 件, 个) from numeric values before parsing (e.g., `4.95KG` → `4.95`)
  - **Leading blank rows (CRITICAL):** Skip blank rows between header row and data rows BEFORE checking stop conditions. This allows files with empty rows between header and first data row to be processed correctly.
    - **Processing order:** For each row after header: (1) Check if row is blank → skip and continue, (2) Check stop conditions → stop if matched, (3) Process data row
    - Example: Header at row 23, row 24 is blank, data starts at row 25 → row 24 is skipped, extraction starts at row 25
  - **Header continuation filtering:** Skip rows where part_no contains standalone header keywords: "part no" (handles sub-header rows being mistakenly extracted as data)
  - **Merged cell handling:** For data rows, propagate ALL string field values from merged cells to all rows in the merge range (see FR12)
  - **Data extraction stops:** When ANY of these conditions are detected:
    - part_no is empty AND qty = 0 (after first data row found)
    - part_no contains "total" (case-insensitive, e.g., "total", "total:", "Grand Total", "subtotal")
    - part_no contains footer keywords (报关行, 有限公司, etc.)
    -  **Any cell in first 10 columns (A-J)** contains "total", "合计", "总计", "小计" (handles TOTAL appearing in po_no or other columns)

### Data Extraction - Packing (FR18-FR25)

**Extraction Order:** Packing data extraction MUST happen before total row detection. This allows the system to determine `last_data_row` (the row number of the last extracted packing item) which is then used as the starting point for total row search.

* **FR18:** System can extract packing fields (part_no, qty, nw)
  - **Numeric fields qty:** Round to cell's display precision to eliminate floating-point artifacts
  - **Numeric fields nw (line-level):** Round to 5 decimal precision for internal calculations (allocation uses high precision)
  - **Unit suffix stripping:** Strip common unit suffixes (KG, KGS, PCS, EA, 件, 个) from numeric values before parsing
  - **Note:** Line-level `nw` differs from `total_nw` - see FR22 for total_nw precision handling

* **FR19:** System handles packing data row extraction:
  - **Leading blank rows:** Skip leading blank rows between header row and packing data rows
  - **Merged cell handling:** Use merged cell tracker to propagate part_no values for row detection
  - **Header continuation filtering:** Skip rows where part_no contains standalone header keywords: "part no"
  - **Pallet summary filtering:** Skip rows where part_no contains pallet keywords: "plt.", "plt ", "pallet" (case-insensitive)
  - **Empty part_no filtering:** Skip rows where part_no is empty (not valid packing data - cannot be matched to invoice items for weight allocation)
  - **No-weight-data row filtering:** Skip rows where qty=0 and nw=0 (rows with no meaningful weight data). These rows are skipped but do not terminate extraction.
    - Example: Row 25 has part_no="ABC", qty=6400, nw=14.27. Row 26 has part_no="ABC",qty=None, nw=None. Row 27 has qty=512, nw=1.14 → Row 26 is skipped, extraction continues to row 27.
  - **Data extraction stops:** At the first row where:
    - **Any cell in first 10 columns (A-J)** contains "total", "合计", "总计", "小计" (handles TOTAL appearing in description or other unmapped columns)
    - OR truly blank row (all key columns empty) after first data row is found
    - OR **implicit total row pattern** (empty part_no with numeric NW > 0 AND GW > 0) after first data row - this ensures FR21 Strategy 2 can find such rows
  - **Merged cell exclusion for implicit total detection (CRITICAL):** When checking for implicit total row pattern, the system MUST exclude rows where the part_no column is part of a merged cell range. These are continuation rows for multi-row items, NOT total rows.
    - **Rationale:** After unmerging, continuation rows have empty part_no cells (only the first row of the merge retains the value). Without this check, valid data rows are incorrectly identified as implicit total rows.
    - **Example:** Part_no merged across rows 23-25, each row has separate NW/GW values. After unmerging, rows 24-25 have empty part_no but valid weights. These must NOT trigger implicit total detection.
    - **Implementation:** Use MergeTracker to check if the part_no cell was part of a merged range before triggering implicit total row stop condition.
  - **Row processing order (CRITICAL):** For each row, check stop conditions (total keywords) BEFORE checking if row is blank. This ensures "TOTAL" in non-part_no columns (e.g., description column) triggers stop even when part_no column is empty.
    - Example: Row has empty part_no (col D) but "TOTAL" in description (col E) → must stop, not skip as blank

* **FR20:** System prevents double-counting of merged weight cells during extraction
  - When NW cells are merged across multiple packing rows, the weight value is only counted on the first row of the merged range
  - Subsequent rows of the merged range return 0.0 for weight aggregation purposes
  - **Example:** A merged NW cell showing 351kg spanning rows 23-24 contributes 351kg total (not 702kg)
  - **Implementation:** Uses `is_first_row_of_merge()` check during weight extraction
  - **Follows FR12 default:** Weight values are NOT propagated (per FR12 default behavior). Only first row counts for correct aggregation.

* **FR21:** System can detect total row using two-strategy approach:

  **Definition:** `last_data_row` is the row number of the last extracted packing item from FR18-FR19. This requires packing item extraction to complete first.

  **Strategy 1: Keyword Matching**
  Search for "TOTAL" keyword to identify the total row.
  - **Keywords:** Case-insensitive "total", "合计", "总计", "小计"
  - **Search columns:** First 10 columns (A-J)
  - **Search rows:** From last_data_row + 1 to last_data_row + 15

  **Strategy 2: Implicit Total Row Detection**
  If Strategy 1 fails, detect rows with empty part_no but numeric NW and GW values.
  - **Search rows:** From last_data_row + 1 to last_data_row + 15
  - **Condition:** The mapped `part_no` column (from FR9 column mapping) is empty AND both `nw` and `gw` columns have numeric value > 0
  - **Differentiation from Data Error:** This specific pattern triggers a valid STOP condition (Total Row). A row with empty `part_no` but *without* valid weights does NOT trigger this stop; it will be processed as a data row and subsequently fail validation (ERR_030) or be skipped if fully blank.
  - **Important:** Use the actual mapped part_no column index, NOT hardcoded column 1 (column A). The part_no column varies by vendor file (e.g., column A, C, or other).
  - **Merged cell exclusion (CRITICAL - see FR19):** Skip rows where the part_no column is part of a merged cell range. After unmerging, these continuation rows have empty part_no but are valid data rows, NOT total rows. Use MergeTracker to verify the cell was not part of a merged range before treating it as an implicit total row.
  - **Dependency on FR19:** FR19's stop conditions include the implicit total row pattern (with the same merged cell exclusion), ensuring extraction stops BEFORE actual total rows. This guarantees `last_data_row` is the actual last data row, not the total row itself.

  **Note:** SUM formula detection is not used because files are opened with `data_only=True` (FR2), which replaces formulas with calculated values.

* **FR22:** System can extract total_nw (total net weight) directly from the nw column on the total row.
  - **Embedded unit handling:** Weight cells may contain embedded units (e.g., "4.95KG", "100 KGS", "50.5 LB"). The system strips these unit suffixes before parsing:
    - Supported units: KG, KGS, G, LB, LBS (case-insensitive)
    - Examples: "4.95KG" → 4.95, "100 KGS" → 100, "50.5LB" → 50.5
  - **Visible Precision (CRITICAL - differs from line-level nw):**
    - `total_nw` and `total_gw` preserve the cell's **visible precision** based on the cell's number format
    - This precision is used for:
      1. Precision detection in weight allocation (FR30)
      2. Log display (FR25)
      3. Final validation comparisons
    - **Implementation (CRITICAL):** Read the cell's `number_format` property (e.g., `"0.00"`, `"0.000"`, `#,##0.00`) and extract decimal places from it:
      - **Complex Format Support:** Parse the format string to count the number of zero placeholders (`0`) after the decimal point (`.`). Ignore currency symbols, separators (`,`), and brackets. Matches include `0.00`, `#,##0.00`, `_($* #,##0.00_)`.
      - Round the raw float value to that precision using `ROUND_HALF_UP`
      - Each weight field (`total_nw`, `total_gw`) uses its OWN cell's number format independently
    - Examples:
      - Cell value `5421.735` with format `0.00` → store as `Decimal("5421.74")` (rounded to 2 decimals)
      - Cell value `212.5` with format `General` → store as `Decimal("212.5")` (no format-based rounding). **Note:** FR30's minimum-2-decimal rule still applies for precision detection — this value yields precision 2, not 1.
      - Cell value `83.848` with format `0.000` → store as `Decimal("83.848")` (3 decimals)
    - **Precision detection with embedded units (CRITICAL):** When format is `General` and cell contains a string with embedded unit suffix (e.g., "4.95KG"), strip the unit suffix BEFORE counting decimal places:
      - Cell value `"4.95KG"` with format `General` → strip "KG" first → "4.95" → detect 2 decimals (NOT 4)
      - Without stripping: "95KG" has length 4 → wrong precision
      - With stripping: "95" has length 2 → correct precision
    - **Contrast with line-level nw:** Line-level packing `nw` (FR18) uses 5 decimal precision for high-precision allocation calculations
  - **Floating-point artifact handling (CRITICAL):** When no number format is available (format is `General` or empty), round to 5 decimals first to clean up floating-point artifacts (e.g., `2.2800000000000002` → `2.28`, `199.23999999999992` → `199.24`), then normalize to remove trailing zeros.

* **FR23:** System can extract total_gw (gross weight) from total row area, checking for packaging weight additions.
  - Some vendors place additional packaging weight calculations below the total row
  - **Packaging weight detection:** After extracting GW from total row, check +1 and +2 rows in the same GW column:
    - If both +1 and +2 rows have numeric values, use +2 row as the final total_gw
    - This handles cases where pallet weight is added below the total row (row +1 = pallet weight, row +2 = final total)
    - Example: Total row GW = 1768.5, row +1 = 70 (pallet), row +2 = 1838.5 → use 1838.5 as total_gw
  - **Embedded unit handling:** Weight cells may contain embedded units (e.g., "6.33KG", "100 KGS", "50.5 LB"). The system strips these unit suffixes before parsing:
    - Supported units: KG, KGS, G, LB, LBS (case-insensitive)
    - Examples: "6.33KG" → 6.33, "100 KGS" → 100, "50.5LB" → 50.5
  - **Visible Precision:** Same as FR22 - `total_gw` preserves cell's visible precision based on number format. Extract decimal places from format and round accordingly.

* **FR24:** System can extract total_packets using multi-priority search:

  **Supported Packet Value Formats (applies to ALL priorities):**
  When extracting packet values, the system handles these formats:
  - **Pure numeric:** `7`, `12`, `100`
  - **With unit suffix:** `7CTNS`, `10CTN`, `30箱`, `50件`, `12托`, `5PCS`
  - **With unit suffix and additional text:** `30箱(兩托)`, `7CTNS (2 pallets)` - extract leading number before unit
  - **Embedded in PLT indicator:** `7 PLT.G`, `PLT.G 5`, `1 PLT.G`
  - **Embedded in Chinese text:** `共7托`, `172件`, `包装种类：再生托板7托`

  The system extracts the leading number followed by optional unit suffix, ignoring any trailing text (e.g., `30箱(兩托)` → `30`).

  - **Column Search Range:** Columns A through (NW column + 2), minimum 11
    - Example: If NW is in column K (11), search columns A-M (1-13)
  - **Priority 1:** Packet/Carton Label - search total row +1 to +3 rows below
    - **Labels:** "件数", "件數"
    - **Value extraction (IMPORTANT - search relative to label position):**
      1. **Adjacent value:** Look for value in the cell immediately to the right of the label (label_col + 1), then try up to 3 more columns to the right. Parse with unit suffix stripping (e.g., `7CTNS` → `7`)
      2. **Embedded value:** If no adjacent value found, extract number from the label cell itself (e.g., "件数: 7" → 7)
    - **Note:** Do NOT search in fixed columns like NW column; always search relative to where the label was found
  - **Priority 2:** "PLT.G"/"PLT. G" Indicator - search at `total_row - 1` or `total_row - 2`
    - **Pattern matching (CRITICAL - handle both formats):**
      1. **Number-before-PLT format:** Match `^\d+\s*PLT\.?\s*G?$` (e.g., `7 PLT.G`, `1 PLT.G`) → extract leading number
      2. **PLT-before-number format:** Match `^PLT\.?\s*G` (e.g., `PLT.G 5`) → check adjacent cell to the right
    - **Value extraction:** For number-before format, extract from the matched cell itself. For PLT-before format, check cell immediately to the right of the indicator (indicator_col + 1)
  - **Priority 3:** Below Total Row Patterns - search +1 to +3 rows below total row
    - **Pattern Check Order (CRITICAL):** Check patterns in this exact order:
      1. **Total with breakdown pattern:** Number followed by parenthesis, e.g., "348（256胶框+92纸箱）" → extract leading number (348), NOT numbers inside parens. The leading number is the total; numbers inside are the breakdown.
      2. **Unit-suffix patterns:** "7托", "30箱", "50件", "55 CTNS"
      3. **Embedded Chinese patterns:** "共7托" → extract 7, "172件" → extract 172
      4. **Pallet range patterns:** "PLT#1(1~34)" → extract pallet count (1)
    - **Pallet vs Box Priority:** When both pallet (托) and carton (件/箱) appear in same text (e.g., "共7托（172件）"), extract pallet count (7), not carton count (172)
  - **Validation:** Must be positive integer in range 1-1000

**PackingTotals Field Classification:**

| Field         | Required | If Missing                   |
|---------------|----------|------------------------------|
| total_nw      | Yes      | Error - Required for output  |
| total_gw      | Yes      | Error - Required for output  |
| total_packets | No       | Warning                      |

* **FR25:** System logs packing totals with **visible precision** (trailing zeros removed):
  - Format: `[INFO] Packing total row at row {row}, NW= {nw}, GW= {gw}, Packets= {packets}`
  - NW and GW display the cell's visible precision (e.g., `212.5` not `212.50000`, `4305.72` not `4305.72000`)
  - Examples: `NW= 14.699`, `NW= 212.5`, `NW= 50.0`, `GW= 38.04`

### Data Transformation (FR26-FR28)

* **FR26:** System cleans 'po_no' values by removing suffix starting from first "-", ".", or "/" delimiter.
  - Examples: `2250600556-2.1` → `2250600556`, `PO32741.0` → `PO32741`, `PO12345/1` → `PO12345`

* **FR27:** System cleans invoice numbers (remove "INV#" and "NO." prefix)
  - **Implementation Note:** Cleaning is applied at extraction time (not transformation phase) for both sources:
    1. Header area extraction (FR15) - cleaned before logging and storage
    2. Data row extraction (inv_no column) - cleaned before storage
  - This ensures log messages display cleaned values and extracted data is consistent

* **FR28:** System standardizes codes using lookup tables in `\config` folder:
  - 'currency' codes using `currency_rules.xlsx`
  - 'coo' codes using `country_rules.xlsx`
  - **COD Override (CRITICAL):** When the COD column exists and a row's COD field has a non-empty value, use the COD value to replace the COO value for that invoice line BEFORE standardization. This allows vendors to specify a different country of origin at the line-item level.
    - Example: Row has coo="CHINA", cod="TAIWAN" → use "TAIWAN" as the COO value for standardization
    - Example: Row has coo="CHINA", cod="" (empty) → keep "CHINA" as the COO value
  - **Placeholder Values:** The following values in COO or COD fields should be treated as empty (not triggering ATT_004 warning):
    - Single or multiple asterisks: `*`, `**`, `***`, `****`, etc.
    - Slash placeholders: `/`, `//`
    - Dash placeholders: `-`, `--`
    - Common null indicators: `N/A`, `NA`, `NONE`, `NULL`
    - Example: Row has coo="CHINA", cod="/" → "/" is treated as empty, keep "CHINA" as the COO value
    - Example: Row has coo="****", cod="" → "****" is treated as empty, COO becomes empty string
  - **Normalization:** Multi-step lookup with progressive normalization:
    1. Try original value (uppercase, trimmed)
    2. Try with ALL internal whitespace removed (e.g., `MADE IN CHINA` → `MADEINCHINA`)

### Weight Allocation (FR29-FR35)

**Algorithm Steps:**

**Step 1: Precision Detection**
- **Input**: `total_nw` (total net weight from packing sheet, already rounded per FR22 cell format precision)
- **Process**: Analyze decimal places from the rounded `total_nw` value
- **Output**: Base precision (N) - minimum 2, maximum 5 decimal places
- **Example**: `45.23` → precision 2, `1.955` → precision 3, `100.0` → precision 2 (minimum), `100` (integer) → precision 2 (minimum). **Clarification:** FR22 preserves visible precision for display/storage, but FR30's minimum-2-decimal floor always governs weight allocation precision. When `General` format yields fewer than 2 decimal places (e.g., integer `100` or `212.5`), the minimum 2 applies.

**Step 2: Weight Aggregation**
- **Process**: Sum all packing item weights grouped by `part_no`
- **Validation**: Check for zero or negative aggregated weights
- **Output**: Dictionary mapping `part_no` → total weight

**Step 3: Precision Determination**
- **Process**: Test if rounded packing weights sum to `total_nw`
  - Try base precision (N)
  - If no match, try precision N+1
  - Use precision N+1 with remainder adjustment if needed
- **Output**: Optimal packing precision (N or N+1)

**Step 4: Rounding & Adjustment**
- **Process**:
  - Round all part weights to packing precision
  - If any weight rounds to zero, increase precision
  - Adjust last part weight to ensure sum equals `total_nw` exactly
- **Output**: Rounded weights per part that sum to `total_nw`

**Step 5: Proportional Allocation**
- **Process**: For each `part_no`:
  - Find all invoice items matching the part
  - Calculate total quantity for the part
  - Allocate weight proportionally: `weight = total_weight × (item_qty / total_qty)`
  - Round to line precision (packing precision + 1)
  - Apply remainder to last invoice item
- **Output**: Invoice items with allocated weights

**Step 6: Validation**
- **Process**: Verify total allocated weight equals `total_nw`
- **Output**: Success/failure status with error messages

---

* **FR29:** System can aggregate packing item weights by `part_no` and validate data integrity before allocation. Returns error if any aggregated weight is zero or negative.

* **FR30:** System validates packing weights sum BEFORE allocation, then detects decimal precision.
  - **Pre-allocation validation (CRITICAL):** Before any rounding or adjustment, compare sum of extracted packing weights against total_nw. If difference > 0.1, fail immediately with ERR_047. This catches data issues early (e.g., missing packing rows, wrong total row).
  - Detects base precision from `total_nw` value (minimum 2 decimals, maximum 5 decimals)
  - Returns error if total_nw is non-numeric or invalid format
  - **Precision Selection Algorithm (two separate conditions):**
    - **Normal (sum matching):** Try N → if perfect match, stop. Try N+1 → if perfect match, stop. Else use N+1 with adjustment (dchecko   NOT try N+2 for sum matching).
    - **Zero check:** If any weight rounds to zero → increase precision (N+1, N+2, ... up to max 5). Stop at first precision with no zeros (do NOT continue for better sum match).

* **FR31:** System can round packing weights to determined precision and adjust the last part's weight to ensure aggregated packing weights sum exactly to `total_nw`.

* **FR32:** System can allocate weights to invoice items proportionally based on quantity ratios, with remainder assigned to the last invoice item per part.

* **FR33:** System can validate part-level weight allocation (allocated = packing total per part, **EXACT match required**)

* **FR34:** System can validate global weight (grand total = extracted total_nw, **EXACT match required**)

**Precision Rules:**
- `total_nw` precision: N (base, detected from value)
- Packing weights precision: N or N+1 (determined dynamically)
- Invoice item weights precision: packing precision + 1

**Logging Messages (MUST output these messages in exact format):**
- `[INFO] Trying precision: {try_precision}`
- `[INFO] Expecting rounded part sum: {rounded_sum}, Target: {grand_total}`
- `[INFO] Perfect match at {try_precision} decimals`
- `[INFO] Can't find perfect match at {base_precision+1} decimals, but use it with part adjustment`
- `[INFO] Adjusting last part weight to match total_nw`
- `[WARNING] Packing weight is rounded to zero for part '{part_no}', need to change to {packing_precision+1} decimals`
- `[INFO] Weight allocation complete: {total_nw}`

* **FR35:** Weight Allocation Error Messages:
  - `[ERR_033] Precision detection failed: total_nw '{total_nw}' is not a valid number`
  - `[ERR_040] Part '{part_no}' in invoice but not in packing`
  - `[ERR_041] Weight allocation mismatch: allocated {allocated} != total {total_nw}`
  - `[ERR_042] Part '{part_no}' has qty but packing weight=0`
  - `[ERR_043] Part '{part_no}' in packing sheet not found in invoice`
  - `[ERR_044] Part '{part_no}' weight rounds to zero even at maximum 5 decimal precision`
  - `[ERR_045] Total quantity for part '{part_no}' is zero`
  - `[ERR_046] Different parts ({parts_str}) share merged NW/qty cell (rows {min_row}-{max_row})`
  - `[ERR_047] Packing weights sum ({sum}) disagrees with total_nw ({total_nw}), difference: {diff}` (threshold: 0.1)

### Validation & Exception Logic (FR36-FR41)

* **FR36:** System validates configuration files at startup:
  - Validates `currency_rules.xlsx` exists and is readable
  - Validates `country_rules.xlsx` exists and is readable
  - Checks for duplicate codes in lookup tables (if found, halt with error code ERR_003)
  - Checks for malformed Excel files (if corrupted, halt with error code ERR_004)
  - Validates `output_template.xlsx` exists and has correct structure (40 columns A-AN, rows 1-4 headers)

* **FR37:** System performs validation before generating output, with strict classification rules:

  **Field Classification:**
  - **Invoice extraction fields (REQUIRED):** part_no, po_no, qty, price, amount, currency, coo, brand, brand_type, model
  - **Invoice extraction fields (OPTIONAL):** inv_no (column), serial
  - **Packing totals (REQUIRED):** total_nw, total_gw
  - **Packing totals (OPTIONAL):** total_packets

  **Output generation fields (REQUIRED - must have value from any source):**
  - `inv_no`: From invoice column OR header area extraction (FR15)
  - `weight`: From weight allocation (FR31-FR36), NOT from invoice extraction

  **Field Validation Classifications:**

  **Required Fields (empty = ERR_030, FAILED):**
  All fields with `required: true` in field_patterns.yaml must have non-empty values:
  - Invoice: part_no, po_no, qty, price, amount, currency, coo, brand, brand_type, model
  - Packing: part_no, qty, nw, gw
  - Empty value in ANY required field → ERR_030 "Empty required field: {field} at row {row}"

  **COO/COD Exception (CRITICAL):** When validating `coo` as required:
  - If `coo` is empty BUT `cod` has a non-empty, non-placeholder value → do NOT report ERR_030 for coo
  - Reason: FR28 COD Override will use `cod` value in place of `coo` during transformation
  - This validation exception must be applied BEFORE transformation occurs
  - Example: Row has empty COO but COD="CN" → validation passes, transformation uses "CN" for country

  **Empty Value Definition (CRITICAL):** A field value is considered empty if ANY of:
  - Value is `None`/null (cell has no value or was not extracted)
  - Value is an empty string `""`
  - Value contains only whitespace `"   "`

  **Note:** Numeric fields (qty, price, amount) are validated separately for NaN/Inf (ERR_031), not for "empty" since they default to 0.0 during extraction.

  **Implementation (CRITICAL - Two-Level Validation):**
  Required field validation happens at TWO levels - both must pass:
  1. **Column header detection (FR8/FR14):** Header pattern must match → ERR_020 if column not found
  2. **Data row validation (FR37):** Each extracted data row must have non-empty values → ERR_030 if empty

  A column can have a valid header but empty data in all rows. This is a DATA error (ERR_030), not a column mapping error (ERR_020). The system must call `validate_required_fields()` on extracted invoice items AFTER extraction and BEFORE weight allocation.

  Example: File has "型号" (model) header in column 14, but all data rows have empty values in that column:
  - Column mapping: SUCCESS (header "型号" matches model pattern)
  - Data validation: FAILED with ERR_030 "Empty required field: model at row 23"

  **Optional Fields (no error if missing):**
  - Invoice: inv_no (fallback to header extraction), serial
  - Packing: pack

  **Standardization Fields (non-empty but unmapped = ATTENTION):**
  - currency: If value exists but NOT in currency_rules.xlsx → ATT_003 (output still generated)
  - coo: If value exists but NOT in country_rules.xlsx → ATT_004 (output still generated)
  - **CRITICAL DISTINCTION:** Empty currency/coo = ERR_030 (FAILED), non-empty but unstandardized = ATT_003/ATT_004 (ATTENTION)

  **Status Classification Rules:**

  **Status = FAILED (Do NOT generate output file):**
  - Empty value in ANY required field (ERR_030)
  - Invalid data type (non-numeric qty/price/amount) (ERR_031)
  - Part number mismatch between invoice and packing (ERR_040/ERR_043)
  - Weight allocation failed (ERR_041-ERR_047)
  - Missing total_nw or total_gw (ERR_033/ERR_034)
  - ANY ERR_xxx code triggers FAILED status

  **Status = ATTENTION (Generate output file, flag for manual review):**
  - **ONLY these 3 specific ATT_xxx cases:**
    1. Missing total_packets (ATT_002) - optional field
    2. Currency value exists but NOT in currency_rules.xlsx (ATT_003) - unstandardized
    3. COO value exists but NOT in country_rules.xlsx (ATT_004) - unstandardized
  - Output file IS generated with available data
  - User must manually verify flagged fields in output

  **Status = SUCCESS:**
  - ALL required fields present and non-empty
  - ALL numeric fields valid
  - Currency and COO successfully standardized (found in lookup tables)
  - Weight allocation exact match achieved
  - No ERR_xxx or ATT_xxx codes

* **FR38:** System generates output file for both SUCCESS and ATTENTION status (not for FAILED)

* **FR39:** System logs detailed validation results including:
  - Which specific field caused failure
  - Expected vs actual data type
  - Suggested corrections for unstandardized values

* **FR40:** System uses the following **Error Code Catalog** for consistent error reporting:

**Startup Errors (Exit Code 2 - Halt before processing):**

| Code | Description | Cause | Resolution |
|------|-------------|-------|------------|
| ERR_001 | Configuration file not found | `field_patterns.yaml` missing from config folder | Restore config file from installation |
| ERR_002 | Invalid regex pattern | Syntax error in pattern definition | Fix regex syntax in field_patterns.yaml |
| ERR_003 | Duplicate lookup code | Same code mapped to multiple values in currency_rules.xlsx or country_rules.xlsx | Remove duplicate entries |
| ERR_004 | Malformed Excel file | currency_rules.xlsx, country_rules.xlsx, or output_template.xlsx corrupted | Replace corrupted file |
| ERR_005 | Template structure invalid | output_template.xlsx missing required columns (A-AN) or header rows (1-4) | Restore template from installation |

**File-Level Errors (Status = FAILED):**

| Code | Description | Cause | Resolution |
|------|-------------|-------|------------|
| ERR_010 | File locked | Excel file open in another application | Close file in Excel and retry |
| ERR_011 | File corrupted | Cannot read Excel file structure | Request new file from vendor |
| ERR_012 | Invoice sheet not found | No sheet matches invoice_sheet.patterns | Add pattern to field_patterns.yaml or check file |
| ERR_013 | Packing sheet not found | No sheet matches packing_sheet.patterns | Add pattern to field_patterns.yaml or check file |
| ERR_014 | Header row not found | No row in range 7-30 has ≥7 valid column headers | Check file structure, may need manual processing |

**Column Mapping Errors (Status = FAILED):**

| Code | Description | Cause | Resolution |
|------|-------------|-------|------------|
| ERR_020 | Required column missing: {field} | Column header not matched by any pattern | Add pattern for this vendor's header format |
| ERR_021 | Invoice number not found | No inv_no in header area or data columns | Check file for invoice number location |

**Data Extraction Errors (Status = FAILED):**

| Code | Description | Cause | Resolution |
|------|-------------|-------|------------|
| ERR_030 | Empty required field: {field} | Required field has no value in data row | Vendor file incomplete, request correction |
| ERR_031 | Invalid numeric value: {field} | Non-numeric value in qty/price/amount | Check for text in numeric columns |
| ERR_032 | Total row not found | Cannot locate TOTAL keyword or numeric pattern | Check packing sheet structure |
| ERR_033 | Invalid total_nw | total_nw is 0, negative, or non-numeric | Verify packing sheet total row |
| ERR_034 | Invalid total_gw | total_gw is 0, negative, or non-numeric | Verify packing sheet total row |

**Weight Allocation Errors (Status = FAILED):**

| Code | Description | Cause | Resolution |
|------|-------------|-------|------------|
| ERR_040 | Part not in packing | Part number exists in invoice but not in packing | Verify part numbers match between sheets |
| ERR_041 | Weight allocation mismatch | Allocated weights sum doesn't match total_nw | Check for data entry errors in weights |
| ERR_042 | Zero packing weight | Part has quantity but packing weight=0 | Ensure part has weight data in packing sheet |
| ERR_043 | Packing part not in invoice | Part exists in packing but not found in invoice | Verify part numbers match between sheets |
| ERR_044 | Weight rounds to zero | Part weight rounds to zero even at max 5 decimal precision | Weight value too small to represent |
| ERR_045 | Zero quantity for part | Total quantity for part is zero, cannot allocate weight | Verify quantity values in invoice |
| ERR_046 | Different parts share merged weight | Different part_no values share the same merged NW/qty cell (e.g., NW cell merged across rows 23-25, but row 23 has part A and rows 24-25 have part B) | Vendor must separate weight cells so each part has its own weight value |
| ERR_047 | Packing sum mismatch | Sum of extracted packing weights differs from total_nw by more than 0.1 (validated BEFORE allocation) | Check for missing packing rows, duplicate weights, or wrong total row detected |

**Attention Codes (Status = ATTENTION - Output generated):**

| Code | Description | Cause | Resolution |
|------|-------------|-------|------------|
| ATT_002 | Missing total_packets | Cannot extract packet count from packing sheet | Manually verify packet count in output |
| ATT_003 | Unstandardized currency: {value} | Currency value not in currency_rules.xlsx | Add mapping or manually correct in output |
| ATT_004 | Unstandardized COO: {value} | COO value not in country_rules.xlsx | Add mapping or manually correct in output |

* **FR41:** When an error or warning occurs, the system logs both the error code and the descriptive message in format: `[ERR_xxx] {message}` or `[ATT_xxx] {message}`.
  - **Single-point logging (CRITICAL):** Each error/warning must be logged exactly ONCE at the point of detection:
    - Phase functions (extraction, allocation, etc.) log errors when they detect them
    - Main orchestrator does NOT re-log errors already logged by phase functions
    - This prevents duplicate error messages in console output
  - **Implementation pattern:** When phase functions return errors/warnings that were already logged:
    - The phase function calls `log_error_code()` or `log_warning_code()` at detection
    - The phase function returns the error/warning in a list for accumulation
    - Main orchestrator adds to ValidationResult with `log=False` to prevent duplicate logging
    - Example: `validation_result.add_warning(code, msg, log=False)`
  - **Example:** If `extract_packing_totals()` detects ATT_002 and logs it, `main.py` must use `add_warning(..., log=False)` when accumulating the warning

### Output Generation (FR42-FR46)

* **FR42:** System can populate 40-column output template `output_template.xlsx` (columns A to AN) read only. Write a standardized Excel output file in the `\data\finished` folder.
  - **Output filename format (CRITICAL):** `{original_vendor_filename}_template.xlsx`
    - Uses the original input filename (without extension), NOT the extracted invoice number
    - Example: Input file `12.09鋐利-中磊( 进口）-蜂鸣器.xlsx` → Output file `12.09鋐利-中磊( 进口）-蜂鸣器_template.xlsx`
    - Example: Input file `中磊出货资料1211.xlsx` → Output file `中磊出货资料1211_template.xlsx`
    - Example: Input file `old_vendor_data.xls` → Output file `old_vendor_data_template.xlsx`
    - **Note:** Any file extension (`.xls` or `.xlsx`) is stripped before appending `_template.xlsx`.
  - **Filename sanitization:** Invalid filename characters (`<>:"/\|?*`) are replaced with underscores
  - **Template preservation (CRITICAL):** Load a fresh copy of the template for each output file to preserve:
    - Sheet name (e.g., "工作表1" from template, not default "Sheet")
    - All formatting, styles, column widths, and other Excel properties
  - **Note:** The extracted invoice number is still used in the output DATA (column N), just not in the output filename

* **FR43:** System can preserve fixed headers in rows 1-4

* **FR44:** System can write invoice line items starting at row 5
  - **Row Order Preservation (CRITICAL):** Invoice items MUST be written in the same order as they appear in the source invoice sheet. The weight allocation algorithm must NOT reorder items by part_no or any other criteria. Items with the same part_no may appear in non-consecutive rows in the source - this order must be preserved in output.
  - Example: If source invoice has rows [Part_A, Part_B, Part_A, Part_C], output must have same order [Part_A, Part_B, Part_A, Part_C], NOT grouped as [Part_A, Part_A, Part_B, Part_C]

* **FR45:** System can apply fixed values and file-level totals per consolidated template mapping

* **FR46:** System uses the following **Consolidated 40-Column Output Template Mapping**:

**COMPLETE OUTPUT TEMPLATE SCHEMA (Columns A-AN, 40 total columns)**

| Column | Field Name | Source | Value Type | Notes |
|--------|------------|--------|------------|-------|
| A | `part_no` | Invoice | String | Part number from invoice sheet |
| B | `po_no` | Invoice | String | Cleaned PO number |
| C | `FIXED_EXEMPTION_METHOD` | Fixed | `"3"` | Constant value for all rows |
| D | `currency` | Invoice | Numeric Code | Standardized to code |
| E | `qty` | Invoice | Numeric | Quantity |
| F | `price` | Invoice | Numeric | Unit price |
| G | `amount` | Invoice | Numeric | Total amount |
| H | `coo` | Invoice | Numeric Code | Country of Origin - standardized |
| I-K | `[Reserved]` | N/A | Empty | Reserved columns |
| L | `serial` | Invoice | String | Item Serial |
| M | `weight` | Invoice or Allocated | Numeric | Net weight from invoice or weight allocation |
| N | `inv_no` | Invoice | String | Invoice number extracted |
| O | `[Reserved]` | N/A | Empty | Reserved column |
| P | `total_gw` | Packing | Numeric | **Row 5 ONLY** - Total gross weight from packing sheet |
| Q | `[Reserved]` | N/A | Empty | Reserved column |
| R | `FIXED_DESTINATION_REGION` | Fixed | `"32052"` | Constant value for all rows |
| S | `FIXED_ADMIN_CODE` | Fixed | `"320506"` | Constant value for all rows |
| T | `FIXED_DESTINATION_COUNTRY` | Fixed | `"142"` | Constant value for all rows |
| U-AJ | `[Reserved]` | N/A | Empty | Reserved columns (16 columns) |
| AK | `total_packets` | Packing | Numeric | **Row 5 ONLY** - Total packages from packing sheet |
| AL | `brand` | Invoice | String | Brand name |
| AM | `brand_type` | Invoice | String | Brand specification |
| AN | `model` | Invoice | String | Model number |

**Key Notes:**
- **Row 5 Special Fields:** `total_gw` (P5) and `total_packets` (AK5) are written ONLY in row 5 (first data row)
- **Fixed Values:** Columns C, R, S, T contain constant values for all data rows
- **Reserved Columns:** Empty columns maintained for template compatibility
- **Data Rows:** Start at row 5, one row per invoice line item

### Result Classification (FR47-FR51)

> **Classification Rules:** See FR37 for detailed field classification and status determination criteria.

* **FR47:** System classifies each file into exactly one status: SUCCESS, ATTENTION, or FAILED

* **FR48:** System determines status based on validation results collected during processing (per FR37 criteria)

* **FR49:** System tracks which specific fields/conditions triggered ATTENTION or FAILED status

* **FR50:** System includes status in per-file console output with emoji indicator:
  - SUCCESS → `✅ SUCCESS`
  - ATTENTION → `⚠️ ATTENTION`
  - FAILED → `❌ FAILED`

* **FR51:** System aggregates status counts for batch summary reporting

### Error Recovery (FR52-FR58)

* **FR52:** System can halt on invalid configuration with exit code 2 (before processing)

* **FR53:** System can handle file access errors:
  - **File locked/in-use** → Log ERROR, skip file, add to error list, continue batch
  - **File corrupted** → Log ERROR, skip file, add to error list, continue batch

* **FR54:** System can handle Phase 1 (Structure) errors, after getting column mapping:
  - Missing required column (header not matched) → Collect errors, mark FAILED
  - Missing optional column → Silently ignored

* **FR55:** System can handle Phase 2 (Data) errors, before writing output:
  - Part mismatch (invoice vs packing) → Collect error, mark FAILED
  - Missing required field value → Collect error, mark FAILED
  - Missing total_packets → Collect warning, mark ATTENTION
  - Unstandardized currency/country → Collect warning, mark ATTENTION

* **FR56:** System reports batch results in this order (summary first for quick overview):
  1. **BATCH PROCESSING SUMMARY** - counts and timing (appears first)
  2. **FAILED FILES** - detailed error list (if any)
  3. **FILES NEEDING ATTENTION** - detailed warning list (if any)

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

* **FR57:** System can report failed files in the FAILED FILES section (after batch summary):
  - List each file with its error messages
  - Multiple same-code errors within a file are condensed to one line with "(N occurrences)"
  - **Representative part_no:** When condensing part-specific errors, show the first encountered part_no as a representative example (e.g., `Part 'ABC123'`), NOT a placeholder like `'...'`
```
[ERROR] FAILED FILES:
[ERROR] --------------------------------------------------------------------------
[ERROR] * vendor_file_1.xlsx
[ERROR]     [ERR_043] Part 'ABC123' in packing sheet not found in invoice (10 occurrences)
[ERROR] * vendor_file_2.xlsx
[ERROR]     [ERR_020] Required column missing: brand_type
[ERROR] * vendor_file_3.xlsx
[ERROR]     [ERR_020] Required column missing: brand_type
[ERROR] --------------------------------------------------------------------------
```

* **FR58:** System can report attention files in the FILES NEED ATTENTION section in batch summary:
  - List each file with its warning messages
```
[WARNING] FILES NEEDING ATTENTION:
[WARNING] ------------------------------------------------------------------------
[WARNING] * another_vendor_1.xlsx
[WARNING]     [ATT_002] total_packets not found or invalid, please verify manually in output
[WARNING] * another_vendor_2.xlsx
[WARNING]     [ATT_002] total_packets not found or invalid, please verify manually in output
[WARNING] ------------------------------------------------------------------------
```

### Diagnostic Mode (FR59)

* **FR59:** System provides diagnostic mode via `--diagnose <filename>` command-line flag for troubleshooting pattern matching issues
  - **Execution:** Process single file in diagnostic mode, do not write output
  - **Output Format (console):**
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
  - **Behavior:** Show ALL attempted pattern matches (success and failures)
  - **Suggestions:** Analyze unmatched columns and suggest regex patterns based on actual header text
  - **Note:** Diagnostic mode uses plain text output (no emojis) for maximum Windows console compatibility. This restriction does NOT apply to regular batch processing status output (FR50), which includes emoji indicators.
  - **Exit code:** 0

### Logging & Reporting (FR60-FR64)

* **FR60:** System displays real-time processing status to console (see **Console Output Format** section for full examples)
  - **Startup banner:** `[INFO] =================================================================` then `[INFO]                     AutoConvert v{version}` centered, then `=` line again
  - **Startup info:** Log `[INFO] Input folder: {path}`, `[INFO] Output folder: {path}`, `[INFO] All regex patterns validated and compiled successfully`, `[INFO] Loaded {N} currency rules, {N} country rules`, `[INFO] Found {N} Excel file(s) to process`
  - **Per-file separator:** `[INFO] -----------------------------------------------------------------` before each file
  - **Per-file progress:** `[INFO] [{n}/{total}] Processing: {filename} ...`
  - **Output confirmation:** `[INFO] Output successfully written to: {filename}_template.xlsx`
  - **Immediate logging:** Errors/warnings logged at moment of detection, before final status
  - **Library warning suppression:** Suppress third-party library warnings (e.g., openpyxl header/footer parsing warnings) to keep console output clean

* **FR61:** System displays batch summary (Success/Attention/Failed counts) at end of processing

* **FR62:** System writes detailed processing log to file
  - **Log file:** `process_log.txt` in project root (rewritable each run)
  - **File format:** `[HH:MM] [LEVEL] message` with DEBUG/INFO/WARNING/ERROR levels
  - **File encoding:** UTF-8 with BOM

* **FR63:** Log includes: field mappings, transformation steps, allocation steps, and validation results
  - **Single-Point Logging (CRITICAL):** Each log message must be emitted from exactly ONE location in the code
    - Either the module performing the action logs it, OR the orchestrator (`main.py`) logs it - never both
    - Phase functions (extraction, allocation, output) should own their logging
    - Main orchestrator should NOT re-log actions already logged by phase functions
    - Example: `extract_invoice_items()` logs "Invoice sheet extracted N items" → `main.py` must NOT log this again
  - **Rationale:** Prevents duplicate messages in console output and log file

* **FR64:** System pauses at end of batch for user review (when double-clicked)

* **FR65:** Console output uses UTF-8 encoding:
  - Set `PYTHONIOENCODING=utf-8` at startup or reconfigure stdout/stderr with UTF-8 encoding
  - Use `errors='replace'` fallback for any characters that cannot be displayed
  - Log file always uses UTF-8 with BOM for full Unicode support

### Integration (FR66)

* **FR66:** System entry point (`__main__.py`) must wire to batch processor and execute the full processing pipeline.
  - Initializes logging
  - Loads and validates configuration
  - Discovers files in data folder
  - Processes each file through complete pipeline
  - Generates batch summary
  - Returns appropriate exit codes:
    - **Exit code 0:** All files processed with no FAILED status. This includes batches with a mix of SUCCESS and ATTENTION results.
    - **Exit code 1:** At least one file has FAILED status.
    - **Exit code 2:** Configuration error — halted before processing any files.


## Non-Functional Requirements

### Performance

- **NFR1:** System processes individual files in <30 seconds average
- **NFR2:** System handles batch sizes of 20+ files without memory issues
- **NFR3:** System starts up and is ready to process within 5 seconds
- **NFR4:** Pattern matching completes within 2 seconds per sheet

### Reliability

- **NFR5:** System achieves 0% false positive rate (bad files never marked "Success")
- **NFR6:** System gracefully handles malformed Excel files without crashing
- **NFR7:** System continues processing remaining files after individual file failures
- **NFR8:** System produces consistent results for identical input files

### Compatibility

- **NFR9:** System runs on Windows 10 and Windows 11 without additional dependencies
- **NFR10:** System processes both .xls (legacy) and .xlsx (modern) Excel formats
- **NFR11:** System handles Excel files created by different applications (Microsoft Excel, LibreOffice, WPS)
- **NFR12:** System supports file paths containing Unicode characters (Chinese folder/file names)

### Maintainability

- **NFR13:** IT Admin with basic regex knowledge can add new patterns via YAML editing
  - **Skill level:** Understands regex basics (wildcards, character classes, optional groups)
  - **Support tools:** Diagnostic mode (FR61) provides pattern suggestions based on actual vendor files
  - **Pattern library:** System ships with comprehensive pattern examples covering common variations
  - **Documentation:** User guide includes regex reference section with logistics-domain examples
- **NFR14:** Pattern changes take effect on next application restart (no recompilation required)
  - **Mechanism:** Patterns loaded from `field_patterns.yaml` at startup
  - **No hot-reload:** Changes require restart to take effect
- **NFR15:** Log files provide sufficient detail to diagnose processing failures
- **NFR16:** Error messages include actionable information (file name, field name, error code)

### Distribution

- **NFR17:** Python CLI tool runs via `uv run autoconvert` with Python 3.11+ and uv package manager
- **NFR18:** Standalone executable size remains under 30 MB
- **NFR19:** System operates fully offline (no network dependencies)
- **NFR20:** Executable is single-file distribution (no installer required)
- **NFR21:** Both CLI and executable provide identical functionality and command-line interface

