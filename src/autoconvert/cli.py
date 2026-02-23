"""Command-line interface for AutoConvert.

Parses command-line arguments, initializes config and logging,
and delegates to batch processing. Implements FR-034 (diagnostic mode).
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from autoconvert import __version__
from autoconvert.batch import run_batch
from autoconvert.config import load_config
from autoconvert.errors import ConfigError
from autoconvert.logger import setup_diagnostic_logging, setup_logging
from autoconvert.report import print_batch_summary

logger = logging.getLogger(__name__)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for AutoConvert.

    Accepts optional ``argv`` list for testability (defaults to
    ``sys.argv[1:]`` when None). Supports ``--diagnostic <filename>``
    for single-file diagnostic mode and ``--version`` for version output.

    Args:
        argv: Argument list to parse. None uses sys.argv[1:].

    Returns:
        Namespace with ``diagnostic: str | None`` attribute.
    """
    parser = argparse.ArgumentParser(
        prog="autoconvert",
        description="AutoConvert \u2014 Vendor Excel to customs template converter",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--diagnostic",
        type=str,
        default=None,
        metavar="FILENAME",
        help="Process a single file in diagnostic mode with DEBUG-level output",
    )
    return parser.parse_args(argv)


def main() -> None:
    """CLI entry point for AutoConvert.

    Orchestrates the full application lifecycle: reconfigures console
    encoding for CJK/emoji, parses arguments, sets up logging, loads
    config, runs batch processing, prints summary, and exits with
    appropriate code (0/1/2).

    Returns:
        None. Calls sys.exit() with 0, 1, or 2.
    """
    # Step 1-2: Reconfigure stdout/stderr for UTF-8 with replace fallback.
    # Handles CJK filenames and emoji status indicators on Windows.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except AttributeError:
        pass  # Not all streams support reconfigure (e.g., StringIO in tests).

    # Step 3: Parse arguments.
    args = parse_args()

    # Step 4: Resolve base_dir.
    if getattr(sys, "frozen", False):
        base_dir = Path(sys.executable).parent
    else:
        base_dir = Path.cwd()

    # Step 5: Log path.
    log_path = base_dir / "process_log.txt"

    # Step 6: Set up logging.
    if args.diagnostic:
        setup_diagnostic_logging(log_path)
    else:
        setup_logging(log_path)

    # Step 7: Load config.
    config_dir = base_dir / "config"
    try:
        config = load_config(config_dir)
    except ConfigError as e:
        logger.error("[%s] %s", e.code, e.message)
        sys.exit(2)

    # Step 8: Resolve diagnostic file path if provided.
    data_dir = base_dir / "data"
    diagnostic_resolved: str | None = None

    if args.diagnostic:
        diag_path = Path(args.diagnostic)
        if not diag_path.is_absolute():
            diag_path = data_dir / diag_path
        if not diag_path.exists():
            logger.error("File not found: %s", diag_path)
            sys.exit(2)
        diagnostic_resolved = str(diag_path)

    # Step 9: Run batch processing.
    batch_result = run_batch(config, data_dir, diagnostic_file=diagnostic_resolved)

    # Step 10: Print summary.
    print_batch_summary(batch_result)

    # Step 11: Exit with appropriate code.
    sys.exit(0 if batch_result.failed_count == 0 else 1)
