"""Data transformation for AutoConvert.

Converts currency codes, country codes, and cleans PO numbers.
Implements FR-018, FR-019, FR-020.
"""

from __future__ import annotations

import logging
import re

from autoconvert.config_helpers import normalize_lookup_key
from autoconvert.errors import ProcessingError, WarningCode
from autoconvert.models import AppConfig, InvoiceItem

logger = logging.getLogger(__name__)

# Delimiter pattern for PO number cleaning (FR-020).
# Matches the first occurrence of -, ., /, (, comma, or semicolon.
_PO_DELIMITER_RE = re.compile(r"[-./,(;]")


def convert_currency(
    items: list[InvoiceItem],
    config: AppConfig,
) -> tuple[list[InvoiceItem], list[ProcessingError]]:
    """Convert raw currency strings to standardized 3-character numeric codes.

    Performs case-insensitive lookup (with comma-space normalization) of each
    item's currency field against config.currency_lookup.  Items whose
    currency string is not found in the lookup table are returned with their
    original value; one ATT_003 warning is appended to the warning list for
    each unmatched item.

    Does NOT raise on no-match.  Does NOT mutate the input list.

    Args:
        items: List of InvoiceItem objects with raw currency strings.
        config: AppConfig carrying the normalized currency_lookup dict.

    Returns:
        A tuple of (updated_items, warnings) where updated_items contains
        new InvoiceItem copies (original values preserved on no-match) and
        warnings contains one ProcessingError(ATT_003) per unmatched item.
    """
    updated: list[InvoiceItem] = []
    warnings: list[ProcessingError] = []

    for item in items:
        normalized_key = normalize_lookup_key(item.currency)
        target_code = config.currency_lookup.get(normalized_key)

        if target_code is not None:
            new_item = item.model_copy(update={"currency": target_code})
            logger.debug(
                "convert_currency: '%s' -> '%s' (row %s)",
                item.currency,
                target_code,
                item.inv_no,
            )
        else:
            new_item = item.model_copy()
            warning = ProcessingError(
                code=WarningCode.ATT_003,
                message=(
                    f"Unstandardized currency '{item.currency}': "
                    f"no match found in currency lookup table. "
                    f"Raw value preserved."
                ),
                filename=None,
                row=None,
                field="currency",
            )
            warnings.append(warning)
            logger.warning(
                "convert_currency: no match for '%s' (ATT_003)", item.currency
            )

        updated.append(new_item)

    return updated, warnings


def convert_country(
    items: list[InvoiceItem],
    config: AppConfig,
) -> tuple[list[InvoiceItem], list[ProcessingError]]:
    """Convert raw COO strings to standardized 3-character numeric codes.

    Performs case-insensitive lookup (with comma-space normalization) of each
    item's coo field against config.country_lookup.  Items whose coo string
    is not found in the lookup table are returned with their original value;
    one ATT_004 warning is appended for each unmatched item.

    config.country_lookup stores Target_Code as str — the config loader
    normalizes int/str at load time so no type coercion is needed here.

    Does NOT raise on no-match.  Does NOT mutate the input list.

    Args:
        items: List of InvoiceItem objects with raw COO strings.
        config: AppConfig carrying the normalized country_lookup dict.

    Returns:
        A tuple of (updated_items, warnings) where updated_items contains
        new InvoiceItem copies (original values preserved on no-match) and
        warnings contains one ProcessingError(ATT_004) per unmatched item.
    """
    updated: list[InvoiceItem] = []
    warnings: list[ProcessingError] = []

    for item in items:
        normalized_key = normalize_lookup_key(item.coo)
        target_code = config.country_lookup.get(normalized_key)

        if target_code is not None:
            # Reason: spec says Target_Code may be stored as int in the source
            # xlsx; config normalizes to str at load time, but we cast anyway
            # to be safe against future config changes.
            new_item = item.model_copy(update={"coo": str(target_code)})
            logger.debug(
                "convert_country: '%s' -> '%s'", item.coo, target_code
            )
        else:
            new_item = item.model_copy()
            warning = ProcessingError(
                code=WarningCode.ATT_004,
                message=(
                    f"Unstandardized COO '{item.coo}': "
                    f"no match found in country lookup table. "
                    f"Raw value preserved."
                ),
                filename=None,
                row=None,
                field="coo",
            )
            warnings.append(warning)
            logger.warning(
                "convert_country: no match for '%s' (ATT_004)", item.coo
            )

        updated.append(new_item)

    return updated, warnings


def clean_po_number(items: list[InvoiceItem]) -> list[InvoiceItem]:
    """Strip everything from the first delimiter onwards in each item's po_no.

    Delimiters are: -, ., /, (, comma (,), semicolon (;).  The first
    occurrence of any delimiter triggers the strip.  If the result after
    stripping is empty (delimiter at position 0), the original value is
    preserved unchanged.

    Does NOT produce warnings or errors (best-effort transformation).
    Does NOT mutate the input list.

    Examples:
        '2250600556-2.1' -> '2250600556'
        'PO32741.0'      -> 'PO32741'
        '-PO12345'       -> '-PO12345'  (delimiter at index 0, preserve)
        'PO12345'        -> 'PO12345'   (no delimiter, no change)

    Args:
        items: List of InvoiceItem objects with raw po_no strings.

    Returns:
        New list of InvoiceItem copies with cleaned po_no values.
    """
    updated: list[InvoiceItem] = []

    for item in items:
        match = _PO_DELIMITER_RE.search(item.po_no)

        if match is None:
            # No delimiter found — copy item unchanged.
            updated.append(item.model_copy())
        else:
            cleaned = item.po_no[: match.start()]
            if cleaned == "":
                # Delimiter at position 0: preserve original (FR-020 edge case).
                logger.debug(
                    "clean_po_number: delimiter at index 0 for '%s', preserving",
                    item.po_no,
                )
                updated.append(item.model_copy())
            else:
                logger.debug(
                    "clean_po_number: '%s' -> '%s'", item.po_no, cleaned
                )
                updated.append(item.model_copy(update={"po_no": cleaned}))

    return updated
