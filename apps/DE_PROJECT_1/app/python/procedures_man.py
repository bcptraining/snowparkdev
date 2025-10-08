
import inspect
from snowflake.snowpark.types import StructType, StructField, StringType, IntegerType, FloatType, BooleanType
import json
from typing import Dict, Union
from datetime import datetime
from snowflake.snowpark import Session
from snowflake.snowpark.types import StringType
from typing import List, Optional, Callable
from pathlib import Path
import sys
import pickle
import importlib.util
import os
from snowflake.snowpark.types import StructType
from tabulate import tabulate  # For tabular outputs
from common.helpers import json_to_struct_type
from app.python.manual_procs import copy_to_table_proc, test_manual_proc


test_manual_proc.__module__ = "app.python.procedures_man"


# Dynamically add the project root to PYTHONPATH...........
ROOT_DIR = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "../../../"))
sys.path.insert(0, ROOT_DIR)

# Dynamically load the common module

# Yes, Cory — you should completely remove that load_common_module() function from procedures_man.py and replace it with a direct import:from common import json_to_struct_type

# def load_common_module():
#     common_path = os.path.abspath(os.path.join(
#         os.path.dirname(__file__), "../common/common.py"))
#     spec = importlib.util.spec_from_file_location("common", common_path)
#     if spec is None or spec.loader is None:
#         raise ImportError(
#             f"Could not load module spec or loader for {common_path}")
#     common = importlib.util.module_from_spec(spec)
#     spec.loader.exec_module(common)
#     print(f"🔍 Loading common.py from: {common_path}")
#     return common


# Load shared schema converter
# common = load_common_module()
# json_to_struct_type = common.json_to_struct_type


# 🧠 Optional tag validation fallback
ValidateTagsType = Callable[[List[str], Optional[str]], List[str]]
try:
    from deploy.deploy_snowflake_app import validate_tags
except ImportError:
    def fallback_validate_tags(tags: List[str], proc_name: Optional[str] = None) -> List[str]:
        return tags
    validate_tags: ValidateTagsType = fallback_validate_tags

# 🔊 Local verbosity helper


def vprint(msg: str, verbosity: str):
    if verbosity == "verbose":
        print(msg)


# 🛠️ Define your manual procedures

def load_copy_to_table():
    from DE_PROJECT_1.app.common.common import copy_to_table
    return copy_to_table


# copy_to_table_proc.__module__ = "app.python.manual_procs"

MANUAL_PROCS = [
    {
        "func": copy_to_table_proc,
        "name": "copy_to_table_proc",
        # "input_types": [StringType(), StringType()],
        "input_types": [StringType()],  # Only schema_key is declared
        "return_type": StringType(),
        "tags": ["experimental"],
        "source": "manual"
    },
    {
        "func": test_manual_proc,
        "name": "test_manual_proc",
        "input_types": [StringType()],
        "return_type": StringType(),
        "tags": ["example"],
        "source": "manual"
    }

    # Add more procedures here as needed
]

for proc in MANUAL_PROCS:
    validate_tags(proc.get("tags", []), proc["name"])

# 🚀 Manual procedure registration logic


