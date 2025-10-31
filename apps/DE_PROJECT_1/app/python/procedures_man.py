from __future__ import annotations
from app.python.manual_procs import copy_to_table_proc, test_manual_proc
# removed unused imports
from snowflake.snowpark.types import StringType
from snowflake.snowpark import Session
import importlib.util
from datetime import datetime
from typing import List, Optional, Callable
import inspect
import os
import sys
from pathlib import Path

# Tests were moved to:
#   apps/DE_PROJECT_1/tests/test_procedures_man.py
# Keep this module runtime-only.

# Dynamically add the project root to PYTHONPATH before any repo-local imports...
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

        patched_func = proc["func"]

        # ✅ Signature inspection and validation
        sig = inspect.signature(patched_func)
        params = list(sig.parameters.values())
        print(f"🔍 Signature of {proc['name']}: {sig}")
        print(f"🔍 Param names: {[p.name for p in params]}")
        print(f"🔍 Param count: {len(params)}")

        def validate_manual_proc_signature(func, expected_input_count):
            if len(params) < 1 or params[0].name != "session":
                msg = "First parameter must be 'session', got '{}'".format(
                    params[0].name
                )
                raise ValueError(msg)
            if len(params[1:]) != expected_input_count:
                raise ValueError(
                    "Expected {} user-supplied args, got {}".format(
                        expected_input_count, len(params[1:])
                    )
                )

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
        # proc["func"].__module__ = "app.python.manual_procs"
        # Set module alias so Snowflake resolves the handler path correctly.
        # (Debug prints removed to satisfy line-length linting.)

        # Debug handler path removed (shortened to satisfy line-length linting).
        # Handler is set via module aliasing elsewhere so Snowflake resolves it.

        # session.sproc.register(
        #     func=patched_func,
        # Temporarily set patched func module to the alias used in the uploaded package
        orig_module = getattr(patched_func, "__module__", None)
        try:
            patched_func.__module__ = alias_path
            handler_path = "🔗 Handler path for {}: {}.{}".format(
                proc["name"], patched_func.__module__, patched_func.__name__
            )
            print(handler_path)

            # Narrow Optional[Session] for type-checkers and at runtime.
            assert session is not None, "session is required for real registration"
            # cast so strict checkers see Session
            from typing import cast
            sess = cast(Session, session)
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

            # success logging / summary record
            print(f"✅ Manually registered: {proc['name']}")
            registered.append({
                "name": proc["name"],
                "kind": "procedure",
                "tags": proc["tags"],
                "source": "manual",
                "status": "registered"  # ✅ Added status for real registrations
            })
        finally:
            # always restore original module to avoid side-effects
            if orig_module is not None:
                patched_func.__module__ = orig_module
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
            row = "| {name:<20} | {kind:<9} | {tags:<12} | manual   |".format(
                name=proc["name"], kind=proc["kind"], tags=", ".join(
                    proc["tags"])
            )
            print(row)
            print("+----------------------+-----------+--------------+----------+")

    # ✅ Dry-run summary block
    if dry_run:
        print(
            f"\n🧪 Dry-Run Summary: {len(registered)} manual procedures simulated")

    print(f"📦 Total manual registered: {len(registered)}")
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"🧠 Manual registration completed at {ts}")
    print(f"🚀 completed register_manual_procs for app '{app_name}'")

    return registered


if __name__ == "__main__":
    # Defensive loader for common helpers (reuse top-level importlib & Session)
    def load_common_module() -> object:
        common_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "../common/common.py"))
        spec = importlib.util.spec_from_file_location("common", common_path)
        if spec is None or spec.loader is None:
            raise ImportError(
                f"Could not load module spec or loader for {common_path}")
        common = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(common)
        return common

    common = load_common_module()
    copy_to_table = load_copy_to_table()
    # (no duplicate assignment)

    # Load Snowflake credentials from env (single, no-duplicates)
    raw_connection_parameters = {
        "account": os.getenv("SNOWFLAKE_ACCOUNT"),
        "user": os.getenv("SNOWFLAKE_USER"),
        "role": os.getenv("SNOWFLAKE_ROLE"),
        "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
        "database": os.getenv("SNOWFLAKE_DATABASE"),
        "schema": os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC"),
    }

    # Remove missing keys (keep simple typing to avoid inner re-imports)
    cleaned_connection_parameters = {
        k: v for k, v in raw_connection_parameters.items() if v is not None
    }

    required_keys = ["account", "user", "password",
                     "role", "warehouse", "database", "schema"]
    missing = [k for k in required_keys if k not in cleaned_connection_parameters]
    if missing:
        raise ValueError(
            f"❌ Missing required connection parameters: {missing}")

    # Create Snowpark session (smoke-run)
    session = Session.builder.configs(cleaned_connection_parameters).create()

    # Set DB/SCHEMA context
    db = cleaned_connection_parameters["database"]
    sch = cleaned_connection_parameters["schema"]
    schema_stmt = "USE SCHEMA {}.{}".format(db, sch)
    session.sql(schema_stmt).collect()

    # Non-destructive smoke test (wrapped to avoid crashing on failure)
    try:
        result = copy_to_table_proc(session, "emp_stg_schema_udemy")
        print("✅ Result with valid schema:", result)
    except Exception as e:
        print("⚠️ Smoke test failed:", e)
