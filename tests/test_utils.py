"""Tests for autoconvert.utils."""

from __future__ import annotations

import re
from decimal import Decimal

import pytest

from autoconvert.errors import ErrorCode, ProcessingError
from autoconvert.utils import (
    DITTO_MARKS,
    FOOTER_KEYWORDS,
    PLACEHOLDER_PATTERN,
    detect_cell_precision,
    is_cell_empty,
    is_placeholder,
    is_stop_keyword,
    normalize_header,
    parse_numeric,
    round_half_up,
    strip_unit_suffix,
)


# ===========================================================================
# strip_unit_suffix
# ===========================================================================


def test_strip_unit_suffix_kg() -> None:
    """Strips a space-separated KG suffix and returns the numeric string."""
    assert strip_unit_suffix("5.2 KG") == "5.2"


def test_strip_unit_suffix_kgs() -> None:
    """Strips KGS suffix with no space between number and suffix."""
    assert strip_unit_suffix("10.5KGS") == "10.5"


def test_strip_unit_suffix_chinese() -> None:
    """Strips Chinese unit characters 件 and 个."""
    assert strip_unit_suffix("1000件") == "1000"
    assert strip_unit_suffix("500个") == "500"


def test_strip_unit_suffix_no_suffix() -> None:
    """Trims leading and trailing whitespace when no unit suffix is present."""
    assert strip_unit_suffix("  3.14  ") == "3.14"


def test_strip_unit_suffix_case_insensitive() -> None:
    """Strips lowercase and mixed-case unit suffixes."""
    assert strip_unit_suffix("7.5 pcs") == "7.5"
    assert strip_unit_suffix("7.5 Ea") == "7.5"


def test_strip_unit_suffix_kgs_before_kg() -> None:
    """KGS is matched before KG to prevent partial stripping of 'K' from 'KGS'."""
    # Regression: naive ordering would strip 'G' or 'KG' from '10 KGS',
    # leaving '10 K'. The regex must try KGS before KG.
    assert strip_unit_suffix("10 KGS") == "10"


def test_strip_unit_suffix_pcs() -> None:
    """Strips PCS suffix."""
    assert strip_unit_suffix("200 PCS") == "200"


def test_strip_unit_suffix_empty_string() -> None:
    """Empty string input returns empty string."""
    assert strip_unit_suffix("") == ""


# ===========================================================================
# round_half_up
# ===========================================================================


def test_round_half_up_standard() -> None:
    """Standard rounding to 2 decimal places."""
    assert round_half_up(Decimal("2.345"), 2) == Decimal("2.35")


def test_round_half_up_half() -> None:
    """0.5 rounds up, not to even (banker's rounding avoidance)."""
    # 0.125 rounded to 2dp must be 0.13, not 0.12 (banker's rounding result).
    assert round_half_up(Decimal("0.125"), 2) == Decimal("0.13")


def test_round_half_up_zero_decimals() -> None:
    """Rounding to 0 decimal places rounds a .7 value up to next integer."""
    assert round_half_up(Decimal("2.7"), 0) == Decimal("3")


def test_round_half_up_five_decimals() -> None:
    """Rounding to 5 decimal places preserves trailing zeros."""
    result = round_half_up(Decimal("1.228001"), 5)
    assert result == Decimal("1.22800")


def test_round_half_up_floating_artifact() -> None:
    """Handles floating-point artifact Decimals without corrupting the value."""
    # Decimal("2.2800000000000002") arises from openpyxl reading floats.
    result = round_half_up(Decimal("2.2800000000000002"), 5)
    assert result == Decimal("2.28000")


def test_round_half_up_half_integer() -> None:
    """2.5 rounds up to 3 (not 2 as banker's rounding would produce)."""
    assert round_half_up(Decimal("2.5"), 0) == Decimal("3")


def test_round_half_up_banker_avoidance_one_decimal() -> None:
    """2.55 rounded to 1dp must be 2.6, not 2.5 (banker's rounding alternative)."""
    assert round_half_up(Decimal("2.55"), 1) == Decimal("2.6")


# ===========================================================================
# parse_numeric
# ===========================================================================


