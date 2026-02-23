"""Tests for autoconvert.column_map.

Covers FR-007 (header row detection), FR-008 (column mapping with
sub-header and currency fallback), and FR-009 (invoice number
extraction from header area).
"""

from __future__ import annotations

import re

import pytest
from openpyxl import Workbook

from autoconvert.column_map import (
    detect_header_row,
    extract_inv_no_from_header,
    map_columns,
)
from autoconvert.errors import ErrorCode, ProcessingError
from autoconvert.models import AppConfig, FieldPattern, InvNoCellConfig

# ---------------------------------------------------------------------------
# Helpers — minimal config/workbook factories
# ---------------------------------------------------------------------------


def _make_field_pattern(
    patterns: list[str],
    field_type: str = "string",
    required: bool = True,
) -> FieldPattern:
    """Build a FieldPattern with pre-compiled regexes."""
    compiled = [re.compile(p, re.IGNORECASE) for p in patterns]
    return FieldPattern(patterns=compiled, field_type=field_type, required=required)


def _invoice_columns() -> dict[str, FieldPattern]:
    """Return a minimal set of 14 invoice column FieldPatterns."""
    return {
        "part_no": _make_field_pattern([r"(?i)part\s*no"]),
        "po_no": _make_field_pattern([r"(?i)p\.?o\.?\s*no"]),
        "qty": _make_field_pattern([r"(?i)^qty"]),
        "price": _make_field_pattern([r"(?i)^price", r"(?i)unit\s*price"]),
        "amount": _make_field_pattern([r"(?i)^amount"]),
        "currency": _make_field_pattern([r"(?i)^currency$", r"^USD$", r"^CNY$", r"^EUR$"]),
        "coo": _make_field_pattern([r"(?i)country.*origin", r"(?i)^coo$"]),
        "brand": _make_field_pattern([r"(?i)^brand$"]),
        "brand_type": _make_field_pattern([r"(?i)品牌类型"]),
        "model": _make_field_pattern([r"(?i)^model"]),
        "cod": _make_field_pattern([r"(?i)^cod$"], required=False),
        "weight": _make_field_pattern(
            [r"(?i)^n\.?w\.?", r"(?i)net.*weight"],
            field_type="numeric",
            required=False,
        ),
        "inv_no": _make_field_pattern(
            [r"(?i)^inv.*no"], required=False
        ),
        "serial": _make_field_pattern(
            [r"(?i)项号"], required=False
        ),
    }


def _packing_columns() -> dict[str, FieldPattern]:
    """Return a minimal set of 6 packing column FieldPatterns."""
    return {
        "part_no": _make_field_pattern([r"(?i)part\s*no"]),
        "qty": _make_field_pattern([r"(?i)^qty"]),
        "nw": _make_field_pattern([r"(?i)^n\.?w\.?", r"(?i)net.*weight"]),
        "gw": _make_field_pattern([r"(?i)^g\.?w\.?", r"(?i)gross"]),
        "po_no": _make_field_pattern([r"(?i)p\.?o\.?\s*no"], required=False),
        "pack": _make_field_pattern(
            [r"(?i)^cartons?$", r"(?i)^ctns?"], required=False
        ),
    }


def _minimal_inv_no_cell() -> InvNoCellConfig:
    """Return InvNoCellConfig with basic patterns for testing."""
    return InvNoCellConfig(
        patterns=[
            re.compile(r"INVOICE\s*NO\.?\s*[:：]\s*(\S+)", re.IGNORECASE),
        ],
        label_patterns=[
            re.compile(r"(?i)^invoice\s*no\.?\s*[:：]?$"),
        ],
        exclude_patterns=[
            re.compile(r"^\d{4}-\d{2}-\d{2}"),
            re.compile(r"(?i)^invoice\s*no\.?[:：]?"),
        ],
    )


