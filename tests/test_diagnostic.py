"""Tests for autoconvert diagnostic mode (cli --diagnostic).

Covers parse_args (normal, diagnostic flag, version), and main function
(config error, normal mode success/failure, diagnostic logging, file not found).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from autoconvert.cli import main, parse_args
from autoconvert.errors import ConfigError, ErrorCode
from autoconvert.models import BatchResult

# ---------------------------------------------------------------------------
# Tests — parse_args
# ---------------------------------------------------------------------------


class TestParseArgs:
    """Tests for CLI argument parsing."""

    def test_parse_args_no_args(self) -> None:
        """Verify default args: diagnostic is None."""
        args = parse_args([])
        assert args.diagnostic is None

    def test_parse_args_diagnostic_flag(self) -> None:
        """Verify --diagnostic captures the filename."""
        args = parse_args(["--diagnostic", "somefile.xlsx"])
        assert args.diagnostic == "somefile.xlsx"

    def test_parse_args_version_flag(self) -> None:
        """Verify --version exits with code 0."""
        with pytest.raises(SystemExit) as exc_info:
            parse_args(["--version"])
        assert exc_info.value.code == 0


# ---------------------------------------------------------------------------
# Tests — main function
# ---------------------------------------------------------------------------


def _make_mock_batch_result(failed_count: int = 0) -> BatchResult:
    """Create a minimal BatchResult for test mocking.

    Args:
        failed_count: Number of failed files.

    Returns:
        BatchResult with specified failed_count and zero for other counts.
    """
    return BatchResult(
        total_files=1,
        success_count=1 if failed_count == 0 else 0,
        attention_count=0,
        failed_count=failed_count,
        processing_time=0.5,
        file_results=[],
        log_path="process_log.txt",
    )


class TestMain:
    """Tests for the CLI main function."""

    def test_main_config_error_exits_code2(self, tmp_path: Path) -> None:
        """Verify ConfigError causes sys.exit(2)."""
        with (
            patch("autoconvert.cli.parse_args", return_value=MagicMock(diagnostic=None)),
            patch("autoconvert.cli.setup_logging"),
            patch(
                "autoconvert.cli.load_config",
                side_effect=ConfigError(
                    code=ErrorCode.ERR_001,
                    message="Config not found",
                ),
            ),
            patch("autoconvert.cli.Path.cwd", return_value=tmp_path),
            pytest.raises(SystemExit) as exc_info,
        ):
            main()

        assert exc_info.value.code == 2

    def test_main_normal_mode_exits_code0_on_all_success(
        self, tmp_path: Path,
    ) -> None:
        """Verify exit code 0 when no files failed."""
        batch_result = _make_mock_batch_result(failed_count=0)

        with (
            patch("autoconvert.cli.parse_args", return_value=MagicMock(diagnostic=None)),
            patch("autoconvert.cli.setup_logging"),
            patch("autoconvert.cli.load_config", return_value=MagicMock()),
            patch("autoconvert.cli.run_batch", return_value=batch_result),
            patch("autoconvert.cli.print_batch_summary"),
            patch("autoconvert.cli.Path.cwd", return_value=tmp_path),
            pytest.raises(SystemExit) as exc_info,
        ):
            main()

        assert exc_info.value.code == 0

    def test_main_normal_mode_exits_code1_on_failure(
        self, tmp_path: Path,
    ) -> None:
        """Verify exit code 1 when one or more files failed."""
        batch_result = _make_mock_batch_result(failed_count=1)

        with (
            patch("autoconvert.cli.parse_args", return_value=MagicMock(diagnostic=None)),
            patch("autoconvert.cli.setup_logging"),
            patch("autoconvert.cli.load_config", return_value=MagicMock()),
            patch("autoconvert.cli.run_batch", return_value=batch_result),
            patch("autoconvert.cli.print_batch_summary"),
            patch("autoconvert.cli.Path.cwd", return_value=tmp_path),
            pytest.raises(SystemExit) as exc_info,
        ):
            main()

        assert exc_info.value.code == 1

    def test_main_diagnostic_mode_calls_diagnostic_logging(
        self, tmp_path: Path,
    ) -> None:
        """Verify diagnostic mode calls setup_diagnostic_logging."""
        batch_result = _make_mock_batch_result(failed_count=0)

        # Create a file in the data dir so diagnostic path resolution succeeds
        data_dir = tmp_path / "data"
        data_dir.mkdir(parents=True)
        test_file = data_dir / "file.xlsx"
        test_file.write_text("dummy")

        mock_diag_logging = MagicMock()

        with (
            patch(
                "autoconvert.cli.parse_args",
                return_value=MagicMock(diagnostic="file.xlsx"),
            ),
            patch("autoconvert.cli.setup_diagnostic_logging", mock_diag_logging),
            patch("autoconvert.cli.setup_logging") as mock_normal_logging,
            patch("autoconvert.cli.load_config", return_value=MagicMock()),
            patch("autoconvert.cli.run_batch", return_value=batch_result),
            patch("autoconvert.cli.print_batch_summary"),
            patch("autoconvert.cli.Path.cwd", return_value=tmp_path),
            pytest.raises(SystemExit),
        ):
            main()

        mock_diag_logging.assert_called_once()
        mock_normal_logging.assert_not_called()

    def test_main_diagnostic_file_not_found_exits_code2(
        self, tmp_path: Path,
    ) -> None:
        """Verify sys.exit(2) when diagnostic file does not exist."""
        with (
            patch(
                "autoconvert.cli.parse_args",
                return_value=MagicMock(diagnostic="nonexistent.xlsx"),
            ),
            patch("autoconvert.cli.setup_diagnostic_logging"),
            patch("autoconvert.cli.load_config", return_value=MagicMock()),
            patch("autoconvert.cli.Path.cwd", return_value=tmp_path),
            pytest.raises(SystemExit) as exc_info,
        ):
            main()

        assert exc_info.value.code == 2
