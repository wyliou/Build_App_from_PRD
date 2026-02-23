"""Batch summary reporting for AutoConvert.

Prints batch processing summary with counts, timing, and
failed/attention file details. Implements FR-033.
"""

from __future__ import annotations

import logging
from collections import defaultdict

from autoconvert.models import BatchResult, FileResult, ProcessingError

logger = logging.getLogger(__name__)

_SEP_MAJOR = "==========================================================================="
_SEP_MINOR = "---------------------------------------------------------------------------"


def _condense_errors(errors: list[ProcessingError]) -> list[tuple[str, str]]:
    """Group errors by code and condense repeated codes within one file.

    For each unique error code in the list, if the code appears more than
    once, the output message is appended with "(N occurrences)". If it
    appears exactly once, the message is unchanged. The representative
    message is taken from the first error seen for each code.

    Args:
        errors: List of ProcessingError objects for a single file.

    Returns:
        List of (code, display_message) tuples in first-seen code order.
    """
    # Preserve insertion order of first occurrence per code
    seen_order: list[str] = []
    groups: dict[str, list[ProcessingError]] = defaultdict(list)

    for err in errors:
        if err.code not in groups:
            seen_order.append(err.code)
        groups[err.code].append(err)

    result: list[tuple[str, str]] = []
    for code in seen_order:
        group = groups[code]
        representative = group[0]
        if len(group) > 1:
            display_msg = f"{representative.message} ({len(group)} occurrences)"
        else:
            display_msg = representative.message
        result.append((code, display_msg))

    return result


def _log_failed_files(failed_files: list[FileResult]) -> None:
    """Log the FAILED FILES section for all files with Failed status.

    Outputs the section header followed by each file's name and its
    condensed error list using logger.error().

    Args:
        failed_files: List of FileResult objects with status "Failed".
    """
    logger.error("FAILED FILES:")
    for file_result in failed_files:
        logger.error("  %s:", file_result.filename)
        condensed = _condense_errors(file_result.errors)
        for code, msg in condensed:
            logger.error("    %s: %s", code, msg)


def _log_attention_files(attention_files: list[FileResult]) -> None:
    """Log the FILES NEEDING ATTENTION section for all attention files.

    Outputs the section header followed by each file's name and its
    warning list using logger.warning().

    Args:
        attention_files: List of FileResult objects with status "Attention".
    """
    logger.warning("FILES NEEDING ATTENTION:")
    for file_result in attention_files:
        logger.warning("  %s:", file_result.filename)
        for warn in file_result.warnings:
            logger.warning("    %s: %s", warn.code, warn.message)


def print_batch_summary(batch_result: BatchResult) -> None:
    """Print the full batch processing summary report via logging.

    Includes total file counts, processing time, log path, and per-file
    error/warning details for failed and attention files. Always completes
    without raising exceptions — report output failures are non-fatal.

    Display order:
        1. Batch Processing Summary block (header, counts, timing, log path).
        2. Failed Files section — only if failed_count > 0.
        3. Separator line — only when BOTH failed and attention sections present.
        4. Files Needing Attention section — only if attention_count > 0.

    Args:
        batch_result: BatchResult containing all per-file results and counts.
    """
    try:
        # --- Summary header block ---
        logger.info(_SEP_MAJOR)
        logger.info("                   BATCH PROCESSING SUMMARY")
        logger.info(_SEP_MAJOR)
        logger.info("Total files:        %d", batch_result.total_files)
        logger.info("Successful:         %d", batch_result.success_count)
        logger.info("Attention:          %d", batch_result.attention_count)
        logger.info("Failed:             %d", batch_result.failed_count)
        logger.info(
            "Processing time:    %.2f seconds",
            batch_result.processing_time,
        )
        logger.info("Log file:           %s", batch_result.log_path)
        logger.info(_SEP_MAJOR)

        # Collect failed and attention files from file_results
        failed_files = [
            fr for fr in batch_result.file_results if fr.status == "Failed"
        ]
        attention_files = [
            fr for fr in batch_result.file_results if fr.status == "Attention"
        ]

        has_failed = batch_result.failed_count > 0
        has_attention = batch_result.attention_count > 0

        if has_failed:
            _log_failed_files(failed_files)

        # Separator only when BOTH sections are present
        if has_failed and has_attention:
            logger.info(_SEP_MINOR)

        if has_attention:
            _log_attention_files(attention_files)

    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to generate batch summary report: %s", exc)
