"""Pydantic data models for AutoConvert.

Defines all data entities used across the processing pipeline:
InvoiceItem, PackingItem, PackingTotals, ColumnMapping, MergeRange,
FileResult, BatchResult, AppConfig, FieldPattern, InvNoCellConfig, SheetPair.
"""

from __future__ import annotations

import re
from decimal import Decimal
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from autoconvert.errors import ProcessingError


class InvoiceItem(BaseModel):
    """Represents one line item extracted from the invoice sheet.

    Includes all post-processing results. Mutable so that weight_alloc.py
    can set allocated_weight after construction.

    Attributes:
        part_no: Part number string from the invoice row.
        po_no: Purchase order number string.
        qty: Quantity as Decimal.
        price: Unit price as Decimal.
        amount: Line total as Decimal.
        currency: Currency code string (e.g., "USD").
        coo: Country of origin string.
        cod: Country of destination string, optional.
        brand: Brand name string.
        brand_type: Brand type string.
        model: Model identifier string.
        inv_no: Invoice number, optional (may come from header fallback).
        serial: Serial number, optional.
        allocated_weight: Weight allocated by weight_alloc.py, starts as None.
    """

    model_config = ConfigDict(frozen=False)

    part_no: str
    po_no: str
    qty: Decimal
    price: Decimal
    amount: Decimal
    currency: str
    coo: str
    cod: str | None
    brand: str
    brand_type: str
    model: str
    inv_no: str | None
    serial: str | None
    allocated_weight: Decimal | None


class PackingItem(BaseModel):
    """Represents one extracted row from the packing sheet.

    Immutable after extraction. Tracks merge/continuation row status
    needed for FR-013 merged weight validation.

    Attributes:
        part_no: Part number string from the packing row.
        qty: Quantity as Decimal.
        nw: Net weight as Decimal.
        is_first_row_of_merge: True if this row is the anchor of a merged
            weight cell or the first implicit continuation row. False for
            all subsequent merge/continuation rows (NW=0.0 rows).
        row_number: 1-based openpyxl row number of the source cell.
    """

    model_config = ConfigDict(frozen=True)

    part_no: str
    qty: Decimal
    nw: Decimal
    is_first_row_of_merge: bool
    row_number: int


class PackingTotals(BaseModel):
    """Extracted totals from the packing sheet footer.

    Immutable after extraction. Precision metadata is carried forward
    for use by FR-023 rounding logic.

    Attributes:
        total_nw: Total net weight as Decimal with visible precision rounding.
        total_nw_precision: Detected decimal precision for total_nw.
        total_gw: Total gross weight as Decimal, may reflect pallet-inclusive
            total from FR-016 +2-row override.
        total_gw_precision: Detected decimal precision for total_gw.
        total_packets: Total packet count, None if ATT_002 fires.
    """

    model_config = ConfigDict(frozen=True)

    total_nw: Decimal
    total_nw_precision: int
    total_gw: Decimal
    total_gw_precision: int
    total_packets: int | None


class ColumnMapping(BaseModel):
    """Maps field names to 1-based column indices for a detected sheet.

    Immutable after header detection. Carries both the detected header row
    and the effective header row after optional sub-header advancement.

    Attributes:
        sheet_type: Either "invoice" or "packing".
        field_map: Maps lowercase snake_case field names to 1-based column
            indices (e.g., {"part_no": 1, "qty": 5}).
        header_row: 1-based row number of the detected header row (FR-007).
        effective_header_row: 1-based row where data extraction begins minus 1.
            Equals header_row when no sub-header found; equals header_row + 1
            when sub-header fallback advanced the effective header (FR-008).
    """

    model_config = ConfigDict(frozen=True)

    sheet_type: str
    field_map: dict[str, int]
    header_row: int
    effective_header_row: int


class MergeRange(BaseModel):
    """Stores one pre-unmerge merged cell range from openpyxl.

    Captures merged cell boundaries before unmerging so that
    MergeTracker can answer is_merge_anchor / is_in_merge queries.
    All indices are 1-based (openpyxl convention).

    Attributes:
        min_row: First row of the merged range (1-based).
        max_row: Last row of the merged range (1-based).
        min_col: First column of the merged range (1-based).
        max_col: Last column of the merged range (1-based).
    """

    model_config = ConfigDict(frozen=True)

    min_row: int
    max_row: int
    min_col: int
    max_col: int


