"""Tests for autoconvert.report."""

from __future__ import annotations

import logging

import pytest

from autoconvert.errors import ProcessingError
from autoconvert.models import BatchResult, FileResult
from autoconvert.report import print_batch_summary


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_file_result(
    filename: str,
    status: str,
    errors: list[ProcessingError] | None = None,
    warnings: list[ProcessingError] | None = None,
) -> FileResult:
    """Build a minimal FileResult for testing.

    Args:
        filename: Name of the file.
        status: Processing status string ("Success", "Attention", or "Failed").
        errors: List of ProcessingError objects (defaults to empty list).
        warnings: List of ProcessingError objects (defaults to empty list).

    Returns:
        FileResult with the given values and all optional fields as None.
    """
    return FileResult(
        filename=filename,
        status=status,
        errors=errors or [],
        warnings=warnings or [],
        invoice_items=None,
        packing_items=None,
        packing_totals=None,
    )


def _make_batch_result(
    total_files: int,
    success_count: int,
    attention_count: int,
    failed_count: int,
    processing_time: float,
    file_results: list[FileResult] | None = None,
    log_path: str = "/some/path/process_log.txt",
) -> BatchResult:
    """Build a BatchResult for testing.

    Args:
        total_files: Total number of files in the batch.
        success_count: Number of successful files.
        attention_count: Number of attention files.
        failed_count: Number of failed files.
        processing_time: Total processing time in seconds.
        file_results: List of FileResult objects (defaults to empty list).
        log_path: Path to the log file.

    Returns:
        BatchResult with the given values.
    """
    return BatchResult(
        total_files=total_files,
        success_count=success_count,
        attention_count=attention_count,
        failed_count=failed_count,
        processing_time=processing_time,
        file_results=file_results or [],
        log_path=log_path,
    )


# ---------------------------------------------------------------------------
# test_print_batch_summary_all_success
# ---------------------------------------------------------------------------


def test_print_batch_summary_all_success(caplog: pytest.LogCaptureFixture) -> None:
    """Summary header appears when all files succeed; no error or warning logs."""
    batch = _make_batch_result(
        total_files=3,
        success_count=3,
        attention_count=0,
        failed_count=0,
        processing_time=5.0,
        file_results=[
            _make_file_result("a.xlsx", "Success"),
            _make_file_result("b.xlsx", "Success"),
            _make_file_result("c.xlsx", "Success"),
        ],
    )

    with caplog.at_level(logging.INFO, logger="autoconvert.report"):
        print_batch_summary(batch)

    assert "BATCH PROCESSING SUMMARY" in caplog.text

    # No error or warning records should be emitted
    error_records = [r for r in caplog.records if r.levelno >= logging.ERROR]
    warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert error_records == []
    assert warning_records == []


# ---------------------------------------------------------------------------
# test_print_batch_summary_failed_and_attention
# ---------------------------------------------------------------------------


