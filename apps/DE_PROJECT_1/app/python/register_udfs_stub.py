# app/python/register_udfs.py

from deploy.deploy_manager import DeployManager
from deploy.utils.change_detection import get_changed_files_for_app
import importlib
from snowflake.snowpark import Session
from typing import Optional, List


def register_udfs(
    session: Session,
    app_name: str,
    env_name: str,
    stage_name: str,
    zip_name: str,
    previous_commit: str,
    current_commit: str,
    include_tags: Optional[List[str]] = None,
    dry_run: bool = False,
    verbosity: str = "summary"
):
    print(f"🚀 Starting register_udfs for app '{app_name}'")

    changed_files = get_changed_files_for_app(
        app_name, previous_commit, current_commit
    )

    manager = DeployManager(
        session=session,
        app_name=app_name,
        stage_name=stage_name,
        changed_files=changed_files,
        include_tags=include_tags,
        dry_run=dry_run,
        verbosity=verbosity
    )

    # This assumes DeployManager has a method for UDF registration
    udf_registered = manager.register_udfs()
    manager.emit_summary()

    udf_count = len(udf_registered)

    if dry_run:
        print(f"\n🧪 Dry-Run Summary")
        print(f"  App: {app_name}")
        print(f"  Environment: {env_name}")
        print(f"  Stage: {stage_name}")
        print(f"  UDFs Simulated: {udf_count}")
    else:
        print(f"\n📜 Registration Summary")
        print(f"  App: {app_name}")
        print(f"  Environment: {env_name}")
        print(f"  Stage: {stage_name}")
        print(f"  UDFs Registered: {udf_count}")

    if udf_count > 0:
        print(f"📦 Total UDFs registered: {udf_count}")
    else:
        print("⚠️ No UDFs were registered.")

    print("\n🔍 Registered UDFs:")
    for udf in udf_registered:
        print(f"  - {udf.get('name', '—')} | source=udf")

    print(f"✅ Completed register_udfs for app '{app_name}'")

    # Tag each UDF with source
    for udf in udf_registered:
        udf["source"] = "udf"

    return udf_registered
