"""Weight allocation for AutoConvert.

Aggregates packing weights by part_no, validates against totals,
determines optimal precision, and allocates proportional weights
to invoice items. Implements FR-021 through FR-026.
"""

from __future__ import annotations

import logging
from decimal import Decimal

from autoconvert.errors import ErrorCode, ProcessingError
from autoconvert.models import InvoiceItem, PackingItem, PackingTotals
from autoconvert.utils import round_half_up

logger = logging.getLogger(__name__)


def allocate_weights(
    invoice_items: list[InvoiceItem],
    packing_items: list[PackingItem],
    packing_totals: PackingTotals,
) -> list[InvoiceItem]:
    """Orchestrate the full weight allocation pipeline (FR-021 through FR-026).

    Aggregates packing NW by part_no, validates sum vs total_nw (ERR_047),
    determines optimal precision (ERR_044), rounds and adjusts last-part
    (ERR_041), proportionally allocates to invoice items (ERR_040, ERR_043),
    and validates final sum (ERR_048).

    Args:
        invoice_items: Extracted invoice line items from extract_invoice_items.
        packing_items: Extracted packing rows from extract_packing_items.
        packing_totals: Extracted totals from extract_packing_totals.

    Returns:
        Invoice items with allocated_weight populated on each item.

    Raises:
        ProcessingError: With codes ERR_040, ERR_041, ERR_042, ERR_043,
            ERR_044, ERR_045, ERR_047, or ERR_048 depending on the failure.
    """
    total_nw = packing_totals.total_nw

    # FR-021: Aggregate packing weights and quantities by part_no
    agg_nw, agg_qty = _aggregate_packing(packing_items)

    # FR-022: Pre-allocation validation (packing sum vs total_nw)
    _validate_packing_sum(agg_nw, total_nw)

    # FR-023: Determine optimal rounding precision
    optimal_precision = _determine_precision(
        total_nw, packing_totals.total_nw_precision, agg_nw
    )

    # FR-024: Round packing weights and adjust last part
    rounded_weights = _round_and_adjust(agg_nw, optimal_precision, total_nw)

    # FR-025: Proportional allocation to invoice items
    result = _proportional_allocate(
        rounded_weights, invoice_items, optimal_precision
    )

    # FR-026: Final weight validation
    _validate_final_sum(result, total_nw)

    logger.info("Weight allocation complete: %s", total_nw)
    return result


def _aggregate_packing(
    packing_items: list[PackingItem],
) -> tuple[dict[str, Decimal], dict[str, Decimal]]:
    """Aggregate packing NW and QTY by part_no (FR-021).

    Groups PackingItem records by whitespace-stripped part_no and sums
    their nw and qty values. Validates that all aggregated weights and
    quantities are positive.

    Args:
        packing_items: Extracted packing rows.

    Returns:
        Tuple of (aggregated_nw, aggregated_qty) dicts keyed by part_no.

    Raises:
        ProcessingError: ERR_042 if any aggregated weight <= 0.
        ProcessingError: ERR_045 if any aggregated qty <= 0.
    """
    agg_nw: dict[str, Decimal] = {}
    agg_qty: dict[str, Decimal] = {}

    for item in packing_items:
        key = item.part_no.strip()
        agg_nw[key] = agg_nw.get(key, Decimal("0")) + item.nw
        agg_qty[key] = agg_qty.get(key, Decimal("0")) + item.qty

    # Validate aggregated weights are positive
    for part_no, weight in agg_nw.items():
        if weight <= Decimal("0"):
            raise ProcessingError(
                code=ErrorCode.ERR_042,
                message=(
                    f"Aggregated net weight for part '{part_no}' is "
                    f"{weight} (must be positive)"
                ),
                field="nw",
            )

    # Validate aggregated quantities are positive
    for part_no, qty in agg_qty.items():
        if qty <= Decimal("0"):
            raise ProcessingError(
                code=ErrorCode.ERR_045,
                message=(
                    f"Aggregated quantity for part '{part_no}' is zero "
                    f"(division by zero would occur)"
                ),
                field="qty",
            )

    return agg_nw, agg_qty


def _validate_packing_sum(
    agg_nw: dict[str, Decimal], total_nw: Decimal
) -> None:
    """Validate that packing weight sum is close to total_nw (FR-022).

    The difference must be <= 0.1. Fires BEFORE any rounding or precision
    adjustment to catch data issues early.

    Args:
        agg_nw: Aggregated weights by part_no from FR-021.
        total_nw: Total net weight from PackingTotals.

    Raises:
        ProcessingError: ERR_047 if abs(sum - total_nw) > 0.1.
    """
    packing_sum = sum(agg_nw.values())
    difference = abs(packing_sum - total_nw)
    threshold = Decimal("0.1")

    if difference > threshold:
        raise ProcessingError(
            code=ErrorCode.ERR_047,
            message=(
                f"Packing weight sum {packing_sum} disagrees with "
                f"total_nw {total_nw} (difference: {difference}, "
                f"threshold: {threshold})"
            ),
            field="nw",
        )


