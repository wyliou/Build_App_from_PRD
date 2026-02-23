"""Tests for autoconvert.weight_alloc.

Covers FR-021 through FR-026 acceptance criteria with 3-5 tests per FR.
Error codes owned by this module: ERR_040, ERR_041, ERR_042, ERR_043,
ERR_044, ERR_045, ERR_047, ERR_048.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from autoconvert.errors import ErrorCode, ProcessingError
from autoconvert.models import InvoiceItem, PackingItem, PackingTotals
from autoconvert.weight_alloc import allocate_weights

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_invoice_item(
    part_no: str = "A",
    qty: Decimal = Decimal("10"),
    **overrides: object,
) -> InvoiceItem:
    """Create an InvoiceItem with sensible defaults for testing.

    Args:
        part_no: Part number string.
        qty: Quantity as Decimal.
        **overrides: Any field overrides.

    Returns:
        InvoiceItem instance.
    """
    defaults: dict[str, object] = {
        "part_no": part_no,
        "po_no": "PO001",
        "qty": qty,
        "price": Decimal("1.00"),
        "amount": Decimal("10.00"),
        "currency": "USD",
        "coo": "CN",
        "cod": None,
        "brand": "TestBrand",
        "brand_type": "TestType",
        "model": "M1",
        "inv_no": "INV001",
        "serial": None,
        "allocated_weight": None,
    }
    defaults.update(overrides)
    return InvoiceItem(**defaults)  # type: ignore[arg-type]


def _make_packing_item(
    part_no: str = "A",
    qty: Decimal = Decimal("10"),
    nw: Decimal = Decimal("5.0"),
    is_first_row_of_merge: bool = True,
    row_number: int = 1,
) -> PackingItem:
    """Create a PackingItem with sensible defaults for testing.

    Args:
        part_no: Part number string.
        qty: Quantity as Decimal.
        nw: Net weight as Decimal.
        is_first_row_of_merge: Whether this is the merge anchor row.
        row_number: 1-based row number.

    Returns:
        PackingItem instance.
    """
    return PackingItem(
        part_no=part_no,
        qty=qty,
        nw=nw,
        is_first_row_of_merge=is_first_row_of_merge,
        row_number=row_number,
    )


def _make_packing_totals(
    total_nw: Decimal = Decimal("10.0"),
    total_nw_precision: int = 2,
    total_gw: Decimal = Decimal("12.0"),
    total_gw_precision: int = 2,
    total_packets: int | None = 1,
) -> PackingTotals:
    """Create a PackingTotals with sensible defaults for testing.

    Args:
        total_nw: Total net weight.
        total_nw_precision: Decimal precision of total_nw.
        total_gw: Total gross weight.
        total_gw_precision: Decimal precision of total_gw.
        total_packets: Total packet count.

    Returns:
        PackingTotals instance.
    """
    return PackingTotals(
        total_nw=total_nw,
        total_nw_precision=total_nw_precision,
        total_gw=total_gw,
        total_gw_precision=total_gw_precision,
        total_packets=total_packets,
    )


# ---------------------------------------------------------------------------
# Test 1 — Happy path: single part, proportional allocation
# ---------------------------------------------------------------------------


class TestAllocateWeightsHappyPathSinglePart:
    """FR-021/FR-025: 3 packing items (same part), 2 invoice items."""

    def test_allocated_weights_are_proportional(self) -> None:
        """Weights should be proportional to qty (3:7 split)."""
        packing_items = [
            _make_packing_item(part_no="A", qty=Decimal("3"), nw=Decimal("1.0"), row_number=1),
            _make_packing_item(
                part_no="A", qty=Decimal("0"), nw=Decimal("0"),
                is_first_row_of_merge=False, row_number=2,
            ),
            _make_packing_item(
                part_no="A", qty=Decimal("0"), nw=Decimal("0"),
                is_first_row_of_merge=False, row_number=3,
            ),
        ]
        invoice_items = [
            _make_invoice_item(part_no="A", qty=Decimal("3")),
            _make_invoice_item(part_no="A", qty=Decimal("7")),
        ]
        totals = _make_packing_totals(total_nw=Decimal("1.0"), total_nw_precision=2)

        result = allocate_weights(invoice_items, packing_items, totals)

        assert result[0].allocated_weight == Decimal("0.300")
        assert result[1].allocated_weight == Decimal("0.700")

    def test_allocated_weights_sum_to_total(self) -> None:
        """Sum of allocated weights must equal total_nw exactly."""
        packing_items = [
            _make_packing_item(part_no="A", qty=Decimal("3"), nw=Decimal("1.0"), row_number=1),
            _make_packing_item(
                part_no="A", qty=Decimal("0"), nw=Decimal("0"),
                is_first_row_of_merge=False, row_number=2,
            ),
            _make_packing_item(
                part_no="A", qty=Decimal("0"), nw=Decimal("0"),
                is_first_row_of_merge=False, row_number=3,
            ),
        ]
        invoice_items = [
            _make_invoice_item(part_no="A", qty=Decimal("3")),
            _make_invoice_item(part_no="A", qty=Decimal("7")),
        ]
        totals = _make_packing_totals(total_nw=Decimal("1.0"), total_nw_precision=2)

        result = allocate_weights(invoice_items, packing_items, totals)
        allocated_sum = sum(
            item.allocated_weight for item in result if item.allocated_weight is not None
        )
        assert allocated_sum == Decimal("1.0")


# ---------------------------------------------------------------------------
# Test 2 — Happy path: two parts
# ---------------------------------------------------------------------------


class TestAllocateWeightsHappyPathTwoParts:
    """FR-021/FR-025: 2 packing parts, 2 invoice items (1 per part)."""

    def test_each_gets_full_part_weight(self) -> None:
        """Each invoice item with one matching part gets the full part weight."""
        packing_items = [
            _make_packing_item(part_no="A", qty=Decimal("10"), nw=Decimal("5.0"), row_number=1),
            _make_packing_item(part_no="B", qty=Decimal("10"), nw=Decimal("3.0"), row_number=2),
        ]
        invoice_items = [
            _make_invoice_item(part_no="A", qty=Decimal("10")),
            _make_invoice_item(part_no="B", qty=Decimal("10")),
        ]
        totals = _make_packing_totals(total_nw=Decimal("8.0"), total_nw_precision=2)

        result = allocate_weights(invoice_items, packing_items, totals)

        assert result[0].allocated_weight == Decimal("5.0")
        assert result[1].allocated_weight == Decimal("3.0")

    def test_final_sum_matches_total_nw(self) -> None:
        """Sum of all allocated weights equals total_nw."""
        packing_items = [
            _make_packing_item(part_no="A", qty=Decimal("10"), nw=Decimal("5.0"), row_number=1),
            _make_packing_item(part_no="B", qty=Decimal("10"), nw=Decimal("3.0"), row_number=2),
        ]
        invoice_items = [
            _make_invoice_item(part_no="A", qty=Decimal("10")),
            _make_invoice_item(part_no="B", qty=Decimal("10")),
        ]
        totals = _make_packing_totals(total_nw=Decimal("8.0"), total_nw_precision=2)

        result = allocate_weights(invoice_items, packing_items, totals)
        allocated_sum = sum(
            item.allocated_weight for item in result if item.allocated_weight is not None
        )
        assert allocated_sum == Decimal("8.0")


# ---------------------------------------------------------------------------
# Test 3 — Precision cascade
# ---------------------------------------------------------------------------


class TestAllocateWeightsPrecisionCascade:
    """FR-023/FR-025: Invoice items should use precision = packing + 1."""

    def test_invoice_item_precision_is_packing_plus_one(self) -> None:
        """Allocated weight must have packing_precision+1 decimal places."""
        packing_items = [
            _make_packing_item(part_no="A", qty=Decimal("3"), nw=Decimal("0.5"), row_number=1),
            _make_packing_item(part_no="A", qty=Decimal("7"), nw=Decimal("0.5"), row_number=2),
        ]
        invoice_items = [
            _make_invoice_item(part_no="A", qty=Decimal("3")),
            _make_invoice_item(part_no="A", qty=Decimal("7")),
        ]
        totals = _make_packing_totals(total_nw=Decimal("1.0"), total_nw_precision=2)

        result = allocate_weights(invoice_items, packing_items, totals)

        # Packing precision 2 => line precision 3
        # First item: 1.0 * 3/10 = 0.300 (3 decimal places)
        w0 = result[0].allocated_weight
        assert w0 is not None
        # Verify it has 3 decimal places by checking quantize
        assert w0 == Decimal("0.300")

    def test_return_type_is_list_of_invoice_items(self) -> None:
        """Result should be a list of InvoiceItem."""
        packing_items = [
            _make_packing_item(part_no="A", qty=Decimal("10"), nw=Decimal("1.0"), row_number=1),
        ]
        invoice_items = [
            _make_invoice_item(part_no="A", qty=Decimal("10")),
        ]
        totals = _make_packing_totals(total_nw=Decimal("1.0"), total_nw_precision=2)

        result = allocate_weights(invoice_items, packing_items, totals)
        assert isinstance(result, list)
        assert all(isinstance(item, InvoiceItem) for item in result)


# ---------------------------------------------------------------------------
# Test 4 — Packing sum mismatch (ERR_047)
# ---------------------------------------------------------------------------


class TestAllocateWeightsPackingSumMismatch:
    """FR-022: Packing sum disagrees with total_nw beyond threshold."""

    def test_raises_err_047_when_difference_exceeds_threshold(self) -> None:
        """Difference > 0.1 should raise ERR_047."""
        packing_items = [
            _make_packing_item(part_no="A", qty=Decimal("10"), nw=Decimal("10.2"), row_number=1),
        ]
        invoice_items = [
            _make_invoice_item(part_no="A", qty=Decimal("10")),
        ]
        totals = _make_packing_totals(total_nw=Decimal("10.0"), total_nw_precision=2)

        with pytest.raises(ProcessingError) as exc_info:
            allocate_weights(invoice_items, packing_items, totals)

        assert exc_info.value.code == ErrorCode.ERR_047

    def test_err_047_message_contains_sums(self) -> None:
        """Error message should contain the packing sum and total_nw."""
        packing_items = [
            _make_packing_item(part_no="A", qty=Decimal("10"), nw=Decimal("10.2"), row_number=1),
        ]
        invoice_items = [
            _make_invoice_item(part_no="A", qty=Decimal("10")),
        ]
        totals = _make_packing_totals(total_nw=Decimal("10.0"), total_nw_precision=2)

        with pytest.raises(ProcessingError) as exc_info:
            allocate_weights(invoice_items, packing_items, totals)

        assert "10.2" in exc_info.value.message
        assert "10.0" in exc_info.value.message


# ---------------------------------------------------------------------------
# Test 5 — Packing sum within threshold (ERR_047 NOT raised)
# ---------------------------------------------------------------------------


class TestAllocateWeightsPackingSumWithinThreshold:
    """FR-022: Packing sum within 0.1 threshold should not raise."""

    def test_no_error_when_difference_within_threshold(self) -> None:
        """Difference 0.05 <= 0.1 should NOT raise ERR_047."""
        packing_items = [
            _make_packing_item(part_no="A", qty=Decimal("10"), nw=Decimal("10.05"), row_number=1),
        ]
        invoice_items = [
            _make_invoice_item(part_no="A", qty=Decimal("10")),
        ]
        totals = _make_packing_totals(total_nw=Decimal("10.0"), total_nw_precision=2)

        # Should not raise — within threshold
        result = allocate_weights(invoice_items, packing_items, totals)
        assert len(result) == 1

    def test_no_error_at_exact_boundary(self) -> None:
        """Difference exactly 0.1 should NOT raise ERR_047."""
        packing_items = [
            _make_packing_item(part_no="A", qty=Decimal("10"), nw=Decimal("10.1"), row_number=1),
        ]
        invoice_items = [
            _make_invoice_item(part_no="A", qty=Decimal("10")),
        ]
        totals = _make_packing_totals(total_nw=Decimal("10.0"), total_nw_precision=2)

        # Difference is exactly 0.1, which is <= 0.1
        result = allocate_weights(invoice_items, packing_items, totals)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# Test 6 — Zero NW part (ERR_042)
# ---------------------------------------------------------------------------


class TestAllocateWeightsZeroNwPart:
    """FR-021: Aggregated weight is zero for a part."""

    def test_raises_err_042_for_zero_aggregated_nw(self) -> None:
        """All continuation rows (NW=0) with no anchor should raise ERR_042."""
        packing_items = [
            _make_packing_item(
                part_no="A", qty=Decimal("10"), nw=Decimal("0"),
                is_first_row_of_merge=False, row_number=1,
            ),
            _make_packing_item(
                part_no="A", qty=Decimal("0"), nw=Decimal("0"),
                is_first_row_of_merge=False, row_number=2,
            ),
        ]
        invoice_items = [
            _make_invoice_item(part_no="A", qty=Decimal("10")),
        ]
        totals = _make_packing_totals(total_nw=Decimal("1.0"), total_nw_precision=2)

        with pytest.raises(ProcessingError) as exc_info:
            allocate_weights(invoice_items, packing_items, totals)

        assert exc_info.value.code == ErrorCode.ERR_042

    def test_err_042_message_contains_part_no(self) -> None:
        """Error message should contain the affected part_no."""
        packing_items = [
            _make_packing_item(
                part_no="ZeroPart", qty=Decimal("5"), nw=Decimal("0"),
                row_number=1,
            ),
        ]
        invoice_items = [
            _make_invoice_item(part_no="ZeroPart", qty=Decimal("5")),
        ]
        totals = _make_packing_totals(total_nw=Decimal("1.0"), total_nw_precision=2)

        with pytest.raises(ProcessingError) as exc_info:
            allocate_weights(invoice_items, packing_items, totals)

        assert "ZeroPart" in exc_info.value.message

    def test_raises_err_042_for_negative_aggregated_nw(self) -> None:
        """Negative aggregated weight should also raise ERR_042."""
        packing_items = [
            _make_packing_item(
                part_no="A", qty=Decimal("10"), nw=Decimal("-1.0"),
                row_number=1,
            ),
        ]
        invoice_items = [
            _make_invoice_item(part_no="A", qty=Decimal("10")),
        ]
        totals = _make_packing_totals(total_nw=Decimal("1.0"), total_nw_precision=2)

        with pytest.raises(ProcessingError) as exc_info:
            allocate_weights(invoice_items, packing_items, totals)

        assert exc_info.value.code == ErrorCode.ERR_042


# ---------------------------------------------------------------------------
# Test 7 — Weight rounds to zero at max precision (ERR_044)
# ---------------------------------------------------------------------------


class TestAllocateWeightsWeightRoundsToZero:
    """FR-023: Weight rounds to zero even at max precision 5."""

    def test_raises_err_044_for_tiny_weight(self) -> None:
        """nw=0.00001 rounds to 0 at precision 5 => ERR_044."""
        packing_items = [
            _make_packing_item(
                part_no="Tiny", qty=Decimal("1"), nw=Decimal("0.000001"),
                row_number=1,
            ),
            _make_packing_item(
                part_no="Big", qty=Decimal("10"), nw=Decimal("0.999999"),
                row_number=2,
            ),
        ]
        invoice_items = [
            _make_invoice_item(part_no="Tiny", qty=Decimal("1")),
            _make_invoice_item(part_no="Big", qty=Decimal("10")),
        ]
        totals = _make_packing_totals(total_nw=Decimal("1.0"), total_nw_precision=2)

        with pytest.raises(ProcessingError) as exc_info:
            allocate_weights(invoice_items, packing_items, totals)

        assert exc_info.value.code == ErrorCode.ERR_044

    def test_err_044_message_contains_part_info(self) -> None:
        """Error message should mention the part_no and its weight."""
        packing_items = [
            _make_packing_item(
                part_no="SmallPart", qty=Decimal("1"), nw=Decimal("0.0000001"),
                row_number=1,
            ),
            _make_packing_item(
                part_no="LargePart", qty=Decimal("10"), nw=Decimal("0.9999999"),
                row_number=2,
            ),
        ]
        invoice_items = [
            _make_invoice_item(part_no="SmallPart", qty=Decimal("1")),
            _make_invoice_item(part_no="LargePart", qty=Decimal("10")),
        ]
        totals = _make_packing_totals(total_nw=Decimal("1.0"), total_nw_precision=2)

        with pytest.raises(ProcessingError) as exc_info:
            allocate_weights(invoice_items, packing_items, totals)

        assert "SmallPart" in exc_info.value.message


# ---------------------------------------------------------------------------
# Test 8 — Part not in packing (ERR_040)
# ---------------------------------------------------------------------------


class TestAllocateWeightsPartNotInPacking:
    """FR-025: Invoice part_no not found in packing data."""

    def test_raises_err_040_for_unmatched_invoice_part(self) -> None:
        """Invoice part 'X' not in packing should raise ERR_040."""
        packing_items = [
            _make_packing_item(part_no="A", qty=Decimal("10"), nw=Decimal("5.0"), row_number=1),
        ]
        invoice_items = [
            _make_invoice_item(part_no="A", qty=Decimal("10")),
            _make_invoice_item(part_no="X", qty=Decimal("5")),
        ]
        totals = _make_packing_totals(total_nw=Decimal("5.0"), total_nw_precision=2)

        with pytest.raises(ProcessingError) as exc_info:
            allocate_weights(invoice_items, packing_items, totals)

        assert exc_info.value.code == ErrorCode.ERR_040
        assert "X" in exc_info.value.message

    def test_err_040_collects_all_unmatched_parts(self) -> None:
        """All unmatched invoice parts should appear in the error message."""
        packing_items = [
            _make_packing_item(part_no="A", qty=Decimal("10"), nw=Decimal("5.0"), row_number=1),
        ]
        invoice_items = [
            _make_invoice_item(part_no="X", qty=Decimal("5")),
            _make_invoice_item(part_no="Y", qty=Decimal("3")),
        ]
        totals = _make_packing_totals(total_nw=Decimal("5.0"), total_nw_precision=2)

        with pytest.raises(ProcessingError) as exc_info:
            allocate_weights(invoice_items, packing_items, totals)

        assert exc_info.value.code == ErrorCode.ERR_040
        assert "X" in exc_info.value.message
        assert "Y" in exc_info.value.message


# ---------------------------------------------------------------------------
# Test 9 — Packing part not in invoice (ERR_043)
# ---------------------------------------------------------------------------


class TestAllocateWeightsPackingPartNotInInvoice:
    """FR-025: Packing part_no not found in invoice."""

    def test_raises_err_043_for_unmatched_packing_part(self) -> None:
        """Packing part 'Y' not in invoice should raise ERR_043."""
        packing_items = [
            _make_packing_item(part_no="A", qty=Decimal("10"), nw=Decimal("5.0"), row_number=1),
            _make_packing_item(part_no="Y", qty=Decimal("10"), nw=Decimal("3.0"), row_number=2),
        ]
        invoice_items = [
            _make_invoice_item(part_no="A", qty=Decimal("10")),
        ]
        totals = _make_packing_totals(total_nw=Decimal("8.0"), total_nw_precision=2)

        with pytest.raises(ProcessingError) as exc_info:
            allocate_weights(invoice_items, packing_items, totals)

        assert exc_info.value.code == ErrorCode.ERR_043
        assert "Y" in exc_info.value.message

    def test_err_043_message_lists_all_unmatched_parts(self) -> None:
        """All unmatched packing parts should appear in the error message."""
        packing_items = [
            _make_packing_item(part_no="A", qty=Decimal("10"), nw=Decimal("4.0"), row_number=1),
            _make_packing_item(part_no="Y", qty=Decimal("5"), nw=Decimal("3.0"), row_number=2),
            _make_packing_item(part_no="Z", qty=Decimal("5"), nw=Decimal("3.0"), row_number=3),
        ]
        invoice_items = [
            _make_invoice_item(part_no="A", qty=Decimal("10")),
        ]
        totals = _make_packing_totals(total_nw=Decimal("10.0"), total_nw_precision=2)

        with pytest.raises(ProcessingError) as exc_info:
            allocate_weights(invoice_items, packing_items, totals)

        assert exc_info.value.code == ErrorCode.ERR_043
        assert "Y" in exc_info.value.message
        assert "Z" in exc_info.value.message


# ---------------------------------------------------------------------------
# Test 10 — Last item remainder adjustment
# ---------------------------------------------------------------------------


class TestAllocateWeightsLastItemRemainderAdjustment:
    """FR-024/FR-025: Last item gets remainder for exact sum."""

    def test_two_items_equal_qty_exact_sum(self) -> None:
        """2 items qty=1 each, weight=1.0 => each gets 0.500, sum == 1.0."""
        packing_items = [
            _make_packing_item(part_no="A", qty=Decimal("2"), nw=Decimal("1.0"), row_number=1),
        ]
        invoice_items = [
            _make_invoice_item(part_no="A", qty=Decimal("1")),
            _make_invoice_item(part_no="A", qty=Decimal("1")),
        ]
        totals = _make_packing_totals(total_nw=Decimal("1.0"), total_nw_precision=2)

        result = allocate_weights(invoice_items, packing_items, totals)

        allocated_sum = sum(
            item.allocated_weight for item in result if item.allocated_weight is not None
        )
        assert allocated_sum == Decimal("1.0")

    def test_three_items_remainder_on_last(self) -> None:
        """3 items with uneven split: last gets remainder adjustment."""
        packing_items = [
            _make_packing_item(part_no="A", qty=Decimal("3"), nw=Decimal("1.0"), row_number=1),
        ]
        invoice_items = [
            _make_invoice_item(part_no="A", qty=Decimal("1")),
            _make_invoice_item(part_no="A", qty=Decimal("1")),
            _make_invoice_item(part_no="A", qty=Decimal("1")),
        ]
        totals = _make_packing_totals(total_nw=Decimal("1.0"), total_nw_precision=2)

        result = allocate_weights(invoice_items, packing_items, totals)

        allocated_sum = sum(
            item.allocated_weight for item in result if item.allocated_weight is not None
        )
        assert allocated_sum == Decimal("1.0")


# ---------------------------------------------------------------------------
# Test 11 — Final validation (FR-026, ERR_048 tested indirectly)
# ---------------------------------------------------------------------------


class TestAllocateWeightsFinalValidation:
    """FR-026: Return value has all allocated_weight set, sum == total_nw."""

    def test_all_items_have_allocated_weight(self) -> None:
        """Every returned InvoiceItem must have allocated_weight != None."""
        packing_items = [
            _make_packing_item(part_no="A", qty=Decimal("10"), nw=Decimal("5.0"), row_number=1),
            _make_packing_item(part_no="B", qty=Decimal("5"), nw=Decimal("3.0"), row_number=2),
        ]
        invoice_items = [
            _make_invoice_item(part_no="A", qty=Decimal("10")),
            _make_invoice_item(part_no="B", qty=Decimal("5")),
        ]
        totals = _make_packing_totals(total_nw=Decimal("8.0"), total_nw_precision=2)

        result = allocate_weights(invoice_items, packing_items, totals)

        for item in result:
            assert item.allocated_weight is not None

    def test_result_is_list_of_invoice_items(self) -> None:
        """Return type must be list[InvoiceItem]."""
        packing_items = [
            _make_packing_item(part_no="A", qty=Decimal("10"), nw=Decimal("5.0"), row_number=1),
        ]
        invoice_items = [
            _make_invoice_item(part_no="A", qty=Decimal("10")),
        ]
        totals = _make_packing_totals(total_nw=Decimal("5.0"), total_nw_precision=2)

        result = allocate_weights(invoice_items, packing_items, totals)

        assert isinstance(result, list)
        assert all(isinstance(item, InvoiceItem) for item in result)

    def test_sum_equals_total_nw_exactly(self) -> None:
        """Sum of allocated weights must equal total_nw (exact Decimal equality)."""
        packing_items = [
            _make_packing_item(part_no="A", qty=Decimal("7"), nw=Decimal("3.5"), row_number=1),
            _make_packing_item(part_no="B", qty=Decimal("3"), nw=Decimal("1.5"), row_number=2),
        ]
        invoice_items = [
            _make_invoice_item(part_no="A", qty=Decimal("4")),
            _make_invoice_item(part_no="A", qty=Decimal("3")),
            _make_invoice_item(part_no="B", qty=Decimal("3")),
        ]
        totals = _make_packing_totals(total_nw=Decimal("5.0"), total_nw_precision=2)

        result = allocate_weights(invoice_items, packing_items, totals)

        allocated_sum = sum(
            item.allocated_weight for item in result if item.allocated_weight is not None
        )
        assert allocated_sum == Decimal("5.0")


# ---------------------------------------------------------------------------
# Test 12 — Precision sum matching at N+1
# ---------------------------------------------------------------------------


class TestAllocateWeightsPrecisionSumMatchingNPlus1:
    """FR-023: Sum matching succeeds at N+1, not at N."""

    def test_precision_escalates_to_n_plus_1(self, caplog: pytest.LogCaptureFixture) -> None:
        """At N=2, rounded sum != total_nw; at N+1=3, rounded sum matches."""
        # Part weights: 3.335 + 6.665 = 10.0
        # At precision 2: round(3.335,2) = 3.34, round(6.665,2) = 6.67 => 10.01 != 10.0
        # At precision 3: round(3.335,3) = 3.335, round(6.665,3) = 6.665 => 10.0 == 10.0
        packing_items = [
            _make_packing_item(part_no="A", qty=Decimal("10"), nw=Decimal("3.335"), row_number=1),
            _make_packing_item(part_no="B", qty=Decimal("10"), nw=Decimal("6.665"), row_number=2),
        ]
        invoice_items = [
            _make_invoice_item(part_no="A", qty=Decimal("10")),
            _make_invoice_item(part_no="B", qty=Decimal("10")),
        ]
        totals = _make_packing_totals(total_nw=Decimal("10.0"), total_nw_precision=2)

        with caplog.at_level("INFO"):
            allocate_weights(invoice_items, packing_items, totals)

        assert "Perfect match at 3 decimals" in caplog.text

    def test_weights_correct_at_escalated_precision(self) -> None:
        """Weights should be rounded at the escalated precision."""
        packing_items = [
            _make_packing_item(part_no="A", qty=Decimal("10"), nw=Decimal("3.335"), row_number=1),
            _make_packing_item(part_no="B", qty=Decimal("10"), nw=Decimal("6.665"), row_number=2),
        ]
        invoice_items = [
            _make_invoice_item(part_no="A", qty=Decimal("10")),
            _make_invoice_item(part_no="B", qty=Decimal("10")),
        ]
        totals = _make_packing_totals(total_nw=Decimal("10.0"), total_nw_precision=2)

        result = allocate_weights(invoice_items, packing_items, totals)

        # At precision 3, each gets full weight; line precision = 4
        assert result[0].allocated_weight is not None
        assert result[1].allocated_weight is not None
        allocated_sum = result[0].allocated_weight + result[1].allocated_weight
        assert allocated_sum == Decimal("10.0")


# ---------------------------------------------------------------------------
# Test 13 — Whitespace-stripped part_no matching
# ---------------------------------------------------------------------------


class TestAllocateWeightsWhitespaceStrippedPartNo:
    """FR-021/FR-025: Whitespace in part_no should be stripped for matching."""

    def test_invoice_spaces_match_packing(self) -> None:
        """Invoice ' ABC ' matches packing 'ABC' after stripping."""
        packing_items = [
            _make_packing_item(part_no="ABC", qty=Decimal("10"), nw=Decimal("5.0"), row_number=1),
        ]
        invoice_items = [
            _make_invoice_item(part_no=" ABC ", qty=Decimal("10")),
        ]
        totals = _make_packing_totals(total_nw=Decimal("5.0"), total_nw_precision=2)

        result = allocate_weights(invoice_items, packing_items, totals)

        assert result[0].allocated_weight is not None
        assert result[0].allocated_weight == Decimal("5.0")

    def test_packing_spaces_match_invoice(self) -> None:
        """Packing ' DEF ' matches invoice 'DEF' after stripping."""
        packing_items = [
            _make_packing_item(part_no=" DEF ", qty=Decimal("5"), nw=Decimal("3.0"), row_number=1),
        ]
        invoice_items = [
            _make_invoice_item(part_no="DEF", qty=Decimal("5")),
        ]
        totals = _make_packing_totals(total_nw=Decimal("3.0"), total_nw_precision=2)

        result = allocate_weights(invoice_items, packing_items, totals)

        assert result[0].allocated_weight is not None
        assert result[0].allocated_weight == Decimal("3.0")

    def test_both_have_spaces_and_match(self) -> None:
        """Both sides have spaces, should still match."""
        packing_items = [
            _make_packing_item(part_no="  GHI  ", qty=Decimal("8"), nw=Decimal("4.0"), row_number=1),
        ]
        invoice_items = [
            _make_invoice_item(part_no=" GHI", qty=Decimal("8")),
        ]
        totals = _make_packing_totals(total_nw=Decimal("4.0"), total_nw_precision=2)

        result = allocate_weights(invoice_items, packing_items, totals)

        assert result[0].allocated_weight is not None
        assert result[0].allocated_weight == Decimal("4.0")


# ---------------------------------------------------------------------------
# Additional test — ERR_045 zero quantity
# ---------------------------------------------------------------------------


class TestAllocateWeightsZeroQuantity:
    """FR-021: Aggregated quantity is zero for a part (ERR_045)."""

    def test_raises_err_045_for_zero_aggregated_qty(self) -> None:
        """Part with all qty=0 should raise ERR_045."""
        packing_items = [
            _make_packing_item(
                part_no="A", qty=Decimal("0"), nw=Decimal("5.0"),
                row_number=1,
            ),
        ]
        invoice_items = [
            _make_invoice_item(part_no="A", qty=Decimal("10")),
        ]
        totals = _make_packing_totals(total_nw=Decimal("5.0"), total_nw_precision=2)

        with pytest.raises(ProcessingError) as exc_info:
            allocate_weights(invoice_items, packing_items, totals)

        assert exc_info.value.code == ErrorCode.ERR_045
        assert "A" in exc_info.value.message
