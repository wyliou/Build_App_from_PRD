"""Sheet detection for AutoConvert.

Identifies invoice and packing sheets within a workbook using
case-insensitive regex matching. Implements FR-004, FR-005, FR-006.
"""

from __future__ import annotations

import logging

from openpyxl.workbook.workbook import Workbook

from autoconvert.errors import ErrorCode, ProcessingError
from autoconvert.models import AppConfig, SheetPair

logger = logging.getLogger(__name__)


def detect_sheets(workbook: Workbook, config: AppConfig) -> SheetPair:
    """Scan all sheet names in workbook against configured regex patterns.

    Scans each sheet name in the workbook (stripped of whitespace) against
    the configured invoice and packing sheet regex patterns (case-insensitive).
    First match wins. Both invoice and packing sheets must be found.

    Args:
        workbook: openpyxl Workbook object (already opened by batch.py).
        config: AppConfig with compiled invoice_sheet_patterns and
            packing_sheet_patterns (case-insensitive, pre-compiled by config.py).

    Returns:
        SheetPair with both matched invoice_sheet and packing_sheet objects.

    Raises:
        ProcessingError: With code ERR_012 if invoice sheet not found.
            Raised immediately before checking packing sheet.
        ProcessingError: With code ERR_013 if packing sheet not found.
    """
    invoice_sheet = None
    packing_sheet = None

    # Reason: Iterate workbook._sheets directly (not workbook.worksheets)
    # because openpyxl's .worksheets property filters by isinstance(Worksheet),
    # which excludes XlrdSheetAdapter objects placed in _sheets for .xls support.
    sheets = workbook._sheets  # type: ignore[attr-defined]
    for ws in sheets:
        sheet_name_stripped = ws.title.strip()

        # Check invoice patterns (if not already found).
        if invoice_sheet is None:
            for pattern in config.invoice_sheet_patterns:
                if pattern.search(sheet_name_stripped):
                    invoice_sheet = ws
                    break

        # Check packing patterns (if not already found).
        if packing_sheet is None:
            for pattern in config.packing_sheet_patterns:
                if pattern.search(sheet_name_stripped):
                    packing_sheet = ws
                    break

        # Early exit if both sheets found.
        if invoice_sheet is not None and packing_sheet is not None:
            break

    # FR-006: Both sheets must be found. Check invoice first.
    if invoice_sheet is None:
        raise ProcessingError(
            code=ErrorCode.ERR_012,
            message="Invoice sheet not found. Checked all sheet names against "
            "configured invoice patterns.",
        )

    if packing_sheet is None:
        raise ProcessingError(
            code=ErrorCode.ERR_013,
            message="Packing sheet not found. Checked all sheet names against "
            "configured packing patterns.",
        )

    return SheetPair(invoice_sheet=invoice_sheet, packing_sheet=packing_sheet)
