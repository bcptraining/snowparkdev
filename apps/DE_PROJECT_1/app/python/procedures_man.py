from snowflake.snowpark import Session
from snowflake.snowpark.types import StringType
from typing import List, Optional, Callable
import sys
import pickle

# 🧠 Optional tag validation fallback
# If validate_tags isn't available (e.g. during local testing), use a no-op fallback
ValidateTagsType = Callable[[List[str], Optional[str]], List[str]]
try:
    from deploy.deploy_snowflake_app import validate_tags
except ImportError:
    def fallback_validate_tags(tags: List[str], proc_name: Optional[str] = None) -> List[str]:
        return tags
    validate_tags: ValidateTagsType = fallback_validate_tags

# 🛠️ Define your manual procedure


def copy_to_table_proc(session: Session, source_table: str, target_table: str) -> str:
    return f"Copied from {source_table} to {target_table}"


# ✅ Patch the function's module path to match what Snowflake expects inside the ZIP
# This ensures that when pickled, the function references a resolvable module path
copy_to_table_proc.__module__ = "app.python.procedures_man"

# 📦 Register the procedure in a manual registry
# This allows you to tag, filter, and deploy it programmatically
MANUAL_PROCS = [
    {
        "func": copy_to_table_proc,
        "name": "copy_to_table_proc",
        "input_types": [StringType(), StringType()],
        "return_type": StringType(),
        "tags": ["experimental"]
    },
    # Add more procedures here as needed
]

# 🧪 Validate tags early to catch invalid or misclassified procedures
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
    registered = []

    for proc in MANUAL_PROCS:
        # 🧼 Skip procedures that don't match the tag filter
        if include_tags and not any(tag in include_tags for tag in proc.get("tags", [])):
            print(f"⏭️ Skipping {proc['name']} due to tag filter.")
            continue

        # 📝 Dry-run mode: simulate registration without executing it
        if dry_run:
            print(f"📝 Would register: {proc['name']}")
            registered.append({
                "name": proc["name"],
                "kind": "procedure",
                "tags": proc.get("tags", []),
                "source": "manual",
                "status": "dry_run"
            })
            continue

        # 🔗 Patch alias path in sys.modules so Snowflake can resolve it inside the ZIP
        # This ensures that the module path embedded in the pickle matches the ZIP structure
        alias_path = f"app.python.procedures_man"
        sys.modules[alias_path] = sys.modules[__name__]

        # 🧊 Pickle the function after rebinding its module path
        # This produces a ZIP-safe hex blob that Snowflake can deserialize
        patched_func = pickle.loads(pickle.dumps(proc["func"]))

        # 🧪 Verbose mode: show hex blob for inspection
        if verbosity == "verbose":
            print(f"🔗 Re-pickled {proc['name']} under alias: {alias_path}")
            print(f"🔍 Pickled hex for {proc['name']}:")
            print(pickle.dumps(patched_func).hex())

        # 📡 Register the procedure with Snowflake
        session.sproc.register(
            func=patched_func,
            name=proc["name"],
            input_types=proc["input_types"],
            return_type=proc["return_type"],
            is_permanent=True,
            stage_location=f"@{stage_name}",
            imports=[f"@{stage_name}/apps/{app_name}/app.zip"],
            packages=["snowflake-snowpark-python==1.33.0",
                      "cloudpickle==3.0.0"],
            replace=True
        )
        print(f"✅ Manually registered: {proc['name']}")
        registered.append({
            "name": proc["name"],
            "kind": "procedure",
            "tags": proc.get("tags", []),
            "source": "manual"
        })

    return registered
