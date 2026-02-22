---
stepsCompleted: ['step-01-init', 'step-02-discovery', 'step-03-journeys', 'step-04-requirements', 'step-05-specifications', 'step-06-complete']
outputPath: 'docs/PRD.md'
---

# Product Requirements Document - AutoConvert

**Author:** Liou
**Date:** 2026-02-20

---

## 1. Overview

### Vision

A CLI tool that automates conversion of vendor Excel files into standardized customs reporting templates using a fully deterministic, configuration-driven approach — no AI or heuristic guessing. 

Sheet identity is resolved by keyword presence in sheet names, columns are mapped via strict regex synonym lists defined in `config/field_patterns.yaml`, and binary validation ensures immediate failure if any required synonym is missing. The tool applies business rules (currency/country codes, weight allocation) and outputs standardized templates with real-time Success/Attention/Failed status reporting. Strictly enforces a Zero False Positive policy — uncertain files are flagged, never passed as correct. Eliminates 80+ hours/month of manual, error-prone processing for logistics staff. Distributed as a standalone Windows executable (<30 MB).

### Classification

| Attribute | Value |
|-----------|-------|
| Project Type | Greenfield |
| Product Category | CLI Tool |
| Primary Context | Internal |

### Actors

| Actor Type | Primary Goal |
|------------|--------------|
| Logistics User | Process vendor Excel files into standardized customs templates efficiently; maintain config rules after training |
| IT Admin | Initialize and set up configuration files, regex mappings, and business rule references |

### Success Metrics

| Metric | Target | Primary |
|--------|--------|---------|
| Fail-Safe Trust | 0% False Positives — "Success" only when all data is valid | Yes |
| Time Compression | < 30 seconds per file (down from 10 min manual) | Yes |
| Automation Rate | ≥60% of vendor files processed without manual intervention | No |
| Standardization | 100% of output files pass strict template validation rules | No |
| Hours Recovered | ~80+ hours/month saved | No |
| Throughput | 20+ files per batch run | No |
| Error Reduction | Eliminate manual data entry typos and calculation errors | No |

### MVP Scope

**In Scope:**
1. **Batch Processing Engine** — Python CLI tool + one-click .exe (<30 MB), processes input folder, Windows 10+
2. **Input** — Read-only access to `\data` folder containing vendor Excel files
3. **Sheet Detection** — Configuration-based pattern matching for sheets (Invoice + Packing) using regex
4. **Intelligent Column Mapping** — Configuration-based pattern matching for 14 invoice fields + 6 packing fields using regex
5. **Invoice Sheet Extraction** — Extract invoice data from invoice sheet
6. **Packing Sheet Extraction** — Extract packing data items from packing sheet; detect total row, retrieve total_nw, total_gw, total_packets
7. **Data Transformation** — Currency/country codes, invoice number cleaning, PO number cleaning
8. **Weight Allocation** — Part-level proportional allocation with validation
9. **Output Generation** — 40-column template population, generate standardized files in `\data\finished`
10. **Transparency** — Real-time console logs + file logging and batch summary (Success/Attention/Failed)
11. **Diagnostic Mode** — Command for debugging and troubleshooting

**Out of Scope:**
- GUI interface
- Network access (all processing is local; no external API calls, telemetry, or update mechanisms)

---

## 2. Command Workflows

### IT Admin: Configuration Setup

1. IT Admin configures `config/field_patterns.yaml` with vendor-specific sheet name keywords and column regex patterns
2. IT Admin populates config Excel files (output template, currency conversion rules, country conversion rules)

### Logistics User: Batch Processing

1. Logistics User places AutoConvert executable on workstation
2. Logistics User places vendor Excel files into `data/` input folder
3. Logistics User runs `autoconvert` command
4. App auto-creates required folder structure (`data/`, `data/finished/`) if missing
5. App detects and validates sheets (Invoice + Packing) in each file via keyword matching
6. App maps columns via regex, extracts data, applies business rules, allocates weights
7. App validates all extracted and transformed data against Zero False Positive policy
8. App generates standardized output files in `data/finished/`
9. Logistics User reviews batch summary (Success/Attention/Failed) in console
10. Logistics User manually handles any Attention/Failed files

### Logistics User: Diagnostic Run

1. Logistics User runs `autoconvert --diagnostic` to troubleshoot a problematic file
2. App outputs detailed step-by-step processing logs (sheet detection, column mapping matches, transformation details)
3. Logistics User identifies the issue (missing column match, unexpected data format, etc.)

---

## 3. Functional Requirements

**Execution Context:** FR-001 and FR-002 execute once at startup. FR-028 executes once per batch before processing. FR-004 through FR-030 execute per file within a batch. FR-033 executes once after all files complete. FR-034 executes on explicit user command.

### Batch Processing

**FR-001**: System auto-creates required folder structure on startup
- **Input:** Application startup event
- **Rules:** Create `data/` and `data/finished/` directories if missing; `config/` must pre-exist
- **Output:** Both directories exist and are writable
- **Error:** Permission denied → log error with exact path, exit with non-zero code

**FR-002**: System loads and validates all configuration files before processing
- **Input:** `config/field_patterns.yaml`, `config/output_template.xlsx`, `config/currency_rules.xlsx`, `config/country_rules.xlsx`
- **Rules:** Load YAML; validate required keys present; compile all regex patterns; validate config Excel structures; validate no duplicate `Source_Value` entries in lookup files; fail fast before processing any data files
- **Output:** Configuration loaded in memory; regex patterns compiled; lookup tables parsed; output template validated
- **Error:** ERR_001 (CONFIG_NOT_FOUND) → missing config file with path; ERR_002 (INVALID_REGEX) → pattern name and compilation error; ERR_003 (DUPLICATE_LOOKUP) → duplicate Source_Value in lookup file; ERR_004 (MALFORMED_CONFIG) → structural issue details; ERR_005 (TEMPLATE_INVALID) → template validation failure

**FR-003**: System scans input folder and queues Excel files for batch processing
- **Input:** `data/` folder
- **Rules:** Identify `.xlsx`/`.xls` files; exclude temp files (prefix `~$`) and hidden files; detect file format by extension; convert `.xls` to in-memory workbook representation (no temp file, original untouched); open all files in values-only mode to read calculated formula values; detect locked files at scan time; process each file independently — one file's failure does not abort the batch
- **Output:** Ordered list of files queued for processing; each file begins with status "Pending"
- **Error:** No processable files → log info, exit gracefully; ERR_010 (FILE_LOCKED) → skip file; ERR_011 (FILE_CORRUPTED) → skip file
- **Depends:** FR-001, FR-002

### Sheet Detection

**FR-004**: System identifies Invoice sheet by keyword matching against sheet names
- **Input:** Excel workbook sheet names; patterns from `config/field_patterns.yaml` (`invoice_sheet.patterns`)
- **Rules:** Strip whitespace from sheet names; match against configured regex patterns (case-insensitive); first match wins; patterns include: `^invoice`, `^inv$`, `^commercial`
- **Output:** Identified Invoice sheet reference
- **Error:** ERR_012 (INVOICE_SHEET_NOT_FOUND) → no sheet matched any invoice pattern
- **Depends:** FR-002

**FR-005**: System identifies Packing sheet by keyword matching against sheet names
- **Input:** Excel workbook sheet names; patterns from `config/field_patterns.yaml` (`packing_sheet.patterns`)
- **Rules:** Strip whitespace from sheet names; match against configured regex patterns (case-insensitive); first match wins; patterns include: `^packing`, `^pack`, `^pak$`, `^dn&pl$`; ignore unrecognized sheets (purchase contracts, lookup tables, etc.)
- **Output:** Identified Packing sheet reference
- **Error:** ERR_013 (PACKING_SHEET_NOT_FOUND) → no sheet matched any packing pattern
- **Depends:** FR-002

