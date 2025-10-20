from snowflake.snowpark.types import StructType
import os
import sys

def _safe_parse_json_expr(obj) -> str:
    """
    Return a SQL expression safe to place in a VALUES clause:
    - PARSE_JSON('<escaped json>') when obj is a non-empty value
    - NULL when obj is None or empty or not serializable
    """
    import json as _json
    if obj is None:
        return "NULL"
    if isinstance(obj, str) and obj.strip() == "":
        return "NULL"
    try:
        s = obj if isinstance(obj, str) else _json.dumps(obj)
    except Exception:
        return "NULL"
    safe = s.replace("'", "''")
    return f"PARSE_JSON('{safe}')"

def copy_to_table(session, config_file: dict, schema: StructType) -> tuple:
    # Defensive guards
    if not config_file:
        return ([], "❌ Missing or empty config_file - ensure app/config is packaged and valid")
    if not schema:
        return ([], "❌ Missing or empty schema - ensure app/schemas contains the requested key")

    # Validate required config keys
    required_keys = ["Database_name", "Schema_name", "Target_table", "Source_location", "Source_file_type"]
    for k in required_keys:
        if not config_file.get(k):
            return ([], f"❌ Missing required config key: {k}")

    database_name = config_file.get("Database_name")
    Schema_name = config_file.get("Schema_name")
    Target_table = config_file.get("Target_table")
    target_columns = config_file.get("target_columns")
    on_error = config_file.get("on_error")
    Source_location = config_file.get("Source_location")
    source_file_type = str(config_file.get("Source_file_type", "csv")).lower()

 # 🧪 Validate file type and apply schema
    if source_file_type == "csv":
        try:
            # Do not add extra quotes around the stage path
            df = session.read.schema(schema).csv(Source_location)
        except Exception as e:
            return ([], f"❌ Failed to read source CSV at {Source_location}: {e}")
    else:
        return ([], f"❌ Unsupported file type: {config_file.get('Source_file_type')}")

    # 🧠 Track query history to extract COPY query ID and run copy
    try:
        with session.query_history() as query_history:
            copied_into_result = df.copy_into_table(
                f'"{database_name}"."{Schema_name}"."{Target_table}"',
                target_columns=target_columns,
                force=True,
                on_error=on_error
            )

            # Find the most recent COPY query id
            qid = None
            for q in reversed(list(query_history.queries or [])):
                try:
                    sql_text = (getattr(q, "sql_text", "") or "").upper()
                    if "COPY" in sql_text:
                        qid = getattr(q, "query_id", None)
                        break
                except Exception:
                    continue
    except Exception as e:
        return ([], f"❌ Copy operation failed: {e}")

    return copied_into_result, qid