def test_parse_numeric_float() -> None:
    """Float input converts via str to avoid floating-point artifacts."""
    result = parse_numeric(2.28, "nw", 5)
    assert result == Decimal("2.28")
    assert isinstance(result, Decimal)


def test_parse_numeric_int() -> None:
    """Integer input converts directly to Decimal."""
    result = parse_numeric(100, "qty", 3)
    assert result == Decimal("100")


def test_parse_numeric_str_plain() -> None:
    """Plain numeric string converts to Decimal."""
    result = parse_numeric("123.45", "price", 1)
    assert result == Decimal("123.45")


def test_parse_numeric_str_with_unit() -> None:
    """String with unit suffix strips the unit before converting."""
    result = parse_numeric("5.5 KGS", "nw", 7)
    assert result == Decimal("5.5")


def test_parse_numeric_invalid_raises_err_031() -> None:
    """Non-numeric string raises ProcessingError with ERR_031 and context info."""
    with pytest.raises(ProcessingError) as exc_info:
        parse_numeric("ABC", "qty", 10)
    err = exc_info.value
    assert err.code == ErrorCode.ERR_031
    # Error message must contain field name and row for actionable context.
    assert "qty" in err.message
    assert "10" in err.message


def test_parse_numeric_none_raises() -> None:
    """None input raises ProcessingError with ERR_031."""
    with pytest.raises(ProcessingError) as exc_info:
        parse_numeric(None, "nw", 5)
    assert exc_info.value.code == ErrorCode.ERR_031


def test_parse_numeric_bool_raises() -> None:
    """bool input raises ProcessingError because bool is not a valid cell numeric type."""
    with pytest.raises(ProcessingError) as exc_info:
        parse_numeric(True, "flag", 2)
    assert exc_info.value.code == ErrorCode.ERR_031


def test_parse_numeric_float_avoids_artifact() -> None:
    """Float input converts via str(value) to avoid Decimal(float) precision artifacts.

    Decimal(2.28) would produce Decimal('2.279999999...'), but Decimal(str(2.28))
    produces Decimal('2.28'). The implementation uses str conversion for floats.
    """
    # Reason: Decimal(float) captures the full IEEE 754 representation.
    # Decimal(str(float)) uses Python's shortest-repr, which rounds back to the
    # intended value. This test confirms the str-conversion path is taken.
    result = parse_numeric(2.28, "nw", 1)
    assert result == Decimal("2.28")
    # Additional guard: verify Decimal(float) would have been wrong.
    assert Decimal(2.28) != Decimal("2.28"), (
        "Decimal(float) should differ from Decimal(str) — if this fails, "
        "the test premise has changed"
    )


def test_parse_numeric_error_stores_row_and_field() -> None:
    """ProcessingError from parse_numeric stores row and field attributes."""
    with pytest.raises(ProcessingError) as exc_info:
        parse_numeric("bad", "part_no", 42)
    err = exc_info.value
    assert err.row == 42
    assert err.field == "part_no"


# ===========================================================================
# is_placeholder
# ===========================================================================


def test_is_placeholder_slash() -> None:
    """Single and multiple forward slashes are placeholders."""
    assert is_placeholder("/") is True
    assert is_placeholder("///") is True


def test_is_placeholder_asterisks() -> None:
    """Single and multiple asterisks are placeholders."""
    assert is_placeholder("*") is True
    assert is_placeholder("****") is True


def test_is_placeholder_na() -> None:
    """'N/A' and 'n/a' are placeholders (case-insensitive match)."""
    assert is_placeholder("N/A") is True
    assert is_placeholder("n/a") is True


def test_is_placeholder_wu_not_placeholder() -> None:
    """The Chinese character 无 (U+65E0) is NOT a placeholder per PRD FR-011."""
    assert is_placeholder("\u65e0") is False


def test_is_placeholder_dash_variants() -> None:
    """Single dash and em-dash (U+2014) are placeholders."""
    assert is_placeholder("-") is True
    assert is_placeholder("\u2014") is True


def test_is_placeholder_dashes() -> None:
    """Three dashes (common Excel placeholder) is a placeholder."""
    assert is_placeholder("---") is True


