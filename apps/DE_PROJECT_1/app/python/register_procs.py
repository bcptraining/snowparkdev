import importlib.util
import os
import sys
from snowflake.snowpark import Session
from typing import Optional, List
from pathlib import Path


def register_all_procs(
    session: Session,
    app_name: str,
    env_name: str,  # ✅ new argument
    stage_name: str,
    zip_name: str,
    include_manual: bool = False,
    include_tags: Optional[List[str]] = None,
    dry_run: bool = False
):
    """
    Registers both automatic and manual procedures for a Snowflake app.
    """
    if dry_run:
        print(
            f"🧪 Dry-run: Skipping procedure registration for app '{app_name}'")
        return []

    registered = []

    # Dynamically load procedures_auto.py from disk
    # project_root = Path(__file__).resolve().parent.parent.parent.parent
    # proc_path = project_root / "apps" / app_name / "app/python/procedures_auto.py"
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    print(f"Project root resolved to: {project_root}")
    # proc_path = project_root / "apps" / app_name / "app/python/procedures_auto.py"
    # proc_path = project_root / app_name / "app/python/procedures_auto.py"
    proc_path = project_root / app_name / "app/python/procedures_auto.py"

    print(f"🔍 Looking for procedures_auto.py at: {proc_path}")
    print("📂 Contents of:", proc_path.parent)
    for f in proc_path.parent.iterdir():
        print("  -", f.name)

    import_root = proc_path.parent.parent.parent  # points to apps/DE_PROJECT_1
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))
    try:
        spec = importlib.util.spec_from_file_location(
            "procedures_auto", str(proc_path))
        if spec is None or spec.loader is None:
            raise ImportError(f"Spec or loader missing for {proc_path}")
    # --
    # Add the app root to sys.path so 'app' becomes importable
        # app_root = proc_path.parent.parent.parent  # points to apps/DE_PROJECT_1
        # if str(app_root) not in sys.path:
        #     sys.path.insert(0, str(app_root))
    # ----
        procedures_auto = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(procedures_auto)

        if hasattr(procedures_auto, "register_procs"):
            registered = procedures_auto.register_procs(
                session,
                app_name=app_name,
                stage_name=stage_name,
                zip_name=zip_name,
                include_tags=include_tags
            )
            print("✅ Auto procedures registered successfully.")
        else:
            print("⚠️ procedures_auto.py exists but register_procs(...) not found")

    except Exception as e:
        print(f"❌ Failed to import or execute procedures_auto.py: {e}")

    # Conditionally register manual procedures
    if include_manual:
        try:
            manual_module = importlib.import_module(
                f"apps.{app_name}.app.python.procedures_man"
            )
            manual_module.register_manual_procs(session, stage_name)
            # print("✅ Manual procedures registered successfully.")
        except ModuleNotFoundError:
            print("ℹ️ procedures_man.py not found. Skipping manual registration.")
        except AttributeError:
            print("⚠️ procedures_man.py exists but missing register_manual_procs(...)")
    # else:
    #     print("⏭️ Manual procedure registration skipped via flag.")

    if registered:
        print(f"✅ {len(registered)} auto procedures/functions registered.")
    # else:
    #     print("⚠️ No auto procedures or functions were registered.")

    if include_manual:
        print("⏭️ Manual procedure registration attempted.")
    # else: <-- There is a better message that displays from /workspaces/snowparkdev/deploy/deploy_snowflake_app.py
    #     print("⏭️ Manual procedure registration skipped via flag.")

    # print( <-- There is a better message that displays from /workspaces/snowparkdev/deploy/deploy_snowflake_app.py
    #     f"📦 Deployment complete for app '{app_name}' in environment '{env_name}'.")

    return registered