def _make_config(
    sheet_type: str = "invoice",
) -> AppConfig:
    """Build a minimal AppConfig for testing column_map functions."""
    return AppConfig(
        invoice_sheet_patterns=[],
        packing_sheet_patterns=[],
        invoice_columns=_invoice_columns(),
        packing_columns=_packing_columns(),
        inv_no_cell=_minimal_inv_no_cell(),
        currency_lookup={},
        country_lookup={},
        output_template_path="config/output_template.xlsx",
        invoice_min_headers=7,
        packing_min_headers=4,
    )


def _make_sheet(data: dict[tuple[int, int], object]) -> Workbook:
    """Create an in-memory workbook with data at specified (row, col) positions.

    Args:
        data: Mapping of (row, col) -> value.

    Returns:
        Workbook (the active sheet is populated).
    """
    wb = Workbook()
    ws = wb.active
    for (row, col), value in data.items():
        ws.cell(row=row, column=col, value=value)
    return wb


# ===========================================================================
# Tests for detect_header_row (FR-007)
# ===========================================================================


class TestDetectHeaderRow:
    """Tests for detect_header_row function."""

    def test_detect_header_row_invoice_standard(self) -> None:
        """Invoice sheet with keyword-rich header at row 10 returns 10."""
        config = _make_config("invoice")
        data: dict[tuple[int, int], object] = {}
        # Place 8 header keywords at row 10.
        headers = [
            "Part No", "PO No", "Qty", "Price",
            "Amount", "Currency", "COO", "Brand",
        ]
        for i, h in enumerate(headers, start=1):
            data[(10, i)] = h
        wb = _make_sheet(data)

        result = detect_header_row(wb.active, "invoice", config)
        assert result == 10

    def test_detect_header_row_packing_low_threshold(self) -> None:
        """Packing sheet with 4-cell row at row 8 returns 8 (threshold 4)."""
        config = _make_config("packing")
        data: dict[tuple[int, int], object] = {}
        headers = ["Part No", "Qty", "N.W.", "G.W."]
        for i, h in enumerate(headers, start=1):
            data[(8, i)] = h
        wb = _make_sheet(data)

        result = detect_header_row(wb.active, "packing", config)
        assert result == 8

    def test_detect_header_row_no_qualifying_row(self) -> None:
        """All rows have <=6 cells for invoice: raises ERR_014."""
        config = _make_config("invoice")
        data: dict[tuple[int, int], object] = {}
        # Place only 6 cells at every candidate row.
        for row in range(7, 31):
            for col in range(1, 7):
                data[(row, col)] = f"cell_{row}_{col}"
        wb = _make_sheet(data)

        with pytest.raises(ProcessingError) as exc_info:
            detect_header_row(wb.active, "invoice", config)
        assert exc_info.value.code == ErrorCode.ERR_014

    def test_detect_header_row_tier0_preferred(self) -> None:
        """Tier 0 row (keywords, <2 numeric) beats earlier Tier 1 row."""
        config = _make_config("invoice")
        data: dict[tuple[int, int], object] = {}
        # Row 8: Tier 1 — 8 non-empty cells, no keywords, no metadata,
        # no data-like (only text cells).
        for col in range(1, 9):
            data[(8, col)] = f"header_{col}"

        # Row 9: Tier 0 — 8 cells with keywords, <2 numeric cells.
        keywords = [
            "Part No", "Qty", "Price", "Amount",
            "Brand", "Model", "COO", "Currency",
        ]
        for i, kw in enumerate(keywords, start=1):
            data[(9, i)] = kw
        wb = _make_sheet(data)

        result = detect_header_row(wb.active, "invoice", config)
        assert result == 9

    def test_detect_header_row_metadata_row_excluded(self) -> None:
        """Row with metadata markers is Tier 2; Tier 0/1 row is preferred."""
        config = _make_config("invoice")
        data: dict[tuple[int, int], object] = {}

        # Row 8: metadata row with Tel:/Fax: — meets threshold but Tier 2.
        meta_cells = [
            "Company", "Tel: 123", "Fax: 456", "Contact: John",
            "Address: 123 St", "Notes", "Info", "Extra",
        ]
        for i, v in enumerate(meta_cells, start=1):
            data[(8, i)] = v

        # Row 12: Tier 0 header row — keywords, <2 numeric.
        headers = [
            "Part No", "Qty", "Price", "Amount",
            "Brand", "Model", "COO", "Currency",
        ]
        for i, h in enumerate(headers, start=1):
            data[(12, i)] = h
        wb = _make_sheet(data)

        result = detect_header_row(wb.active, "invoice", config)
        assert result == 12


