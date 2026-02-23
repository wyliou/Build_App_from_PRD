"""Tests for autoconvert.validate."""

from __future__ import annotations

from autoconvert.errors import ProcessingError
from autoconvert.validate import determine_file_status


def test_determine_file_status_success() -> None:
    """Empty errors and warnings lists → returns "Success"."""
    result = determine_file_status(errors=[], warnings=[])
    assert result == "Success"


def test_determine_file_status_attention_only() -> None:
    """Empty errors, one ATT_003 warning → returns "Attention"."""
    warning = ProcessingError(
        code="ATT_003",
        message="Optional field missing",
        filename="test.xlsx",
    )
    result = determine_file_status(errors=[], warnings=[warning])
    assert result == "Attention"


def test_determine_file_status_failed_single_error() -> None:
    """One ERR_020 in errors, empty warnings → returns "Failed"."""
    error = ProcessingError(
        code="ERR_020",
        message="Missing required column",
        filename="test.xlsx",
    )
    result = determine_file_status(errors=[error], warnings=[])
    assert result == "Failed"


def test_determine_file_status_failed_overrides_attention() -> None:
    """Both ERR_020 in errors AND ATT_003 in warnings → returns "Failed"."""
    error = ProcessingError(
        code="ERR_020",
        message="Missing required column",
        filename="test.xlsx",
    )
    warning = ProcessingError(
        code="ATT_003",
        message="Optional field missing",
        filename="test.xlsx",
    )
    result = determine_file_status(errors=[error], warnings=[warning])
    assert result == "Failed"


def test_determine_file_status_multiple_warnings_no_errors() -> None:
    """Multiple ATT codes (ATT_002, ATT_003, ATT_004) with empty errors → "Attention"."""
    warnings = [
        ProcessingError(
            code="ATT_002",
            message="Total packets count not found",
            filename="test.xlsx",
        ),
        ProcessingError(
            code="ATT_003",
            message="Optional field missing",
            filename="test.xlsx",
        ),
        ProcessingError(
            code="ATT_004",
            message="Another warning",
            filename="test.xlsx",
        ),
    ]
    result = determine_file_status(errors=[], warnings=warnings)
    assert result == "Attention"
