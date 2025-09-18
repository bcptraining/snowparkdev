from snowflake.snowpark import Session
from snowflake.snowpark.types import StringType
from typing import List, Optional, Callable  # , Dict, Any
import sys
# from deploy.deploy_snowflake_app import validate_tags
ValidateTagsType = Callable[[List[str], Optional[str]], List[str]]
try:
    from deploy.deploy_snowflake_app import validate_tags
except ImportError:
    def fallback_validate_tags(tags: List[str], proc_name: Optional[str] = None) -> List[str]:
        return tags

    validate_tags: ValidateTagsType = fallback_validate_tags


# from deploy.deploy_snowflake_app import env_tag_defaults


# Valid functional tags for procedure classification
# VALID_TAGS = {
#     "core", "dev", "prod", "staging", "experimental",
#     "utility", "test", "internal", "public", "deprecated",
#     "custom", "analytics", "etl"
# }

# Define your procedure here
# if dry_run:
#     print(f"📝 Would register: {proc['name']}")
#     continue


def copy_to_table_proc(session: Session, source_table: str, target_table: str) -> str:
    # Your procedure logic goes here
    return f"Copied from {source_table} to {target_table}"


# Registry of manual procedures
MANUAL_PROCS = [
    {
        "func": copy_to_table_proc,
        "name": "copy_to_table_proc",
        "input_types": [StringType(), StringType()],
        "return_type": StringType(),
        "tags": ["experimental"]
    },
    # Add more procedures here
]


def zip_safe_alias(alias_path: str) -> str:
    sys.modules[alias_path] = sys.modules[__name__]
    return alias_path


for proc in MANUAL_PROCS:
    validate_tags(proc.get("tags", []), proc["name"])


def register_manual_procs(
    session: Session,
    stage_name: str,
    app_name: str,
    include_tags: Optional[List[str]] = None,
    dry_run: bool = False,
    verbosity: str = "summary"
) -> List[dict]:
    registered = []

    # Patch the module path for ZIP-safe pickling
    alias_1 = zip_safe_alias(f"apps.{app_name}.app.python.procedures_man")
    alias_2 = zip_safe_alias("app.python.procedures_man")
    # alias_path = f"apps.{app_name}.app.python.procedures_man"
    # sys.modules[alias_path] = sys.modules[__name__]
    # zip_safe_alias(f"apps.{app_name}.app.python.procedures_man")
    # zip_safe_alias("app.python.procedures_man")
    if verbosity == "verbose":
        print(f"🔗 Patched module aliases:",)
        print(f"   - {alias_1} → {__name__}")
        print(f"   - {alias_2} → {__name__}")

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

        # Actual registration ----------------------

        # Assign the function to the alias path
        patched_func = proc["func"]

        session.sproc.register(
            func=patched_func,
            # func=proc["func"],
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

# Functional tags used for procedure classification:
# - "dev", "prod", "staging": environment targeting
# - "core", "experimental", "utility", "test": purpose and stability
# - "internal", "public", "deprecated": deployment exposure
# - "custom", "analytics", "etl": domain-specific roles

# Tag filtering is environment-aware via deploy_snowflake_app.py:
#   dev: includes "core", "experimental", "diagnostic"
#   qa:  includes "core", "diagnostic"
#   prod: includes "core", excludes "experimental", "diagnostic"
# Tags prefixed with "!" are excluded during filtering.


# if __name__ == "__main__":
#     def main():
#         session = get_session()
#         # stage_name = f"{env_name}_deployment"
#         register_manual_procs(session, stage_name = stage_name)
#     main()