def _determine_precision(
    total_nw: Decimal,
    total_nw_precision: int,
    agg_nw: dict[str, Decimal],
) -> int:
    """Determine optimal rounding precision (FR-023).

    Uses a two-step algorithm:
    1. Sum matching: try precision N, then N+1, to find exact match.
    2. Zero check: escalate if any weight rounds to zero.

    Args:
        total_nw: Total net weight from PackingTotals.
        total_nw_precision: Detected decimal precision for total_nw.
        agg_nw: Aggregated weights by part_no from FR-021.

    Returns:
        Optimal precision as integer in range 2-5.

    Raises:
        ProcessingError: ERR_044 if any weight rounds to zero at max precision 5.
    """
    # Step 1: Base precision (already clamped 2-5 by extract_packing,
    # but enforce bounds here defensively)
    base_n = max(2, min(total_nw_precision, 5))

    # Step 2: Sum matching — try N, then N+1
    weights = list(agg_nw.values())

    precision = base_n

    logger.info("Trying precision: %d", base_n)
    rounded_at_n = [round_half_up(w, base_n) for w in weights]
    rounded_sum_n = sum(rounded_at_n)
    logger.info(
        "Expecting rounded part sum: %s, Target: %s", rounded_sum_n, total_nw
    )

    if rounded_sum_n == total_nw:
        logger.info("Perfect match at %d decimals", base_n)
        precision = base_n
    else:
        n_plus_1 = min(base_n + 1, 5)
        logger.info("Trying precision: %d", n_plus_1)
        rounded_at_n1 = [round_half_up(w, n_plus_1) for w in weights]
        rounded_sum_n1 = sum(rounded_at_n1)
        logger.info(
            "Expecting rounded part sum: %s, Target: %s",
            rounded_sum_n1,
            total_nw,
        )

        if rounded_sum_n1 == total_nw:
            logger.info("Perfect match at %d decimals", n_plus_1)
            precision = n_plus_1
        else:
            # Use N+1 with remainder adjustment (FR-024 will handle it)
            precision = n_plus_1

    # Step 3: Zero check (independent — can escalate further)
    precision = _zero_check_escalation(precision, agg_nw)

    return precision


def _zero_check_escalation(
    precision: int, agg_nw: dict[str, Decimal]
) -> int:
    """Escalate precision if any weight rounds to zero (FR-023 Step 3).

    Tries increasing precision from the current value up to max 5.
    Raises ERR_044 if any weight still rounds to zero at precision 5.

    Args:
        precision: Current precision chosen by sum matching.
        agg_nw: Aggregated weights by part_no.

    Returns:
        Escalated precision (may be same as input if no zeros found).

    Raises:
        ProcessingError: ERR_044 if any weight rounds to zero at max 5.
    """
    current = precision
    while current <= 5:
        has_zero = False
        for part_no, weight in agg_nw.items():
            rounded = round_half_up(weight, current)
            if rounded == Decimal("0"):
                has_zero = True
                # Reason: We need the part_no for the error message if at max
                zero_part = part_no
                zero_weight = weight
                break
        if not has_zero:
            return current
        if current == 5:
            raise ProcessingError(
                code=ErrorCode.ERR_044,
                message=(
                    f"Weight for part '{zero_part}' ({zero_weight}) "  # noqa: F821
                    f"rounds to zero at maximum precision 5"
                ),
                field="nw",
            )
        current += 1

    return current  # pragma: no cover


