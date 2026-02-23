"""Logging configuration for AutoConvert.

Provides dual-output logging: console (INFO+) and file (DEBUG+).
Implements FR-031 (real-time console output) and FR-032 (detailed file logging).
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path


def _setup_logging_base(log_path: Path, console_level: int) -> None:
    """Configure dual-output logging with a given console level.

    Sets up a StreamHandler on stdout at ``console_level`` and a
    FileHandler at DEBUG level. Clears existing handlers first to
    prevent duplicate entries on repeated calls.

    Args:
        log_path: Path to the log file (e.g., process_log.txt).
        console_level: Minimum level for console output (logging.INFO
            for normal mode, logging.DEBUG for diagnostic mode).
    """
    # Configure stdout encoding for Windows CJK and emoji support
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

    # Clear any existing handlers to prevent duplicates
    logging.root.handlers.clear()

    # Create console handler at the requested level
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_formatter = logging.Formatter("[%(levelname)s] %(message)s")
    console_handler.setFormatter(console_formatter)

    # Configure root logger
    logging.root.setLevel(logging.DEBUG)
    logging.root.addHandler(console_handler)

    # Create file handler (DEBUG level)
    try:
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%H:%M"
        )
        file_handler.setFormatter(file_formatter)
        logging.root.addHandler(file_handler)
    except OSError as e:
        # Log write failure to console but continue processing
        logging.warning(f"Failed to create log file at {log_path}: {e}")


def setup_logging(log_path: Path) -> None:
    """
    Configure dual-output logging: console (INFO) and file (DEBUG).

    Configures the root logger with two handlers:
    - StreamHandler (console/stdout): INFO level, simple format
    - FileHandler (file): DEBUG level, timestamp + level format

    Args:
        log_path: Path to the log file (e.g., process_log.txt).

    Returns:
        None
    """
    _setup_logging_base(log_path, logging.INFO)


def setup_diagnostic_logging(log_path: Path) -> None:
    """
    Configure diagnostic logging: console (DEBUG) and file (DEBUG).

    Same as setup_logging() but with console handler level set to DEBUG
    for verbose output.

    Args:
        log_path: Path to the log file (e.g., process_log.txt).

    Returns:
        None
    """
    _setup_logging_base(log_path, logging.DEBUG)
