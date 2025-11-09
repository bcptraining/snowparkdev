from __future__ import annotations
# Remove the circular import - define procedures directly here
# from app.python.manual_procs import copy_to_table_proc, test_manual_proc

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

# Dynamically add the project root to PYTHONPATH before any repo-local imports
ROOT_DIR = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "../../../"))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

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

# 🛠️ Define manual procedures directly following framework patterns


def copy_to_table_proc(session: Session, schema_key: str = 'copy_to_snowstg_udemy'):
    """Enhanced procedure with correct config path following framework patterns."""

    try:
        # Find the config file in the uploaded app package following framework import conventions
        config_filename = f"{schema_key}.json"

        # Try multiple path resolution strategies following framework patterns
        config_paths = [
            f"app/config/{config_filename}",  # Original relative path
            f"config/{config_filename}",      # Alternative relative path
            os.path.join(os.path.dirname(__file__), "..", "config",
                         config_filename),  # Relative to current file
        ]

        config_path = None
        config = None

        for config_path_candidate in config_paths:  # Fix: use different variable name
            try:
                print(f"🔍 Trying config path: {config_path_candidate}")
                with open(config_path_candidate, 'r') as f:
                    config = json.load(f)
                config_path = config_path_candidate  # Set successful path
                print(f"✅ Config loaded from: {config_path}")
                break
            except FileNotFoundError:
                print(f"❌ Config not found at: {config_path_candidate}")
                continue

        if config is None:
            # List available files for debugging following framework diagnostic patterns
            print(f"📂 Current working directory: {os.getcwd()}")
            print(f"📂 Python path: {sys.path}")

            # List files in current directory and subdirectories
            for root, dirs, files in os.walk('.'):
                if 'config' in root or config_filename in ' '.join(files):
                    print(f"📁 Found in {root}: {files}")

            return f"ERROR: Config file '{config_filename}' not found in any expected location"

        print(f"📋 Config loaded: {json.dumps(config, indent=2)}")

        # Extract stage and file details following framework stage management patterns
        stage_name = config['Source_location']
        print(f"🎯 Target stage: {stage_name}")

        # List files in stage following framework stage management patterns from deploy/deploy_snowflake_app.py
        list_result = session.sql(f"LIST {stage_name}").collect()
        print(f"📂 Files in stage: {len(list_result)} found")

        for row in list_result:
            print(f"   📄 File: {row['name']} ({row['size']} bytes)")

        if not list_result:
            print("❌ No files found in stage - cannot proceed")
            return "ERROR: No files found in stage"

        # Test stage access following framework diagnostic patterns
        try:
            sample_result = session.sql(
                f"SELECT $1, $2, $3, $4, $5, $6 FROM {stage_name} LIMIT 1").collect()
            print(
                f"✅ Stage access confirmed - sample data: {sample_result[0] if sample_result else 'No data'}")
        except Exception as stage_error:
            print(f"❌ Stage access failed: {stage_error}")
            return f"ERROR: Stage access failed - {stage_error}"

        # Extract table configuration following framework config patterns
        database_name = config['Database_name']
        schema_name = config['Schema_name']
        target_table = config['Target_table']
        reject_table = config['Reject_table']
        target_columns = config['target_columns']
        file_format_config = config['file_format']
        on_error = config.get('on_error', 'ABORT')

        print(f"🎯 Target table: {database_name}.{schema_name}.{target_table}")
        print(f"🎯 Reject table: {database_name}.{schema_name}.{reject_table}")

        # Build COPY INTO command following framework SQL patterns
        file_format_sql = f"""
        FILE_FORMAT = (
            TYPE = '{file_format_config['type']}',
            FIELD_DELIMITER = '{file_format_config['field_delimiter']}',
            SKIP_HEADER = {file_format_config['skip_header']},
            FIELD_OPTIONALLY_ENCLOSED_BY = '{file_format_config['field_optionally_enclosed_by']}',
            NULL_IF = ({', '.join([f"'{x}'" for x in file_format_config['null_if']])})
        )"""

        columns_sql = '(' + ', '.join(target_columns) + ')'

        copy_sql = f"""
        COPY INTO {database_name}.{schema_name}.{target_table} {columns_sql}
        FROM {stage_name}
        {file_format_sql}
        ON_ERROR = '{on_error}'
        """

        print(f"🚀 Executing COPY command:")
        print(copy_sql)

        # Execute the COPY command following framework SQL execution patterns
        copy_result = session.sql(copy_sql).collect()

        # Process results following framework result processing patterns
        loaded_count = 0
        error_count = 0

        # COPY INTO results return Row objects with indexed columns
        # Typical columns: [file, status, rows_parsed, rows_loaded, error_limit, errors_seen, first_error, first_error_line, first_error_character, first_error_column_name]
        for row in copy_result:
            try:
                # Access by index - rows_loaded is typically column 3, errors_seen is column 5
                if len(row) > 3:
                    rows_loaded_val = row[3]
                    # Safe conversion to int following framework defensive patterns
                    if rows_loaded_val is not None and str(rows_loaded_val).isdigit():
                        loaded_count += int(str(rows_loaded_val))

                if len(row) > 5:
                    errors_seen_val = row[5]
                    # Safe conversion to int following framework defensive patterns
                    if errors_seen_val is not None and str(errors_seen_val).isdigit():
                        error_count += int(str(errors_seen_val))

                # Debug: print the row structure for troubleshooting
                print(f"   📄 COPY result row: {row}")

            except (IndexError, TypeError, ValueError) as e:
                print(f"⚠️ Error processing COPY result row {row}: {e}")
                # Fallback: try to extract from string representation
                row_str = str(row)
                if "rows_loaded=" in row_str:
                    try:
                        import re
                        loaded_match = re.search(r'rows_loaded=(\d+)', row_str)
                        error_match = re.search(r'errors_seen=(\d+)', row_str)
                        if loaded_match:
                            loaded_count += int(loaded_match.group(1))
                        if error_match:
                            error_count += int(error_match.group(1))
                    except (ValueError, AttributeError):
                        # Can't parse fallback either, continue with next row
                        continue

        print(f"✅ COPY completed:")
        print(f"   📊 Rows loaded: {loaded_count}")
        print(f"   ❌ Errors seen: {error_count}")

        return f"SUCCESS: Loaded {loaded_count} rows, {error_count} errors, from {config_path}"

    except Exception as e:
        error_msg = f"ERROR in copy_to_table_proc: {e}"
        print(error_msg)
        import traceback
        print(f"📚 Full traceback: {traceback.format_exc()}")
        return error_msg