def test_is_placeholder_normal_value() -> None:
    """Ordinary strings are not placeholders."""
    assert is_placeholder("CHINA") is False
    assert is_placeholder("CN") is False
    assert is_placeholder("hello") is False


def test_is_placeholder_numeric_string() -> None:
    """A plain numeric string is not a placeholder."""
    assert is_placeholder("123") is False


# ===========================================================================
# detect_cell_precision
# ===========================================================================


def test_detect_cell_precision_fixed_2() -> None:
    """Formats '0.00' and '#,##0.00' both yield 2 decimal places."""
    assert detect_cell_precision(1.23, "0.00") == 2
    assert detect_cell_precision(1.23, "#,##0.00") == 2


def test_detect_cell_precision_fixed_5() -> None:
    """Format '0.00000_' yields 5 decimal places (trailing underscore stripped)."""
    assert detect_cell_precision(1.23456, "0.00000_") == 5


def test_detect_cell_precision_complex_format() -> None:
    """Complex accounting format '_($* #,##0.00_)' yields 2 decimal places."""
    assert detect_cell_precision(1.23, "_($* #,##0.00_)") == 2


def test_detect_cell_precision_general_format() -> None:
    """'General' and empty format both return 5 (max precision for normalization)."""
    assert detect_cell_precision(2.280, "General") == 5
    assert detect_cell_precision(2.28, "") == 5


def test_detect_cell_precision_no_decimal() -> None:
    """Format '0' with no decimal point yields 0 decimal places."""
    assert detect_cell_precision(100, "0") == 0


def test_detect_cell_precision_integer_format() -> None:
    """Format '##0' (no decimal separator) yields 0."""
    assert detect_cell_precision(42, "##0") == 0


def test_detect_cell_precision_returns_int() -> None:
    """Return type is always int."""
    result = detect_cell_precision(1.23, "0.00")
    assert isinstance(result, int)


# ===========================================================================
# normalize_header
# ===========================================================================


def test_normalize_header_newline() -> None:
    """Embedded newline is collapsed to a single space and result is lowercased."""
    assert normalize_header("N.W.\n(KGS)") == "n.w. (kgs)"


def test_normalize_header_tab() -> None:
    """Tab character is collapsed to a single space."""
    assert normalize_header("Part\tNo") == "part no"


def test_normalize_header_multiple_spaces() -> None:
    """Leading/trailing whitespace is stripped."""
    assert normalize_header("  qty  ") == "qty"


def test_normalize_header_mixed() -> None:
    """Mixed newline + spaces collapses correctly."""
    assert normalize_header("Net WT\n(KGS)") == "net wt (kgs)"


def test_normalize_header_already_normal() -> None:
    """Already-normalized header is returned unchanged."""
    assert normalize_header("part no") == "part no"


def test_normalize_header_uppercase_lowercased() -> None:
    """Uppercase letters are lowercased."""
    assert normalize_header("  HELLO  ") == "hello"


def test_normalize_header_multiple_internal_spaces() -> None:
    """Multiple consecutive spaces are collapsed to one."""
    assert normalize_header("a\t\tb") == "a b"


# ===========================================================================
# is_stop_keyword
# ===========================================================================


def test_is_stop_keyword_total_english() -> None:
    """'TOTAL', 'total', and sentences containing 'total' all match."""
    assert is_stop_keyword("TOTAL") is True
    assert is_stop_keyword("total") is True
    assert is_stop_keyword("Total Amount") is True


def test_is_stop_keyword_chinese() -> None:
    """Chinese stop keywords 合计, 总计, 小计 all match."""
    # Encoding note: these are written as literals; pytest must run with UTF-8.
    assert is_stop_keyword("合计") is True
    assert is_stop_keyword("总计") is True
    assert is_stop_keyword("小计") is True


def test_is_stop_keyword_no_match() -> None:
    """Unrelated strings and empty string return False."""
    assert is_stop_keyword("part no") is False
    assert is_stop_keyword("") is False


def test_is_stop_keyword_embedded() -> None:
    """'GRAND TOTAL' matches because 'total' is a substring (case-insensitive)."""
    assert is_stop_keyword("GRAND TOTAL") is True


