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

    # Allow callers to override database/schema or provide app_name/schema_key
    database_name = kwargs.get("database_name") or config_file.get(
        "database_name") or database_name
    schema_name = kwargs.get("schema_name") or config_file.get(
        "schema_name") or schema_name
    app_name = kwargs.get("app_name") or config_file.get(
        "app_name") or "DE_PROJECT_1"
    schema_key = kwargs.get("schema_key") or config_file.get(
        "schema_key") or None

    # Normalize / provide a sane default for on_error if missing
    on_error = (on_error or "CONTINUE").upper()

    # Allow overriding validation_mode via config; default to RETURN_ERRORS so we can capture rejects
    validation_mode = (config_file.get("validation_mode")
                       or "RETURN_ERRORS").upper()

    # Ensure reject table exists (safe schema using VARIANT payload)
    if reject_table:
        # allow caller to supply a simple name; map to fully-qualified name
        reject_table_full_name = (
            reject_table if "." in reject_table else f"{database_name}.{schema_name}.{reject_table}"
        )
        # create an enriched rejects table schema (idempotent)
        session.sql(
            f"""
            CREATE TABLE IF NOT EXISTS {reject_table_full_name} (
              id BIGINT AUTOINCREMENT,
              app_name VARCHAR,                -- application name that owns the load
              schema_key VARCHAR,              -- optional schema key / version used for validation
              payload VARIANT,
              error_message VARCHAR,
              error_code VARCHAR,
              source_stage VARCHAR,
              source_file VARCHAR,
              source_row INTEGER,
              raw_line STRING,
              parsed_cols VARIANT,
              copy_qid VARCHAR,
              target_table VARCHAR,
              retry_status VARCHAR DEFAULT 'NEW',
              attempts INTEGER DEFAULT 0,
              first_seen_ts TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP,
              last_attempt_ts TIMESTAMP_LTZ
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

    # Immediately capture the COPY query id (do this before any other SQL)
    qid = None
    try:
        qid = session.sql("SELECT LAST_QUERY_ID()").collect()[0][0]
    except Exception:
        qid = None

    # DEBUG: show how many rows COPY returned and sample shape
    try:
        print(f"📋 COPY returned {len(rows)} result rows (qid={qid})")
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

    # Persist COPY result rows into the reject table in a deterministic way
    persisted_count = None
    if reject_table and rows:
        # prefer using the helper with the explicit query id so RESULT_SCAN is deterministic
        try:
            # normalize fully-qualified reject table name (computed once)
            reject_table_full_name = (
                reject_table
                if "." in reject_table
                else f"{database_name}.{schema_name}.{reject_table}"
            )

            # Use the helper which will call TABLE(RESULT_SCAN('<qid>'))
            persisted_count = persist_copy_errors_from_last_query(
                session,
                reject_table_full_name=reject_table_full_name,
                full_audit=False,
                query_id=qid,
                target_table=target_table,
                app_name=app_name,
                schema_key=schema_key,
            )
            print(f"persisted_count={persisted_count} for qid={qid}")
        except Exception as e:
            # fallback: if helper not available, leave the old per-row insert logic (or log)
            print(f"persist_copy_errors helper failed: {e}")
            persisted_count = None

    # Return rows, qid and persisted_count (persisted_count may be None)
    return rows, qid, persisted_count
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


def persist_copy_errors_from_last_query(
    session,
    reject_table_full_name="DEMO_DB.PUBLIC.EMPLOYEE_REJECTS",
    full_audit=False,
    query_id=None,
    target_table: Optional[str] = None,
    app_name: Optional[str] = None,
    schema_key: Optional[str] = None,
):
    """
    Persist COPY/RESULT_SCAN rows into the reject table in a resilient way.

    - If query_id is provided, use TABLE(RESULT_SCAN('<query_id>')) to avoid LAST_QUERY_ID() races.
    - Persists file-summary rows and per-row rejects; captures raw_line, parsed_cols and copy_qid for recovery.
    - Adds app_name and schema_key to help tie rejects to the deploying app + validation schema.
    - When full_audit is False only non-LOADED rows are persisted.
    - Returns number of rows inserted (0 when nothing to persist), or -1 on error.
    """
    try:
        # choose RESULT_SCAN target deterministically
        if query_id:
            result_table_expr = f"TABLE(RESULT_SCAN('{query_id}'))"
        else:
            result_table_expr = "TABLE(RESULT_SCAN(LAST_QUERY_ID()))"

        # uniform object constructor for extraction
        from_subselect = f"(SELECT OBJECT_CONSTRUCT(*) AS obj FROM {result_table_expr})"

        # If not doing a full audit, only persist rows that look like per-row rejects:
        # require either a row/record or explicit error and exclude pure summary rows (COUNT(*), totals)
        status_filter = "" if full_audit else (
            "AND ( (obj:\"row\" IS NOT NULL OR obj:\"record\" IS NOT NULL "
            "OR obj:\"first_error\" IS NOT NULL OR obj:\"error\" IS NOT NULL OR obj:\"message\" IS NOT NULL) "
            "AND obj:\"COUNT(*)\" IS NULL )"
        )
        exclude_last_qid = "AND obj:\"LAST_QUERY_ID()\" IS NULL"

        # quick count check: avoid inserting when only LAST_QUERY_ID() or zero rows present
        count_sql = f"SELECT COUNT(*) FROM {from_subselect} WHERE 1=1 {status_filter} {exclude_last_qid}"
        try:
            cnt = int(session.sql(count_sql).collect()[0][0])
        except Exception:
            cnt = 0

        if cnt == 0:
            try:
                print(
                    f"persist_copy_errors_from_last_query: no rows to persist (count=0) for query_id={query_id}")
            except Exception:
                pass
            return 0

        # prepare SQL literal for copy_qid, target_table, app_name and schema_key
        # literal copy qid OR fall back to fields inside the RESULT_SCAN object
        copy_qid_lit = _sql_literal(query_id) if query_id else "NULL"
        target_table_lit = _sql_literal(
            target_table) if target_table else "NULL"
        # default app_name to a sensible literal if not supplied
        app_name_lit = _sql_literal(app_name or "DE_PROJECT_1")
        schema_key_lit = _sql_literal(schema_key) if schema_key else "NULL"

        # Insert only reject-like rows and populate fallbacks for file/row/parsed record keys
        insert_sql = f"""
        INSERT INTO {reject_table_full_name}
          (app_name, schema_key, payload, error_message, error_code, source_stage, source_file, source_row, raw_line, parsed_cols, copy_qid, target_table, first_seen_ts)
        SELECT
          {app_name_lit} AS APP_NAME,
          {schema_key_lit} AS SCHEMA_KEY,
          obj AS PAYLOAD,
          COALESCE(
            obj:"first_error"::STRING,
            obj:"error"::STRING,
            obj:"message"::STRING,
            obj:"first_error_message"::STRING,
            ''
          ) AS ERROR_MESSAGE,
          COALESCE(
            obj:"error_code"::STRING,
            obj:"code"::STRING,
            CASE
              WHEN LOWER(COALESCE(obj:"first_error"::STRING, '')) LIKE '%date%' AND LOWER(COALESCE(obj:"first_error"::STRING, '')) LIKE '%not recognized%' THEN 'DATE_PARSE_ERROR'
              WHEN LOWER(COALESCE(obj:"first_error"::STRING, '')) LIKE '%matching enclosing character%' THEN 'CSV_QUOTE_ERROR'
              WHEN LOWER(COALESCE(obj:"first_error"::STRING, '')) LIKE '%column count%' OR LOWER(COALESCE(obj:"first_error"::STRING, '')) LIKE '%column count mismatch%' THEN 'COLUMN_COUNT_MISMATCH'
              ELSE 'COPY_ERROR'
            END
          ) AS ERROR_CODE,
          -- try multiple common keys for stage
          COALESCE(obj:"stage"::STRING, obj:"stage_location"::STRING, obj:"stage_path"::STRING, '') AS SOURCE_STAGE,
          -- try multiple common keys for filename/path
          COALESCE(obj:"file"::STRING, obj:"source_file"::STRING, obj:"path"::STRING, '') AS SOURCE_FILE,
          COALESCE(obj:"first_error_line"::NUMBER, obj:"source_row"::NUMBER, obj:"line"::NUMBER, NULL) AS SOURCE_ROW,
          -- RAW_LINE: prefer obj.row (string) but fallback to textual variants of record/count
          COALESCE(
            TRY_CAST(obj:"row"::STRING AS STRING),
            TRY_CAST(obj:"raw_line"::STRING AS STRING),
            TRY_CAST(obj:"record"::STRING AS STRING),
            TRY_CAST(obj:"COUNT(*)"::STRING AS STRING),
            '') AS RAW_LINE,
          -- PARSED_COLS: try several keys that may contain structured record info
          COALESCE(obj:"record"::VARIANT, obj:"record_values"::VARIANT, obj:"parsed"::VARIANT, NULL) AS PARSED_COLS,
          COALESCE({copy_qid_lit}, TRY_CAST(obj:\"LAST_QUERY_ID()\" AS STRING), TRY_CAST(obj:\"query_id\" AS STRING), NULL) AS COPY_QID,
          {target_table_lit} AS TARGET_TABLE,
          CURRENT_TIMESTAMP() AS FIRST_SEEN_TS
        FROM {from_subselect}
        WHERE 1=1
        {status_filter}
        {exclude_last_qid}
        ;
        """
        session.sql(insert_sql).collect()
        return cnt
    except Exception as e:
        try:
            print(f"persist_copy_errors_from_last_query: {e}")
        except Exception:
            pass
        return -1
