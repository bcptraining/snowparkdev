from snowflake.snowpark.types import StructType
from snowflake.snowpark import Session
from tabulate import tabulate
import json
from common.helpers import copy_to_table, json_to_struct_type
# Import example schema and config for copy_to_table_proc
from common.helpers import COPY_TO_TABLE_PROC_CONFIG_PATH, COPY_TO_TABLE_PROC_SCHEMA_PATH


#  Example procedure to copy data from one table to another using dynamic config and schema files

def copy_to_table_proc(session: Session, schema_key: str) -> str:
    # Note: metadata in doc string is just documentation as the real metadata is provided in the MANUAL_PROCS registration dict in procedures_man.py
    """
    tags: core
    description: This procedure handles core dev logic.
    """
    def format_copy_results(copy_result_rows):
        table_data = []
        # Build table data summarizing copy results
        for row in copy_result_rows:
            file_name = row.file.split("/")[-1]
            status = row.status
            loaded = row.rows_loaded
            parsed = row.rows_parsed
            errors = row.errors_seen
            if errors:
                error_msg = f"{row.first_error} (line {row.first_error_line}, column {row.first_error_column_name})"
            else:
                error_msg = "—"
            table_data.append([file_name, status, loaded,
                               parsed, errors, error_msg])

        headers = ["📄 File Name", "Status", "Rows Loaded",
                   "Rows Parsed", "Errors Seen", "First Error"]
        print("\n✅ Copy Result Summary\n")
        print(tabulate(table_data, headers=headers, tablefmt="github"))

    # Load config from JSON
    with open(COPY_TO_TABLE_PROC_CONFIG_PATH, "r") as f:
        config_file = json.load(f)

    # Load schema file
    with open(COPY_TO_TABLE_PROC_SCHEMA_PATH, "r") as f:
        schema_file = json.load(f)

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
    copied_into_result, qid = copy_to_table(
        session, config_file, schema=schema)

    # Narrate Partial Loads in Deploy Summary
    # for row in copied_into_result:
    #     print(f"📄 {row.file}")
    #     print(f"   Status: {row.status}")
    #     print(f"   Rows: {row.rows_loaded}/{row.rows_parsed} loaded")
    #     if row.errors_seen:
    #         print(
    #             f"   ⚠️ Error: {row.first_error} at line {row.first_error_line}, column {row.first_error_column_name}")

    summary_text = format_copy_results(copied_into_result)

    # return f"Copy Result: {copied_into_result}, Query ID: {qid}"
    return f"✅ Copy completed.\n\nQuery ID: {qid}"
