"""File status validation for AutoConvert.

Determines file processing status (Success/Attention/Failed) based
on collected errors and warnings. Implements FR-027.
"""

from __future__ import annotations

from autoconvert.errors import ProcessingError


def determine_file_status(
    errors: list[ProcessingError], warnings: list[ProcessingError]
) -> str:
    """Determine final file status based on accumulated errors and warnings.

    Returns "Failed" if any ERR_xxx code present in errors;
    "Attention" if only ATT_xxx codes present in warnings (no errors);
    "Success" if both lists are empty.

    Args:
        errors: List of ProcessingErrors with ERR_xxx codes.
        warnings: List of ProcessingErrors with ATT_xxx codes.

    Returns:
        One of: "Success", "Attention", or "Failed".
    """
    # Any ERR_xxx code in errors → return "Failed"
    if errors:
        return "Failed"

    # No errors; check for ATT_xxx codes in warnings
    if warnings:
        return "Attention"

    # Both lists empty → return "Success"
    return "Success"
