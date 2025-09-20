# ------------------------------------------------------------------------------------
# 📦 Legacy Auto Procedure Registry — Deprecated as of definition_version: '2'
#
# This file previously defined auto procedures using @auto_proc decorators for
# dynamic registration and tag-based filtering. As of Snowflake's declarative
# deployment framework (definition_version: '2'), all auto procedures are now
# defined in snowflake.yml and deployed via `snowflake deploy`.
#
# These decorators are commented out and retained for reference only.
# Manual procedures with parameters are still registered dynamically via procedures_man.py.
#
# ✅ Current Source of Truth: snowflake.yml
# ❌ Dynamic registration no longer used for auto procedures
#
# For historical context, the legacy dynamic registration logic is retained
# in register_procs(...) below, but is not invoked by deploy scripts.
# If you want to try it then go to procedures_auto.py and change the legace_code
# variable to True in register_all_procs(...) in register_procs.py. -- not used
# ------------------------------------------------------------------------------------


from snowflake.snowpark import Session
from snowflake.snowpark.stored_procedure import StoredProcedureRegistration
from snowflake.snowpark.functions import udf, sproc
from snowflake.snowpark.types import StringType
from app.common.registry import auto_proc, AUTO_PROCS
from typing import List, Optional


# 🎯 Tagging procedures with @auto_proc

print("✅ procedures_auto.py loaded")

# Note: All procedures must accept 'session' as the first parameter -- functions do not need this.


@auto_proc(name="hello_procedure", input_types=[StringType()], return_type=StringType(), tags=["core", "dev"])
def hello_procedure(session: Session, name: str) -> str:
    return f"Hello, {name}!"


@auto_proc(name="hello_procedure2", input_types=[StringType()], return_type=StringType(), tags=["dev"])
def hello_procedure2(session: Session, name: str) -> str:
    return f"Hi there, {name}!"


@auto_proc(name="test_procedure", input_types=[], return_type=StringType(), tags=["dev"])
def test_procedure(session: Session) -> str:
    return "Test procedure executed."


@auto_proc(name="test_procedure_two", input_types=[], return_type=StringType(), tags=["experimental"])
def test_procedure_two(session: Session) -> str:
    return "Second test procedure executed."


@auto_proc(name="hello_function", input_types=[StringType()], return_type=StringType(), tags=["core"], kind="function")
def hello_function(name: str) -> str:
    return f"Echo: {name}"

# 🚀 Auto-registration logic


def register_procs(
    session: Session,
    app_name: str,
    stage_name: str,
    zip_name: str,
    include_tags: Optional[List[str]] = None,
    dry_run: bool = False,
    verbosity: str = "summary"
) -> List[dict]:
    # def register_procs(session, app_name, stage_name, zip_name, include_tags=None, verbosity="normal"):
    """
    Registers tagged procedures/functions from AUTO_PROCS.
    Returns a list of dicts with source attribution.
    """
    from app.common.registry import AUTO_PROCS
    from snowflake.snowpark.functions import udf
    from tabulate import tabulate

    if verbosity in ("normal", "verbose"):
        print(
            f"📡 Auto-registering procedures for {app_name} in stage {stage_name}")

    # Filter by tags
    selected = []
    if include_tags:
        tag_set = set(include_tags)
        positive_tags = {tag for tag in tag_set if not tag.startswith("!")}
        negative_tags = {tag[1:] for tag in tag_set if tag.startswith("!")}

        for proc in AUTO_PROCS:
            proc_tags = proc.get("tags", set())
            if positive_tags and not proc_tags.intersection(positive_tags):
                continue
            if proc_tags.intersection(negative_tags):
                continue
            selected.append(proc)
    else:
        selected = AUTO_PROCS.copy()

    if verbosity == "verbose":
        print(
            f"🔍 Filtering procedures with tags: {', '.join(include_tags) if include_tags else 'ALL'}")
        print(f"✅ Selected {len(selected)} procedures for registration")

    # Register each entity
    for proc in selected:
        kind = proc.get("kind", "procedure")
        if kind == "function":
            udf(
                func=proc["func"],
                input_types=proc["input_types"],
                return_type=proc["return_type"],
                name=proc["name"],
                stage_location=f"@{stage_name}",
                replace=True,
                is_permanent=True,
                session=session
            )
        else:
            session.sproc.register(
                func=proc["func"],
                input_types=proc["input_types"],
                return_type=proc["return_type"],
                name=proc["name"],
                stage_location=f"@{stage_name}",
                replace=True,
                is_permanent=True,
                session=session
            )

        if verbosity == "verbose":
            print(
                f"✅ Registered {kind}: {proc['name']} ({', '.join(proc['tags'])})")

    # Inject source attribution
    for proc in selected:
        proc["source"] = "auto"

    # Summary table
    if verbosity in ("normal", "verbose") and selected:
        summary = [
            [proc["name"], "Function" if proc.get("kind") == "function" else "Procedure",
             ", ".join(proc.get("tags", [])), proc["source"]]
            for proc in selected
        ]
        print("\n📜 Registered Entities Summary:")
        print(tabulate(summary, headers=[
              "Name", "Type", "Tags", "Source"], tablefmt="grid"))

    return selected