def register_manual_procs(
    session: Session,
    stage_name: str,
    app_name: str,
    include_tags: Optional[List[str]] = None,
    dry_run: bool = False,
    verbosity: str = "summary"
) -> List[dict]:
    vprint(
        f"📡 Manual-registering procedures for {app_name} in stage {stage_name}", verbosity)

    proc_dir = Path(__file__).parent
    vprint(f"🔍 Looking for procedures_man.py at: {__file__}", verbosity)
    vprint(f"📂 Contents of: {proc_dir}", verbosity)
    for f in sorted(proc_dir.iterdir()):
        vprint(f"  - {f.name}", verbosity)

    # ✅ Normalize tag case
    normalized_tags = [tag.lower()
                       for tag in include_tags] if include_tags else None

    registered = []

    included = [proc for proc in MANUAL_PROCS if not normalized_tags or any(
        tag.lower() in normalized_tags for tag in proc.get("tags", []))]
    excluded = [proc for proc in MANUAL_PROCS if normalized_tags and not any(
        tag.lower() in normalized_tags for tag in proc.get("tags", []))]

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

        alias_path = "app.python.procedures_man"
        sys.modules[alias_path] = sys.modules[__name__]

        # Debuggin an issue with signature for the manual proc . The line below was replace with the 2 lines following
        # # patched_func = pickle.loads(pickle.dumps(proc["func"]))
        # import inspect

        # print(f"🔍 Signature of {proc['name']} before:",
        #       inspect.signature(proc["func"]))

        # import cloudpickle

        patched_func = proc["func"]

        # ✅ Signature inspection and validation
        sig = inspect.signature(patched_func)
        params = list(sig.parameters.values())
        print(f"🔍 Signature of {proc['name']}: {sig}")
        print(f"🔍 Param names: {[p.name for p in params]}")
        print(f"🔍 Param count: {len(params)}")

        def validate_manual_proc_signature(func, expected_input_count):
            if len(params) < 1 or params[0].name != "session":
                raise ValueError(
                    f"First parameter must be 'session', got '{params[0].name}'")
            if len(params[1:]) != expected_input_count:
                raise ValueError(
                    f"Expected {expected_input_count} user-supplied args, got {len(params[1:])}")

        validate_manual_proc_signature(patched_func, len(proc["input_types"]))
        # Debug lines above

        # # Added this as a debug step

        # print(f"🔍 Signature of {proc['name']} after patching:",
        #       inspect.signature(patched_func))

        # vprint(
        #     f"🔗 Re-pickled {proc['name']} under alias: {alias_path}", verbosity)
        # vprint(f"🔍 Pickled hex for {proc['name']}:", verbosity)
        # vprint(pickle.dumps(patched_func).hex(), verbosity)

        # This is critical for Snowflake to resolve the handler path correctly
        proc["func"].__module__ = "app.python.manual_procs"

        print(
            f"🔗 Handler path for {proc['name']}: {proc['func'].__module__}.{proc['func'].__name__}")

        session.sproc.register(
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
            is_pandas=False  # This was added during debugging when the manual proc signature was nt matching for some reason
        )

        print(f"✅ Manually registered: {proc['name']}")
        registered.append({
            "name": proc["name"],
            "kind": "procedure",
            "tags": proc["tags"],
            "source": "manual",
            "status": "registered"  # ✅ Added status for real registrations
        })

    # ✅ Narration block
    if verbosity in ["summary", "verbose"]:
        print(
            f"\n✅ Included {len(included)} manual procedures based on tag filter")
        if excluded:
            print(
                f"⏭️ Skipped {len(excluded)} manual procedures due to tag mismatch")

        print("\n📜 Registered Entities Summary:")
        print("+----------------------+-----------+--------------+----------+")
        print("| Name                 | Type      | Tags         | Source   |")
        print("+======================+===========+==============+==========+")
        for proc in registered:
            print(
                f"| {proc['name']:<20} | {proc['kind']:<9} | {', '.join(proc['tags']):<12} | manual   |")
            print("+----------------------+-----------+--------------+----------+")

    # ✅ Dry-run summary block
    if dry_run:
        print(
            f"\n🧪 Dry-Run Summary: {len(registered)} manual procedures simulated")

    print(f"📦 Total manual registered: {len(registered)}")
    print(
        f"🧠 Manual registration completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🚀 completed register_manual_procs for app '{app_name}'")

    return registered


if __name__ == "__main__":
    import os
    import importlib.util
    from snowflake.snowpark import Session
    from typing import Dict, Union

    # 🔧 Dynamically load common.py
    def load_common_module():
        common_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "../common/common.py"))
        spec = importlib.util.spec_from_file_location("common", common_path)
        if spec is None or spec.loader is None:
            raise ImportError(
                f"Could not load module spec or loader for {common_path}")
        common = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(common)
        return common

    # ✅ Load shared utilities
    common = load_common_module()
    json_to_struct_type = common.json_to_struct_type
    # import copy_to_table from common
    copy_to_table = load_copy_to_table()

    # 🔐 Load Snowflake credentials from env
    raw_connection_parameters = {
        "account": os.getenv("SNOWFLAKE_ACCOUNT"),
        "user": os.getenv("SNOWFLAKE_USER"),
        "password": os.getenv("SNOWFLAKE_PASSWORD"),
        "role": os.getenv("SNOWFLAKE_ROLE"),
        "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
        "database": os.getenv("SNOWFLAKE_DATABASE"),
        "schema": os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC")
    }

    # 🧼 Remove missing keys
    cleaned_connection_parameters: Dict[str, Union[str, int]] = {
        k: v for k, v in raw_connection_parameters.items() if v is not None
    }

    required_keys = ["account", "user", "password",
                     "role", "warehouse", "database", "schema"]
    missing = [k for k in required_keys if k not in cleaned_connection_parameters]
    if missing:
        raise ValueError(
            f"❌ Missing required connection parameters: {missing}")

    # 🚀 Create Snowpark session
    session = Session.builder.configs(cleaned_connection_parameters).create()

    # Set the default database and schema (context)
    session.sql(
        f"USE SCHEMA {cleaned_connection_parameters['database']}.{cleaned_connection_parameters['schema']}").collect()

    # 🧪 Run test with valid schema key
    result = copy_to_table_proc(session, "emp_stg_schema_udemy")
    print("✅ Result with valid schema:", result)

    # 🧪 Run test with invalid schema key
    # result = copy_to_table_proc(session, "nonexistent_schema_key")
    # print("❌ Result with invalid schema:", result)