**FR-006**: System validates that both required sheets were detected before proceeding
- **Input:** Sheet detection results from FR-004 and FR-005
- **Rules:** Both Invoice and Packing sheets must be successfully identified; if either is missing, halt processing for this file
- **Output:** Confirmed Invoice + Packing sheet pair ready for processing
- **Error:** Missing sheet → file status "Failed" with ERR_012 or ERR_013
- **Depends:** FR-004, FR-005

### Column Mapping

**FR-007**: System detects header row position by scanning for non-empty cell density
- **Input:** Sheet data (Invoice or Packing)
- **Rules:** Scan rows 7-30, first 13 columns; count non-empty cells per row after filtering; **Invoice threshold:** ≥7 non-empty cells; **Packing threshold:** ≥4 non-empty cells; filter out "Unnamed:" prefix cells (library-generated placeholders); **Three-tier priority system:** Tier 0 (highest) — row contains header keywords AND has fewer than 2 numeric/data-like cells; Tier 1 — all other qualifying rows; Tier 2 (lowest) — metadata rows (Tel:, Fax:, Cust ID:, Contact:, Address:) OR data-like rows (3+ cells with pure numbers, decimals, alphanumeric codes); select the row with the lowest tier; if tied, select the earliest row number; header keywords: qty, n.w., g.w., part no, amount, price, 品牌, 料号, 数量, etc.; merged cells are already unmerged at this point (non-first rows won't trigger false detection). See Section 7: Header Row Detection Algorithm
- **Output:** Header row number for the sheet
- **Error:** ERR_014 (HEADER_ROW_NOT_FOUND) → no row met threshold
- **Depends:** FR-006

**FR-008**: System maps columns using case-insensitive regex patterns from configuration
- **Input:** Header row cells; field patterns from `config/field_patterns.yaml` (`invoice_columns` or `packing_columns`)
- **Rules:** Normalize headers before matching: collapse newlines, tabs, multiple spaces → single space, strip leading/trailing whitespace; match each header against each field's regex synonym list (case-insensitive); first match per field wins; map by header name, not by column position (handles extra/missing/reordered columns); **Column scan range:** scan up to 20 columns for column mapping (wider than header detection's 13-column scan in FR-007, because brand/brand_type/model columns commonly appear at positions 14-20 in vendor files); **Invoice fields (14):** part_no, po_no, qty, price, amount, currency, coo, brand, brand_type, model (all required), cod (optional), weight (optional), inv_no (optional), serial (optional); **Packing fields (6):** part_no, po_no (optional), qty, nw, gw, pack (optional); **Two-row merged header handling:** after scanning the primary header row, if any required fields remain unmapped, scan the immediately following row (header_row+1) as a sub-header fallback; only advance the effective header row to header_row+1 if (1) one or more fields match in the sub-header row AND (2) the sub-header row is not data-like (fewer than 3 numeric/code cells); data extraction then begins at effective_header_row+1; **Currency field fallback (invoice only):** if the currency column is not found during header-row scanning, perform a data-row fallback scan (rows header_row+1 through header_row+4, all columns) for currency patterns; when found in a data cell at a column already mapped to price or amount, advance that field's mapping to the next column (col+1) so it points at the actual numeric value instead of the currency string
- **Output:** Column index mapping for all detected fields per sheet
- **Error:** ERR_020 (REQUIRED_COLUMN_MISSING) → lists specific missing field name(s) and sheet
- **Depends:** FR-007

**FR-009**: System extracts invoice number from header area as fallback
- **Input:** Invoice sheet rows 1-15; patterns from `config/field_patterns.yaml` (`inv_no_cell`)
- **Rules:** Used when no `inv_no` column detected in data table; search using capture-group patterns (e.g., `INVOICE\s*NO\.?\s*[:：]\s*(\S+)`); search using label patterns where value is in adjacent cell — right (up to +3 columns) or below (row+1 AND row+2, to handle cases where row+1 contains a date or other excluded value and the actual invoice number is at row+2); filter out false positives using exclude patterns (dates, label text captured as values); clean extracted value by removing "INV#" and "NO." prefixes
- **Output:** Extracted and cleaned invoice number
- **Error:** ERR_021 (INVOICE_NUMBER_NOT_FOUND) → both column and header extraction failed
- **Depends:** FR-008

### Data Extraction

**FR-010**: System resolves merged cells before data extraction
- **Input:** Sheet with merged cell ranges
- **Rules:** Capture all merged cell ranges BEFORE unmerging; unmerge all cells; **String fields** (part_no, po_no, brand, brand_type, etc.): propagate anchor cell value to all cells in merge range — this covers both vertical merges (same column, multiple rows) and horizontal merges (same row, multiple columns, e.g., brand+brand_type merged into one cell); **Weight fields** (NW, QTY in packing): only first row retains value, subsequent rows return 0.0 (prevents double-counting); **Header-area vs data-area distinction:** only data-area merges (starting after header row) are processed for data propagation; header-area merges are formatting only
- **Output:** Unmerged sheet with propagated values and merge tracking metadata
- **Error:** N/A (preprocessing step)
- **Depends:** FR-006

**FR-011**: System extracts 13 per-item fields from Invoice sheet
- **Input:** Invoice sheet, column mapping from FR-008, merge tracker from FR-010
- **Rules:** Extract fields: part_no, po_no, qty, price, amount, currency, coo, brand, brand_type, model (all required), cod (optional), inv_no (optional column), serial (optional column); weight is NOT extracted (calculated by weight allocation); **String fields:** strip leading/trailing whitespace; **Numeric precision (ROUND_HALF_UP):** qty = cell display precision, price = 5 decimals, amount = 2 decimals; uses floating-point safety correction (see Section 7: Numeric Precision Rules); **Unit suffix stripping:** strip KG, KGS, PCS, EA, 件, 个 from numeric values before parsing; **Leading blank rows:** skip blanks between header and data before checking stop conditions; **Header continuation filtering:** skip rows where part_no contains "part no"; **Merged cell handling:** propagate string fields per FR-010; **Invoice number cleaning:** remove "INV#" and "NO." prefixes at extraction time; **COD overrides COO:** when COD field contains a meaningful country value, use COD value as the item's COO regardless of whether the COO field is populated (COD takes priority because it reflects the actual shipping origin); when COD is empty or contains a placeholder value, retain the COO value as-is; **Placeholder detection:** values matching the pattern `^[/\\*\-—]+$` or `N/A` are treated as empty (vendors commonly use "/", "****", "N/A" to indicate "not applicable"); `无` is NOT a placeholder — it is a valid value that should be preserved as-is; **Stop conditions:** (1) empty part_no AND qty=0 after first data row, (2) part_no contains "total" (case-insensitive), (3) footer keywords (报关行, 有限公司, 口岸关别, 进境口岸), (4) any cell in columns A-J contains "total", "合计", "总计", "小计" — NOTE: condition 4 must be checked even on blank rows (where part_no and qty are both empty) because some vendors place "TOTAL" in a non-part_no column. See Section 7: Invoice Extraction Algorithm
- **Output:** List of structured invoice item records
- **Error:** ERR_030 (EMPTY_REQUIRED_FIELD) → required field empty with row details; ERR_031 (INVALID_NUMERIC) → non-numeric value in numeric field with row/column
- **Depends:** FR-008, FR-010