# ===========================================================================
# Tests for map_columns (FR-008)
# ===========================================================================


class TestMapColumns:
    """Tests for map_columns function."""

    def test_map_columns_invoice_all_required(self) -> None:
        """All 10 required invoice fields found at correct column indices."""
        config = _make_config("invoice")
        data: dict[tuple[int, int], object] = {}
        # Place all 10 required invoice fields in row 10.
        required_headers = {
            1: "Part No",
            2: "PO No",
            3: "Qty",
            4: "Price",
            5: "Amount",
            6: "Currency",
            7: "COO",
            8: "Brand",
            9: "品牌类型",
            10: "Model",
        }
        for col, header in required_headers.items():
            data[(10, col)] = header
        wb = _make_sheet(data)

        result = map_columns(wb.active, 10, "invoice", config)
        assert result.field_map["part_no"] == 1
        assert result.field_map["po_no"] == 2
        assert result.field_map["qty"] == 3
        assert result.field_map["price"] == 4
        assert result.field_map["amount"] == 5
        assert result.field_map["currency"] == 6
        assert result.field_map["coo"] == 7
        assert result.field_map["brand"] == 8
        assert result.field_map["brand_type"] == 9
        assert result.field_map["model"] == 10
        assert result.header_row == 10
        assert result.effective_header_row == 10

    def test_map_columns_missing_required_field(self) -> None:
        """Missing 'qty' raises ERR_020 with 'qty' in the message."""
        config = _make_config("invoice")
        data: dict[tuple[int, int], object] = {}
        # Place 9 of 10 required fields — omit qty.
        headers = {
            1: "Part No",
            2: "PO No",
            # 3: qty is missing
            4: "Price",
            5: "Amount",
            6: "Currency",
            7: "COO",
            8: "Brand",
            9: "品牌类型",
            10: "Model",
        }
        for col, header in headers.items():
            data[(10, col)] = header
        wb = _make_sheet(data)

        with pytest.raises(ProcessingError) as exc_info:
            map_columns(wb.active, 10, "invoice", config)
        assert exc_info.value.code == ErrorCode.ERR_020
        assert "qty" in exc_info.value.message

    def test_map_columns_sub_header_fallback(self) -> None:
        """Primary maps 9 of 10; row+1 maps the 10th; effective_header_row advances."""
        config = _make_config("invoice")
        data: dict[tuple[int, int], object] = {}
        # Row 10: 9 required fields (missing coo).
        headers_main = {
            1: "Part No",
            2: "PO No",
            3: "Qty",
            4: "Price",
            5: "Amount",
            6: "Currency",
            7: "Brand",
            8: "品牌类型",
            9: "Model",
        }
        for col, header in headers_main.items():
            data[(10, col)] = header
        # Row 11 (sub-header): has COO.
        data[(11, 10)] = "Country of Origin"
        wb = _make_sheet(data)

        result = map_columns(wb.active, 10, "invoice", config)
        assert result.field_map["coo"] == 10
        assert result.effective_header_row == 11

    def test_map_columns_sub_header_guard_data_like(self) -> None:
        """Row+1 has 4 numeric cells; effective_header_row is NOT advanced."""
        config = _make_config("invoice")
        data: dict[tuple[int, int], object] = {}
        # Row 10: 9 required fields (missing coo).
        headers_main = {
            1: "Part No",
            2: "PO No",
            3: "Qty",
            4: "Price",
            5: "Amount",
            6: "Currency",
            7: "Brand",
            8: "品牌类型",
            9: "Model",
        }
        for col, header in headers_main.items():
            data[(10, col)] = header
        # Row 11: data-like (4 numeric cells) even though it contains a
        # pattern match.
        data[(11, 1)] = "12345"
        data[(11, 2)] = "67890"
        data[(11, 3)] = "111"
        data[(11, 4)] = "222"
        data[(11, 10)] = "Country of Origin"
        wb = _make_sheet(data)

        # Should raise ERR_020 because coo remains unmapped (sub-header
        # guarded by data-like check).
        with pytest.raises(ProcessingError) as exc_info:
            map_columns(wb.active, 10, "invoice", config)
        assert exc_info.value.code == ErrorCode.ERR_020
        assert "coo" in exc_info.value.message

    def test_map_columns_currency_data_row_fallback(self) -> None:
        """Currency found in data row; price shifted by +1."""
        config = _make_config("invoice")
        data: dict[tuple[int, int], object] = {}
        # Row 10: all required fields EXCEPT currency.
        headers = {
            1: "Part No",
            2: "PO No",
            3: "Qty",
            4: "Brand",
            5: "Price",  # will be at col 5 initially
            6: "Amount",
            7: "COO",
            8: "品牌类型",
            9: "Model",
        }
        for col, header in headers.items():
            data[(10, col)] = header
        # Row 11 (data row): data-like row (3+ numeric cells) with USD
        # at column 5 (same as price column). The sub-header guard
        # blocks this row; the currency data-row fallback picks it up.
        data[(11, 1)] = "PT-001"
        data[(11, 2)] = "PO-123"
        data[(11, 3)] = "100"
        data[(11, 4)] = "BrandX"
        data[(11, 5)] = "USD"
        data[(11, 6)] = "25.50"
        wb = _make_sheet(data)

        result = map_columns(wb.active, 10, "invoice", config)
        assert result.field_map["currency"] == 5
        assert result.field_map["price"] == 6  # shifted from 5 to 6

    def test_map_columns_currency_two_columns(self) -> None:
        """Two currency values shift both price and amount columns."""
        config = _make_config("invoice")
        data: dict[tuple[int, int], object] = {}
        # Row 10: all required except currency; price at col 5, amount at col 8.
        headers = {
            1: "Part No",
            2: "PO No",
            3: "Qty",
            4: "Brand",
            5: "Price",
            6: "COO",
            7: "品牌类型",
            8: "Amount",
            9: "Model",
        }
        for col, header in headers.items():
            data[(10, col)] = header
        # Row 11: data-like row with USD at col 5 and col 8 (both mapped
        # to price and amount columns). Sub-header guard blocks this row.
        data[(11, 1)] = "PT-001"
        data[(11, 2)] = "PO-123"
        data[(11, 3)] = "100"
        data[(11, 5)] = "USD"
        data[(11, 8)] = "USD"
        wb = _make_sheet(data)

        result = map_columns(wb.active, 10, "invoice", config)
        assert result.field_map["currency"] == 5
        assert result.field_map["price"] == 6  # shifted from 5 to 6
        assert result.field_map["amount"] == 9  # shifted from 8 to 9

    def test_map_columns_header_normalization(self) -> None:
        """Header "N.W.\\n(KGS)" matches nw field after normalization."""
        config = _make_config("packing")
        data: dict[tuple[int, int], object] = {}
        headers = {
            1: "Part No",
            2: "Qty",
            3: "N.W.\n(KGS)",
            4: "G.W.",
        }
        for col, header in headers.items():
            data[(10, col)] = header
        wb = _make_sheet(data)

        result = map_columns(wb.active, 10, "packing", config)
        assert result.field_map["nw"] == 3

    def test_map_columns_20col_scan(self) -> None:
        """Brand field at column 16 is found (scan extends beyond 13)."""
        config = _make_config("invoice")
        data: dict[tuple[int, int], object] = {}
        # Place most required fields in the first 13 columns.
        headers = {
            1: "Part No",
            2: "PO No",
            3: "Qty",
            4: "Price",
            5: "Amount",
            6: "Currency",
            7: "COO",
            8: "品牌类型",
            9: "Model",
            16: "Brand",  # beyond 13-column range
        }
        for col, header in headers.items():
            data[(10, col)] = header
        wb = _make_sheet(data)

        result = map_columns(wb.active, 10, "invoice", config)
        assert result.field_map["brand"] == 16


