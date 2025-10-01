from snowflake.snowpark.types import StructType
import os
import sys


def copy_to_table(session, config_file: dict, schema: StructType) -> tuple:
    database_name = config_file.get("Database_name")
    Schema_name = config_file.get("Schema_name")
    Target_table = config_file.get("Target_table")
    target_columns = config_file.get("target_columns")
    on_error = config_file.get("on_error")
    Source_location = config_file.get("Source_location")

    # 🧪 Validate file type and apply schema
    if config_file.get("Source_file_type") == 'csv':
        df = session.read.schema(schema).csv(f"'{Source_location}'")
    else:
        raise ValueError(
            f"Unsupported file type: {config_file.get('Source_file_type')}")

    # 🧠 Track query history to extract COPY query ID
    with session.query_history() as query_history:
        copied_into_result = df.copy_into_table(
            f"{database_name}.{Schema_name}.{Target_table}",
            target_columns=target_columns,
            force=True,
            on_error=on_error
        )

    qid = None
    for id in query_history.queries:
        if "COPY" in id.sql_text:
            qid = id.query_id
            break

    return copied_into_result, qid
