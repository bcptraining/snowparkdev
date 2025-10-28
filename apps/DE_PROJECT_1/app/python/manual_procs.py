from snowflake.snowpark.types import StructType
from snowflake.snowpark import Session
from tabulate import tabulate
import json
from importlib import resources
from pathlib import Path
from app.common.helpers import copy_to_table, json_to_struct_type, persist_copy_errors_from_last_query
# Import example schema and config for copy_to_table_proc
from app.common.helpers import COPY_TO_TABLE_PROC_CONFIG_PATH, COPY_TO_TABLE_PROC_SCHEMA_PATH
# typing.Optional not used anymore


#  Example procedure to copy data from one table to another using dynamic config and schema files

def test_manual_proc(session: Session, name: str) -> str:
    return f"Hello, {name}"


def copy_to_table_proc(session, schema_key, *args, **kwargs):
    """
    Wrapper around copy_to_table that prints a human-friendly summary (stdout only),
    returns the authoritative COPY LAST_QUERY_ID (qid), and persists rejects (in the same session).
    """
    # Load config (prefer package resource inside app.zip, fallback to file)
    cfg_name = Path(COPY_TO_TABLE_PROC_CONFIG_PATH).name
    try:
        cfg_text = resources.files("app").joinpath(
            "config", cfg_name).read_text()
        config_file = json.loads(cfg_text)
    except Exception:
        try:
            with open(COPY_TO_TABLE_PROC_CONFIG_PATH, "r") as f:
                config_file = json.load(f)
        except Exception as e:
            return f"❌ Failed to load config: {e}"

    # Load schemas (prefer packaged resource)
    schema_name = Path(COPY_TO_TABLE_PROC_SCHEMA_PATH).name
    try:
        schemas_text = resources.files("app").joinpath(
            "schemas", schema_name).read_text()
        schema_file = json.loads(schemas_text)
    except Exception:
        try:
            with open(COPY_TO_TABLE_PROC_SCHEMA_PATH, "r") as f:
                schema_file = json.load(f)
        except Exception as e:
            return f"❌ Failed to load schema file: {e}"

    # Extract raw schema by key
    raw_schema = schema_file.get(schema_key)
    if not raw_schema:
        available_keys = list(schema_file.keys())
        return (
            f"❌ Schema key '{schema_key}' not found in schema file.\n"
            f"📂 Available schema keys: {available_keys}"
        )

    # Convert raw schema to StructType
    try:
        schema = json_to_struct_type(raw_schema)
    except Exception as e:
        return f"❌ Failed to convert schema for key '{schema_key}': {e}"

    # Resolve flags and reject table name once
    full_audit_flag = bool(config_file.get("persist_all_copy_results", False))
    reject_table_cfg = (
        config_file.get("Reject_table")
        or config_file.get("reject_table")
        or config_file.get("RejectTable")
    )
    if reject_table_cfg:
        if "." not in reject_table_cfg:
            db = config_file.get(
                "Database_name") or config_file.get("database")
            schema_cfg = config_file.get(
                "Schema_name") or config_file.get("schema")
            reject_table_full_name = f"{db}.{schema_cfg}.{reject_table_cfg}" if db and schema_cfg else reject_table_cfg
        else:
            reject_table_full_name = reject_table_cfg
    else:
        reject_table_full_name = None

    # Prepare kwargs forwarded into copy_to_table
    new_kwargs = dict(kwargs or {})
    new_kwargs.setdefault("schema_key", schema_key)
    new_kwargs.setdefault("app_name", new_kwargs.get(
        "app_name") or "DE_PROJECT_1")

    # Execute copy and persist rejects (if configured)
    try:
        rows, qid, persisted_count = copy_to_table(
            session, config_file, schema=schema_key, **new_kwargs)
    except Exception as e:
        return f"❌ Copy operation failed: {e}"

    # Format & print summary (stdout only)yes
    def format_copy_results(copy_result_rows):
        table_data = []
        for row in (copy_result_rows or []):
            file_name = getattr(row, "file", "") or ""
            file_name = file_name.split("/")[-1] if file_name else ""
            status = getattr(row, "status", "") or ""
            loaded = getattr(row, "rows_loaded", "") or ""
            parsed = getattr(row, "rows_parsed", "") or ""
            errors = getattr(row, "errors_seen", 0) or 0
            if errors:
                error_msg = f"{getattr(row, 'first_error', '')} (line {getattr(row, 'first_error_line', '')}, column {getattr(row, 'first_error_column_name', '')})"
            else:
                error_msg = "—"
            table_data.append([file_name, status, loaded,
                              parsed, errors, error_msg])

        headers = ["📄 File Name", "Status", "Rows Loaded",
                   "Rows Parsed", "Errors Seen", "First Error"]
        summary = tabulate(table_data, headers=headers, tablefmt="github")
        return summary

    summary_text = format_copy_results(rows)

    # Persist rejects using helper (only if a reject table is configured)
    if reject_table_full_name:
        try:
            persist_copy_errors_from_last_query(
                session,
                reject_table_full_name=reject_table_full_name,
                full_audit=full_audit_flag,
                query_id=qid,
                app_name=new_kwargs.get("app_name"),
                schema_key=new_kwargs.get("schema_key"),
            )
        except Exception as e:
            # Log but do not mask the copy success
            print(f"Warning: persist_copy_errors_from_last_query failed: {e}")

    # Print human summary and return authoritative qid
    print("\n✅ Copy Result Summary\n")
    print(summary_text)
    return qid


CALL DEMO_DB.PUBLIC.COPY_TO_TABLE_PROC('emp_stg_schema_udemy')
-- read the qid value from the CALL result(the client will show it)
-- then inspect the COPY results using that returned qid:
SELECT COUNT(*) FROM TABLE(RESULT_SCAN('<returned_qid>'))
SELECT TO_VARCHAR(obj) FROM(SELECT OBJECT_CONSTRUCT(*) AS obj FROM TABLE(RESULT_SCAN('<returned_qid>'))) t
