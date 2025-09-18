from snowflake.snowpark import Session
from snowflake.snowpark.types import StringType
from typing import List, Optional, Callable
from pathlib import Path
import sys
import pickle

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

# 🛠️ Define your manual procedure


def copy_to_table_proc(session: Session, source_table: str, target_table: str) -> str:
    return f"Copied from {source_table} to {target_table}"


copy_to_table_proc.__module__ = "app.python.procedures_man"

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

    registered = []

    for proc in MANUAL_PROCS:
        if include_tags and not any(tag in include_tags for tag in proc.get("tags", [])):
            print(f"⏭️ Skipping {proc['name']} due to tag filter.")
            continue

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

        alias_path = "app.python.procedures_man"
        sys.modules[alias_path] = sys.modules[__name__]
        patched_func = pickle.loads(pickle.dumps(proc["func"]))

        vprint(
            f"🔗 Re-pickled {proc['name']} under alias: {alias_path}", verbosity)
        vprint(f"🔍 Pickled hex for {proc['name']}:", verbosity)
        vprint(pickle.dumps(patched_func).hex(), verbosity)

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

    if verbosity in ["summary", "verbose"]:
        print("\n📜 Registered Entities Summary:")
        print("+----------------------+-----------+--------------+----------+")
        print("| Name                 | Type      | Tags         | Source   |")
        print("+======================+===========+==============+==========+")
        for proc in registered:
            print(
                f"| {proc['name']:<20} | {proc['kind']:<9} | {', '.join(proc['tags']):<12} | manual   |")
            print("+----------------------+-----------+--------------+----------+")

    print(f"📦 Total manual registered: {len(registered)}")
    print(f"🚀 completed register_manual_procs for app '{app_name}'")

    return registered