def test_is_stop_keyword_subtotal_matches() -> None:
    """'subtotal' matches because 'total' is a substring within it.

    The implementation uses substring matching, so any word containing
    'total' will match. This is the specified behavior (FR-014 / FR-011).
    """
    assert is_stop_keyword("subtotal") is True


def test_is_stop_keyword_negative_hello() -> None:
    """Plain word 'hello' does not match any stop keyword."""
    assert is_stop_keyword("hello") is False


# ===========================================================================
# DITTO_MARKS constant
# ===========================================================================


def test_ditto_marks_contains_all_four() -> None:
    """DITTO_MARKS is a frozenset of exactly 4 recognized ditto characters."""
    assert isinstance(DITTO_MARKS, frozenset)
    assert len(DITTO_MARKS) == 4
    # U+0022 — standard double quotation mark
    assert '"' in DITTO_MARKS
    # U+3003 — ditto mark
    assert "\u3003" in DITTO_MARKS
    # U+201C — left double quotation mark
    assert "\u201c" in DITTO_MARKS
    # U+201D — right double quotation mark
    assert "\u201d" in DITTO_MARKS


def test_ditto_marks_is_immutable() -> None:
    """frozenset cannot be mutated (attempting add raises AttributeError)."""
    with pytest.raises(AttributeError):
        DITTO_MARKS.add("x")  # type: ignore[attr-defined]


# ===========================================================================
# FOOTER_KEYWORDS constant
# ===========================================================================


def test_footer_keywords_tuple() -> None:
    """FOOTER_KEYWORDS is a tuple of exactly 4 Chinese stop strings."""
    assert isinstance(FOOTER_KEYWORDS, tuple)
    assert len(FOOTER_KEYWORDS) == 4
    assert "报关行" in FOOTER_KEYWORDS
    assert "有限公司" in FOOTER_KEYWORDS
    assert "口岸关别" in FOOTER_KEYWORDS
    assert "进境口岸" in FOOTER_KEYWORDS


# ===========================================================================
# PLACEHOLDER_PATTERN constant
# ===========================================================================


def test_placeholder_pattern_compiled() -> None:
    """PLACEHOLDER_PATTERN is a compiled re.Pattern that matches placeholder strings."""
    assert isinstance(PLACEHOLDER_PATTERN, re.Pattern)


def test_placeholder_pattern_matches_slash() -> None:
    """Pattern matches a single forward slash."""
    assert PLACEHOLDER_PATTERN.match("/") is not None


def test_placeholder_pattern_matches_stars() -> None:
    """Pattern matches sequences of asterisks."""
    assert PLACEHOLDER_PATTERN.match("***") is not None


def test_placeholder_pattern_matches_dashes() -> None:
    """Pattern matches sequences of dashes."""
    assert PLACEHOLDER_PATTERN.match("--") is not None


def test_placeholder_pattern_no_match_wu() -> None:
    """Pattern does NOT match 无 (U+65E0)."""
    assert PLACEHOLDER_PATTERN.match("\u65e0") is None


def test_placeholder_pattern_no_match_na() -> None:
    """Pattern does NOT match 'N/A' (is_placeholder handles N/A separately)."""
    assert PLACEHOLDER_PATTERN.match("N/A") is None


# ===========================================================================
# is_cell_empty
# ===========================================================================


def test_is_cell_empty_none() -> None:
    """None is treated as an empty cell."""
    assert is_cell_empty(None) is True


def test_is_cell_empty_whitespace_only() -> None:
    """Whitespace-only strings are treated as empty."""
    assert is_cell_empty("   ") is True
    assert is_cell_empty("\t") is True
    assert is_cell_empty("") is True


def test_is_cell_empty_zero_string() -> None:
    """The string '0' is not empty (it contains a non-whitespace character)."""
    assert is_cell_empty("0") is False


def test_is_cell_empty_numeric_value() -> None:
    """Numeric values (int, float) are never empty."""
    assert is_cell_empty(0) is False
    assert is_cell_empty(0.0) is False
    assert is_cell_empty(42) is False


def test_is_cell_empty_normal_string() -> None:
    """Normal non-empty strings are not empty."""
    assert is_cell_empty("CHINA") is False
    assert is_cell_empty("1.5") is False
