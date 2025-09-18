import importlib.util
import sys
from snowflake.snowpark import Session
from typing import Optional, List
from pathlib import Path


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
    """
    Registers both automatic and manual procedures for a Snowflake app.
    """
    print(f"🚀 Starting register_all_procs for app '{app_name}'")

    if dry_run:
        print(
            f"🧪 Dry-run: Skipping procedure registration for app '{app_name}'")
        return []

    registered = []
    manual_registered = []

    # Locate procedures_auto.py
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    proc_path = project_root / app_name / "app/python/procedures_auto.py"
    print(f"🔍 Looking for procedures_auto.py at: {proc_path}")
    print("📂 Contents of:", proc_path.parent)
    for f in proc_path.parent.iterdir():
        print(f"  - {f.name}")

    # Ensure import path includes app root
    import_root = proc_path.parent.parent.parent
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

    # Load and execute register_procs
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
                include_tags=include_tags
            )
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
            if hasattr(manual_module, "register_manual_procs"):
                manual_registered = manual_module.register_manual_procs(
                    session=session,
                    stage_name=stage_name,
                    app_name=app_name,
                    include_tags=include_tags,
                    dry_run=dry_run,
                    # Fix this to pass in verbosity flag instead of hardcoding
                    verbosity="verbose" if dry_run else "summary"

                )
                print(
                    f"✅ {len(manual_registered)} manual procedures/functions registered.")
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
    print(
        f"✅ Auto procedure registration complete — {auto_count} entities tagged and deployed.")

    if registered or manual_registered:
        print(
            f"📦 Total registered: {len(registered)} auto, {len(manual_registered)} manual.")
    else:
        print("⚠️ No procedures or functions were registered.")

    print(f"🚀 completed register_all_procs for app '{app_name}'")

    return registered + manual_registered
