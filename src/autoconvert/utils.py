"""Shared utility functions and constants for AutoConvert.

Pure functions and constants imported by 2+ consumer modules.
No file I/O, no logging, no global state mutation.
"""

from __future__ import annotations

import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from autoconvert.errors import ErrorCode, ProcessingError

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DITTO_MARKS: frozenset[str] = frozenset({'"', '\u3003', '\u201c', '\u201d'})
"""Recognized ditto mark characters (U+0022, U+3003, U+201C, U+201D)."""

FOOTER_KEYWORDS: tuple[str, ...] = ("报关行", "有限公司", "口岸关别", "进境口岸")
"""Chinese footer keywords that terminate invoice extraction (FR-011 stop condition 3)."""

PLACEHOLDER_PATTERN: re.Pattern[str] = re.compile(r'^[/\\*\-\u2014]+$')
"""Pre-compiled regex for placeholder detection: strings of /, \\, *, -, or em-dash."""

# Regex for stripping trailing unit suffixes (longest match first to avoid partial stripping).
_UNIT_SUFFIX_RE: re.Pattern[str] = re.compile(
    r'(?:KGS|KG|LBS|LB|PCS|EA|件|个|G)\s*$',
    re.IGNORECASE,
)

# Stop keywords for total row detection (case-insensitive).
_STOP_KEYWORDS: tuple[str, ...] = ("total", "合计", "总计", "小计")


# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------


def strip_unit_suffix(value: str) -> str:
    """Strip trailing unit suffixes and whitespace from a string value.

    Removes trailing KG, KGS, G, LB, LBS, PCS, EA, 件, 个 (case-insensitive)
    and leading/trailing whitespace.

    Args:
        value: The string to clean, typically a cell value converted to str.

    Returns:
        Cleaned string ready for numeric parsing.
    """
    stripped = value.strip()
    return _UNIT_SUFFIX_RE.sub("", stripped).strip()


def round_half_up(value: Decimal, decimals: int) -> Decimal:
    """Round a Decimal using ROUND_HALF_UP semantics.

    Uses proper Decimal quantize with ROUND_HALF_UP rounding mode.
    This ensures 0.5 always rounds away from zero (e.g., 0.125 -> 0.13 at 2dp).
    Never uses Python's built-in round() which applies banker's rounding.

    Args:
        value: The Decimal value to round.
        decimals: Number of decimal places (>= 0).

    Returns:
        Decimal quantized to the specified number of decimal places.
    """
    quantizer = Decimal(10) ** -decimals
    return value.quantize(quantizer, rounding=ROUND_HALF_UP)


def parse_numeric(value: Any, field_name: str, row: int) -> Decimal:
    """Convert a cell value to Decimal.

    Handles str (strips units first), int, and float types. Raises
    ProcessingError with ERR_031 for unexpected types or parse failures.

    Args:
        value: The cell value from openpyxl (any type).
        field_name: Name of the field being parsed (for error context).
        row: Row number in the sheet (1-based, for error context).

    Returns:
        Decimal representation of the value.

    Raises:
        ProcessingError: With code ERR_031 when value cannot be parsed.
    """
    try:
        if isinstance(value, str):
            cleaned = strip_unit_suffix(value)
            return Decimal(cleaned)
        if isinstance(value, int) and not isinstance(value, bool):
            # Reason: bool is a subclass of int in Python; we must reject it explicitly.
            return Decimal(value)
        if isinstance(value, float):
            # Reason: Decimal(str(float)) avoids floating-point artifacts like 2.2800000...02.
            return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ProcessingError(
            code=ErrorCode.ERR_031,
            message=f"Invalid numeric value '{value}' at row {row}, field '{field_name}'",
            row=row,
            field=field_name,
        ) from exc

    # None, bool, datetime, or any other unexpected type
    raise ProcessingError(
        code=ErrorCode.ERR_031,
        message=f"Invalid numeric value '{value}' at row {row}, field '{field_name}'",
        row=row,
        field=field_name,
    )


def is_placeholder(value: str) -> bool:
    """Check whether a string value is a placeholder.

    Returns True if value matches the placeholder pattern (strings consisting
    entirely of /, \\, *, -, or em-dash) or case-insensitive "N/A".
    Returns False for the Chinese character 无 (U+65E0) which is a valid value.

    Args:
        value: The string to check.

    Returns:
        True if the value is a placeholder, False otherwise.
    """
    if value.strip().upper() == "N/A":
        return True
    return bool(PLACEHOLDER_PATTERN.match(value.strip()))


def detect_cell_precision(cell_value: Any, number_format: str) -> int:
    """Determine the number of decimal places from an openpyxl number format string.

    Handles formats like "0.00", "#,##0.00", "_($* #,##0.00_)", "0.00000_".
    For "General" or empty format, returns 5 as the initial precision value.
    Callers (e.g., extract_packing FR-015) then round to 5 decimals, convert to
    string, and strip trailing zeros to get the visible precision.

    Args:
        cell_value: The cell's value (unused for explicit formats; reserved for
            future General-format value-based precision if needed).
        number_format: The openpyxl number_format string from the cell.

    Returns:
        Integer number of decimal places (0 to 5).
    """
    fmt = number_format.strip() if number_format else ""

    # General or empty format: return 5 as the initial precision value.
    # Reason: Callers round to 5 decimals then normalize trailing zeros to get
    # the visible precision. This is specified in build-plan.md Section 6.5.
    if fmt == "" or fmt.lower() == "general":
        return 5

    # Strip trailing underscore padding characters (e.g., "0.00000_" -> "0.00000")
    # Reason: openpyxl format strings use _ as a padding char meaning "space equal to next char width".
    cleaned_fmt = fmt.rstrip("_) ")

    # Find the decimal point and count digits after it
    dot_idx = cleaned_fmt.rfind(".")
    if dot_idx == -1:
        return 0

    # Count only digit-placeholder characters (0, #) after the decimal point
    after_dot = cleaned_fmt[dot_idx + 1:]
    count = sum(1 for ch in after_dot if ch in ("0", "#"))
    return min(count, 5)



def normalize_header(value: str) -> str:
    """Normalize a column header string for regex matching.

    Collapses newlines, tabs, and multiple spaces to a single space,
    strips leading/trailing whitespace, and returns lowercased string.

    Args:
        value: The raw header string from an Excel cell.

    Returns:
        Normalized lowercase header string.
    """
    # Reason: Excel headers often contain embedded newlines like "N.W.\\n(KGS)".
    collapsed = re.sub(r'[\n\t]+', ' ', value)
    collapsed = re.sub(r' {2,}', ' ', collapsed)
    return collapsed.strip().lower()


def is_cell_empty(value: object) -> bool:
    """Return True if a cell value is None or a whitespace-only string.

    Used by extraction modules to determine whether a cell should be
    treated as empty (no data present).

    Args:
        value: Raw cell value from openpyxl or an xlrd adapter.

    Returns:
        True when the value is None or a string containing only whitespace.
    """
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    return False


def is_stop_keyword(value: str) -> bool:
    """Check whether a string contains a stop keyword (case-insensitive).

    Stop keywords indicate total/subtotal rows: "total", "合计", "总计", "小计".
    The check is a substring match (e.g., "GRAND TOTAL" matches).

    Args:
        value: The string to check.

    Returns:
        True if the value contains any stop keyword, False otherwise.
    """
    if not value:
        return False
    lowered = value.lower()
    for keyword in _STOP_KEYWORDS:
        if keyword in lowered:
            return True
    return False
