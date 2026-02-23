"""Configuration loader for AutoConvert.

Loads and validates all config files (field_patterns.yaml, currency_rules.xlsx,
country_rules.xlsx, output_template.xlsx). Implements FR-002.

Error codes owned by this module: ERR_001, ERR_002, ERR_003, ERR_004, ERR_005.
"""

from __future__ import annotations

from pathlib import Path

from autoconvert.config_helpers import (
    build_field_patterns,
    build_inv_no_cell_config,
    compile_pattern_list,
    load_lookup_table,
    load_yaml,
    validate_template,
)
from autoconvert.errors import ConfigError, ErrorCode
from autoconvert.models import AppConfig

# Expected field names for invoice and packing column definitions.
_INVOICE_FIELD_NAMES: frozenset[str] = frozenset(
    {
        "part_no",
        "po_no",
        "qty",
        "price",
        "amount",
        "currency",
        "coo",
        "cod",
        "brand",
        "brand_type",
        "model",
        "weight",
        "inv_no",
        "serial",
    }
)

_PACKING_FIELD_NAMES: frozenset[str] = frozenset(
    {"part_no", "po_no", "qty", "nw", "gw", "pack"}
)

# Config file names (relative to config_dir).
_YAML_FILENAME = "field_patterns.yaml"
_CURRENCY_FILENAME = "currency_rules.xlsx"
_COUNTRY_FILENAME = "country_rules.xlsx"
_TEMPLATE_FILENAME = "output_template.xlsx"


def load_config(config_dir: Path) -> AppConfig:
    """Load all four configuration files, validate, and return AppConfig.

    Reads field_patterns.yaml, currency_rules.xlsx, country_rules.xlsx,
    and output_template.xlsx from ``config_dir``. Validates structure,
    compiles regex patterns, builds lookup tables, and returns a fully
    populated AppConfig instance. Raises ConfigError on any validation
    failure. Fatal: caller must not proceed if this raises.

    Args:
        config_dir: Path to the directory containing the four config files.

    Returns:
        Fully populated AppConfig with all patterns compiled and lookups built.

    Raises:
        ConfigError: On any missing file, invalid regex, duplicate lookup key,
            missing YAML key, or invalid template structure.
    """
    # Step 1: Existence checks for all four files.
    yaml_path = config_dir / _YAML_FILENAME
    currency_path = config_dir / _CURRENCY_FILENAME
    country_path = config_dir / _COUNTRY_FILENAME
    template_path = config_dir / _TEMPLATE_FILENAME

    for path in (yaml_path, currency_path, country_path, template_path):
        if not path.exists():
            raise ConfigError(
                code=ErrorCode.ERR_001,
                message=f"Config file not found: {path}",
                path=str(path),
            )

    # Step 2: Load and validate YAML.
    yaml_data = load_yaml(yaml_path)

    # Step 3: Compile patterns and build field definitions from YAML data.
    invoice_sheet_patterns = compile_pattern_list(
        yaml_data["invoice_sheet"]["patterns"],
        "invoice_sheet",
        str(yaml_path),
    )
    packing_sheet_patterns = compile_pattern_list(
        yaml_data["packing_sheet"]["patterns"],
        "packing_sheet",
        str(yaml_path),
    )

    invoice_columns = build_field_patterns(
        yaml_data["invoice_columns"],
        _INVOICE_FIELD_NAMES,
        "invoice_columns",
        str(yaml_path),
    )
    packing_columns = build_field_patterns(
        yaml_data["packing_columns"],
        _PACKING_FIELD_NAMES,
        "packing_columns",
        str(yaml_path),
    )

    inv_no_cell = build_inv_no_cell_config(
        yaml_data["inv_no_cell"], str(yaml_path)
    )

    # Step 4: Load currency rules.
    currency_lookup = load_lookup_table(
        currency_path, "Currency_Rules", "currency_rules.xlsx"
    )

    # Step 5: Load country rules (with int->str normalization on Target_Code).
    country_lookup = load_lookup_table(
        country_path, "Country_Rules", "country_rules.xlsx"
    )

    # Step 6: Validate template structure.
    validate_template(template_path)

    # Step 7: Construct and return AppConfig.
    return AppConfig(
        invoice_sheet_patterns=invoice_sheet_patterns,
        packing_sheet_patterns=packing_sheet_patterns,
        invoice_columns=invoice_columns,
        packing_columns=packing_columns,
        inv_no_cell=inv_no_cell,
        currency_lookup=currency_lookup,
        country_lookup=country_lookup,
        output_template_path=template_path.resolve(),
        invoice_min_headers=7,
        packing_min_headers=4,
    )
