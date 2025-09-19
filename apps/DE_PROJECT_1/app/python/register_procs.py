import importlib.util
import importlib
import sys
from snowflake.snowpark import Session
from typing import Optional, List
from pathlib import Path


def vprint(msg: str, verbosity: str):
    if verbosity == "verbose":
        print(msg)


def register_all_procs(
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
    # ------------------------------------------------------------------------------------
    # 📦 Auto Procedure Registration (Legacy Stub)
    #
    # Auto procedures were previously registered dynamically via procedures_auto.py.
    # As of Snowflake's declarative deployment framework (definition_version: '2'),
    # all auto procedures are now defined in snowflake.yml and deployed via `snowflake deploy`.
    #
    # This stub is retained for historical context only — no dynamic registration is performed.
    # ------------------------------------------------------------------------------------

    print(f"🚀 Starting register_all_procs for app '{app_name}'")

    print("📡 Auto procedures are deployed via snowflake.yml — skipping dynamic registration")
    registered = []
    manual_registered = []
    legacy_code = True  # Set to True to attempt legacy dynamic registration for reference
    if legacy_code:
        # Locate procedures_auto.py
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        proc_path = project_root / app_name / "app/python/procedures_auto.py"
        vprint(f"🔍 Looking for procedures_auto.py at: {proc_path}", verbosity)
        vprint(f"📂 Contents of: {proc_path.parent}", verbosity)
        for f in proc_path.parent.iterdir():
            vprint(f"  - {f.name}", verbosity)

        # Ensure import path includes app root
        import_root = proc_path.parent.parent.parent
        if str(import_root) not in sys.path:
            sys.path.insert(0, str(import_root))

        # Load and execute register_procs from procedures_auto
        try:
            spec = importlib.util.spec_from_file_location(
                "procedures_auto", str(proc_path))
            if spec is None or spec.loader is None:
                raise ImportError(f"Spec or loader missing for {proc_path}")

            procedures_auto = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(procedures_auto)

            if hasattr(procedures_auto, "register_procs"):
                registered = procedures_auto.register_procs(
                    session=session,
                    app_name=app_name,
                    stage_name=stage_name,
                    zip_name=zip_name,
                    include_tags=include_tags,
                    dry_run=dry_run,
                    verbosity=verbosity
                )
            else:
                print("⚠️ procedures_auto.py exists but register_procs(...) not found")
        except Exception as e:
            print(f"❌ Failed to import or execute procedures_auto.py: {e}")

    # Conditionally register manual procedures
    if include_manual:
        try:
            manual_module = importlib.import_module(
                f"apps.{app_name}.app.python.procedures_man")
            if hasattr(manual_module, "register_manual_procs"):
                manual_registered = manual_module.register_manual_procs(
                    session=session,
                    stage_name=stage_name,
                    app_name=app_name,
                    include_tags=include_tags,
                    dry_run=dry_run,
                    verbosity=verbosity
                )
            else:
                print(
                    "⚠️ procedures_man.py exists but missing register_manual_procs(...)")
        except ModuleNotFoundError:
            print("ℹ️ procedures_man.py not found. Skipping manual registration.")
        except Exception as e:
            print(f"❌ Failed to import or execute procedures_man.py: {e}")
    else:
        print("⏭️ Manual procedure registration skipped via flag.")

    # Summary
    auto_count = sum(1 for proc in registered if proc.get("source") == "auto")

    manual_count = sum(
        1 for proc in manual_registered if proc.get("source") == "manual")

    if not legacy_code:
        print("ℹ️ Auto procedure registration skipped — handled via snowflake.yml")

        if dry_run:
            print(f"\n🧪 Dry-Run Summary")
            print(f"  App: {app_name}")
            print(f"  Environment: {env_name}")
            print(f"  Stage: {stage_name}")
            if legacy_code:
                print(
                    f"  Auto Procedures Simulated (legacy path): {auto_count}")
            else:
                print(f"  Auto Procedures Simulated: 0 (handled via snowflake.yml)")
            print(f"  Manual Procedures Simulated: {manual_count}")
        else:
            print(f"\n📜 Registration Summary")
            print(f"  App: {app_name}")
            print(f"  Environment: {env_name}")
            print(f"  Stage: {stage_name}")
            if legacy_code:
                print(
                    f"  Auto Procedures Registered (legacy path): {auto_count}")
            else:
                print(f"  Auto Procedures Registered: 0 (handled via snowflake.yml)")
            print(f"  Manual Procedures Registered: {manual_count}")

        total = auto_count + manual_count
        if total > 0:
            print(
                f"📦 Total registered: {auto_count} auto, {manual_count} manual.")
        else:
            print("⚠️ No procedures or functions were registered.")

        print(f"🚀 completed register_all_procs for app '{app_name}'")

    return registered + manual_registered
