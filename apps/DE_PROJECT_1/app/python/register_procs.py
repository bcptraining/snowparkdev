import importlib
from snowflake.snowpark import Session


def register_all_procs(session: Session, app_name: str, stage_name: str, zip_name: str, include_manual: bool = False):
    """
    Registers both automatic and manual procedures for a Snowflake app.

    Parameters:
    - session: Snowflake session object
    - app_name: Name of the app folder under apps/
    - stage_name: Name of the Snowflake stage (e.g., 'dev_deployment')
    - zip_name: Name of the zip file containing the app code
    - include_manual: Whether to include manual procedure registration
    """

    # Register automatic procedures
    try:
        auto_module = importlib.import_module(
            f"apps.{app_name}.app.python.procedures_auto"
        )
        auto_module.register_procs(session, app_name, stage_name, zip_name)
        print("✅ Auto procedures registered successfully.")
    except ModuleNotFoundError:
        print("ℹ️ procedures_auto.py not found. Skipping auto registration.")
    except AttributeError:
        print("⚠️ procedures_auto.py exists but missing register_procs(session, app_name, stage_name, zip_name)")

    # Conditionally register manual procedures
    if include_manual:
        try:
            manual_module = importlib.import_module(
                f"apps.{app_name}.app.python.procedures_man"
            )
            manual_module.register_manual_procs(session, stage_name)
            print("✅ Manual procedures registered successfully.")
        except ModuleNotFoundError:
            print("ℹ️ procedures_man.py not found. Skipping manual registration.")
        except AttributeError:
            print(
                "⚠️ procedures_man.py exists but missing register_manual_procs(session, stage_name)")
    else:
        print("⏭️ Manual procedure registration skipped via flag.")
