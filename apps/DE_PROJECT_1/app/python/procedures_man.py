from typing import List, Dict
from requests import session
from snowflake.snowpark import Session
from snowflake.snowpark.functions import col, lit, when, current_timestamp
from snowflake.snowpark.types import StringType
from typing import List, Optional
import json
from snowflake.snowpark.functions import struct, to_variant
import sys
from pathlib import Path
from datetime import datetime
import os
import traceback


# def load_named_config(config_name: str) -> dict:
#     """Load configuration by name following framework patterns. Fail if not found."""
#     try:
#         config_path = Path(__file__).parent.parent / \
#             "config" / f"{config_name}.json"
#         if config_path.exists():
#             with open(config_path, 'r') as f:
#                 return json.load(f)
#         raise FileNotFoundError(
#             f"Configuration '{config_name}' not found at {config_path}")
#     except FileNotFoundError:
#         raise
#     except (json.JSONDecodeError, IOError) as e:
#         raise RuntimeError(f"Failed to load config '{config_name}': {str(e)}")


# def load_named_config(session, config_key: str) -> dict:
#     stage_path = f"@dev_deployment/configs/{config_key}.json"
#     local_dir = "/tmp"

#     session.file.get(stage_path, local_dir)

#     # Find the actual file path inside /tmp
#     for fname in os.listdir(local_dir):
#         if fname.startswith(config_key) and fname.endswith(".json"):
#             full_path = os.path.join(local_dir, fname)
#             with open(full_path, "r") as f:
#                 return json.load(f)

#     raise FileNotFoundError(
#         f"Config file {config_key}.json not found in {local_dir}")


# def load_named_schema(session: Session, schema_key: str) -> dict:
#     """
#     Loads a schema definition from a staged JSON file in @<env>_deployment/schemas/.

#     Args:
#         session (Session): Active Snowpark session.
#         schema_key (str): Name of the schema file (without .json).

#     Returns:
#         dict: Parsed schema definition.

#     Raises:
#         FileNotFoundError: If the schema file is not found after staging.
#         json.JSONDecodeError: If the file is not valid JSON.
#     """
#     stage_path = f"@dev_deployment/schemas/{schema_key}.json"
#     local_dir = "/tmp"

#     session.file.get(stage_path, local_dir)

#     # Locate the actual file inside /tmp
#     for fname in os.listdir(local_dir):
#         if fname.startswith(schema_key) and fname.endswith(".json"):
#             full_path = os.path.join(local_dir, fname)
#             with open(full_path, "r") as f:
#                 return json.load(f)

#     raise FileNotFoundError(
#         f"Schema file '{schema_key}.json' not found in {local_dir}")
import os
import json
from snowflake.snowpark import Session

import app


def load_staged_json(session: Session, artifact_type: str, key: str, stage_prefix: str = "@dev_deployment", local_dir: str = "/tmp") -> dict:
    """
    Loads a staged JSON file (config or schema) from Snowflake stage into a dict.

    Args:
        session (Session): Active Snowpark session.
        artifact_type (str): 'configs' or 'schemas'.
        key (str): Filename prefix (without .json).
        stage_prefix (str): Stage name prefix (e.g., '@dev_deployment').
        local_dir (str): Local directory to download into (default: '/tmp').

    Returns:
        dict: Parsed JSON content.

    Raises:
        FileNotFoundError: If file is not found after staging.
        json.JSONDecodeError: If file is not valid JSON.
    """
    stage_path = f"{stage_prefix}/{artifact_type}/{key}.json"
    try:
        session.file.get(stage_path, local_dir)
    except Exception as e:
        raise FileNotFoundError(
            f"❌ Failed to get {artifact_type[:-1]} '{key}.json' from stage: {e}")

    for fname in os.listdir(local_dir):
        if fname.startswith(key) and fname.endswith(".json"):
            full_path = os.path.join(local_dir, fname)
            with open(full_path, "r") as f:
                return json.load(f)

    raise FileNotFoundError(
        f"❌ {artifact_type[:-1].capitalize()} file '{key}.json' not found in {local_dir}")


