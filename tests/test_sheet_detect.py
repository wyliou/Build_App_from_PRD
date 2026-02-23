"""Tests for autoconvert.sheet_detect.

Tests cover FR-004 (invoice detection), FR-005 (packing detection),
and FR-006 (both sheets required).
"""

from __future__ import annotations

from typing import Any

import pytest

from autoconvert.errors import ErrorCode, ProcessingError
from autoconvert.models import AppConfig, SheetPair
from autoconvert.sheet_detect import detect_sheets


class TestDetectSheets:
    """Tests for detect_sheets() function."""

    def test_detect_sheets_invoice_found(
        self, make_workbook: Any, app_config: AppConfig
    ) -> None:
        """Happy path: workbook with Invoice and Packing List sheets.

        Both sheets match configured patterns. Should return SheetPair
        with both sheets correctly identified.
        """
        wb = make_workbook(sheets=["Invoice", "Packing List"])
        result = detect_sheets(wb, app_config)

        assert isinstance(result, SheetPair)
        assert result.invoice_sheet is not None
        assert result.packing_sheet is not None
        assert result.invoice_sheet.title == "Invoice"
        assert result.packing_sheet.title == "Packing List"

    def test_detect_sheets_invoice_not_found(
        self, make_workbook: Any, app_config: AppConfig
    ) -> None:
        """Edge case: workbook with no invoice-pattern-matching sheet.

        Workbook has "Packing List" but no sheet matching invoice patterns.
        Should raise ProcessingError with code ERR_012 immediately
        (before checking packing).
        """
        wb = make_workbook(sheets=["Lookup Table", "Packing List"])

        with pytest.raises(ProcessingError) as exc_info:
            detect_sheets(wb, app_config)

        assert exc_info.value.code == ErrorCode.ERR_012
        assert "Invoice sheet not found" in exc_info.value.message

    def test_detect_sheets_packing_not_found(
        self, make_workbook: Any, app_config: AppConfig
    ) -> None:
        """Edge case: workbook with invoice but no packing-pattern-matching sheet.

        Workbook has "Commercial Invoice" but no sheet matching packing patterns.
        Should raise ProcessingError with code ERR_013.
        """
        wb = make_workbook(sheets=["Commercial Invoice", "Lookup Table"])

        with pytest.raises(ProcessingError) as exc_info:
            detect_sheets(wb, app_config)

        assert exc_info.value.code == ErrorCode.ERR_013
        assert "Packing sheet not found" in exc_info.value.message

    def test_detect_sheets_case_insensitive(
        self, make_workbook: Any, app_config: AppConfig
    ) -> None:
        """Edge case: sheet names "INVOICE" and "PACKING" (uppercase).

        Patterns are case-insensitive (compiled by config.py with re.IGNORECASE).
        Should still match and return both sheets.
        """
        wb = make_workbook(sheets=["INVOICE", "PACKING"])
        result = detect_sheets(wb, app_config)

        assert result.invoice_sheet.title == "INVOICE"
        assert result.packing_sheet.title == "PACKING"

    def test_detect_sheets_extra_sheets_ignored(
        self, make_workbook: Any, app_config: AppConfig
    ) -> None:
        """Edge case: workbook with extra sheet "Lookup Table" plus valid sheets.

        Unrecognized sheets are silently ignored. Should return only the
        invoice and packing sheets in SheetPair.
        """
        wb = make_workbook(sheets=["Lookup Table", "Invoice", "Packing List"])
        result = detect_sheets(wb, app_config)

        assert result.invoice_sheet.title == "Invoice"
        assert result.packing_sheet.title == "Packing List"
        # Verify the extra sheet is NOT in the result.
        assert result.invoice_sheet.title != "Lookup Table"
        assert result.packing_sheet.title != "Lookup Table"

    def test_detect_sheets_whitespace_stripped(
        self, make_workbook: Any, app_config: AppConfig
    ) -> None:
        """Edge case: sheet names with leading/trailing whitespace.

        Sheet names " Invoice " and " Packing List " should be stripped
        before regex matching and should match successfully.
        """
        wb = make_workbook(sheets=["  Invoice  ", "  Packing List  "])
        result = detect_sheets(wb, app_config)

        assert result.invoice_sheet.title == "  Invoice  "
        assert result.packing_sheet.title == "  Packing List  "

    def test_detect_sheets_first_match_wins(
        self, make_workbook: Any, app_config: AppConfig
    ) -> None:
        """Edge case: multiple sheets that could match invoice pattern.

        First matching sheet should be selected. Tab order is preserved.
        """
        # Create workbook with two invoice-like sheets
        wb = make_workbook(sheets=["Invoice", "Commercial Invoice", "Packing List"])
        result = detect_sheets(wb, app_config)

        # First invoice match should be "Invoice"
        assert result.invoice_sheet.title == "Invoice"
        assert result.packing_sheet.title == "Packing List"
