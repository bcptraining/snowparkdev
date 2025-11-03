from __future__ import annotations
from app.python.manual_procs import copy_to_table_proc, test_manual_proc
# removed unused imports
from snowflake.snowpark.types import StringType
from snowflake.snowpark import Session
from snowflake.snowpark.functions import col, lit, when, current_timestamp
from snowflake.snowpark.types import StructType, StructField, StringType, TimestampType
import importlib.util
from datetime import datetime
from typing import List, Optional, Callable
import inspect
import os
import sys
from pathlib import Path
import logging
import json

# Tests were moved to:
#   apps/DE_PROJECT_1/tests/test_procedures_man.py
# Keep this module runtime-only.

# Dynamically add the project root to PYTHONPATH before any repo-local imports....
ROOT_DIR = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "../../../"))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)


# Repo-local imports (safe now that ROOT_DIR is on sys.path)

test_manual_proc.__module__ = "app.python.procedures_man"
copy_to_table_proc.__module__ = "app.python.procedures_man"

# 🧠 Optional tag validation fallback
ValidateTagsType = Callable[[List[str], Optional[str]], List[str]]
try:
    from deploy.deploy_snowflake_app import validate_tags
except ImportError:
    def fallback_validate_tags(
        tags: List[str],
        proc_name: Optional[str] = None,
    ) -> List[str]:
        return tags
    validate_tags: ValidateTagsType = fallback_validate_tags

# 🔊 Local verbosity helper


def vprint(msg: str, verbosity: str):
    if verbosity == "verbose":
        print(msg)


# 🛠️ Define your manual procedures

def load_copy_to_table():
    # runtime package layout places app/ as package root inside the uploaded zip
    from app.common.helpers import copy_to_table
    return copy_to_table


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
