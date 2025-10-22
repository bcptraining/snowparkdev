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


def _sql_literal(val):
    """Return a SQL literal for string-like values (escape single quotes)."""
    if val is None:
        return "NULL"
    if isinstance(val, (dict, list)):
        s = json.dumps(val)
    else:
        s = str(val)
    # escape single quotes for SQL and wrap in single quotes
    escaped = s.replace("'", "''")
    return f"'{escaped}'"


def copy_to_table(session, config_file, schema=None, **kwargs):
    """
    Execute a COPY using the supplied config_file (dict). This function expects
    extract_copy_config(...) to return eight values including `on_error`.
    """
    (
        database_name,
        schema_name,
        target_table,
        reject_table,
        source_location,
        source_file_type,
        target_columns,
        on_error,
    ) = extract_copy_config(config_file)

    # Normalize / provide a sane default for on_error if missing
    on_error = (on_error or "CONTINUE").upper()

    # Allow overriding validation_mode via config; default to RETURN_ERRORS so we can capture rejects
    validation_mode = (config_file.get("validation_mode")
                       or "RETURN_ERRORS").upper()

    # Ensure reject table exists (safe schema using VARIANT payload)
    if reject_table:
        session.sql(
            f"""
            CREATE TABLE IF NOT EXISTS {database_name}.{schema_name}.{reject_table} (
              payload VARIANT,
              error_message VARCHAR,
              error_code VARCHAR,
              source_file VARCHAR,
              source_row INTEGER,
              load_ts TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP
            )
            """
        ).collect()

    # Build COPY statement (use VALIDATION_MODE to return errors for inspection)
    copy_sql = f"""
      COPY INTO {database_name}.{schema_name}.{target_table}
      FROM '{source_location}'
      FILE_FORMAT = (TYPE = '{source_file_type}')
      VALIDATION_MODE = '{validation_mode}'
      ON_ERROR = '{on_error}'
    """

    # Execute COPY and capture returned rows (errors) if any
    rows = session.sql(copy_sql).collect()

    # DEBUG: show how many rows COPY returned and sample shape
    try:
        print(f"📋 COPY returned {len(rows)} result rows")
        if rows:
            try:
                sample = rows[0].asDict()
            except Exception:
                # fallback for row-like objects
                try:
                    sample = dict(rows[0])
                except Exception:
                    sample = str(rows[0])
            print("📌 Sample returned row:", sample)
    except Exception:
        pass

    # If VALIDATION_MODE='RETURN_ERRORS', Snowflake returns error rows describing rejects.
    # Persist them into the reject table if configured.
    if reject_table and rows:
        for r in rows:
            try:
                d = r.asDict()
            except Exception:
                # Best-effort fallback for row->dict
                try:
                    d = dict(r)
                except Exception:
                    d = {"raw": str(r)}

            # Best-effort mapping: adapt keys depending on returned structure
            payload = d.get("row") or d.get(
                "content") or d.get("record") or d.get("raw")
            err_msg = d.get("error") or d.get("message") or d.get("err") or ""
            err_code = d.get("code") or d.get("error_code") or ""
            src_file = d.get("file") or d.get(
                "source") or d.get("src_file") or ""
            src_row = d.get("line") or d.get(
                "row_number") or d.get("row") or None

            # Insert into reject table (use PARSE_JSON for payload when possible)
            # Emit NULL when payload is missing to avoid PARSE_JSON(NULL) SQL error
            payload_literal = (
                "NULL" if payload is None else f"PARSE_JSON({_sql_literal(payload)})"
            )
            err_msg_lit = _sql_literal(err_msg)
            err_code_lit = _sql_literal(err_code)
            src_file_lit = _sql_literal(src_file)
            src_row_lit = str(src_row) if src_row is not None else "NULL"

            insert_sql = f"""
                INSERT INTO {database_name}.{schema_name}.{reject_table}
                  (payload, error_message, error_code, source_file, source_row)
                VALUES ({payload_literal}, {err_msg_lit}, {err_code_lit}, {src_file_lit}, {src_row_lit})
            """
            session.sql(insert_sql).collect()

    # Return the rows and a pseudo qid (adapt as your code expects)
    # If COPY returns a query id elsewhere, preserve that; otherwise return the rows
    qid = None
    try:
        qid = session.sql("SELECT LAST_QUERY_ID()").collect()[0][0]
    except Exception:
        qid = None

    return rows, qid
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


def persist_copy_errors_from_last_query(session, reject_table_full_name="DEMO_DB.PUBLIC.EMPLOYEE_REJECTS"):
    """
    Read the result of the most recent COPY (via RESULT_SCAN(LAST_QUERY_ID()))
    and persist per-file error metadata into the configured reject table.
    This function is defensive about available columns and uses an explicit
    INSERT column list to avoid column-misalignment issues.
    """
    try:
        rows = session.sql(
            "SELECT * FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()))").collect()
    except Exception:
        # nothing to persist or could not read last query result
        return

    def q(s):
        return ("'" + str(s).replace("'", "''") + "'") if s is not None and str(s) != "" else "NULL"

    for r in rows:
        try:
            d = r.asDict()
        except Exception:
            try:
                d = dict(r)
            except Exception:
                d = {"raw": str(r)}

        # robust field extraction (different COPY outputs expose slightly different names)
        errors = d.get("errors_seen") or d.get("errors") or 0
        if not errors:
            continue

        file_name = (d.get("file") or d.get("file_name")
                     or d.get("filename") or "").split("/")[-1]
        status = d.get("status") or ""
        rows_loaded = d.get("rows_loaded") if d.get(
            "rows_loaded") is not None else d.get("rows_parsed")
        rows_parsed = d.get("rows_parsed")
        first_error = d.get("first_error") or d.get(
            "first_error_message") or ""
        first_error_line = d.get("first_error_line") or d.get(
            "first_error_line_number")
        first_error_column = d.get(
            "first_error_column_name") or d.get("first_error_column")

        insert_sql = f"""
        INSERT INTO {reject_table_full_name}
          (FILE_NAME, STATUS, ROWS_LOADED, ROWS_PARSED, ERRORS_SEEN,
           FIRST_ERROR_MESSAGE, FIRST_ERROR_LINE_NUMBER, FIRST_ERROR_COLUMN_NAME, LOAD_TS)
        VALUES (
          {q(file_name)}, {q(status)}, {rows_loaded if rows_loaded is not None else 'NULL'},
          {rows_parsed if rows_parsed is not None else 'NULL'}, {errors},
          {q(first_error)}, {first_error_line if first_error_line is not None else 'NULL'},
          {q(first_error_column)}, CURRENT_TIMESTAMP()
        );
        """
        try:
            session.sql(insert_sql).collect()
        except Exception:
            import sys
            import traceback
            print("Warning: failed to persist reject metadata", file=sys.stderr)
            traceback.print_exc()