# ===========================================================================
# Tests for extract_inv_no_from_header (FR-009)
# ===========================================================================


class TestExtractInvNoFromHeader:
    """Tests for extract_inv_no_from_header function."""

    def test_extract_inv_no_capture_group(self) -> None:
        """Capture-group pattern extracts invoice number from inline text."""
        config = _make_config()
        data: dict[tuple[int, int], object] = {}
        data[(3, 2)] = "INVOICE NO.: INV2024-001"
        wb = _make_sheet(data)

        result = extract_inv_no_from_header(wb.active, config)
        assert result == "INV2024-001"

    def test_extract_inv_no_label_adjacent_right(self) -> None:
        """Label pattern matches; value in adjacent right cell."""
        config = _make_config()
        data: dict[tuple[int, int], object] = {}
        data[(5, 1)] = "Invoice No:"
        data[(5, 2)] = "PI240001"
        wb = _make_sheet(data)

        result = extract_inv_no_from_header(wb.active, config)
        assert result == "PI240001"

    def test_extract_inv_no_label_below_row2(self) -> None:
        """Label at row 6; row+1=date (excluded); row+2=inv number."""
        config = _make_config()
        data: dict[tuple[int, int], object] = {}
        data[(6, 1)] = "Invoice No"
        data[(7, 1)] = "2024-01-15"  # date — excluded
        data[(8, 1)] = "INV-2024"
        wb = _make_sheet(data)

        result = extract_inv_no_from_header(wb.active, config)
        assert result == "INV-2024"

    def test_extract_inv_no_prefix_cleaning(self) -> None:
        """Extracted "INV#2024-001" is cleaned to "2024-001"."""
        config = _make_config()
        data: dict[tuple[int, int], object] = {}
        data[(3, 2)] = "INVOICE NO: INV#2024-001"
        wb = _make_sheet(data)

        result = extract_inv_no_from_header(wb.active, config)
        assert result == "2024-001"

    def test_extract_inv_no_not_found(self) -> None:
        """No patterns match; returns None (NOT ProcessingError)."""
        config = _make_config()
        data: dict[tuple[int, int], object] = {}
        # Unrelated content only.
        data[(1, 1)] = "Company Name"
        data[(2, 1)] = "Some Address"
        wb = _make_sheet(data)

        result = extract_inv_no_from_header(wb.active, config)
        assert result is None

    def test_extract_inv_no_exclude_filter(self) -> None:
        """Candidate matching exclude pattern is discarded; returns None."""
        config = AppConfig(
            invoice_sheet_patterns=[],
            packing_sheet_patterns=[],
            invoice_columns=_invoice_columns(),
            packing_columns=_packing_columns(),
            inv_no_cell=InvNoCellConfig(
                patterns=[
                    re.compile(
                        r"INVOICE\s*NO\.?\s*[:：]\s*(\S+)", re.IGNORECASE
                    ),
                ],
                label_patterns=[],
                exclude_patterns=[
                    # Exclude anything starting with a date.
                    re.compile(r"^\d{4}-\d{2}-\d{2}"),
                    # Exclude the label text itself.
                    re.compile(r"(?i)^invoice\s*no"),
                ],
            ),
            currency_lookup={},
            country_lookup={},
            output_template_path="config/output_template.xlsx",
            invoice_min_headers=7,
            packing_min_headers=4,
        )
        data: dict[tuple[int, int], object] = {}
        # The capture group extracts "2025-01-15" which matches exclude.
        data[(3, 1)] = "Invoice No: 2025-01-15"
        wb = _make_sheet(data)

        result = extract_inv_no_from_header(wb.active, config)
        assert result is None
