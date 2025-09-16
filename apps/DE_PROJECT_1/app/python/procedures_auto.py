from snowflake.snowpark import Session
from snowflake.snowpark.stored_procedure import StoredProcedureRegistration
from snowflake.snowpark.functions import udf, sproc
from snowflake.snowpark.types import StringType
from app.common.registry import auto_proc, AUTO_PROCS


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


def register_procs(session, app_name, stage_name, zip_name, include_tags=None):
    # For summary of registered procedures (keep out of deployed handlers)
    from tabulate import tabulate
    print(
        f"📡 Auto-registering procedures for {app_name} in stage {stage_name}")

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

    print(
        f"🔍 Filtering procedures with tags: {', '.join(include_tags) if include_tags else 'ALL'}")
    print(f"✅ Selected {len(selected)} procedures for registration")

    for proc in selected:
        kind = proc.get("kind", "procedure")  # ✅ pull from correct key

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
            print(
                f"✅ Registered function: {proc['name']} ({', '.join(proc['tags'])})")

        elif kind == "procedure":
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
            print(
                f"✅ Registered procedure: {proc['name']} ({', '.join(proc['tags'])})")

    print("✅ Tagged procedure registration complete.")
    #  Summary table of registered procs

    if selected:
        summary = []
        for proc in selected:
            summary.append([
                proc["name"],
                "Function" if proc.get("kind") == "function" else "Procedure",
                ", ".join(proc.get("tags", []))
            ])
        print("\n📜 Registered Entities Summary:")
        print(tabulate(summary, headers=[
              "Name", "Type", "Tags"], tablefmt="grid"))
    else:
        print("⚠️ No procedures or functions matched the tag filters.")
