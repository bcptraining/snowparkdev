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

    # Build FILE_FORMAT clause from config.file_format (if present)
    ff_conf = config_file.get("file_format") or {}
    ff_items = []
    create_ff_items = []
    for k, v in ff_conf.items():
        key = k.upper()
        if isinstance(v, bool):
            val = "TRUE" if v else "FALSE"
            lit = val
        elif isinstance(v, (list, tuple)):
            lit = "(" + ", ".join([_sql_literal(x) for x in v]) + ")"
        else:
            lit = _sql_literal(v) if isinstance(v, str) else str(v)
        # For COPY without SELECT wrapper we will use the "(KEY => VAL)" form in the table-function
        ff_items.append(f"{key} => {lit}")
        # For CREATE FILE FORMAT we need "KEY = VAL" form
        create_ff_items.append(f"{key} = {lit}")
    ff_inner = ", ".join(
        ff_items) if ff_items else f"TYPE = '{source_file_type}'"
    # CREATE FILE FORMAT expects space-separated key = value pairs (no surrounding parentheses)
    create_ff_inner = " ".join(
        create_ff_items) if create_ff_items else f"TYPE = '{source_file_type}'"

    # qualify target_table if needed
    if "." not in target_table:
        target_table = f"{database_name}.{schema_name}.{target_table}"
    target_table = target_table.strip()

    # Use raw stage token (expecting '@my_s3_stage' or '@my_s3_stage/path') - do NOT quote it
    from_loc = source_location

    # If target_columns provided, build SELECT wrapper (explicit conversions).
    # VALIDATION_MODE is not allowed with transformations, so only include it when not using the wrapper.
    if target_columns:
        # create a temporary/permanent file format object and use its name (table-function requires a constant)
        fmt_name = (
            config_file.get("file_format_object")
            or f"{database_name}.{schema_name}.PROC_COPY_FMT"
        )
        # make sure fully qualified
        if "." not in fmt_name:
            fmt_name = f"{database_name}.{schema_name}.{fmt_name}"
        # create or replace file format using config props
        # emit CREATE ... FILE FORMAT without parentheses (valid Snowflake syntax)
        create_ff_sql = f"CREATE OR REPLACE FILE FORMAT {fmt_name} {create_ff_inner}"
        session.sql(create_ff_sql).collect()
        # e.g. 'DEMO_DB.PUBLIC.PROC_COPY_FMT'
        fmt_literal = _sql_literal(fmt_name)

        sel_parts = []
        for idx, col in enumerate(target_columns, start=1):
            if str(col).strip().upper() == "DOJ":
                sel_parts.append(f"TO_DATE(${idx}, 'MM/DD/YYYY') AS {col}")
            else:
                sel_parts.append(f"${idx} AS {col}")
        select_clause = ", ".join(sel_parts)

        # Use the file-format object name as a constant (string literal) for the table-function
        copy_sql = f"""
          COPY INTO {target_table}
          FROM (
            SELECT {select_clause}
            FROM {from_loc} (FILE_FORMAT => {fmt_literal})
          )
          ON_ERROR = '{on_error}'
        """
    else:
        # safe to include VALIDATION_MODE when there's no SELECT transform
        copy_sql = f"""
          COPY INTO {target_table}
          FROM {from_loc} (FILE_FORMAT => ({ff_inner}))
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
    Read TABLE(RESULT_SCAN(LAST_QUERY_ID())) and persist each result row as JSON
    into the reject table. This ensures we always capture whatever Snowflake
    returned (even when named fields are missing).
    """
    try:
        rows = session.sql(
            "SELECT * FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()))").collect()
    except Exception:
        return

    def q(s):
        return ("'" + str(s).replace("'", "''") + "'") if s is not None and str(s) != "" else "NULL"

    import json
    for r in rows:
        try:
            d = r.asDict()
        except Exception:
            try:
                d = dict(r)
            except Exception:
                d = {"raw": str(r)}

        # Always persist the raw RESULT_SCAN row as JSON payload for diagnostics
        payload_json = json.dumps(d, default=str)
        payload_lit = f"PARSE_JSON({_sql_literal(payload_json)})"

        # Best-effort extract of common fields for searchable columns
        err_msg = d.get("first_error") or d.get(
            "first_error_message") or d.get("error") or d.get("message") or ""
        err_code = d.get("code") or d.get("error_code") or ""
        src_file = (d.get("file") or d.get("file_name")
                    or d.get("filename") or "").split("/")[-1]
        src_row = d.get("first_error_line") or d.get(
            "first_error_line_number") or d.get("line") or d.get("row") or None

        err_msg_lit = _sql_literal(err_msg)
        err_code_lit = _sql_literal(err_code)
        src_file_lit = _sql_literal(src_file)
        src_row_lit = str(src_row) if src_row is not None else "NULL"

        insert_sql = f"""
            INSERT INTO {reject_table_full_name}
              (payload, error_message, error_code, source_file, source_row, load_ts)
            VALUES ({payload_lit}, {err_msg_lit}, {err_code_lit}, {src_file_lit}, {src_row_lit}, CURRENT_TIMESTAMP())
        """
        try:
            session.sql(insert_sql).collect()
        except Exception:
            # avoid failing the proc for logging errors; print for debug
            import sys
            import traceback
            print("Warning: failed to persist reject metadata", file=sys.stderr)
            traceback.print_exc()
