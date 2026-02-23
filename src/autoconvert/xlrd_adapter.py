"""Lightweight adapter wrapping xlrd.Sheet to provide openpyxl-like interface.

Normalizes xlrd's 0-based indexing to 1-based (openpyxl convention) so that
all downstream extraction modules work uniformly with both .xlsx and .xls files.
"""

from __future__ import annotations

from typing import Any

import xlrd  # type: ignore[import-untyped]


class _CellProxy:
    """Minimal cell proxy matching openpyxl Cell.value and number_format.

    Attributes:
        value: The cell value (converted from xlrd types).
        number_format: Always "General" for xlrd cells (format detection
            is not supported for .xls files).
    """

    __slots__ = ("value", "number_format")

    def __init__(self, value: Any) -> None:
        """Initialize a cell proxy.

        Args:
            value: The cell value from xlrd.
        """
        self.value = value
        self.number_format: str = "General"


class XlrdSheetAdapter:
    """Adapts an xlrd.Sheet to provide openpyxl Worksheet-compatible interface.

    Converts xlrd's 0-based row/column indices to 1-based indices so that
    extraction modules using ``sheet.cell(row=r, column=c).value`` work
    identically for both .xlsx and .xls files.

    Attributes:
        _sheet: The underlying xlrd.Sheet object.
        max_row: Number of rows (matches openpyxl convention).
        max_column: Number of columns (matches openpyxl convention).
        title: Sheet name string.
    """

    def __init__(self, sheet: xlrd.sheet.Sheet) -> None:
        """Initialize the adapter from an xlrd sheet.

        Args:
            sheet: An xlrd Sheet object.
        """
        self._sheet = sheet
        self.max_row: int = sheet.nrows
        self.max_column: int = sheet.ncols
        self.title: str = sheet.name

    def cell(self, row: int = 1, column: int = 1) -> _CellProxy:
        """Read a cell value using 1-based row and column indices.

        Converts from 1-based (openpyxl convention) to 0-based (xlrd
        convention) before delegating to xlrd.Sheet.cell_value().

        Args:
            row: 1-based row index.
            column: 1-based column index.

        Returns:
            A _CellProxy with .value and .number_format attributes.
        """
        # Reason: openpyxl uses 1-based; xlrd uses 0-based.
        xlrd_row = row - 1
        xlrd_col = column - 1

        # Bounds check: return empty cell for out-of-range access
        if xlrd_row < 0 or xlrd_row >= self._sheet.nrows:
            return _CellProxy(None)
        if xlrd_col < 0 or xlrd_col >= self._sheet.ncols:
            return _CellProxy(None)

        try:
            value = self._sheet.cell_value(xlrd_row, xlrd_col)
        except (IndexError, Exception):  # noqa: BLE001
            return _CellProxy(None)

        # Reason: xlrd returns empty strings for empty cells;
        # openpyxl returns None. Normalize to openpyxl convention.
        if value == "":
            return _CellProxy(None)

        return _CellProxy(value)

    @property
    def merged_cells(self) -> _EmptyMergedCells:
        """Return an empty merged cells container.

        xlrd has limited merge support. MergeTracker will receive
        a sheet with no merge data, which is acceptable per the spec.

        Returns:
            An object with an empty .ranges attribute.
        """
        return _EmptyMergedCells()


class _EmptyMergedCells:
    """Stub for merged_cells attribute — returns empty ranges.

    xlrd does not expose merge ranges in the same format as openpyxl.
    This stub allows MergeTracker to construct without error but will
    find no merge ranges to track.
    """

    @property
    def ranges(self) -> list[Any]:
        """Return an empty list of merge ranges.

        Returns:
            Empty list.
        """
        return []
