"""Tests for autoconvert.errors."""

from __future__ import annotations

import pytest

from autoconvert.errors import ConfigError, ErrorCode, ProcessingError, WarningCode


# ---------------------------------------------------------------------------
# ErrorCode
# ---------------------------------------------------------------------------


def test_error_code_values() -> None:
    """All ErrorCode members have string values equal to their names.

    Spot-checks ERR_001, ERR_031, ERR_052 and verifies every member in the
    catalog (per spec) exists and round-trips through string comparison.
    """
    expected_codes = [
        "ERR_001", "ERR_002", "ERR_003", "ERR_004", "ERR_005",
        "ERR_010", "ERR_011", "ERR_012", "ERR_013",
        "ERR_014",
        "ERR_020", "ERR_021",
        "ERR_030", "ERR_031", "ERR_032", "ERR_033", "ERR_034",
        "ERR_040", "ERR_041", "ERR_042", "ERR_043", "ERR_044",
        "ERR_045", "ERR_046", "ERR_047", "ERR_048",
        "ERR_051", "ERR_052",
    ]
    defined_names = {member.name for member in ErrorCode}

    # Every code in the catalog must be defined.
    for code in expected_codes:
        assert code in defined_names, f"Missing ErrorCode member: {code}"

    # Spot-checks: str value equals the name.
    assert ErrorCode.ERR_001 == "ERR_001"
    assert ErrorCode.ERR_031 == "ERR_031"
    assert ErrorCode.ERR_052 == "ERR_052"

    # No reserved codes that should not exist.
    reserved_absent = ["ERR_049", "ERR_050"]
    for code in reserved_absent:
        assert code not in defined_names, f"Reserved code must not be defined: {code}"


def test_error_code_is_str_enum() -> None:
    """ErrorCode members are both str and Enum instances."""
    assert isinstance(ErrorCode.ERR_001, str)
    assert ErrorCode.ERR_020.value == "ERR_020"
    # str, Enum identity: the member itself compares equal to its plain string.
    assert ErrorCode.ERR_020 == "ERR_020"


# ---------------------------------------------------------------------------
# WarningCode
# ---------------------------------------------------------------------------


def test_warning_code_values() -> None:
    """WarningCode has ATT_002, ATT_003, ATT_004; ATT_001 must NOT exist."""
    assert WarningCode.ATT_002 == "ATT_002"
    assert WarningCode.ATT_003 == "ATT_003"
    assert WarningCode.ATT_004 == "ATT_004"

    defined_names = {member.name for member in WarningCode}
    assert "ATT_001" not in defined_names, "ATT_001 must not be defined (not in PRD catalog)"
    assert len(defined_names) == 3


# ---------------------------------------------------------------------------
# ProcessingError
# ---------------------------------------------------------------------------


def test_processing_error_fields() -> None:
    """ProcessingError stores all five fields correctly."""
    err = ProcessingError(
        "ERR_030",
        "msg",
        filename="f.xlsx",
        row=5,
        field="qty",
    )
    assert err.code == "ERR_030"
    assert err.message == "msg"
    assert err.filename == "f.xlsx"
    assert err.row == 5
    assert err.field == "qty"
    # str(Exception) reflects the message argument passed to super().__init__
    assert str(err) == "msg"


def test_processing_error_optional_fields_default_none() -> None:
    """ProcessingError optional fields default to None without raising."""
    err = ProcessingError("ERR_031", "msg")
    assert err.code == "ERR_031"
    assert err.message == "msg"
    assert err.filename is None
    assert err.row is None
    assert err.field is None


def test_processing_error_is_exception_subclass() -> None:
    """ProcessingError is a subclass of Exception and can be raised/caught."""
    assert issubclass(ProcessingError, Exception)
    with pytest.raises(ProcessingError) as exc_info:
        raise ProcessingError("ERR_040", "allocation error", row=10, field="nw")
    assert exc_info.value.code == "ERR_040"


def test_processing_error_uses_error_code_enum() -> None:
    """ProcessingError.code compares equal to ErrorCode enum members (str, Enum)."""
    err = ProcessingError(ErrorCode.ERR_031, "bad value")
    # ErrorCode is (str, Enum), so err.code == ErrorCode.ERR_031 must hold.
    assert err.code == ErrorCode.ERR_031
    assert err.code == "ERR_031"


# ---------------------------------------------------------------------------
# ConfigError
# ---------------------------------------------------------------------------


def test_config_error_fields() -> None:
    """ConfigError stores code, message, and path correctly."""
    err = ConfigError("ERR_001", "config missing", path="/config/x.yaml")
    assert err.code == "ERR_001"
    assert err.message == "config missing"
    assert err.path == "/config/x.yaml"
    assert str(err) == "config missing"


def test_config_error_path_optional() -> None:
    """ConfigError accepts path=None without raising."""
    err = ConfigError("ERR_002", "bad schema")
    assert err.path is None


def test_config_error_is_exception_subclass() -> None:
    """ConfigError is a subclass of Exception and can be raised/caught independently."""
    assert issubclass(ConfigError, Exception)
    # Must NOT be a subclass of ProcessingError (must remain separate for catch isolation).
    assert not issubclass(ConfigError, ProcessingError)
    with pytest.raises(ConfigError) as exc_info:
        raise ConfigError("ERR_003", "missing key")
    assert exc_info.value.code == "ERR_003"
