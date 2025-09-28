from deploy.deploy_manager import DeployManager
from deploy.utils.change_detection import get_changed_files_for_app
import importlib.util
import importlib
import sys
from snowflake.snowpark import Session
from typing import Optional, List
from pathlib import Path


def vprint(msg: str, verbosity: str):
    if verbosity == "verbose":
        print(msg)


def register_manual_procs(
    session: Session,
    app_name: str,
    env_name: str,
    stage_name: str,
    zip_name: str,
    include_manual: bool = False,
    include_tags: Optional[List[str]] = None,
    dry_run: bool = False,
    verbosity: str = "summary"
):
    # Declarative procedures are now validated and registered via ProcRegistrar, not here.
    # declarative_procs = [
    #     {"name": "hello_procedure", "source": "declarative"},
    #     {"name": "hello_procedure2", "source": "declarative"},
    #     {"name": "test_procedure", "source": "declarative"},
    #     {"name": "test_procedure_two", "source": "declarative"},
    # ]
    manual_registered = []

    print(f"🚀 Starting register_manual_procs for app '{app_name}'")
    # print("📡 Auto procedures are deployed via snowflake.yml — skipping dynamic registration")

    # Manual procedure registration (refactored to detect file changes -- see below)
    # if include_manual:
    #     try:
    #         manual_module = importlib.import_module(
    #             f"apps.{app_name}.app.python.procedures_man")
    #         if hasattr(manual_module, "register_manual_procs"):
    #             manual_registered = manual_module.register_manual_procs(
    #                 session=session,
    #                 stage_name=stage_name,
    #                 app_name=app_name,
    #                 include_tags=include_tags,
    #                 dry_run=dry_run,
    #                 verbosity=verbosity
    #             )
    #             if manual_registered:
    #                 print("\n📊 Manual Procedure Summary:\n")
    #                 for proc in manual_registered:
    #                     name = proc.get("name", "—")
    #                     handler = proc.get("handler", "—")
    #                     params = ", ".join(
    #                         f'{p["name"]}: {p["type"]}' for p in proc.get("signature", [])) or "—"
    #                     returns = proc.get("returns", "—")
    #                     print(f" - {name} → {handler}({params}) → {returns}")
    #         else:
    #             print(
    #                 "⚠️ procedures_man.py exists but missing register_manual_procs(...)")
    #     except ModuleNotFoundError:
    #         print("ℹ️ procedures_man.py not found. Skipping manual registration.")
    #     except Exception as e:
    #         print(f"❌ Failed to import or execute procedures_man.py: {e}")
    # else:
    #     print("⏭️ Manual procedure registration skipped via flag.")

    # Summary counts

    changed_files = get_changed_files_for_app(app_name)

    manager = DeployManager(
        session=session,
        app_name=app_name,
        stage_name=stage_name,
        changed_files=changed_files,
        include_tags=include_tags,
        dry_run=dry_run,
        verbosity=verbosity
    )

    manual_registered = manager.register_manual()
    manager.emit_summary()

    # auto_count = len(declarative_procs)
    auto_count = len(validated_declarative_procs)
    manual_count = sum(
        1 for proc in manual_registered if proc.get("source") == "manual")

    # Summary narration
    if dry_run:
        print(f"\n🧪 Dry-Run Summary")
        print(f"  App: {app_name}")
        print(f"  Environment: {env_name}")
        print(f"  Stage: {stage_name}")
        print(f"  Auto Procedures Simulated: {auto_count}")
        print(f"  Manual Procedures Simulated: {manual_count}")
    else:
        print(f"\n📜 Registration Summary")
        print(f"  App: {app_name}")
        print(f"  Environment: {env_name}")
        print(f"  Stage: {stage_name}")
        print(f"  Auto Procedures Registered: {auto_count}")
        print(f"  Manual Procedures Registered: {manual_count}")

    total = auto_count + manual_count
    if total > 0:
        print(f"📦 Total registered: {auto_count} auto, {manual_count} manual.")
    else:
        print("⚠️ No procedures or functions were registered.")

    # ✅ Unified Registered Procs Summary
    print("\n🔍 Registered manual Procedures:")
    # for proc in declarative_procs:
    #     print(f"  - {proc['name']} | source=declarative")

    for proc in manual_registered:
        print(f"  - {proc.get('name', '—')} | source=manual")

    if not manual_registered:
        print("  ⚠️ No manual procedures registered.")

    print(f"🚀 completed register_manual_procs for app '{app_name}'")

    # tag each manual proc with source
    for proc in manual_registered:
        proc["source"] = "manual"

    # return validated_declarative_procs + manual_registered <-- original, but now declarative handled elsewhere

    return manual_registered