def test_print_batch_summary_failed_and_attention(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Failed section, separator, and attention section all appear in order."""
    failed_file = _make_file_result(
        "fail.xlsx",
        "Failed",
        errors=[
            ProcessingError("ERR_020", "Missing column qty", "fail.xlsx"),
            ProcessingError("ERR_020", "Missing column nw", "fail.xlsx"),
        ],
    )
    attention_file = _make_file_result(
        "warn.xlsx",
        "Attention",
        warnings=[
            ProcessingError("ATT_003", "Total packet count not found", "warn.xlsx"),
        ],
    )
    batch = _make_batch_result(
        total_files=2,
        success_count=0,
        attention_count=1,
        failed_count=1,
        processing_time=3.0,
        file_results=[failed_file, attention_file],
    )

    with caplog.at_level(logging.DEBUG, logger="autoconvert.report"):
        print_batch_summary(batch)

    # Collect messages in level order for ordering assertions
    messages = [r.getMessage() for r in caplog.records]
    text = caplog.text

    # All three section markers must be present
    assert any("FAILED FILES:" in m for m in messages)
    assert any("---------------------------------------------------------------------------" in m for m in messages)
    assert any("FILES NEEDING ATTENTION:" in m for m in messages)

    # Filenames must appear under the correct sections
    assert "fail.xlsx" in text
    assert "warn.xlsx" in text

    # Order: failed section header before separator before attention section header
    idx_failed = next(
        i for i, r in enumerate(caplog.records) if "FAILED FILES:" in r.getMessage()
    )
    idx_sep = next(
        i
        for i, r in enumerate(caplog.records)
        if "---------------------------------------------------------------------------" in r.getMessage()
    )
    idx_attention = next(
        i
        for i, r in enumerate(caplog.records)
        if "FILES NEEDING ATTENTION:" in r.getMessage()
    )
    assert idx_failed < idx_sep < idx_attention


# ---------------------------------------------------------------------------
# test_print_batch_summary_error_condensing
# ---------------------------------------------------------------------------


def test_print_batch_summary_error_condensing(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Three errors with the same code produce '(3 occurrences)' in output."""
    failed_file = _make_file_result(
        "multi.xlsx",
        "Failed",
        errors=[
            ProcessingError("ERR_030", "Numeric parse failed at row 5", "multi.xlsx", row=5),
            ProcessingError("ERR_030", "Numeric parse failed at row 6", "multi.xlsx", row=6),
            ProcessingError("ERR_030", "Numeric parse failed at row 7", "multi.xlsx", row=7),
        ],
    )
    batch = _make_batch_result(
        total_files=1,
        success_count=0,
        attention_count=0,
        failed_count=1,
        processing_time=1.0,
        file_results=[failed_file],
    )

    with caplog.at_level(logging.DEBUG, logger="autoconvert.report"):
        print_batch_summary(batch)

    assert "(3 occurrences)" in caplog.text


# ---------------------------------------------------------------------------
# test_print_batch_summary_processing_time_format
# ---------------------------------------------------------------------------


def test_print_batch_summary_processing_time_format(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Processing time is formatted to exactly 2 decimal places."""
    batch = _make_batch_result(
        total_files=1,
        success_count=1,
        attention_count=0,
        failed_count=0,
        processing_time=12.3,
    )

    with caplog.at_level(logging.INFO, logger="autoconvert.report"):
        print_batch_summary(batch)

    assert "12.30 seconds" in caplog.text


# ---------------------------------------------------------------------------
# test_print_batch_summary_no_separator_when_only_failed
# ---------------------------------------------------------------------------


def test_print_batch_summary_no_separator_when_only_failed(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Separator line does NOT appear when there are failed but no attention files."""
    failed_file = _make_file_result(
        "only_fail.xlsx",
        "Failed",
        errors=[ProcessingError("ERR_020", "Missing column", "only_fail.xlsx")],
    )
    batch = _make_batch_result(
        total_files=1,
        success_count=0,
        attention_count=0,
        failed_count=1,
        processing_time=0.5,
        file_results=[failed_file],
    )

    with caplog.at_level(logging.DEBUG, logger="autoconvert.report"):
        print_batch_summary(batch)

    # The minor separator must not appear (major separator is in the header block;
    # we check that no record contains the minor separator string)
    minor_sep = "---------------------------------------------------------------------------"
    assert not any(minor_sep in r.getMessage() for r in caplog.records)


# ---------------------------------------------------------------------------
# test_print_batch_summary_no_separator_when_only_attention
# ---------------------------------------------------------------------------


def test_print_batch_summary_no_separator_when_only_attention(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Separator line does NOT appear when there are attention but no failed files."""
    attention_file = _make_file_result(
        "only_warn.xlsx",
        "Attention",
        warnings=[ProcessingError("ATT_003", "Packet count missing", "only_warn.xlsx")],
    )
    batch = _make_batch_result(
        total_files=1,
        success_count=0,
        attention_count=1,
        failed_count=0,
        processing_time=0.5,
        file_results=[attention_file],
    )

    with caplog.at_level(logging.DEBUG, logger="autoconvert.report"):
        print_batch_summary(batch)

    minor_sep = "---------------------------------------------------------------------------"
    assert not any(minor_sep in r.getMessage() for r in caplog.records)


# ---------------------------------------------------------------------------
# test_print_batch_summary_never_raises
# ---------------------------------------------------------------------------


def test_print_batch_summary_never_raises() -> None:
    """print_batch_summary never raises even with an otherwise-problematic BatchResult.

    Uses a BatchResult where file_results is empty but counts are non-zero,
    which would cause an AttributeError if the implementation tried to
    index into the empty list. The function must swallow any internal error.
    """
    # Non-zero counts but empty file_results — any naive iteration is safe,
    # but the broad try/except must still protect against unforeseen issues.
    batch = _make_batch_result(
        total_files=2,
        success_count=0,
        attention_count=1,
        failed_count=1,
        processing_time=0.0,
        file_results=[],  # mismatched counts; iteration will be empty
    )

    # Must not raise any exception
    print_batch_summary(batch)
