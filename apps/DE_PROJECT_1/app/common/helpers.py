from snowflake.snowpark.types import StructType, StructField,   StringType, IntegerType, FloatType, DateType, BooleanType, TimestampType

from typing import Optional
import json
from pathlib import Path

# Definitions
TYPE_MAP = {
    "string": StringType(),
    "StringType": StringType(),
    "int": IntegerType(),
    "integer": IntegerType(),
    "IntegerType": IntegerType(),
    "float": FloatType(),
    "FloatType": FloatType(),
    "boolean": BooleanType(),
    "BooleanType": BooleanType(),
    "date": DateType(),
    "DateType": DateType(),
    "timestamp": TimestampType()
}

#  The paths to config and schema for
COPY_TO_TABLE_PROC_CONFIG_PATH = Path("app/config/copy_to_snowstg_udemy.json")
COPY_TO_TABLE_PROC_SCHEMA_PATH = Path("app/schemas/schemas.json")


def print_hello(name: str):
    return f"Hello {name}!"


def _normalize_config_keys(cfg: dict) -> dict:
    """
    Normalize config keys to lowercase underscored names so callers may supply
    either PascalCase / camelCase keys (as in your JSON) or the expected
    lowercase keys used by the helper functions.
    """
    if not isinstance(cfg, dict):
        return cfg
    return {str(k).strip().lower(): v for k, v in cfg.items()}


def extract_copy_config(config_file: dict):
    """
    Backwards-compatible extractor: accepts config files with mixed-case keys
    and returns the canonical tuple expected by copy_to_table.
    """
    cfg = _normalize_config_keys(config_file)

    required = [
        "database_name",
        "schema_name",
        "target_table",
        "source_location",
        "source_file_type",
    ]
    missing = [k for k in required if k not in cfg]
    if missing:
        raise KeyError(f"Missing required config keys: {missing}")

    # Optional values
    reject_table = cfg.get("reject_table") or cfg.get("rejecttable")
    target_columns = cfg.get("target_columns") or cfg.get("targetcolumns")
    on_error = cfg.get("on_error") or cfg.get("onerror") or "CONTINUE"

    return (
        cfg["database_name"],
        cfg["schema_name"],
        cfg["target_table"],
        reject_table,
        cfg["source_location"],
        cfg["source_file_type"],
        target_columns,
        on_error,
    )


def read_source_data(session, source_location: str, source_file_type: str, schema: Optional[StructType]):
    if source_file_type == "csv":
        if schema is None:
            raise ValueError("Schema must be provided for CSV source files.")
        return session.read.schema(schema).csv(source_location)
    else:
        raise NotImplementedError(f"Unsupported file type: {source_file_type}")


def get_copy_query_id(query_history) -> Optional[str]:
    for query in query_history.queries:
        if "COPY" in query.sql_text.upper():
            return query.query_id
    return None


def copy_to_table(session, config_file, schema: Optional[StructType] = None):
    (
        database_name,
        schema_name,
        target_table,
        target_columns,
        on_error,
        source_location,
        source_file_type
    ) = extract_copy_config(config_file)

    df = read_source_data(session, source_location, source_file_type, schema)

    with session.query_history() as query_history:
        copied_into_result = df.copy_into_table(
            f"{database_name}.{schema_name}.{target_table}",
            target_columns=target_columns,
            force=True,
            on_error=on_error
        )

    qid = get_copy_query_id(query_history)
    return copied_into_result, qid
# ✅ Function to convert JSON schema to StructType


def json_to_struct_type(schema_json: list) -> StructType:
    """
    Converts a JSON schema definition into a Snowpark StructType.
    Each field must contain 'name' and 'type', where 'type' matches a key in TYPE_MAP.
    """
    fields = []
    for field in schema_json:
        key = field["type"].lower()
        field_type = TYPE_MAP.get(key)
        if not field_type:
            raise ValueError(f"Unsupported type: {field['type']}")
        fields.append(StructField(field["name"], field_type))
    return StructType(fields)


def load_schema_from_json(json_path: str, schema_name: str) -> StructType:
    with open(json_path, "r") as f:
        all_schemas = json.load(f)
    fields = all_schemas.get(schema_name)
    if not fields:
        raise ValueError(f"Schema '{schema_name}' not found in {json_path}")
    return StructType([
        StructField(field["name"], TYPE_MAP[field["type"]])
        for field in fields
    ])


def load_named_config(config_name: str, config_dir: str | Path = "app/config") -> dict:
    config_dir = Path(config_dir)
    config_file = config_dir / f"{config_name}.json"

    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_file}")

    with open(config_file, "r") as f:
        config = json.load(f)

    if not isinstance(config, dict):
        raise ValueError(
            f"Expected a JSON object at root of {config_file}, got {type(config)}")

    return config


def prepare_copy_inputs(schema_file: str, schema_key: str, config_name: str):
    schema = load_schema_from_json(schema_file, schema_key)
    config = load_named_config(config_name)
    return config, schema


#  This version was working. Refactoring to helpers.py
#  but leaving here for reference.
# def copy_to_table(session, config_file, schema: Optional[StructType] = None):
#     database_name = config_file.get("database_name")
#     schema_name = config_file.get("schema_name")
#     target_table = config_file.get("target_table")
#     target_columns = config_file.get("target_columns")
#     on_error = config_file.get("on_error")
#     source_location = config_file.get("source_location")

#     if config_file.get("source_file_type") == 'csv':
#         if schema is None:
#             raise ValueError("Schema must be provided for CSV source files.")
#         df = session.read.schema(schema).csv(source_location)

#     with session.query_history() as query_history:
#         copied_into_result = df.copy_into_table(
#             f"{database_name}.{schema_name}.{target_table}",
#             target_columns=target_columns,
#             force=True,
#             on_error=on_error
#         )

#     qid = None
#     for query in query_history.queries:
#         if "COPY" in query.sql_text:
#             qid = query.query_id
#             break

#     return copied_into_result, qid
