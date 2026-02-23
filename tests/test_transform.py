"""Tests for autoconvert.transform.

Covers FR-018 (convert_currency), FR-019 (convert_country),
and FR-020 (clean_po_number) acceptance criteria.

Tests use minimal AppConfig objects constructed in-memory — the real
config files are not loaded here so tests run without the config/ directory.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from autoconvert.errors import WarningCode
from autoconvert.models import AppConfig, InvNoCellConfig, InvoiceItem
from autoconvert.transform import clean_po_number, convert_country, convert_currency

# A do-nothing InvNoCellConfig used by _make_app_config.
_EMPTY_INV_NO_CELL = InvNoCellConfig(
    patterns=[],
    label_patterns=[],
    exclude_patterns=[],
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_app_config(
    currency_lookup: dict[str, str] | None = None,
    country_lookup: dict[str, str] | None = None,
) -> AppConfig:
    """Build a minimal AppConfig suitable for transform tests.

    Uses MagicMock for fields that transform.py does not touch so that
    we don't need to load YAML or xlsx files.

    Args:
        currency_lookup: Custom currency lookup dict (already normalized).
        country_lookup: Custom country lookup dict (already normalized).

    Returns:
        AppConfig instance with the given lookup tables.
    """
    return AppConfig(
        invoice_sheet_patterns=[],
        packing_sheet_patterns=[],
        invoice_columns={},
        packing_columns={},
        inv_no_cell=_EMPTY_INV_NO_CELL,
        currency_lookup=currency_lookup or {},
        country_lookup=country_lookup or {},
        output_template_path=Path("/dev/null"),
        invoice_min_headers=7,
        packing_min_headers=4,
    )


def _make_item(**overrides: object) -> InvoiceItem:
    """Create a minimal InvoiceItem with sensible defaults for testing.

    Args:
        **overrides: Field values to override on the default item.

    Returns:
        InvoiceItem instance.
    """
    defaults: dict[str, object] = {
        "part_no": "PART-001",
        "po_no": "PO12345",
        "qty": Decimal("10"),
        "price": Decimal("1.00"),
        "amount": Decimal("10.00"),
        "currency": "USD",
        "coo": "CHINA",
        "cod": None,
        "brand": "TestBrand",
        "brand_type": "TypeA",
        "model": "M100",
        "inv_no": "INV-001",
        "serial": None,
        "allocated_weight": None,
    }
    defaults.update(overrides)
    return InvoiceItem(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# FR-018: convert_currency
# ---------------------------------------------------------------------------


class TestConvertCurrency:
    """Tests for convert_currency (FR-018)."""

    def test_convert_currency_known_code(self) -> None:
        """Happy path: 'USD' maps to '502' via currency_lookup."""
        config = _make_app_config(currency_lookup={"USD": "502"})
        items = [_make_item(currency="USD")]

        result_items, warnings = convert_currency(items, config)

        assert len(result_items) == 1
        assert result_items[0].currency == "502"
        assert warnings == []

    def test_convert_currency_unknown_code(self) -> None:
        """Error case: 'XYZ' not in lookup — raw value preserved + ATT_003."""
        config = _make_app_config(currency_lookup={"USD": "502"})
        items = [_make_item(currency="XYZ")]

        result_items, warnings = convert_currency(items, config)

        assert result_items[0].currency == "XYZ"
        assert len(warnings) == 1
        assert warnings[0].code == WarningCode.ATT_003

    def test_convert_currency_case_insensitive(self) -> None:
        """Edge case: lowercase 'usd' must match UPPERCASE lookup key 'USD'."""
        config = _make_app_config(currency_lookup={"USD": "502"})
        items = [_make_item(currency="usd")]

        result_items, warnings = convert_currency(items, config)

        assert result_items[0].currency == "502"
        assert warnings == []

    def test_convert_currency_mixed_case(self) -> None:
        """Edge case: mixed case 'Usd' must also match via normalization."""
        config = _make_app_config(currency_lookup={"USD": "502"})
        items = [_make_item(currency="Usd")]

        result_items, warnings = convert_currency(items, config)

        assert result_items[0].currency == "502"
        assert warnings == []

    def test_convert_currency_does_not_mutate_input(self) -> None:
        """Side-effect rule: original item list must not be modified."""
        config = _make_app_config(currency_lookup={"USD": "502"})
        original = _make_item(currency="USD")
        items = [original]

        convert_currency(items, config)

        # Original InvoiceItem object is unchanged.
        assert original.currency == "USD"

    def test_convert_currency_empty_list(self) -> None:
        """Edge case: empty input produces empty output with no warnings."""
        config = _make_app_config(currency_lookup={"USD": "502"})

        result_items, warnings = convert_currency([], config)

        assert result_items == []
        assert warnings == []

    def test_convert_currency_warning_contains_actionable_message(self) -> None:
        """ATT_003 warning message must contain the raw unmatched value."""
        config = _make_app_config(currency_lookup={})
        items = [_make_item(currency="UNKNOWN_CUR")]

        _, warnings = convert_currency(items, config)

        assert "UNKNOWN_CUR" in warnings[0].message
        assert warnings[0].field == "currency"


# ---------------------------------------------------------------------------
# FR-019: convert_country
# ---------------------------------------------------------------------------


class TestConvertCountry:
    """Tests for convert_country (FR-019)."""

    def test_convert_country_known_code(self) -> None:
        """Happy path: 'CHINA' maps to an expected numeric code."""
        config = _make_app_config(country_lookup={"CHINA": "142"})
        items = [_make_item(coo="CHINA")]

        result_items, warnings = convert_country(items, config)

        assert result_items[0].coo == "142"
        assert warnings == []

    def test_convert_country_unknown_code(self) -> None:
        """Error case: 'ATLANTIS' not in lookup — raw value preserved + ATT_004."""
        config = _make_app_config(country_lookup={"CHINA": "142"})
        items = [_make_item(coo="ATLANTIS")]

        result_items, warnings = convert_country(items, config)

        assert result_items[0].coo == "ATLANTIS"
        assert len(warnings) == 1
        assert warnings[0].code == WarningCode.ATT_004

    def test_convert_country_comma_spacing(self) -> None:
        """Edge case: 'Taiwan, China' (space after comma) matches 'TAIWAN,CHINA'."""
        config = _make_app_config(country_lookup={"TAIWAN,CHINA": "158"})
        items = [_make_item(coo="Taiwan, China")]

        result_items, warnings = convert_country(items, config)

        assert result_items[0].coo == "158"
        assert warnings == []

    def test_convert_country_case_insensitive(self) -> None:
        """Edge case: lowercase 'china' must match stored key 'CHINA'."""
        config = _make_app_config(country_lookup={"CHINA": "142"})
        items = [_make_item(coo="china")]

        result_items, warnings = convert_country(items, config)

        assert result_items[0].coo == "142"
        assert warnings == []

    def test_convert_country_target_code_is_str(self) -> None:
        """Type edge case: returned coo must be str even if lookup value was int-like."""
        # config normalises int->str at load time; simulate a str "142".
        config = _make_app_config(country_lookup={"CHINA": "142"})
        items = [_make_item(coo="CHINA")]

        result_items, _ = convert_country(items, config)

        assert isinstance(result_items[0].coo, str)

    def test_convert_country_does_not_mutate_input(self) -> None:
        """Side-effect rule: original item list must not be modified."""
        config = _make_app_config(country_lookup={"CHINA": "142"})
        original = _make_item(coo="CHINA")
        items = [original]

        convert_country(items, config)

        assert original.coo == "CHINA"

    def test_convert_country_warning_contains_actionable_message(self) -> None:
        """ATT_004 warning message must contain the raw unmatched value."""
        config = _make_app_config(country_lookup={})
        items = [_make_item(coo="ATLANTIS")]

        _, warnings = convert_country(items, config)

        assert "ATLANTIS" in warnings[0].message
        assert warnings[0].field == "coo"


# ---------------------------------------------------------------------------
# FR-020: clean_po_number
# ---------------------------------------------------------------------------


class TestCleanPoNumber:
    """Tests for clean_po_number (FR-020)."""

    def test_clean_po_number_dash_delimiter(self) -> None:
        """Happy path: '2250600556-2.1' -> '2250600556'."""
        items = [_make_item(po_no="2250600556-2.1")]

        result = clean_po_number(items)

        assert result[0].po_no == "2250600556"

    def test_clean_po_number_dot_delimiter(self) -> None:
        """Happy path: 'PO32741.0' -> 'PO32741'."""
        items = [_make_item(po_no="PO32741.0")]

        result = clean_po_number(items)

        assert result[0].po_no == "PO32741"

    def test_clean_po_number_leading_delimiter(self) -> None:
        """Edge case: '-PO12345' — delimiter at index 0, value preserved."""
        items = [_make_item(po_no="-PO12345")]

        result = clean_po_number(items)

        assert result[0].po_no == "-PO12345"

    def test_clean_po_number_no_delimiter(self) -> None:
        """Edge case: 'PO12345' has no delimiter — unchanged."""
        items = [_make_item(po_no="PO12345")]

        result = clean_po_number(items)

        assert result[0].po_no == "PO12345"

    def test_clean_po_number_slash_delimiter(self) -> None:
        """Edge case: slash is a supported delimiter."""
        items = [_make_item(po_no="PO12345/A")]

        result = clean_po_number(items)

        assert result[0].po_no == "PO12345"

    def test_clean_po_number_does_not_mutate_input(self) -> None:
        """Side-effect rule: original item list must not be modified."""
        original = _make_item(po_no="PO32741.0")
        items = [original]

        clean_po_number(items)

        assert original.po_no == "PO32741.0"

    def test_clean_po_number_empty_list(self) -> None:
        """Edge case: empty input produces empty output."""
        result = clean_po_number([])

        assert result == []

    def test_clean_po_number_returns_new_list(self) -> None:
        """Side-effect rule: returned list must be a new object."""
        items = [_make_item(po_no="PO12345")]

        result = clean_po_number(items)

        assert result is not items