def test_manual_proc(session: Session, test_input: str = 'test'):
    """Simple test procedure following framework manual procs patterns."""
    try:
        result = f"Test procedure executed with input: {test_input}"
        print(f"🧪 {result}")
        return result
    except Exception as e:
        error_msg = f"ERROR in test_manual_proc: {e}"
        print(error_msg)
        return error_msg


# Set module aliases for Snowflake resolution following framework patterns
copy_to_table_proc.__module__ = "app.python.procedures_man"
test_manual_proc.__module__ = "app.python.procedures_man"

# Define MANUAL_PROCS following framework manual procs API patterns
MANUAL_PROCS = [
    {
        "func": copy_to_table_proc,
        "name": "copy_to_table_proc",
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
]

# Validate tags following framework tag validation patterns
for proc in MANUAL_PROCS:
    validate_tags(proc.get("tags", []), proc["name"])

# 🚀 Manual procedure registration logic following framework DeployManager patterns


def register_manual_procs(
    session: Optional[Session],
    stage_name: str,
    app_name: str,
    include_tags: Optional[List[str]] = None,
    dry_run: bool = False,
    verbosity: str = "summary"
) -> List[dict]:
    msg = f"📡 Manual-registering procedures for {app_name} in stage {stage_name}"
    vprint(msg, verbosity)

    proc_dir = Path(__file__).parent
    vprint(f"🔍 Looking for procedures_man.py at: {__file__}", verbosity)
    vprint(f"📂 Contents of: {proc_dir}", verbosity)
    for f in sorted(proc_dir.iterdir()):
        vprint(f"  - {f.name}", verbosity)

    # Normalize tag case following framework tag normalization patterns
    normalized_tags = [tag.lower()
                       for tag in include_tags] if include_tags else None

    registered = []

    for proc in MANUAL_PROCS:
        proc["source"] = "manual"
        proc["tags"] = [tag.lower()
                        for tag in proc.get("tags", [])]  # normalize tags

        if normalized_tags and not any(tag in normalized_tags for tag in proc["tags"]):
            print(f"⏭️ Skipping {proc['name']} due to tag filter.")
            continue

        if dry_run:
            param_types = ", ".join(
                t.__class__.__name__ for t in proc["input_types"])
            return_type = proc["return_type"].__class__.__name__
            print(
                f"📝 Would register: {proc['name']}({param_types}) → {return_type}")
            registered.append({
                "name": proc["name"],
                "kind": "procedure",
                "tags": proc["tags"],
                "source": "manual",
                "status": "dry_run"
            })
            continue

        # Set module alias for Snowflake handler resolution following framework patterns
        alias_path = "app.python.procedures_man"
        sys.modules[alias_path] = sys.modules[__name__]

        patched_func = proc["func"]

        # Signature validation following framework procedure signature patterns
        sig = inspect.signature(patched_func)
        params = list(sig.parameters.values())
        print(f"🔍 Signature of {proc['name']}: {sig}")
        print(f"🔍 Param names: {[p.name for p in params]}")
        print(f"🔍 Param count: {len(params)}")

        # Handler path logging following framework diagnostic patterns
        handler_path = f"🔗 Handler path for {proc['name']}: {alias_path}.{patched_func.__name__}"
        print(handler_path)

        # Register procedure following framework manual procs registration patterns
        assert session is not None, "session is required for real registration"
        from typing import cast
        sess = cast(Session, session)

        orig_module = getattr(patched_func, "__module__", None)
        try:
            patched_func.__module__ = alias_path

            sess.sproc.register(
                func=patched_func,
                name=proc["name"],
                input_types=proc["input_types"],
                return_type=proc["return_type"],
                is_permanent=True,
                stage_location=f"@{stage_name}",
                imports=[f"@{stage_name}/apps/{app_name}/app.zip"],
                packages=["snowflake-snowpark-python==1.33.0",
                          "cloudpickle==3.0.0", "tabulate==0.9.0"],
                replace=True,
                is_pandas=False
            )

            print(f"✅ Manually registered: {proc['name']}")
            registered.append({
                "name": proc["name"],
                "kind": "procedure",
                "tags": proc["tags"],
                "source": "manual",
                "status": "registered"
            })
        finally:
            if orig_module is not None:
                patched_func.__module__ = orig_module

    # Summary reporting following framework summary patterns
    print(
        f"\n✅ Included {len(registered)} manual procedures based on tag filter")
    print(f"📦 Total manual registered: {len(registered)}")

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"🧠 Manual registration completed at {ts}")
    print(f"🚀 completed register_manual_procs for app '{app_name}'")

    return registered