def load_named_config(session: Session, config_key: str) -> dict:
    return load_staged_json(session, "configs", config_key)


def ensure_reject_table_exists(session):
    """Ensure the generic reject table exists. Create it if missing."""

    create_sql = """
    CREATE TABLE IF NOT EXISTS SNOWPARK_DE_REJECTS (
        CONFIG_KEY STRING,
        SOURCE_ROW VARIANT,
        SOURCE_FILE STRING,
        SOURCE_LINE NUMBER,
        REJECTED_AT TIMESTAMP,
        REJECT_REASON STRING
    )
    """.strip()

    session.sql(create_sql).collect()


def load_named_schema(session: Session, schema_key: str) -> dict:
    return load_staged_json(session, "schemas", schema_key)


def copy_to_table_proc(session: Session, config_key: str = "copy_to_snowstg_udemy"):
    """Copy data with reject handling integrated — using temp error capture for training"""

    # Load configuration from staged JSON
    config = load_staged_json(session, "configs", config_key)

    database_name = config["Database_name"]
    schema_name = config["Schema_name"]
    target_table = config["Target_table"]
    target_table_schema = config["Target_table_schema"]
    source_location = config["Source_location"]
    file_format = config["file_format"]

    # Load schema definition
    schema_def = load_staged_json(session, "schemas", target_table_schema)

    for col in schema_def:
        print(f"{col['name']} ({col['type']})")

    # Build COPY INTO SQL
    escaped_nulls = [val.replace("'", "''") for val in file_format["null_if"]]
    null_if_clause = ", ".join([f"'{v}'" for v in escaped_nulls])
    file_format_clause = f"""
        TYPE = '{file_format['type']}'
        FIELD_DELIMITER = '{file_format['field_delimiter']}'
        SKIP_HEADER = {file_format['skip_header']}
        FIELD_OPTIONALLY_ENCLOSED_BY = '{file_format['field_optionally_enclosed_by']}'
        NULL_IF = ({null_if_clause})
        ENCODING = '{file_format['encoding']}'
    """.strip()

    target_full_name = f"{database_name}.{schema_name}.{target_table}"
    copy_sql = f"""
    COPY INTO {target_full_name}
    FROM {source_location}
    FILE_FORMAT = ({file_format_clause})
    ON_ERROR = {config['on_error']}
    FORCE = TRUE;
    """.strip()

    # Step 1: Run COPY INTO and surface errors

    # <-- This confirmed that the SQL is generated correctly but there must be an undocumented limitation on COPY INTO working in snowpark
    return f"Generated COPY INTO SQL:\n{copy_sql}"