class FileResult(BaseModel):
    """Aggregates all results and diagnostics for a single processed file.

    Mutable so that errors and warnings can be accumulated during the
    processing pipeline before final status is determined.

    Attributes:
        filename: Base filename (not full path).
        status: Processing outcome — "Success", "Attention", or "Failed".
        errors: All ERR_xxx ProcessingErrors collected during processing.
        warnings: All ATT_xxx ProcessingErrors collected during processing.
        invoice_items: Extracted invoice rows, None if extraction failed.
        packing_items: Extracted packing rows, None if extraction failed.
        packing_totals: Extracted packing totals, None if extraction failed.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=False)

    filename: str
    status: str
    errors: list[ProcessingError]
    warnings: list[ProcessingError]
    invoice_items: list[InvoiceItem] | None
    packing_items: list[PackingItem] | None
    packing_totals: PackingTotals | None


class BatchResult(BaseModel):
    """Summary of a completed batch processing run.

    Immutable snapshot created after all files are processed.

    Attributes:
        total_files: Total number of files submitted for processing.
        success_count: Number of files with "Success" status.
        attention_count: Number of files with "Attention" status.
        failed_count: Number of files with "Failed" status.
        processing_time: Total wall-clock seconds for the batch.
        file_results: Per-file result objects in processing order.
        log_path: Path string to process_log.txt for display in summary.
    """

    model_config = ConfigDict(frozen=True)

    total_files: int
    success_count: int
    attention_count: int
    failed_count: int
    processing_time: float
    file_results: list[FileResult]
    log_path: str


class FieldPattern(BaseModel):
    """Compiled regex patterns and metadata for one column field definition.

    Used by AppConfig to describe how to detect each invoice/packing column
    header in FR-008 matching.

    Attributes:
        patterns: Compiled regex patterns for matching column header text.
        field_type: Data type string — "string", "numeric", or "currency".
        required: True if ERR_020 fires when the column is not found.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    patterns: list[re.Pattern]  # type: ignore[type-arg]
    field_type: str
    required: bool


class InvNoCellConfig(BaseModel):
    """Configuration for invoice number extraction from header area (FR-009).

    Holds three separate pattern lists for inline extraction, label-adjacent
    extraction, and false-positive filtering.

    Attributes:
        patterns: Capture-group patterns for inline invoice number extraction.
        label_patterns: Patterns matching label text; the value is in the
            adjacent cell (right up to +3 cols, or row below).
        exclude_patterns: Patterns that filter out false-positive matches.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    patterns: list[re.Pattern]  # type: ignore[type-arg]
    label_patterns: list[re.Pattern]  # type: ignore[type-arg]
    exclude_patterns: list[re.Pattern]  # type: ignore[type-arg]


class AppConfig(BaseModel):
    """Application-level configuration loaded from YAML and lookup files.

    Immutable after construction. Contains compiled patterns, column
    definitions, lookup tables, and processing thresholds.

    Attributes:
        invoice_sheet_patterns: Compiled regexes for invoice sheet name detection.
        packing_sheet_patterns: Compiled regexes for packing sheet name detection.
        invoice_columns: 14 field definitions keyed by lowercase snake_case name.
        packing_columns: 6 field definitions keyed by lowercase snake_case name.
        inv_no_cell: Header area extraction config for invoice number.
        currency_lookup: Normalized UPPERCASE key to 3-char numeric code string.
        country_lookup: Normalized UPPERCASE key to 3-char numeric code string.
        output_template_path: Absolute path to config/output_template.xlsx.
        invoice_min_headers: Minimum matching headers for invoice detection (7).
        packing_min_headers: Minimum matching headers for packing detection (4).
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    invoice_sheet_patterns: list[re.Pattern]  # type: ignore[type-arg]
    packing_sheet_patterns: list[re.Pattern]  # type: ignore[type-arg]
    invoice_columns: dict[str, FieldPattern]
    packing_columns: dict[str, FieldPattern]
    inv_no_cell: InvNoCellConfig
    currency_lookup: dict[str, str]
    country_lookup: dict[str, str]
    output_template_path: Path
    invoice_min_headers: int
    packing_min_headers: int


class SheetPair(BaseModel):
    """Holds the detected invoice and packing worksheet objects for one file.

    Accepts both openpyxl Worksheet and the xlrd adapter (which wraps an
    xlrd.Sheet). Using Any is intentional to support both backends.

    Attributes:
        invoice_sheet: openpyxl Worksheet or xlrd Sheet adapter for the invoice.
        packing_sheet: openpyxl Worksheet or xlrd Sheet adapter for the packing.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    invoice_sheet: Any
    packing_sheet: Any