**FR-012**: System extracts packing items (part_no, qty, nw) from Packing sheet
- **Input:** Packing sheet, column mapping from FR-008, merge tracker from FR-010
- **Rules:** Extract 3 fields: part_no, qty, nw; **Numeric precision:** qty = cell display precision, nw = 5 decimals (high precision for allocation); **Unit suffix stripping:** same as FR-011; **Merged NW handling:** only first row of merged range contributes weight (subsequent rows return 0.0); **Implicit continuation handling:** when NW is empty and the current row has the same part_no as the previous extracted item, treat as a continuation row (NW=0.0, is_first_row_of_merge=false) — this handles vendors that group multiple PO lines under one carton without using merged cells; **Merged QTY handling:** apply the same merged-cell and implicit-continuation logic to QTY as to NW — when QTY is empty and the row is a non-anchor merge continuation OR the current part_no matches the previous item's part_no, set QTY=0 (the qty=0 AND nw=0 skip filter then correctly skips these PO-reference rows); **Ditto mark handling:** recognize ditto marks (`"`, `〃` U+3003, `"` U+201C, `"` U+201D) in the NW column as meaning "same carton as above"; when detected, set NW=0.0 to prevent double-counting and mark the row as is_first_row_of_merge=false (same as non-anchor merge rows); do NOT propagate the previous row's NW value — this prevents weight inflation in FR-021 aggregation; **Row filtering:** skip leading blank rows, skip header continuation ("part no"), skip pallet summary rows ("plt.", "pallet"), skip empty part_no rows, skip no-weight-data rows (qty=0 AND nw=0, but don't terminate); **Row processing order (CRITICAL):** check stop conditions BEFORE blank check; **Merged part_no propagation:** when part_no is empty but the cell is a non-anchor row of a vertical merge (e.g., C23:C25), propagate the anchor value so the row is processed as a data continuation with its own qty/nw values; **Stop conditions:** (1) any cell in columns A-J contains "total/合计/总计/小计", (2) truly blank row after first data row, (3) implicit total row pattern (empty part_no + numeric NW>0 AND GW>0, excluding BOTH NW-column merge continuations AND part_no-column merge continuations via MergeTracker — a row with empty part_no due to vertical merge is a data continuation, not a total row). See Section 7: Packing Extraction Algorithm
- **Output:** List of packing item records; `last_data_row` (row number of last extracted item)
- **Error:** ERR_030, ERR_031 (same as FR-011)
- **Depends:** FR-008, FR-010

**FR-013**: System validates merged weight cells in packing sheet
- **Input:** Packing items from FR-012, merge tracker from FR-010
- **Rules:** **Timing (CRITICAL):** Run immediately after packing extraction, BEFORE weight allocation; check only data-area merges (starting after header row); **Same part_no sharing merged NW/qty:** allowed; **Different part_no sharing merged NW/qty:** error; provides clear root cause instead of downstream ERR_042 symptom
- **Output:** Validation pass
- **Error:** ERR_046 (DIFFERENT_PARTS_SHARE_MERGED_WEIGHT) → different parts share same merged weight cell
- **Depends:** FR-012

**FR-014**: System detects total row using two-strategy approach
- **Input:** Packing sheet, `last_data_row` from FR-012, column mapping from FR-008, merge tracker from FR-010
- **Rules:** **Strategy 1 (Keyword):** Search rows `last_data_row+1` to `+15`, columns A-J, for "total/合计/总计/小计" (case-insensitive); **Strategy 2 (Implicit):** If Strategy 1 fails, search same range for rows with empty mapped part_no column + numeric NW>0 AND GW>0; must use actual mapped column index (not hardcoded); exclude rows where part_no is in a merged cell range (continuation rows, not total rows). See Section 7: Total Row Detection Algorithm
- **Output:** Total row number, or not found
- **Error:** ERR_032 (TOTAL_ROW_NOT_FOUND) → neither strategy found a total row
- **Depends:** FR-012

**FR-015**: System extracts total_nw from total row with visible precision
- **Input:** Total row from FR-014, NW column mapping from FR-008
- **Rules:** Read NW value from total row; strip embedded unit suffixes (KG, KGS, G, LB, LBS); read cell's display format to determine visible precision (parse format string for decimal places after `.`, handling complex formats like `#,##0.00`); round using ROUND_HALF_UP; **General/empty format:** round to 5 decimals first to clean floating-point artifacts, then normalize trailing zeros; **Precision for embedded units in General format:** strip unit BEFORE counting decimal places; store as Decimal with detected precision
- **Output:** `total_nw` value with precision metadata
- **Error:** ERR_033 (INVALID_TOTAL_NW) → non-numeric or missing value
- **Depends:** FR-014

**FR-016**: System extracts total_gw from total row with packaging weight addition check
- **Input:** Total row from FR-014, GW column mapping from FR-008
- **Rules:** Extract GW from total row (same unit stripping and precision rules as FR-015); **Packaging weight detection:** check +1 and +2 rows in GW column; if both have numeric values, use +2 row as final total_gw (handles pallet weight addition: row+1 = pallet weight, row+2 = final total); visible precision from cell format
- **Output:** `total_gw` value with precision metadata
- **Error:** ERR_034 (INVALID_TOTAL_GW) → non-numeric or missing value
- **Depends:** FR-014

**FR-017**: System extracts total_packets using multi-priority search
- **Input:** Total row from FR-014, column mappings from FR-008
- **Rules:** **Column search range:** A to (NW column + 2), minimum 11 columns; **Priority 1:** Search total_row+1 to +3 for "件数/件數" label, extract value from adjacent cells (right of label up to +3 cols) or embedded in label cell; adjacent cell values must be stripped of unit suffixes (e.g., "3 件" → "3") before numeric parsing; **Priority 2:** Search total_row-1 and -2 for "PLT.G" indicator (two formats: number-before-PLT or PLT-before-number); **Priority 3:** Search +1 to +3 rows for patterns in order: total-with-breakdown (extract leading number before parens), unit-suffix patterns (托/箱/件/CTNS), embedded Chinese (共N托), pallet range (PLT#N); **Pallet vs box priority:** when both appear, extract pallet count; **Validation:** positive integer 1-1000; **Field classification:** optional. See Section 7: Total Packets Extraction Algorithm
- **Output:** `total_packets` value, or null if not found
- **Error:** ATT_002 (MISSING_TOTAL_PACKETS) → not found or invalid (warning, not failure)
- **Depends:** FR-014

### Data Transformation

**FR-018**: System converts currency codes to standardized numeric customs codes
- **Input:** Raw currency values from invoice items; `config/currency_rules.xlsx` (Source_Value → Target_Code)
- **Rules:** Case-insensitive lookup of extracted currency value against Source_Value column; normalize whitespace around commas before lookup (collapse `, ` → `,`) so config entries with inconsistent comma spacing still match; map to 3-character numeric Target_Code; many-to-one mapping (e.g., "USD" and "美元" both → "502")
- **Output:** Standardized numeric currency code per invoice item
- **Error:** ATT_003 (UNSTANDARDIZED_CURRENCY) → no match found (warning; value preserved as-is for manual review)
- **Depends:** FR-002

**FR-019**: System converts country codes/names to standardized numeric customs codes
- **Input:** Raw COO values from invoice items; `config/country_rules.xlsx` (Source_Value → Target_Code)
- **Rules:** Case-insensitive lookup; normalize whitespace around commas before lookup (collapse `, ` → `,`) so "Taiwan, China" matches config key "TAIWAN,CHINA"; map to 3-character numeric Target_Code; normalize mixed int/str types in config (cast all Target_Code to consistent type); handles English names, ISO codes, Traditional Chinese, Simplified Chinese variants
- **Output:** Standardized numeric COO code per invoice item
- **Error:** ATT_004 (UNSTANDARDIZED_COO) → no match found (warning; value preserved as-is)
- **Depends:** FR-002

**FR-020**: System cleans PO numbers by removing suffixes
- **Input:** Raw po_no values from invoice items
- **Rules:** Strip everything from the first occurrence of `-`, `.`, or `/` delimiter onwards; applied as transformation step (not at extraction time); if cleaning produces an empty string (delimiter at position 0), preserve the original value unchanged
- **Output:** Cleaned PO numbers (e.g., `2250600556-2.1` → `2250600556`, `PO32741.0` → `PO32741`, `-PO12345` → `-PO12345` preserved)
- **Error:** N/A (cleaning is best-effort)

### Weight Allocation

**FR-021**: System aggregates packing item weights by part_no and validates integrity
- **Input:** Packing items from FR-012
- **Rules:** Sum NW values grouped by part_no (whitespace-stripped exact string match); for merged NW cells and implicit continuation rows, only the first row of each group contributes weight (per FR-010 and FR-012); validate all aggregated weights are positive (non-zero, non-negative)
- **Output:** Dictionary mapping part_no → aggregated total weight
- **Error:** ERR_042 (PACKING_PART_ZERO_NW) → aggregated weight is zero for a part; ERR_045 (ZERO_QUANTITY_FOR_PART) → qty is zero
- **Depends:** FR-012, FR-013

**FR-022**: System validates packing weight sum against total_nw before allocation
- **Input:** Aggregated weights from FR-021, total_nw from FR-015
- **Rules:** Compare sum of all aggregated packing weights against total_nw; threshold: difference must be ≤ 0.1; fires before any rounding or precision adjustment; catches data issues early (missing packing rows, wrong total row)
- **Output:** Validation pass
- **Error:** ERR_047 (AGGREGATE_DISAGREE_TOTAL) → packing sum vs total_nw difference > 0.1
- **Depends:** FR-021, FR-015

**FR-023**: System detects precision and determines optimal rounding level
- **Input:** total_nw from FR-015, aggregated weights from FR-021
- **Rules:** **Step 1:** Detect base precision (N) from total_nw value — minimum 2, maximum 5 decimals; **Step 2 (Sum matching):** try precision N → if rounded sum matches total_nw, use N; try N+1 → if match, use N+1; else use N+1 with remainder adjustment (never try N+2 for sum matching); **Step 3 (Zero check, independent):** if any weight rounds to zero at chosen precision → escalate N+1, N+2... up to max 5, stop at first precision with no zeros. See Section 7: Weight Allocation Algorithm
- **Output:** Optimal packing precision level
- **Error:** ERR_044 (WEIGHT_ROUNDS_TO_ZERO) → weight still rounds to zero at max precision
- **Depends:** FR-022

**FR-024**: System rounds packing weights and adjusts last part for exact sum
- **Input:** Aggregated weights from FR-021, precision from FR-023, total_nw from FR-015
- **Rules:** Round all part weights to determined packing precision using ROUND_HALF_UP; adjust last part's weight so sum equals total_nw exactly (remainder correction)
- **Output:** Rounded weights per part_no that sum to total_nw
- **Error:** ERR_041 (WEIGHT_ALLOCATION_MISMATCH) → adjustment failed
- **Depends:** FR-023

**FR-025**: System proportionally allocates part weights to individual invoice items
- **Input:** Rounded part weights from FR-024, invoice items from FR-011
- **Rules:** Match invoice items to packing parts by part_no (exact match after whitespace stripping); for each part_no: find all matching invoice items, calculate total qty, allocate weight proportionally (`weight = part_weight × (item_qty / total_qty)`); round to line precision (packing precision + 1); apply remainder to last invoice item in the group; **Precision cascade:** total_nw=N, packing weights=N or N+1, invoice items=packing+1
- **Output:** Invoice items with allocated net weight per line
- **Error:** ERR_040 (PART_NOT_IN_PACKING) → invoice part_no not found in packing; ERR_043 (PACKING_PART_NOT_IN_INVOICE) → packing part_no not found in invoice
- **Depends:** FR-024, FR-011

**FR-026**: System validates final weight allocation
- **Input:** Allocated weights from FR-025, total_nw from FR-015
- **Rules:** Verify sum of all allocated invoice item weights equals total_nw
- **Output:** Validation pass; file eligible for output generation
- **Error:** ERR_048 (WEIGHT_FINAL_VALIDATION_FAILED) → allocated sum does not match total_nw after full allocation pipeline
- **Depends:** FR-025

### Validation

**FR-027**: System determines final file status based on accumulated errors and warnings
- **Input:** All errors (ERR_xxx) and warnings (ATT_xxx) collected during processing
- **Rules:** Any ERR_xxx → file status "Failed"; any ATT_xxx with no ERR_xxx → file status "Attention"; no issues → file status "Success"; errors and warnings logged immediately when detected (not deferred); **Pipeline short-circuit:** when any ERR occurs, skip all downstream phases but collect all errors within the current phase. Phase order: (1) Sheet Detection, (2) Column Mapping, (3) Extraction, (4) Weight Allocation, (5) Output. Example: ERR_020 (missing column) collects all missing fields within Column Mapping phase, then skips Extraction/Allocation/Output. This avoids cascading symptom errors while maximizing actionable information per run
- **Output:** Final file status (Success/Attention/Failed)
- **Error:** N/A (status aggregation)

### Output Generation

**FR-028**: System clears `data/finished/` directory before batch processing
- **Input:** Batch start event
- **Rules:** Remove all existing files in `data/finished/` before processing any input files
- **Output:** Empty `data/finished/` directory
- **Error:** Permission denied → log error, exit

**FR-029**: System populates 40-column output template for each Success file
- **Input:** Validated invoice items with allocated weights; `config/output_template.xlsx` (sheet `工作表1`); total_gw from FR-016; total_packets from FR-017
- **Rules:** Preserve template rows 1-4 (headers, data types, required/optional rules, fill instructions); write data starting at row 5, one row per invoice line item; **Column mapping (A-AN):** A=part_no, B=po_no, C="3" (fixed), D=currency code, E=qty, F=price, G=amount, H=COO code, I-K=empty, L=serial, M=net weight, N=inv_no, O=empty, P=total_gw (row 5 only), Q=empty, R="32052" (fixed), S="320506" (fixed), T="142" (fixed), U-AJ=empty, AK=total_packets (row 5 only), AL=brand, AM=brand_type, AN=model; for Attention files with ATT_003/ATT_004, raw vendor string passes through to columns D/H as-is for manual review; only generate for files with "Success" or "Attention" status. See Section 7: Output Template Schema
- **Output:** Populated output workbook
- **Error:** ERR_051 (TEMPLATE_LOAD_FAILED) → template cannot be loaded
- **Depends:** FR-027, FR-002

**FR-030**: System saves output files to `data/finished/`
- **Input:** Populated workbook from FR-029
- **Rules:** Save as `{input_filename}_template.xlsx`; overwrite if exists (cleared at batch start per FR-028)
- **Output:** Output file written to `data/finished/`
- **Error:** ERR_052 (OUTPUT_WRITE_FAILED) → write failure (permission, disk)
- **Depends:** FR-029

### Logging & Reporting

**FR-031**: System provides real-time per-file console output during processing
- **Input:** Processing events per file
- **Rules:** Display `[N/M] Processing: {filename} ...` header; log key milestones: inv_no extraction, sheet extraction counts with row ranges, total row values, weight allocation precision and result, output path; errors logged with `[ERROR]` prefix immediately when detected; warnings logged with `[WARNING]` prefix immediately when detected; final status: ✅ SUCCESS, ❌ FAILED, or ⚠️ ATTENTION. See Section 7: Console Output Format
- **Output:** Real-time console output per file
- **Error:** Console failure → continue processing (non-blocking)

**FR-032**: System writes detailed processing logs to `process_log.txt`
- **Input:** All processing events and decisions
- **Rules:** Log to `process_log.txt` at project root; format: `[HH:MM] [LEVEL]` prefix; includes `[DEBUG]` level (regex match details, cell-by-cell parsing, intermediate calculations); more detailed than console output
- **Output:** Persistent log file with full audit trail
- **Error:** Log write failure → warn to console, continue processing

**FR-033**: System produces batch summary report after all files processed
- **Input:** Processing results for all files
- **Rules:** **Display order:** (1) Batch Processing Summary (total files, success/attention/failed counts, processing time, log path), (2) Failed Files section with per-file error list (condensed same-code errors with "(N occurrences)" and representative part_no), (3) Files Needing Attention section with per-file warning list; always produces summary even if all files failed. See Section 7: Batch Report Format
- **Output:** Batch summary in console
- **Error:** N/A (always produces summary)

### Diagnostics

**FR-034**: Logistics User runs diagnostic mode for single-file troubleshooting
- **Input:** `autoconvert --diagnostic <filename>`
- **Rules:** Process the specified file with maximum verbosity to console; output step-by-step: sheet detection matches, header row detection scores, column mapping matches (which regex matched which column), extraction details, transformation details, weight allocation steps, validation results
- **Output:** Detailed diagnostic output to console for the target file
- **Error:** Same error handling as normal mode with enhanced detail
- **Depends:** FR-001, FR-002

---

## 4. Non-Functional Requirements

### Performance
- **NFR-PERF-001**: Per-file processing time < 30 seconds for files with up to 100 line items under normal conditions
- **NFR-PERF-002**: Batch of 30 files completes in < 5 minutes on standard office workstation (i5, 8GB RAM)
- **NFR-PERF-003**: Executable startup time < 3 seconds (cold start)

### Reliability
- **NFR-REL-001**: Zero False Positive rate — no file achieves "Success" status when any extracted, transformed, or allocated value is incorrect, validated against the 41-file test corpus
- **NFR-REL-002**: Single file failure does not abort batch — 100% fault isolation between files

### Usability
- **NFR-USE-001**: Logistics User can process a batch with a single command (`autoconvert`) with no parameters required
- **NFR-USE-002**: Error messages include actionable context (file name, field name, row number) sufficient for manual resolution

### Portability
- **NFR-PORT-001**: Console output uses UTF-8 encoding with replacement fallback — handles CJK filenames, Chinese error messages, and emoji status indicators on Windows systems regardless of the default console codepage (e.g., cp950, cp936, cp932)

### Maintainability
- **NFR-MAINT-001**: New vendor column patterns added by editing `field_patterns.yaml` only — no code changes required
- **NFR-MAINT-002**: New currency/country mappings added by editing Excel lookup files only — no code changes required

---

## 5. Data Entities

| Entity | Key Attributes | Related FRs |
|--------|---------------|-------------|
| InvoiceItem | part_no, po_no, qty, price, amount, currency, coo, cod, brand, brand_type, model, inv_no, serial, allocated_weight | FR-011, FR-018, FR-019, FR-020, FR-025 |
| PackingItem | part_no, qty, nw, is_first_row_of_merge | FR-012, FR-021 |
| PackingTotals | total_nw (Decimal + precision), total_gw (Decimal + precision), total_packets (int, nullable) | FR-015, FR-016, FR-017 |
| ColumnMapping | sheet_type, field_name → column_index mapping | FR-007, FR-008 |
| MergeTracker | merged_ranges (pre-unmerge), cell → merge_range lookup | FR-010, FR-013, FR-014 |
| FileResult | filename, status (Success/Attention/Failed), errors (list of ERR codes), warnings (list of ATT codes), invoice_items, packing_items, packing_totals | FR-027, FR-031 |
| BatchResult | total_files, success_count, attention_count, failed_count, processing_time, file_results | FR-033 |

---

## 6. Technology Constraints

**Decided (non-negotiable):**
- Language: Python 3.11+
- Packaging: Standalone Windows executable (<30 MB)
- Target OS: Windows 10+
- Excel parsing: openpyxl (`.xlsx`), xlrd (`.xls` → in-memory conversion)
- Configuration: YAML (`field_patterns.yaml`) + Excel lookup files (`currency_rules.xlsx`, `country_rules.xlsx`, `output_template.xlsx`)
- File access: Read-only (input files never modified)
- Data processing: `data_only=True` (formula values, not formulas)
- Numeric precision: Python `Decimal` with ROUND_HALF_UP

**Open (agent can decide):**
- Executable packaging tool (PyInstaller, cx_Freeze, etc.)
- Logging framework
- YAML parsing library
- Project internal structure/architecture

### Compliance Notes

N/A

---

## 7. Implementation Reference

### Configuration Schema

- **field_patterns.yaml (FR-002, FR-008):**
  - `invoice_sheet.patterns`: List of regex patterns for invoice sheet name matching
  - `packing_sheet.patterns`: List of regex patterns for packing sheet name matching
  - `invoice_columns`: 14 field definitions (part_no, po_no, qty, price, amount, currency, coo, cod, brand, brand_type, model, weight, inv_no, serial), each with `patterns` (regex list), `type` (string/numeric/currency), `required` (bool)
  - `packing_columns`: 6 field definitions (part_no, po_no, qty, nw, gw, pack), each with patterns/type/required
  - `inv_no_cell`: Header area extraction patterns with `patterns` (capture group), `label_patterns` (adjacent value), `exclude_patterns` (false positive filtering)

- **currency_rules.xlsx (FR-018):** Sheet `Currency_Rules`, columns: `Source_Value` (string, currency name/code), `Target_Code` (numeric customs code). Many-to-one mapping. Currently 2 entries (USD→502, 美元→502).

- **country_rules.xlsx (FR-019):** Sheet `Country_Rules`, columns: `Source_Value` (string), `Target_Code` (numeric customs code). 56 entries → 20 distinct codes. Includes English, ISO 2-letter, Traditional Chinese, Simplified Chinese variants. **Data quality note:** 3 Target_Code values stored as string instead of int — code must normalize.

- **output_template.xlsx (FR-029):** Sheet `工作表1`, 40 columns (A-AN). Rows 1-4: metadata (headers, data types, required/optional, fill instructions). Data from row 5. Number format: columns L and M use `0.00000_` (5 decimals); all others use `@` (text).

### Output Formats

- **Output Template Column Mapping (FR-029):**

| Col | Field | Source | Notes |
|-----|-------|--------|-------|
| A | 企业料号 (part_no) | Invoice | Required |
| B | 采购订单号 (po_no) | Invoice | Cleaned per FR-020 |
| C | 征免方式 | Fixed "3" | All rows |
| D | 币制 (currency) | Invoice | Numeric code via FR-018 |
| E | 申报数量 (qty) | Invoice | |
| F | 申报单价 (price) | Invoice | |
| G | 申报总价 (amount) | Invoice | |
| H | 原产国 (coo) | Invoice | Numeric code via FR-019 |
| I-K | Reserved | N/A | Empty |
| L | 报关单商品序号 (serial) | Invoice | |
| M | 净重 (weight) | Allocated | Weight from FR-025 |
| N | 发票号码 (inv_no) | Invoice | |
| O | Reserved | N/A | Empty |
| P | 毛重 (total_gw) | Packing | Row 5 ONLY |
| Q | Reserved | N/A | Empty |
| R | 境内目的地代码 | Fixed "32052" | All rows |
| S | 行政区划代码 | Fixed "320506" | All rows |
| T | 最终目的国 | Fixed "142" | All rows |
| U-AJ | Reserved | N/A | Empty (16 columns) |
| AK | 件数 (total_packets) | Packing | Row 5 ONLY |
| AL | 品牌 (brand) | Invoice | |
| AM | 品牌类型 (brand_type) | Invoice | |
| AN | 型号 (model) | Invoice | |

- **Console Output Format (FR-031):**

```
[INFO] -----------------------------------------------------------------
[INFO] [N/M] Processing: {filename} ...
[INFO] Inv_No extracted ({method}): {value} at '{cell}'
[INFO] Invoice sheet extracted {N} items (rows {start}-{end})
[INFO] Packing total row at row {N}, NW= {val}, GW= {val}, Packets= {val}
[INFO] Packing sheet extracted {N} items (rows {start}-{end})
[INFO] Trying precision: {N}
[INFO] Expecting rounded part sum: {val}, Target: {val}
[INFO] Perfect match at {N} decimals
[INFO] Weight allocation complete: {val}
[INFO] Output successfully written to: {filename}_template.xlsx
[INFO] ✅ SUCCESS
```

Errors: `[ERROR] [ERR_xxx] {message}` → `[ERROR] ❌ FAILED`
Warnings: `[WARNING] [ATT_xxx] {message}` → `[WARNING] ⚠️ ATTENTION`

- **Batch Report Format (FR-033):**

```
[INFO] ===========================================================================
[INFO]                    BATCH PROCESSING SUMMARY
[INFO] ===========================================================================
[INFO] Total files:        {N}
[INFO] Successful:         {N}
[INFO] Attention:          {N}
[INFO] Failed:             {N}
[INFO] Processing time:    {N.NN} seconds
[INFO] Log file:           {path}/process_log.txt
[INFO] ===========================================================================
```

Failed section: `[ERROR] FAILED FILES:` with per-file error list, condensed same-code errors with "(N occurrences)" and representative part_no.
Separation line `[INFO] ---------------------------------------------------------------------------` between Failed and Attention sections (only when both are present).
Attention section: `[WARNING] FILES NEEDING ATTENTION:` with per-file warning list.

### Error/Status Code Catalog

**Error Codes (ERR_xxx → Failed status):**

| Range | Code | Name | Trigger | Resolution |
|-------|------|------|---------|------------|
| 001-009 | ERR_001 | CONFIG_NOT_FOUND | Config file missing at expected path | Verify config file exists at expected path in `config/` |
| | ERR_002 | INVALID_REGEX | Regex pattern fails to compile | Fix regex syntax in `field_patterns.yaml` for the named pattern |
| | ERR_003 | DUPLICATE_LOOKUP | Same Source_Value appears twice in lookup file | Remove duplicate Source_Value entry from the lookup Excel file |
| | ERR_004 | MALFORMED_CONFIG | Config file has invalid structure | Fix config file structure per Configuration Schema (Section 7) |
| | ERR_005 | TEMPLATE_INVALID | Output template validation failure | Verify `output_template.xlsx` structure matches expected schema |
| 010-019 | ERR_010 | FILE_LOCKED | Excel file is locked (open in another process) | Close the file in other applications, then re-run |
| | ERR_011 | FILE_CORRUPTED | Excel file cannot be read (corrupt/damaged) | Re-obtain the source file from the vendor |
| | ERR_012 | INVOICE_SHEET_NOT_FOUND | No sheet matched invoice patterns | Add sheet name pattern to `invoice_sheet.patterns` in `field_patterns.yaml` |
| | ERR_013 | PACKING_SHEET_NOT_FOUND | No sheet matched packing patterns | Add sheet name pattern to `packing_sheet.patterns` in `field_patterns.yaml` |
| | ERR_014 | HEADER_ROW_NOT_FOUND | No row met header detection threshold | Check file layout; header may be outside scan range (rows 7-30) |
| 020-029 | ERR_020 | REQUIRED_COLUMN_MISSING | Required field not mapped to any column | Add column regex pattern to `field_patterns.yaml` for the missing field |
| | ERR_021 | INVOICE_NUMBER_NOT_FOUND | Both column and header area extraction failed | Add inv_no pattern to `field_patterns.yaml` (column or `inv_no_cell` section) |
| 030-039 | ERR_030 | EMPTY_REQUIRED_FIELD | Required field is empty in data row | Check source file for missing data at the indicated row |
| | ERR_031 | INVALID_NUMERIC | Non-numeric value in numeric field | Check source file for non-numeric value at the indicated row/column |
| | ERR_032 | TOTAL_ROW_NOT_FOUND | Neither keyword nor implicit strategy found total row | Check packing sheet has a total row with keyword or numeric totals |
| | ERR_033 | INVALID_TOTAL_NW | total_nw non-numeric or missing | Check packing sheet total row NW cell contains a numeric value |
| | ERR_034 | INVALID_TOTAL_GW | total_gw non-numeric or missing | Check packing sheet total row GW cell contains a numeric value |
| 040-049 | ERR_040 | PART_NOT_IN_PACKING | Invoice part_no not found in packing data | Verify part_no spelling matches between invoice and packing sheets |
| | ERR_041 | WEIGHT_ALLOCATION_MISMATCH | Allocated weight sum ≠ total_nw | Run `--diagnostic` to identify allocation discrepancy |
| | ERR_042 | PACKING_PART_ZERO_NW | Aggregated packing weight is zero for a part | Check packing sheet for missing/zero NW value for the indicated part |
| | ERR_043 | PACKING_PART_NOT_IN_INVOICE | Packing part_no not found in invoice data | Verify part_no spelling matches between packing and invoice sheets |
| | ERR_044 | WEIGHT_ROUNDS_TO_ZERO | Weight rounds to zero even at max precision | Part weight too small for precision range; check source NW data |
| | ERR_045 | ZERO_QUANTITY_FOR_PART | Quantity is zero for a part | Check packing sheet for zero quantity at the indicated part |
| | ERR_046 | DIFFERENT_PARTS_SHARE_MERGED_WEIGHT | Different part_nos share merged NW cell | Unmerge NW cells in packing sheet so each part has its own weight |
| | ERR_047 | AGGREGATE_DISAGREE_TOTAL | Packing NW sum vs total_nw difference > 0.1 | Check packing item NW values sum against total row; possible missing/extra rows |
| | ERR_048 | WEIGHT_FINAL_VALIDATION_FAILED | Allocated sum ≠ total_nw after full allocation pipeline | Run `--diagnostic` to identify precision or rounding edge case |
| 050-059 | ERR_051 | TEMPLATE_LOAD_FAILED | Output template cannot be loaded | Verify `output_template.xlsx` exists and is not corrupted |
| | ERR_052 | OUTPUT_WRITE_FAILED | Output file write failure | Check write permissions and disk space for `data/finished/` |
| 060-069 | — | Reserved | Future use | — |

**Warning Codes (ATT_xxx → Attention status):**

| Code | Name | Trigger | Resolution |
|------|------|---------|------------|
| ATT_002 | MISSING_TOTAL_PACKETS | total_packets not found or invalid | Manually enter total_packets in the output file |
| ATT_003 | UNSTANDARDIZED_CURRENCY | Currency value not in lookup table | Add currency mapping to `currency_rules.xlsx` |
| ATT_004 | UNSTANDARDIZED_COO | COO value not in lookup table | Add country mapping to `country_rules.xlsx` |

### Algorithm Details

- **Header Row Detection Algorithm (FR-007):**
  1. Scan rows 7-30, first 13 columns
  2. For each row, count non-empty cells after filtering:
     - Exclude "Unnamed:" prefix cells (pandas artifacts)
     - Detect metadata markers: Tel:, Fax:, Cust ID:, Contact:, Address:
     - Detect data-like rows: 3+ cells with pure numbers, decimals, or alphanumeric codes
     - Detect keyword matches: qty, n.w., g.w., part no, amount, price, quantity, weight, 品牌, 料号, 数量, 单价, 金额, 净重, 毛重, 原产, country, origin, brand, model, description, unit, currency, coo
  3. **Invoice threshold:** ≥7 non-empty cells; **Packing threshold:** ≥4 non-empty cells
  4. **Three-tier priority classification** for rows meeting the threshold:
     - **Tier 0 (highest):** Contains header keywords AND has fewer than 2 numeric/data-like cells (true header rows)
     - **Tier 1:** All other qualifying rows (no keywords, not metadata/data-like)
     - **Tier 2 (lowest):** Metadata markers present OR data-like (3+ numeric cells) — these are weight summary rows, contact info rows, or data rows that happen to meet the cell count threshold
  5. Select the row with the lowest tier number; if tied, select the earliest row number
  6. After unmerging, non-first rows of merged cells are empty and won't trigger false detection

- **Column Header Normalization (FR-008):**
  1. Collapse newlines, tabs, multiple spaces → single space
  2. Strip leading/trailing whitespace
  3. Case-insensitive regex matching against normalized result
  4. Example: `"N.W.\n(KGS)"` → `"N.W. (KGS)"`

- **Sub-Header Scanning Algorithm (FR-008):**
  1. After primary header row scan, check if any required fields remain unmapped
  2. If unmapped fields exist, scan header_row+1 (all columns) for matching field patterns
  3. Guard: verify the sub-header row is not data-like (fewer than 3 numeric/code cells) before advancing
  4. If sub-header matches found and row is not data-like, advance effective_header_row to header_row+1
  5. Data extraction begins at effective_header_row+1
  6. Use case: two-row merged headers like "WEIGHT(KGS)" on row N spanning "N.W.(KGS)" and "G.M.(KGS)" on row N+1

- **Currency Data-Row Fallback Algorithm (FR-008, invoice only):**
  1. After header scan, if currency column is not found in field_map
  2. Scan rows header_row+1 through header_row+4, all columns (up to 20)
  3. For each cell, check if value matches a currency pattern (e.g., "USD", "CNY", recognized currency strings)
  4. If a currency value is found at a column already mapped to price or amount, shift that field's mapping to col+1 (the actual numeric value is one column right of the embedded currency string)
  5. Record the first currency match as the currency column in field_map
  6. **Multi-column handling:** continue scanning remaining columns in the same row after the first match — some vendors embed currency values in TWO columns (one before price, one before amount); all affected field mappings (price, amount) must be shifted before returning

- **Invoice Extraction Stop Conditions (FR-011):**
  Processing order per row: (1) Check if blank → scan columns A-J for stop keywords before skipping (a blank row with "TOTAL" in a non-part_no column must still trigger stop condition 4), (2) Check stop conditions → stop if matched, (3) Process data row.
  Stop when ANY condition met:
  1. part_no is empty AND qty = 0 (after first data row)
  2. part_no contains "total" (case-insensitive)
  3. part_no contains footer keywords (报关行, 有限公司, 口岸关别, 进境口岸)
  4. Any cell in columns A-J contains "total", "合计", "总计", "小计"
  NOTE: Stop condition 4 must be evaluated even on blank rows (where both part_no and qty are empty). Some vendors place "TOTAL" in a non-part_no column (e.g., PO No. column) while leaving part_no and qty empty. Without scanning A-J on blank rows, these TOTAL rows are silently skipped and extraction continues into footer administrative rows.

- **Packing Extraction Stop Conditions (FR-012):**
  Processing order per row (DIFFERS from invoice): (1) Check stop conditions BEFORE blank check, (2) Then check filtering rules, (3) Process data row.
  Stop when ANY condition met:
  1. Any cell in columns A-J contains "total/合计/总计/小计"
  2. Truly blank row (all key columns empty) after first data row
  3. Implicit total row: empty part_no + numeric NW>0 AND GW>0 (excluding merged cell continuations)

- **Packing Implicit Continuation Handling (FR-012):**
  Some vendors group multiple PO lines under one carton without using merged cells. The NW value appears only on the first row of each group; subsequent rows with the same part_no leave NW empty. A related pattern uses merged cells across data columns (CTNS, QTY, NW, GW, etc.) to group multiple POs under one part — after unmerging, non-anchor rows become "PO reference" rows with only PO No. and Part No. filled.
  1. **NW continuation** — Detection: NW is empty AND (non-anchor merge row OR current part_no matches previous item's part_no). Treatment: set NW=0.0, mark is_first_row_of_merge=false
  2. **QTY continuation** — Detection: QTY is empty AND (non-anchor merge row OR current part_no matches previous item's part_no). Treatment: set QTY=0. Combined with NW=0.0, the qty=0+nw=0 skip filter removes these PO-reference rows
  3. **Part_no vertical merge propagation** — Detection: part_no is empty AND cell is a non-anchor row of a vertical merge (e.g., C23:C25). Treatment: propagate the anchor value so the row is processed as a data continuation with its own qty/nw values. CRITICAL: the implicit total row detector (stop condition 3) must also exclude these rows — a row with empty part_no due to vertical merge is a data continuation, not a total row
  4. Do NOT raise ERR_030 for these rows — the empty fields are intentional (merged-cell artifacts or vendor convention), not data errors
  5. Example (no merge): `加高電子股份有限公司.xlsx` — CTNS=1 row has NW, continuation rows (same part, different PO) have empty NW
  6. Example (merged data cols): `登壹企業股份有限公司.xlsx` — rows 25-26 merged across CTNS/QTY/NW/GW columns; row 26 is a PO-reference row with only PO No. and Part No. filled after unmerging
  7. Example (merged part_no): `12.8 发票箱单模版-苏州.xlsx` — Part No. merged vertically (C23:C25); rows 24-25 have empty part_no but their own NW/GW values. Without merge-aware detection, stop condition 3 falsely triggers at row 24

- **Packing Ditto Mark Handling (FR-012):**
  Some vendors use ditto marks in the NW column to mean "same carton as above."
  1. Recognized ditto characters: `"` (U+0022), `〃` (U+3003), `"` (U+201C), `"` (U+201D)
  2. When a ditto mark is detected in NW: set NW=0.0, mark is_first_row_of_merge=false
  3. Do NOT propagate the previous row's NW value — the weight was already counted for the first row of that carton
  4. This prevents weight inflation in FR-021 aggregation (ERR_047)

- **Packing Sheet Processing Pipeline (FR-010 through FR-017):**
  1. Capture all numeric merges BEFORE unmerging
  2. Unmerge sheets
  3. Find headers & map columns (FR-007, FR-008)
  4. Extract packing items (FR-012)
  5. Validate merged weight cells — ERR_046, data-area only (FR-013)
  6. Total row detection (FR-014)
  7. Extract total_nw, total_gw, total_packets (FR-015, FR-016, FR-017)
  8. Weight allocation (FR-021 through FR-026)

- **Total Row Detection Two-Strategy (FR-014):**
  - **Strategy 1 (Keyword):** Search `last_data_row+1` to `+15`, columns A-J, for "total/合计/总计/小计" (case-insensitive)
  - **Strategy 2 (Implicit):** Same range, empty mapped part_no + numeric NW>0 AND GW>0, excluding merged cell rows (use MergeTracker)
  - SUM formula detection not needed — `data_only=True` resolves formulas to values

- **Total Packets Multi-Priority Search (FR-017):**
  Column search range: A to (NW column + 2), minimum 11.
  1. **Priority 1 (件数/件數 label):** Search total_row+1 to +3. Value: adjacent right (up to +3 cols) or embedded in label cell.
  2. **Priority 2 (PLT.G indicator):** Search total_row-1 and -2. Two formats: number-before-PLT (extract from cell) or PLT-before-number (check cell right).
  3. **Priority 3 (Below-total patterns):** Search +1 to +3 in order: (a) total-with-breakdown `"348（256胶框+92纸箱）"` → extract leading number, (b) unit-suffix `"7托"`, `"30箱"`, `"55 CTNS"`, (c) embedded Chinese `"共7托"`, (d) pallet range `"PLT#1(1~34)"`.
  - **Pallet vs box:** When both appear (e.g., "共7托（172件）"), extract pallet count.
  - **Supported formats:** Pure numeric, with unit suffix, with suffix+text, PLT indicator, pallet range, embedded in Chinese text.
  - **Validation:** Positive integer, range 1-1000.

- **Weight Allocation Algorithm (FR-021 through FR-026):**
  - **Step 1 — Precision Detection:** Analyze decimal places from total_nw. Base precision N: minimum 2, maximum 5. General format values use minimum 2 regardless of actual decimals (e.g., `212.5` → precision 2, not 1).
  - **Step 2 — Weight Aggregation:** Sum packing NW by part_no (whitespace-stripped exact match). Merged NW: only first row contributes. Validate non-zero/non-negative.
  - **Step 3 — Pre-allocation Validation:** Compare packing sum vs total_nw. Difference > 0.1 → ERR_047.
  - **Step 4 — Precision Determination:** Sum matching: try N → N+1 → use N+1 with adjustment (never N+2). Zero check (independent): escalate N+1, N+2... up to 5 until no zeros.
  - **Step 5 — Rounding & Adjustment:** Round all part weights to packing precision (ROUND_HALF_UP). Adjust last part's weight for exact sum = total_nw.
  - **Step 6 — Proportional Allocation:** For each part_no: find matching invoice items, calculate total qty, allocate `weight = part_weight × (item_qty / total_qty)`. Round to packing precision + 1. Apply remainder to last item.
  - **Step 7 — Final Validation:** Verify sum of allocated weights equals total_nw.
  - **Precision cascade:** total_nw = N, packing weights = N or N+1, invoice items = packing + 1.
  - **Rounding method:** ROUND_HALF_UP with epsilon trick: `round(value × 10^decimals + 1e-9) / 10^decimals`.

- **Numeric Precision Rules (FR-011, FR-012, FR-015):**
  - **ROUND_HALF_UP:** 0.5 always rounds up (e.g., 0.125 → 0.13). Uses epsilon trick to handle floating-point representation.
  - **Cell format precision:** Read `number_format` property, extract decimal places from format string (handle `0.00`, `#,##0.00`, `_($* #,##0.00_)` etc.).
  - **General format:** Round to 5 decimals to clean artifacts, then normalize trailing zeros.
  - **Embedded units in General format:** Strip unit BEFORE counting decimal places.
  - **Unit suffix stripping:** KG, KGS, G, LB, LBS, PCS, EA, 件, 个 (case-insensitive).

### Test Corpus

- **Location:** `tests/fixtures/` (41 vendor Excel files)
- **Composition:** Mix of `.xlsx` and `.xls` files across multiple vendor formats, covering all capability areas (sheet detection variants, merged cells, missing columns, weight allocation edge cases, `.xls` legacy format)
- **Purpose:** Regression suite validating NFR-REL-001 (Zero False Positive rate); append-only — new vendor patterns are added, existing files are never removed
- **Coverage:** Every ERR_xxx and ATT_xxx code is triggered by at least one file in the corpus

### Examples & Edge Cases

- **Missing N.W. column in invoice (FR-011):** Some vendors have only 14 invoice columns (no weight). Weight is always calculated by allocation (FR-025), so this is handled by design.
- **Missing TOTAL row in packing (FR-014):** Some vendors have no total row in the packing sheet. ERR_032 fires.
- **Phantom 256 columns (FR-007, FR-008):** Some files report 256 columns but only ~15 contain data. Header row detection (FR-007) scans 13 columns; column mapping (FR-008) scans 20 columns to reach brand/model fields.
- **Floating-point artifacts:** Values like `2.2800000000000002` appear in many files. Handled by precision-based ROUND_HALF_UP.
- **Embedded newlines in headers:** Many files contain literal newlines in header cells (e.g., `"N.W.\n(KGS)"`, `"Net WT\n(KGS)"`, `"Invoice\nNo"`). Normalized to single-line text before regex matching.
- **Sheet name variants:** Some vendors append Chinese suffixes to sheet names (e.g., `"INVOICE-隨機"`, `"PACKING LIST-隨機"`), matched by `^invoice` and `^packing` patterns.
- **Extra sheets:** Some vendors include extra sheets (purchase contract, lookup tables) — unrecognized sheets ignored by sheet detection.
- **Merged cells spanning data range:** Some vendors merge CTNS and MEASUREMENT columns across all data rows. Handled by merge propagation (FR-010).
- **KGS sub-header row:** Most packing sheets have a "KGS|KGS" row after the header. Some exceptions: no KGS row at all, non-standard layout, or KGS embedded in the header cell via newline. Filtered by header continuation logic and blank row skipping.
- **Part_no mismatch:** Some vendors use different part identifier columns between invoice and packing sheets → ERR_040/ERR_043. Exact match policy (Zero False Positive) means no fuzzy matching.
- **.xls format:** Some vendors use legacy `.xls` format. Converted in-memory via xlrd. Numeric values may be floats (91600.0 vs 91600) — handled by precision rounding.
- **Packaging weight addition:** Some vendors add pallet weight below the total row using keywords like 棧板/栈板, PALLET, PLT, or 塑膠託盤 (row+1 = pallet, row+2 = final GW). FR-016 checks +1/+2 rows.
- **Invoice number below label (FR-009):** Some vendors place date at row+1 below the "Invoice No." label and the actual invoice number at row+2. Below-label scan must check both offsets.
- **COD overrides COO (FR-011):** Some vendors include both COO and COD columns. COD (Country of Departure) takes priority over COO (Country of Origin) because it reflects the actual shipping origin. When COD has a meaningful country value, it replaces COO regardless of whether COO is populated; when COD is empty or contains a placeholder, the original COO value is retained. **Observed placeholders:** `"/"` (中磊, 寰泰科技), `"****"` (新加坡商普思電子), `"N/A"` (聯寶電子) — these indicate "not applicable" and must not override valid COO values like `"中国"`, `"CN"`, `"CHINA"`.
- **Two-row merged header (FR-008):** Nearly all packing sheets use merged header cells spanning two rows (e.g., "WEIGHT(KGS)" merged over "N.W.(KGS)" and "G.M.(KGS)"). Some vendors also have two-row merged headers in the invoice sheet. Sub-header scanning handles this.
- **Currency embedded in data rows (FR-008):** Some vendors embed currency values (e.g., "USD") in data cells under a merged "UNIT PRICE" header rather than as a standalone column. Data-row fallback detection handles this. Some vendors have TWO currency columns (one before price, one before amount); the fallback must shift ALL affected numeric fields, not just the first match.
- **Implicit continuation rows (FR-012):** Some vendors group multiple PO lines under one carton. The NW value appears only on the first row of each group; subsequent rows with the same part_no leave NW empty (no merged cells, no ditto marks). These must be treated as NW=0.0 continuation rows, not ERR_030 errors. A related pattern uses merged cells across data columns (CTNS, QTY, NW, GW); after unmerging, non-anchor rows become "PO reference" rows with only PO No. and Part No. — both QTY and NW are empty. The same continuation logic must apply to QTY so that the qty=0+nw=0 skip filter removes these rows.
- **Vertically merged part_no in packing (FR-012):** Some vendors merge Part No. vertically across multiple rows (e.g., C23:C25) where each row has its own QTY/NW/GW. After unmerging, non-anchor rows have empty part_no but valid weight data. The part_no must be propagated from the merge anchor, and the implicit total row detector (stop condition 3) must exclude these merge-continuation rows to avoid premature extraction termination.
- **Ditto marks in packing NW (FR-012):** Some vendors use `"` as a ditto mark in the NW column meaning "same carton as above." These must be treated as NW=0.0, not propagated, to prevent ERR_047 weight inflation.
- **Horizontally merged invoice fields (FR-010, FR-011):** Some vendors merge adjacent column cells horizontally per data row (e.g., 品牌+品牌类型 merged into one cell with value '无品牌'). After unmerging, the non-anchor column becomes empty. Invoice string field reading must propagate the anchor value via MergeTracker to prevent false ERR_030 on the non-anchor cell.