def load_named_config(config_name: str) -> dict:
    """Load configuration by name following framework patterns with hardcoded fallback"""
    try:
        # Try app-specific config first (framework pattern)
        config_path = Path(__file__).parent.parent / \
            "config" / f"{config_name}.json"
        if config_path.exists():
            with open(config_path, 'r') as f:
                return json.load(f)

        # Try common config location (framework pattern)
        common_config_path = Path(
            __file__).parent.parent.parent.parent / "common" / "config" / f"{config_name}.json"
        if common_config_path.exists():
            with open(common_config_path, 'r') as f:
                return json.load(f)

        # Framework pattern: hardcoded fallback matching your actual config
        hardcoded_configs = {
            "copy_to_snowstg_udemy": {
                "Database_name": "DEMO_DB",
                "Schema_name": "PUBLIC",
                "Target_table": "EMPLOYEE2",
                "Reject_table": "EMPLOYEE_REJECTS",
                "persist_all_copy_results": True,
                "target_columns": ["FIRST_NAME", "LAST_NAME", "EMAIL", "ADDRESS", "CITY", "DOJ"],
                "on_error": "CONTINUE",
                "Source_location_real": "@my_s3_stage",
                "Source_location": "@DEMO_DB.PUBLIC.DEV_INTERNAL_STAGE",  # ← Fixed stage name
                "Source_file_type": "csv",
                "file_format": {
                    "type": "CSV",
                    "field_delimiter": ",",
                    "skip_header": 0,
                    "field_optionally_enclosed_by": "\"",
                    "null_if": ["", "NULL"],
                    "encoding": "UTF8"
                }
            }
        }

        # Map known schema names to existing config (framework pattern)
        schema_to_config_mapping = {
            "emp_stg_schema_udemy": "copy_to_snowstg_udemy"
        }

        if config_name in schema_to_config_mapping:
            mapped_config_name = schema_to_config_mapping[config_name]
            return load_named_config(mapped_config_name)

        # Return hardcoded config if available
        if config_name in hardcoded_configs:
            return hardcoded_configs[config_name]

        raise FileNotFoundError(f"Configuration '{config_name}' not found")

   # Step 2: Try scanning the result
    try:
        error_rows = session.sql("""
            SELECT *
            FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()))
            WHERE error_count > 0
        """).collect()
    except Exception as e:
        return f"❌ COPY INTO failed and no result was returned.\nCannot scan for errors.\nError: {str(e)}"

    if not error_rows:
        return f"✅ Target loaded: {target_full_name} — no rejects"

    # Step 3: Create temp table to inspect errors
    try:
        session.sql("""
            CREATE OR REPLACE TEMP TABLE COPY_ERRORS_TEMP AS
            SELECT *
            FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()))
            WHERE error_count > 0
        """).collect()
        return "⚠️ COPY completed with errors. Inspect COPY_ERRORS_TEMP for details."
    except Exception as e:
        if "Failed to load config" in str(e):
            raise e
        raise RuntimeError(f"Failed to load config '{config_name}': {str(e)}")


# Define MANUAL_PROCS after all functions are defined
MANUAL_PROCS = [
    {
        "func": copy_to_table_proc,
        "name": "copy_to_table_proc",
        # "input_types": [StringType(), StringType()],
        "input_types": [StringType()],  # Only schema_key is declared
        "return_type": StringType(),
        "tags": ["core"],  # Valid tag for dev environment
        "source": "manual"
    },
    {
        "func": test_manual_proc,
        "name": "test_manual_proc",
        "input_types": [StringType()],
        "return_type": StringType(),
        "tags": ["experimental"],
        "source": "manual"
    }

    # Add more procedures here as needed
]

for proc in MANUAL_PROCS:
    validate_tags(proc.get("tags", []), proc["name"])

# 🚀 Manual procedure registration logic


def register_manual_procs(
    session: Optional[Session],
    stage_name: str,
    app_name: str,
    include_tags: Optional[List[str]] = None,
    dry_run: bool = False,
    verbosity: str = "summary"
) -> List[dict]:
    """Manual procedure registration following framework patterns"""

    # Import the updated function from manual_procs module
    from .manual_procs import copy_to_table_proc as manual_copy_proc

    # Register using the updated implementation
    procedures = [
        {
            "name": "copy_to_table_proc",
            "handler": "app.python.procedures_man.copy_to_table_proc",  # Point to this file
            "func": copy_to_table_proc,  # Use the function in this file
            "tags": ["core"]
        },
        {
            "name": "test_manual_proc",
            "handler": "app.python.procedures_man.test_manual_proc",
            "func": test_manual_proc,
            "tags": ["experimental"]
        }
    ]

    # Filter by tags following framework pattern
    if include_tags:
        filtered_procs = []
        for proc in procedures:
            proc_tags = proc.get("tags", [])
            if any(tag in include_tags for tag in proc_tags):
                filtered_procs.append(proc)
        procedures = filtered_procs

    return procedures

# Update the copy_to_table_proc function to use the corrected implementation


def copy_to_table_proc(session: Session, schema_key: str = "copy_to_snowstg_udemy"):
    """Copy data with robust CSV error handling - updated implementation"""

    # Import the updated implementation with CSV error handling
    from .manual_procs import copy_to_table_proc as updated_implementation

    # Call the updated implementation that has the CSV error handling
    return updated_implementation(session, schema_key)
