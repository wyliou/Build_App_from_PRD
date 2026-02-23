"""Tests for autoconvert.models.

Covers: InvoiceItem, PackingItem, PackingTotals, ColumnMapping, MergeRange,
AppConfig, FileResult (and their frozen/mutable behaviour).
"""

from __future__ import annotations

import re
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from autoconvert.errors import ErrorCode, ProcessingError
from autoconvert.models import (
    AppConfig,
    BatchResult,
    ColumnMapping,
    FieldPattern,
    FileResult,
    InvNoCellConfig,
    InvoiceItem,
    MergeRange,
    PackingItem,
    PackingTotals,
    SheetPair,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_invoice_item(**overrides) -> InvoiceItem:
    """Return a minimal valid InvoiceItem, applying keyword overrides."""
    defaults = dict(
        part_no="PN-001",
        po_no="PO-12345",
        qty=Decimal("10"),
        price=Decimal("1.00"),
        amount=Decimal("10.00"),
        currency="USD",
        coo="CN",
        cod=None,
        brand="BrandA",
        brand_type="TypeX",
        model="ModelZ",
        inv_no=None,
        serial=None,
        allocated_weight=None,
    )
    defaults.update(overrides)
    return InvoiceItem(**defaults)


def _make_processing_error(code: str = "ERR_030") -> ProcessingError:
    """Return a minimal ProcessingError for use in FileResult tests."""
    return ProcessingError(code=code, message="test error", filename="test.xlsx")


# ---------------------------------------------------------------------------
# InvoiceItem tests
# ---------------------------------------------------------------------------


class TestInvoiceItem:
    """Tests for InvoiceItem model."""

    def test_invoice_item_construction_happy_path(self) -> None:
        """Construct with all required fields; optional fields default to None."""
        item = _make_invoice_item()
        assert item.part_no == "PN-001"
        assert item.po_no == "PO-12345"
        assert item.currency == "USD"
        assert item.coo == "CN"
        assert item.cod is None
        assert item.inv_no is None
        assert item.serial is None
        assert item.allocated_weight is None

    def test_invoice_item_decimal_fields(self) -> None:
        """Decimal fields are stored as Decimal, not float."""
        item = _make_invoice_item(
            qty=Decimal("10"),
            price=Decimal("1.23456"),
            amount=Decimal("12.35"),
        )
        assert isinstance(item.qty, Decimal)
        assert isinstance(item.price, Decimal)
        assert isinstance(item.amount, Decimal)
        assert item.qty == Decimal("10")
        assert item.price == Decimal("1.23456")
        assert item.amount == Decimal("12.35")

    def test_invoice_item_mutable(self) -> None:
        """allocated_weight can be set after construction (model is not frozen)."""
        item = _make_invoice_item()
        assert item.allocated_weight is None
        item.allocated_weight = Decimal("1.5")
        assert item.allocated_weight == Decimal("1.5")

    def test_invoice_item_optional_fields_none(self) -> None:
        """cod, inv_no, serial, and allocated_weight may all be None simultaneously."""
        item = _make_invoice_item(
            cod=None,
            inv_no=None,
            serial=None,
            allocated_weight=None,
        )
        assert item.cod is None
        assert item.inv_no is None
        assert item.serial is None
        assert item.allocated_weight is None

    def test_invoice_item_rejects_invalid_type(self) -> None:
        """Passing a non-numeric string for qty raises ValidationError."""
        with pytest.raises(ValidationError):
            _make_invoice_item(qty="not_a_number")


# ---------------------------------------------------------------------------
# PackingItem tests
# ---------------------------------------------------------------------------


class TestPackingItem:
    """Tests for PackingItem model."""

    def test_packing_item_construction(self) -> None:
        """Construct with all fields; verify values are stored correctly."""
        item = PackingItem(
            part_no="ABC",
            qty=Decimal("5"),
            nw=Decimal("1.23000"),
            is_first_row_of_merge=True,
            row_number=10,
        )
        assert item.part_no == "ABC"
        assert item.qty == Decimal("5")
        assert item.nw == Decimal("1.23000")
        assert item.is_first_row_of_merge is True
        assert item.row_number == 10

    def test_packing_item_is_frozen(self) -> None:
        """Mutation attempt raises ValidationError or TypeError (frozen model)."""
        item = PackingItem(
            part_no="ABC",
            qty=Decimal("5"),
            nw=Decimal("1.23"),
            is_first_row_of_merge=True,
            row_number=3,
        )
        with pytest.raises((ValidationError, TypeError)):
            item.nw = Decimal("2")  # type: ignore[misc]

    def test_packing_item_continuation_row(self) -> None:
        """is_first_row_of_merge=False with nw=0 is valid (ditto/continuation row)."""
        item = PackingItem(
            part_no="ABC",
            qty=Decimal("5"),
            nw=Decimal("0"),
            is_first_row_of_merge=False,
            row_number=11,
        )
        assert item.is_first_row_of_merge is False
        assert item.nw == Decimal("0")


# ---------------------------------------------------------------------------
# PackingTotals tests
# ---------------------------------------------------------------------------


class TestPackingTotals:
    """Tests for PackingTotals model."""

    def test_packing_totals_with_packets(self) -> None:
        """total_packets stores a positive integer correctly."""
        totals = PackingTotals(
            total_nw=Decimal("100.500"),
            total_nw_precision=3,
            total_gw=Decimal("110.50"),
            total_gw_precision=2,
            total_packets=7,
        )
        assert totals.total_packets == 7
        assert isinstance(totals.total_packets, int)

    def test_packing_totals_no_packets(self) -> None:
        """total_packets=None is valid (ATT_002 scenario)."""
        totals = PackingTotals(
            total_nw=Decimal("50.00"),
            total_nw_precision=2,
            total_gw=Decimal("55.00"),
            total_gw_precision=2,
            total_packets=None,
        )
        assert totals.total_packets is None

    def test_packing_totals_precision_fields(self) -> None:
        """Precision fields are stored as int."""
        totals = PackingTotals(
            total_nw=Decimal("10.123"),
            total_nw_precision=3,
            total_gw=Decimal("11.50"),
            total_gw_precision=2,
            total_packets=4,
        )
        assert totals.total_nw_precision == 3
        assert totals.total_gw_precision == 2
        assert isinstance(totals.total_nw_precision, int)
        assert isinstance(totals.total_gw_precision, int)


# ---------------------------------------------------------------------------
# ColumnMapping tests
# ---------------------------------------------------------------------------


class TestColumnMapping:
    """Tests for ColumnMapping model."""

    def test_column_mapping_invoice(self) -> None:
        """Invoice column mapping stores sheet_type, field_map, header_row."""
        cm = ColumnMapping(
            sheet_type="invoice",
            field_map={"part_no": 1, "qty": 5},
            header_row=8,
            effective_header_row=8,
        )
        assert cm.sheet_type == "invoice"
        assert cm.field_map["part_no"] == 1
        assert cm.field_map["qty"] == 5
        assert cm.header_row == 8
        assert cm.effective_header_row == 8

    def test_column_mapping_sub_header_advanced(self) -> None:
        """Sub-header scenario: effective_header_row > header_row."""
        cm = ColumnMapping(
            sheet_type="packing",
            field_map={"nw": 3},
            header_row=8,
            effective_header_row=9,
        )
        assert cm.effective_header_row != cm.header_row
        assert cm.effective_header_row == cm.header_row + 1

    def test_column_mapping_is_frozen(self) -> None:
        """Mutation attempt raises ValidationError or TypeError."""
        cm = ColumnMapping(
            sheet_type="invoice",
            field_map={"part_no": 1},
            header_row=5,
            effective_header_row=5,
        )
        with pytest.raises((ValidationError, TypeError)):
            cm.header_row = 99  # type: ignore[misc]


# ---------------------------------------------------------------------------
# MergeRange tests
# ---------------------------------------------------------------------------


class TestMergeRange:
    """Tests for MergeRange model."""

    def test_merge_range_stores_1based_indices(self) -> None:
        """All four 1-based indices are stored as-is."""
        mr = MergeRange(min_row=3, max_row=5, min_col=2, max_col=2)
        assert mr.min_row == 3
        assert mr.max_row == 5
        assert mr.min_col == 2
        assert mr.max_col == 2

    def test_merge_range_is_frozen(self) -> None:
        """Mutation attempt raises ValidationError or TypeError."""
        mr = MergeRange(min_row=1, max_row=3, min_col=1, max_col=1)
        with pytest.raises((ValidationError, TypeError)):
            mr.min_row = 99  # type: ignore[misc]


# ---------------------------------------------------------------------------
# AppConfig tests
# ---------------------------------------------------------------------------


class TestAppConfig:
    """Tests for AppConfig model."""

    def _make_app_config(self, **overrides) -> AppConfig:
        """Return a minimal valid AppConfig, applying overrides."""
        field_pat = FieldPattern(
            patterns=[re.compile(r"part")],
            field_type="string",
            required=True,
        )
        inv_no_cfg = InvNoCellConfig(
            patterns=[re.compile(r"INV#?(\S+)")],
            label_patterns=[re.compile(r"Invoice\s*No")],
            exclude_patterns=[re.compile(r"N/A")],
        )
        defaults = dict(
            invoice_sheet_patterns=[re.compile(r"^invoice")],
            packing_sheet_patterns=[re.compile(r"^packing")],
            invoice_columns={"part_no": field_pat},
            packing_columns={"part_no": field_pat},
            inv_no_cell=inv_no_cfg,
            currency_lookup={"USD": "502"},
            country_lookup={"CN": "142"},
            output_template_path=Path("/config/output_template.xlsx"),
            invoice_min_headers=7,
            packing_min_headers=4,
        )
        defaults.update(overrides)
        return AppConfig(**defaults)

    def test_app_config_accepts_compiled_patterns(self) -> None:
        """arbitrary_types_allowed=True lets re.Pattern fields be stored."""
        cfg = self._make_app_config()
        assert len(cfg.invoice_sheet_patterns) == 1
        assert cfg.invoice_sheet_patterns[0].pattern == "^invoice"

    def test_app_config_lookup_tables(self) -> None:
        """currency_lookup and country_lookup values are str type."""
        cfg = self._make_app_config(
            currency_lookup={"USD": "502"},
            country_lookup={"CN": "142"},
        )
        assert cfg.currency_lookup["USD"] == "502"
        assert cfg.country_lookup["CN"] == "142"
        assert isinstance(cfg.currency_lookup["USD"], str)
        assert isinstance(cfg.country_lookup["CN"], str)

    def test_app_config_thresholds(self) -> None:
        """invoice_min_headers=7 and packing_min_headers=4 per FR-007."""
        cfg = self._make_app_config(invoice_min_headers=7, packing_min_headers=4)
        assert cfg.invoice_min_headers == 7
        assert cfg.packing_min_headers == 4


# ---------------------------------------------------------------------------
# FileResult tests
# ---------------------------------------------------------------------------


class TestFileResult:
    """Tests for FileResult model."""

    def test_file_result_failed_status(self) -> None:
        """Failed status with one error and no warnings is valid."""
        err = _make_processing_error(ErrorCode.ERR_030)
        result = FileResult(
            filename="invoice.xlsx",
            status="Failed",
            errors=[err],
            warnings=[],
            invoice_items=None,
            packing_items=None,
            packing_totals=None,
        )
        assert result.status == "Failed"
        assert len(result.errors) == 1
        assert result.errors[0].code == ErrorCode.ERR_030
        assert result.warnings == []

    def test_file_result_mutable_append(self) -> None:
        """Appending to errors list after construction succeeds (not frozen)."""
        result = FileResult(
            filename="invoice.xlsx",
            status="Success",
            errors=[],
            warnings=[],
            invoice_items=None,
            packing_items=None,
            packing_totals=None,
        )
        err = _make_processing_error(ErrorCode.ERR_031)
        result.errors.append(err)
        assert len(result.errors) == 1
        assert result.errors[0].code == ErrorCode.ERR_031

    def test_file_result_attention_status(self) -> None:
        """Attention status with one warning and no errors is valid."""
        warn = _make_processing_error("ATT_002")
        result = FileResult(
            filename="packing.xlsx",
            status="Attention",
            errors=[],
            warnings=[warn],
            invoice_items=None,
            packing_items=None,
            packing_totals=None,
        )
        assert result.status == "Attention"
        assert result.errors == []
        assert len(result.warnings) == 1
        assert result.warnings[0].code == "ATT_002"


# ---------------------------------------------------------------------------
# BatchResult tests
# ---------------------------------------------------------------------------


class TestBatchResult:
    """Tests for BatchResult model."""

    def test_batch_result_construction(self) -> None:
        """BatchResult stores all count and timing fields correctly."""
        br = BatchResult(
            total_files=3,
            success_count=2,
            attention_count=0,
            failed_count=1,
            processing_time=1.234,
            file_results=[],
            log_path="process_log.txt",
        )
        assert br.total_files == 3
        assert br.success_count == 2
        assert br.failed_count == 1
        assert br.processing_time == pytest.approx(1.234)
        assert br.log_path == "process_log.txt"

    def test_batch_result_is_frozen(self) -> None:
        """BatchResult is frozen; mutation raises ValidationError or TypeError."""
        br = BatchResult(
            total_files=1,
            success_count=1,
            attention_count=0,
            failed_count=0,
            processing_time=0.5,
            file_results=[],
            log_path="log.txt",
        )
        with pytest.raises((ValidationError, TypeError)):
            br.total_files = 99  # type: ignore[misc]


# ---------------------------------------------------------------------------
# SheetPair tests
# ---------------------------------------------------------------------------


class TestSheetPair:
    """Tests for SheetPair model."""

    def test_sheet_pair_accepts_any_type(self) -> None:
        """SheetPair accepts arbitrary objects as sheet fields (arbitrary_types_allowed)."""
        mock_invoice = object()
        mock_packing = object()
        sp = SheetPair(invoice_sheet=mock_invoice, packing_sheet=mock_packing)
        assert sp.invoice_sheet is mock_invoice
        assert sp.packing_sheet is mock_packing

    def test_sheet_pair_is_frozen(self) -> None:
        """SheetPair is frozen; mutation raises ValidationError or TypeError."""
        sp = SheetPair(invoice_sheet="ws1", packing_sheet="ws2")
        with pytest.raises((ValidationError, TypeError)):
            sp.invoice_sheet = "other"  # type: ignore[misc]