def _round_and_adjust(
    agg_nw: dict[str, Decimal],
    optimal_precision: int,
    total_nw: Decimal,
) -> dict[str, Decimal]:
    """Round packing weights and adjust last part for exact sum (FR-024).

    Rounds all aggregated part weights to optimal_precision using
    round_half_up. Adjusts the last part so that the sum equals total_nw
    exactly.

    Args:
        agg_nw: Aggregated weights by part_no from FR-021.
        optimal_precision: Precision from FR-023.
        total_nw: Total net weight from PackingTotals.

    Returns:
        Dict of part_no to rounded weight, sum equals total_nw exactly.

    Raises:
        ProcessingError: ERR_041 if remainder adjustment produces a
            negative weight.
    """
    parts = list(agg_nw.keys())
    rounded: dict[str, Decimal] = {}

    for part_no in parts:
        rounded[part_no] = round_half_up(agg_nw[part_no], optimal_precision)

    # Adjust last part for exact sum
    if parts:
        last_part = parts[-1]
        sum_others = sum(
            w for p, w in rounded.items() if p != last_part
        )
        remainder = total_nw - sum_others
        if remainder < Decimal("0"):
            raise ProcessingError(
                code=ErrorCode.ERR_041,
                message=(
                    f"Weight allocation remainder adjustment failed: "
                    f"remainder {remainder} is negative "
                    f"(total_nw={total_nw}, sum_others={sum_others})"
                ),
                field="nw",
            )
        rounded[last_part] = remainder

    return rounded


def _proportional_allocate(
    rounded_weights: dict[str, Decimal],
    invoice_items: list[InvoiceItem],
    optimal_precision: int,
) -> list[InvoiceItem]:
    """Proportionally allocate part weights to invoice items (FR-025).

    Matches invoice items to packing parts by whitespace-stripped part_no.
    Allocates weight proportionally based on qty. Uses collect-then-report
    for ERR_040 and ERR_043.

    Args:
        rounded_weights: Rounded part weights from FR-024.
        invoice_items: Invoice line items to allocate weights to.
        optimal_precision: Packing precision from FR-023.

    Returns:
        Invoice items with allocated_weight populated.

    Raises:
        ProcessingError: ERR_040 if invoice parts not found in packing.
        ProcessingError: ERR_043 if packing parts not found in invoice.
    """
    line_precision = optimal_precision + 1
    err_040_parts: list[str] = []
    err_043_parts: list[str] = []

    # Build lookup: stripped invoice part_no -> list of invoice item indices
    invoice_by_part: dict[str, list[int]] = {}
    for idx, item in enumerate(invoice_items):
        key = item.part_no.strip()
        invoice_by_part.setdefault(key, []).append(idx)

    # Track which invoice part_nos were matched by packing
    matched_invoice_parts: set[str] = set()

    # Allocate for each packing part
    for part_no, part_weight in rounded_weights.items():
        if part_no not in invoice_by_part:
            err_043_parts.append(part_no)
            continue

        matched_invoice_parts.add(part_no)
        indices = invoice_by_part[part_no]
        matching_items = [invoice_items[i] for i in indices]

        # Calculate total qty for this part group
        total_qty = sum(item.qty for item in matching_items)

        # Allocate proportionally and round to line_precision
        allocated_sum = Decimal("0")
        for i, item_idx in enumerate(indices):
            item = invoice_items[item_idx]
            if i < len(indices) - 1:
                # Reason: Proportional allocation for all but the last item
                raw_alloc = part_weight * (item.qty / total_qty)
                alloc = round_half_up(raw_alloc, line_precision)
                item.allocated_weight = alloc
                allocated_sum += alloc
            else:
                # Last item gets remainder for exact per-group sum
                item.allocated_weight = part_weight - allocated_sum

    # Check for invoice parts not found in packing (ERR_040)
    for inv_part_no in invoice_by_part:
        if inv_part_no not in rounded_weights:
            err_040_parts.append(inv_part_no)

    # Collect-then-report: raise ERR_040 first if any
    if err_040_parts:
        raise ProcessingError(
            code=ErrorCode.ERR_040,
            message=(
                f"Invoice part(s) not found in packing data: "
                f"{', '.join(err_040_parts)}"
            ),
            field="part_no",
        )

    # Collect-then-report: raise ERR_043 if any
    if err_043_parts:
        raise ProcessingError(
            code=ErrorCode.ERR_043,
            message=(
                f"Packing part(s) not found in invoice: "
                f"{', '.join(err_043_parts)}"
            ),
            field="part_no",
        )

    return invoice_items


def _validate_final_sum(
    items: list[InvoiceItem], total_nw: Decimal
) -> None:
    """Validate that allocated weights sum to total_nw exactly (FR-026).

    Args:
        items: Invoice items with allocated_weight set.
        total_nw: Expected total net weight.

    Raises:
        ProcessingError: ERR_048 if sum of allocated weights != total_nw.
    """
    allocated_sum = sum(
        item.allocated_weight
        for item in items
        if item.allocated_weight is not None
    )

    if allocated_sum != total_nw:
        raise ProcessingError(
            code=ErrorCode.ERR_048,
            message=(
                f"Final weight validation failed: allocated sum "
                f"{allocated_sum} != total_nw {total_nw}"
            ),
            field="nw",
        )
