import pytz
from datetime import datetime
import importlib
import zipfile
import subprocess
import shutil
import sys
import os
import time
import argparse
from pathlib import Path
from snowflake.core import Root
from snowflake.core.task.dagv1 import DAGOperation
import re  # for regex operations
from tag_registry import TAG_SETS
# tags = TAG_SETS[args.env] if 'env_name' in locals() else []  # Example usage


# Global constants
APPS_DIR = Path("apps")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

env_tag_defaults = {  # moved from inside parse_cli_args() to be a global constant
    "dev": ["core", "experimental", "diagnostic"],
    "qa": ["core", "diagnostic"],
    "prod": ["core", "!experimental", "!diagnostic"]
}

VALID_TAGS = {
    "core", "dev", "prod", "staging", "experimental",
    "utility", "test", "internal", "public", "deprecated",
    "custom", "analytics", "etl", "diagnostic"
}


def validate_tags(tags: list[str], proc_name: str | None = None) -> list[str]:
    invalid = [t for t in tags if t not in VALID_TAGS]
    if invalid:
        raise ValueError(
            f"❌ Procedure '{proc_name}' has invalid tags: {invalid}")
    return tags


# These functions are not currently used but might be helpful for future enhancements to compare existing procedure definitions.
# def get_current_def(session, proc_name):
#     ddl_query = f"SELECT GET_DDL('procedure', '{proc_name}')"
#     result = session.sql(ddl_query).collect()
#     return result[0][0] if result else None


# def extract_python_body(ddl_text):
#     match = re.search(r"AS\s+\$\$\s+(.*?)\s+\$\$", ddl_text, re.DOTALL)
#     return match.group(1).strip() if match else None

def get_snowflake_credentials():
    return {
        "account": os.environ["SNOWFLAKE_ACCOUNT"],
        "user": os.environ["SNOWFLAKE_USER"],
        "password": os.environ["SNOWFLAKE_PASSWORD"],
        "role": os.environ["SNOWFLAKE_ROLE"],
        "warehouse": os.environ["SNOWFLAKE_WAREHOUSE"],
        "database": os.environ["SNOWFLAKE_DATABASE"],
        "schema": os.environ.get("SNOWFLAKE_SCHEMA", "public")
    }


def ensure_init_files(app_path: Path):
    for subdir in ["", "app", "app/python"]:
        init_path = app_path / subdir / "__init__.py"
        if not init_path.exists():
            raise FileNotFoundError(
                f"Missing __init__.py in {init_path.parent}")


def load_app_modules(app_name):
    app_path = APPS_DIR / app_name
    ensure_init_files(app_path)
    session_module = importlib.import_module(
        f"apps.{app_name}.app.python.session")
    try:
        dags_module = importlib.import_module(
            f"apps.{app_name}.app.python.dags")
        dag_list = getattr(dags_module, "dags", [])
    except ModuleNotFoundError:
        dag_list = []
    return session_module.get_session, dag_list


