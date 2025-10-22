from snowflake.snowpark.types import StructType
from snowflake.snowpark import Session
from tabulate import tabulate
import json
from importlib import resources
from pathlib import Path
from typing import Optional

from app.common.helpers import copy_to_table, json_to_struct_type
# Import example schema and config for copy_to_table_proc
from app.common.helpers import COPY_TO_TABLE_PROC_CONFIG_PATH, COPY_TO_TABLE_PROC_SCHEMA_PATH


#  Example procedure to copy data from one table to another using dynamic config and schema files

def test_manual_proc(session: Session, name: str) -> str:
    return f"Hello, {name}"


def copy_to_table_proc(session: Session, schema_key: str) -> str:
    """
    tags: core
    description: Copy staging data into target table using a schema key to select
                 the schema from app/schemas/schemas.json. Config is loaded from
                 app/config/copy_to_snowstg_udemy.json (packaged resource preferred).
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
        copied_into_result, qid = copy_to_table(
            session, config_file, schema=schema)
    except Exception as e:
        return f"❌ Copy operation failed: {e}"

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
    summary_text = format_copy_results(copied_into_result)

    # The actual copy is handled by copy_to_table(...) above.
    # Removed the redundant manual COPY which referenced an undefined csv_file_name.
    return f"✅ Copy completed.\n\nQuery ID: {qid}\n\n{summary_text}"
