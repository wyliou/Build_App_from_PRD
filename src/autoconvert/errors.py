"""Error types and error/warning code enums for AutoConvert.

Defines ErrorCode (ERR_001-ERR_052), WarningCode (ATT_002-ATT_004),
ProcessingError, and ConfigError exception classes.
"""

from __future__ import annotations

from enum import Enum


class ErrorCode(str, Enum):
    """Error codes for file processing failures.

    Each member's string value equals its name (e.g., ErrorCode.ERR_001 == "ERR_001").
    Codes are grouped by processing phase:
        ERR_001-005: Config errors (fatal startup)
        ERR_010-013: File/sheet access errors
        ERR_014, ERR_020-021: Column mapping errors
        ERR_030-034: Extraction errors
        ERR_040-048: Weight allocation errors
        ERR_051-052: Output errors
    """

    # Config errors (fatal startup)
    ERR_001 = "ERR_001"
    ERR_002 = "ERR_002"
    ERR_003 = "ERR_003"
    ERR_004 = "ERR_004"
    ERR_005 = "ERR_005"

    # File/sheet access errors
    ERR_010 = "ERR_010"
    ERR_011 = "ERR_011"
    ERR_012 = "ERR_012"
    ERR_013 = "ERR_013"

    # Column mapping errors
    ERR_014 = "ERR_014"
    ERR_020 = "ERR_020"
    ERR_021 = "ERR_021"

    # Extraction errors
    ERR_030 = "ERR_030"
    ERR_031 = "ERR_031"
    ERR_032 = "ERR_032"
    ERR_033 = "ERR_033"
    ERR_034 = "ERR_034"

    # Weight allocation errors
    ERR_040 = "ERR_040"
    ERR_041 = "ERR_041"
    ERR_042 = "ERR_042"
    ERR_043 = "ERR_043"
    ERR_044 = "ERR_044"
    ERR_045 = "ERR_045"
    ERR_046 = "ERR_046"
    ERR_047 = "ERR_047"
    ERR_048 = "ERR_048"

    # Output errors
    ERR_051 = "ERR_051"
    ERR_052 = "ERR_052"


class WarningCode(str, Enum):
    """Warning codes for non-fatal processing issues (Attention status).

    Each member's string value equals its name (e.g., WarningCode.ATT_002 == "ATT_002").
    Note: ATT_001 does not exist in the PRD catalog.
    """

    ATT_002 = "ATT_002"
    ATT_003 = "ATT_003"
    ATT_004 = "ATT_004"


class ProcessingError(Exception):
    """Exception raised during file processing phases.

    Raised by extraction, transform, and weight allocation modules.
    Caught by the batch orchestrator for per-file error reporting.

    Attributes:
        code: The ERR_NNN or ATT_NNN error code string.
        message: Human-readable description with actionable context.
        filename: The input file being processed (None for utility errors).
        row: Row number where the error occurred (1-based, openpyxl convention).
        field: Field name involved (e.g., "qty", "part_no").
    """

    def __init__(
        self,
        code: str,
        message: str,
        filename: str | None = None,
        row: int | None = None,
        field: str | None = None,
    ) -> None:
        """Initialize a ProcessingError.

        Args:
            code: The ERR_NNN or ATT_NNN error code string.
            message: Human-readable description with actionable context.
            filename: The input file being processed.
            row: Row number where the error occurred (1-based).
            field: Field name involved.
        """
        super().__init__(message)
        self.code = code
        self.message = message
        self.filename = filename
        self.row = row
        self.field = field


class ConfigError(Exception):
    """Exception raised for fatal configuration errors during startup.

    Raised only by config.py. Caught by cli.py which exits with code 2.

    Attributes:
        code: The ERR_NNN error code string (ERR_001 through ERR_005).
        message: Human-readable description of the config problem.
        path: Path to the config file that caused the error.
    """

    def __init__(
        self,
        code: str,
        message: str,
        path: str | None = None,
    ) -> None:
        """Initialize a ConfigError.

        Args:
            code: The ERR_NNN error code string.
            message: Human-readable description of the config problem.
            path: Path to the config file that caused the error.
        """
        super().__init__(message)
        self.code = code
        self.message = message
        self.path = path