def parse_cli_args():
    valid_apps = sorted([p.name for p in APPS_DIR.iterdir() if p.is_dir()])
    valid_envs = ["dev", "qa", "prod"]
    parser = argparse.ArgumentParser(description="Deploy Snowpark app")
    parser.add_argument("--app", required=True)
    parser.add_argument("--env", required=True, choices=valid_envs)
    parser.add_argument("--skip-dag", action="store_true")
    parser.add_argument("--include-manual-procs", action="store_true")
    parser.add_argument("--tags", nargs="*", default=None)
    parser.add_argument(
        "--verbosity",
        choices=["summary", "verbose"],
        default="verbose",
        help="Control output verbosity: 'verbose' shows full logs, 'summary' shows final deployment summary only"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Simulate deployment without executing Snowflake commands")
    args = parser.parse_args()

    # env_tag_defaults = {  <-- moved to be a global vonstant (see top)
    #     "dev": ["core", "experimental", "diagnostic"],
    #     "qa": ["core", "diagnostic"],
    #     "prod": ["core", "!experimental", "!diagnostic"]
    # }

    if not args.tags:
        args.tags = env_tag_defaults.get(args.env, [])
        print(
            f"🧠 No tags provided. Using default tags for '{args.env}': {', '.join(args.tags)}")

    if args.app not in valid_apps:
        suggestion = next((a for a in valid_apps if a.lower()
                          == args.app.lower()), None)
        if suggestion:
            print(f"⚠️ Did you mean: '{suggestion}'?")
        print(
            f"❌ Invalid app name: '{args.app}'. Available apps: {', '.join(valid_apps)}")
        sys.exit(1)

    return args


def validate_env_vars(required_vars):
    missing = [v for v in required_vars if not os.environ.get(v)]
    if missing:
        raise EnvironmentError(
            f"Missing required env vars: {', '.join(missing)}")


def print_env_summary(required_vars):
    print("\n🔗 Using Snowflake connection:")
    for var in required_vars:
        val = "***" if "PASSWORD" in var else os.environ[var]
        print(f"{var}: {val}")
    print()


def run_command(command, description):
    print(f"🚀 {description}...")
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Error during {description}:\n{result.stderr}")
        raise RuntimeError(f"{description} failed")
    else:
        print(f"✅ {description} succeeded\n{result.stdout}")


def inject_shared_modules(app_path: Path):
    # Thnis fn copies a shared registry.py file into a specific location inside an app structure.
    shared_registry = Path("common/registry.py")
    target_path = app_path / "app/common/registry.py"
    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(shared_registry, target_path)
    print(f"🔗 Injected shared registry.py into {target_path}")


def zip_source_code(source_dir: Path, zip_name: str = "app.zip", verbosity: str = "verbose") -> Path:
    print(
        f"📦 zip_source_code Zipping source code from: {source_dir} (excluding __pycache__, .pyc, .pyo)")
    zip_path = source_dir / zip_name
    for artifact in ["app.zip", "dependencies.zip"]:
        artifact_path = source_dir / artifact
        if artifact_path.exists():
            artifact_path.unlink()
            if verbosity == "verbose":
                print(f"🧹 Removed old artifact: {artifact_path.name}")

    app_dir = source_dir / "app"
    if not app_dir.exists():
        raise FileNotFoundError(f"Missing app directory: {app_dir}")

    def should_include(file_path: Path) -> bool:
        return not ("__pycache__" in file_path.parts or file_path.suffix in [".pyc", ".pyo"])

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file_path in app_dir.rglob("*"):
            if file_path.is_file() and should_include(file_path):
                zipf.write(file_path, file_path.relative_to(source_dir))

    print(f"✅ Created zip at {zip_path}")
    if verbosity == "verbose":
        with zipfile.ZipFile(zip_path, "r") as zipf:
            print("📦 Contents of zip:")
            for name in sorted(zipf.namelist()):
                print(f"  - {name}")
    vprint(f"end of zip_source_code: {zip_path}", verbosity)
    return zip_path


def vprint(msg: str, verbosity: str):
    if verbosity == "verbose":
        print(msg)


def main():
    args = parse_cli_args()
    app_name = args.app
    env_name = args.env
    verbosity = args.verbosity
    dry_run = args.dry_run
    app_path = APPS_DIR / app_name
    start_time = time.time()
    tags = TAG_SETS.get(env_name, [])

    print(
        f"🧭 Verbosity: {verbosity} — detailed logs {'enabled' if verbosity == 'verbose' else 'suppressed'}")
    print(f"🧠 Using tags for env '{env_name}': {tags}")

    print(
        f"\n🚀 Starting deployment for app: {app_name} in environment: {env_name}")

    get_session, dag_list = load_app_modules(app_name)

    required_vars = [
        "SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_PASSWORD",
        "SNOWFLAKE_ROLE", "SNOWFLAKE_WAREHOUSE", "SNOWFLAKE_DATABASE"
    ]
    validate_env_vars(required_vars)
    creds = get_snowflake_credentials()
    print_env_summary(required_vars)

    account, user, password, role = creds["account"], creds["user"], creds["password"], creds["role"]
    warehouse, database, schema = creds["warehouse"], creds["database"], creds["schema"]

    try:
        session = get_session()
        session.sql(f"USE DATABASE {database}").collect()
        root = Root(session)
    except Exception as e:
        print(f"❌ Failed to initialize Snowflake session: {e}")
        sys.exit(1)

    build_cmd = [
        "snow", "snowpark", "build",
        "--project", str(APPS_DIR / app_name),
        "--temporary-connection",
        "--account", account,
        "--user", user,
        "--role", role,
        "--warehouse", warehouse,
        "--database", database,
        "--schema", schema,
        "--allow-shared-libraries"
    ]
    run_command(build_cmd, f"Building Snowpark project for app: {app_name}")

    inject_shared_modules(app_path)

    stage_name = f"{env_name}_deployment"
    stage_target = f"@{stage_name}/apps/{app_name}"
    zip_file = zip_source_code(
        app_path, zip_name="app.zip", verbosity=verbosity)
    # print(f"📦 Zipping source code in: {app_path}") # redundant
    # print(f"📦 Created zip: {zip_file}") # redundant

    if not args.dry_run:
        vprint(f"📂 Files on stage @dev_deployment before upload:", verbosity)
        session.file.put(str(zip_file), stage_target,
                         overwrite=True, source_compression="NONE")
        files = session.sql(
            "LIST @dev_deployment/apps/DE_PROJECT_1/").collect()
        vprint(f"📂 Files on stage @dev_deployment  after upload:", verbosity)
        for f in files:
            vprint(f"📦 {f['name']}", verbosity)

    else:
        vprint(
            f"🧪 Dry-run: Skipping actual execution of session.file.put(", verbosity)

    print(f"📦 Uploaded app.zip to {stage_target}")

    deploy_cmd = [
        "snow", "snowpark", "deploy", "--replace", "--temporary-connection",
        "--project", str(APPS_DIR / app_name),
        "--account", account,
        "--user", user,
        "--role", role,
        "--warehouse", warehouse,
        "--database", database,
        "--schema", schema
    ]
    run_command(deploy_cmd, f"Deploying Snowpark project for app: {app_name}")
    print("⚠️ Note: Declarative procedures were deployed live. Dry-run mode does not simulate Snowpark deploy.")

    print("\n🔍 Registering auto procedures...")
    try:
        register_module = importlib.import_module(
            f"apps.{app_name}.app.python.register_procs")
        registered_procs = register_module.register_all_procs(
            session=session,
            app_name=app_name,
            env_name=env_name,
            stage_name=stage_name,
            zip_name=os.path.basename(zip_file),
            include_manual=args.include_manual_procs,
            include_tags=tags,
            dry_run=dry_run,
            verbosity=verbosity
        )

        auto_count = sum(
            1 for proc in (registered_procs or [])
            if proc.get("source") == "auto"
        )
        for proc in registered_procs or []:
            print(
                f"🔍 proc keys: {list(proc.keys())} — source: {proc.get('source')}")

        print(
            f"✅ Auto procedure registration complete. auto_count= {auto_count} procedures/functions registered.")
        # if registered_procs and verbosity == "verbose":
        #     # if registered_procs:
        #     print(f"\n📜 Auto-registered procedures:")
        #     for proc in registered_procs:
        #         print(
        #             f"  - {proc['kind']}: {proc['name']} ({', '.join(proc['tags'])})")
        # else: <-- This case is already handled inside register_all_procs
        #     print("⚠️ No auto procedures or functions were registered.")
    except ModuleNotFoundError:
        print(
            f"ℹ️ procedures_auto.py not found for app: {app_name}. Skipping auto registration.")
    except AttributeError as e:
        print(f"⚠️ register_all_procs() missing or misconfigured: {e}")

    # ✅ Step 10B: Register Manual Procedures (only if flag is passed)
    if args.include_manual_procs:
        try:
            manual_module = importlib.import_module(
                "app.python.procedures_man"
                # f"apps.{app_name}.app.python.procedures_man"
            )
            # See what files are in the stage before manual registration
            files = session.sql("LIST @dev_deployment/").collect()
            vprint(
                f"📂 Files on stage @dev_deployment/ before manual registration:", verbosity)
            for f in files:
                vprint(
                    f"📦 {f['name']} | {f['size']} bytes | {f['last_modified']}", verbosity)
            vprint(
                f"📂 Files on stage @dev_deployment/ after manual registration:", verbosity)

            # manual_module.register_manual_procs(session, stage_name, app_name, args.tags, dry_run=dry_run)
            print(
                f"stage_name={stage_name}, app_name={app_name}, tags={args.tags}, dry_run={dry_run}")
            # Ensure latest zip is on stage
            session.file.put(str(zip_file), stage_target, overwrite=True)
            manual_registered = manual_module.register_manual_procs(
                session=session,
                stage_name=stage_name,
                app_name=app_name,
                include_tags=tags,
                dry_run=dry_run,
                verbosity=verbosity
            )
            print(f"✅ Registered manual procedures from procedures_man.py")
        except ModuleNotFoundError:
            print(f"ℹ️ No procedures_man.py found for app: {app_name}")
        except AttributeError:
            print(
                f"⚠️ procedures_man.py exists but missing register_manual_procs(session)")
    else:
        print(f"⏭️ Manual procedure registration skipped via --include-manual-procs flag.")

    # ✅ Step 11: Deploy DAGs
    target_db = database
    schema_name = schema
    snowflake_schema = root.databases[target_db].schemas[schema_name]

    if not args.skip_dag:
        if dag_list:
            from snowflake.snowpark.stored_procedure import CreateMode  # type: ignore
            dag_op = DAGOperation(snowflake_schema)

            for dag in dag_list:
                try:
                    vprint(
                        f"📡 Deploying DAG handler: {dag.__name__}", verbosity)
                    # dag_op.deploy(dag, CreateMode.or_replace)
                    if not dry_run:
                        dag_op.deploy(dag, CreateMode.or_replace)
                        print(
                            f"✅ DAG '{dag.__name__}' deployed for app: {args.app}")
                    else:
                        print(
                            f"🧪 Dry-run: Skipping DAG deployment for '{dag.__name__}'")

                    # print(
                    #     f"✅ DAG '{dag.__name__}' deployed for app: {args.app}")
                except Exception as e:
                    print(f"❌ DAG '{dag.__name__}' deployment failed: {e}")
                    sys.exit(1)
        else:
            print(
                f"⚠️ No DAGs defined for app 'DE_PROJECT_1'. Skipping DAG deployment.")

    else:
        print(f"⏭️ DAG deployment skipped via CLI flag.")

    print(
        f"\n✅ Deployment completed successfully for app '{app_name}' in environment '{env_name}'.")


#  Step 12: Summary and Validation
# Comfirm whether registered_procs is populated and source is set to auto
    print("🔍 Registered Procs:")
    for proc in (registered_procs or []):
        print(f"  - {proc.get('name')} | source={proc.get('source')}")

    duration = round(time.time() - start_time, 2)
# 🧪 Print Summary Statement
    tag_summary = ", ".join(args.tags) if args.tags else "None"

    summary_time = datetime.now(pytz.timezone(
        "America/Vancouver")).strftime("%Y-%m-%d %H:%M %Z")

    if dry_run and verbosity in ["summary", "verbose"]:
        custom_auto_count = sum(
            1 for proc in registered_procs
            if proc.get("source") == "auto" and proc.get("status") == "dry_run"
        )

        manual_simulated = sum(
            1 for proc in manual_registered
            if proc.get("source") == "manual" and proc.get("status") == "dry_run"
        )

        print(
            f"🧪 Dry-Run Summary\n"
            f"  App: {app_name}\n"
            f"  Environment: {env_name}\n"
            f"  Stage: {stage_name}\n"
            f"  Tags Used: {tag_summary}\n"
            # f"✅ Auto Procedures(auto registry only): {auto_count} were deployed\n"
            f"  Auto Procedures (custom registry only): {custom_auto_count} simulated\n"
            f"  Manual Procedures: {manual_simulated} Simulated\n"
            f"  DAGs: Skipped\n"
            f"  Artifacts Uploaded: Simulated\n"
            f"🕒 Dry-run finished at: {summary_time}\n"
            f"⏱️ Total dry-run duration: {duration:.2f} seconds\n"
            f"✅ Dry-run completed. Manual and custom procedures were simulated only. Declarative procedures were deployed live via Snowpark.")

    else:
        print(
            f"\n📦 Deployment Summary\n"
            f"  App: {app_name}\n"
            f"  Environment: {env_name}\n"
            f"  Stage: {stage_name}\n"
            # f"✅ Auto Procedures(auto registry only): {auto_count} were deployed\n"
            f"  Auto Procedures Registered: {len(registered_procs) if registered_procs else 0}\n"
            f"  Manual Procedures: {'Registered' if args.include_manual_procs else 'Skipped'}\n"
            f"  DAGs: {'Deployed' if dag_list else 'None found'}\n"
            f"🕒 Deployment finished at: {summary_time}\n"
            f"\n✅ Deployment completed successfully for app '{app_name}' in environment '{env_name}'."
        )


if __name__ == "__main__":
    main()
