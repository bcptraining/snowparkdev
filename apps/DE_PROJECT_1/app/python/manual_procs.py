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
    Wrapper around copy_to_table that ensures we DO NOT return a SQL result
    containing a human-readable summary (which pollutes RESULT_SCAN).
    Instead print the summary and return the authoritative COPY qid.
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

    # Execute copy
    try:
        # ensure schema_key and app_name flow into the helper
        new_kwargs = dict(kwargs or {})
        new_kwargs.setdefault("schema_key", schema_key)
        new_kwargs.setdefault("app_name", new_kwargs.get(
            "app_name") or "DE_PROJECT_1")

        # call the core helper (which should return rows, qid, persisted_count)
        rows, qid, persisted_count = copy_to_table(
            session, config_file, schema=schema_key, **kwargs)
    except Exception as e:
        return f"❌ Copy operation failed: {e}"

    # Print summary for human consumption (Python stdout only)
    print("✅ Copy completed.")
    if qid:
        print(f"Query ID: {qid}")
    # short tabular summary (optional)
    # print(...)  # keep prints, avoid returning them as SQL rows

    # Return the qid (string) so callers / tests can use RESULT_SCAN(qid) in the same session
    return qid

    # Robust unpacking: accept old (rows, qid) and new (rows, qid, persisted_count)
    rows = qid = persisted_count = None
    if isinstance(result, (tuple, list)):
        if len(result) == 3:
            rows, qid, persisted_count = result
        elif len(result) == 2:
            rows, qid = result
            persisted_count = None
        else:
            # unexpected shape, keep as single value
            rows = result
    else:
        rows = result

    # preserve previous behavior but include persisted_count in logs/result
    if persisted_count is not None:
        print(f"📥 persisted_count={persisted_count}")
    # continue to formatting and final string return below

    # -----------------------
    # Helper to format results (kept in place)
    # -----------------------
    def format_copy_results(copy_result_rows):
        table_data = []
        for row in copy_result_rows:
            file_name = getattr(row, "file", "").split("/")[-1]
            status = getattr(row, "status", "")
            loaded = getattr(row, "rows_loaded", "")
            parsed = getattr(row, "rows_parsed", "")
            errors = getattr(row, "errors_seen", 0)
            if errors:
                error_msg = f"{getattr(row, 'first_error', '')} (line {getattr(row, 'first_error_line', '')}, column {getattr(row, 'first_error_column_name', '')})"
            else:
                error_msg = "—"
            table_data.append([file_name, status, loaded,
                              parsed, errors, error_msg])

        headers = ["📄 File Name", "Status", "Rows Loaded",
                   "Rows Parsed", "Errors Seen", "First Error"]
        summary = tabulate(table_data, headers=headers, tablefmt="github")
        print("\n✅ Copy Result Summary\n")
        print(summary)
        return summary

    # Narrate Partial Loads in Deploy Summary
    summary_text = format_copy_results(rows)

    # The actual copy is handled by copy_to_table(...) above.
    # Removed the redundant manual COPY which referenced an undefined csv_file_name.
    # Respect only the canonical config key "persist_all_copy_results"
    full_audit_flag = bool(config_file.get("persist_all_copy_results", False))
    # Resolve reject_table_full_name from config (case-insensitive)
    reject_table = (
        config_file.get("Reject_table")
        or config_file.get("reject_table")
        or config_file.get("RejectTable")
    )
    if reject_table:
        if "." not in reject_table:
            db = config_file.get(
                "Database_name") or config_file.get("database")
            schema = config_file.get(
                "Schema_name") or config_file.get("schema")
            if db and schema:
                reject_table_full_name = f"{db}.{schema}.{reject_table}"
            else:
                # leave unqualified; rely on session's current DB/SCHEMA
                reject_table_full_name = reject_table
        else:
            reject_table_full_name = reject_table

        persist_copy_errors_from_last_query(
            session, reject_table_full_name=reject_table_full_name, full_audit=full_audit_flag
        )
    else:
        # No reject table configured; skip persisting copy result rows.
        print("Info: No Reject_table configured in copy config; skipping persist of copy results.")
    return f"✅ Copy completed.\n\nQuery ID: {qid}\n\n{summary_text}"
