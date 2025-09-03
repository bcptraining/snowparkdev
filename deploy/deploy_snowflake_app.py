import importlib  # for dynamic imports from the calling app
import zipfile
import subprocess

# type: ignore[attr-defined]
# from snowflake.snowpark.stored_procedure import CreateMode  # type: ignore  linter does not like this import so moved to dag where its needed


from snowflake.core import Root
from snowflake.core.task.dagv1 import DAGOperation

# from first_snowpark_project.app.python.session import get_session
# from first_snowpark_project.app.python.dags import dag
import sys
import os
import argparse
from pathlib import Path

APPS_DIR = Path("apps")
# sys.path.insert(0, str(APPS_DIR.resolve()))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


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
    required_dirs = ["", "app", "app/python"]
    for subdir in required_dirs:
        init_path = app_path / subdir / "__init__.py"
        if not init_path.exists():
            raise FileNotFoundError(
                f"Missing __init__.py in {init_path.parent}. "
                "Make sure this directory is a Python package."
            )


def load_app_modules(app_name):
    app_path = APPS_DIR / app_name
    ensure_init_files(app_path)

    # Trigger procedure registration via side effects
    # importlib.import_module(f"apps.{app_name}.app.python.register_procs")

    session_module = importlib.import_module(
        f"apps.{app_name}.app.python.session"
    )

    try:
        dags_module = importlib.import_module(
            f"apps.{app_name}.app.python.dags"
        )
        dag = getattr(dags_module, "dag", None)
    except ModuleNotFoundError:
        dag = None

    return session_module.get_session, dag


def parse_cli_args():
    # Dynamically list all subdirectories in apps/
    try:
        valid_apps = sorted([
            path.name for path in APPS_DIR.iterdir() if path.is_dir()
        ])
    except FileNotFoundError:
        print(f"❌ Error: '{APPS_DIR}' directory not found.")
        sys.exit(1)

    valid_envs = ["dev", "qa", "prod"]

    parser = argparse.ArgumentParser(
        description="Deploy Snowpark app",
        epilog="Example: python deploy_snowflake_app.py --app DE_PROJECT_1 --env dev"
    )
    parser.add_argument("--app", required=True, help="App name under apps/")
    parser.add_argument("--env", required=True, choices=valid_envs,
                        help="Environment name (dev, qa, prod)")
    parser.add_argument("--skip-dag", action="store_true",
                        help="Skip DAG deployment")

    args = parser.parse_args()

    # Validate app name with optional fuzzy suggestion
    if args.app not in valid_apps:
        suggestion = next(
            (app for app in valid_apps if app.lower() == args.app.lower()), None)
        if suggestion:
            print(f"⚠️ Did you mean: '{suggestion}'?")
        print(
            f"❌ Invalid app name: '{args.app}'. Available apps: {', '.join(valid_apps)}")
        sys.exit(1)

    return args


def validate_env_vars(required_vars):
    missing = [var for var in required_vars if not os.environ.get(var)]
    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}")


def print_env_summary(required_vars):
    print("\n🔗 Using Snowflake connection:")
    for var in required_vars:
        value = "***" if "PASSWORD" in var else os.environ[var]
        print(f"{var}: {value}")
    print()


def run_command(command, description):
    print(f"🚀 {description}...")
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Error during {description}:")
        print(result.stderr)
        raise RuntimeError(f"{description} failed")
    else:
        print(f"✅ {description} succeeded")
        print(result.stdout)

# Refactored zip function to accept project directory


def zip_source_code(source_dir: Path):
    source_dir = Path(source_dir)

    # Step 1. Clean up old artifacts
    for artifact in ["app.zip", "dependencies.zip"]:
        artifact_path = source_dir / artifact
        if artifact_path.exists():
            artifact_path.unlink()
            print(f"🧹 Removed old artifact: {artifact_path.name}")

    # Step 2. Zip the app/ folder
    print("Preparing artifacts for source code")

    app_dir = source_dir / "app"
    zip_path = source_dir / "app.zip"

    if not app_dir.exists():
        raise FileNotFoundError(
            f"Expected app directory at {app_dir}, but it was not found.")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file_path in app_dir.rglob("*"):
            if file_path.is_file():
                relative_path = file_path.relative_to(source_dir)
                zipf.write(file_path, relative_path)

    print(f"✅ Created zip at {zip_path}")


def main():

    # Step 0: Parse CLI arguments
    args = parse_cli_args()
    app_name = args.app
    env_name = args.env
    app_path = APPS_DIR / app_name

    # Step 1: dynamic import of session and dag from the calling app

    get_session, dag = load_app_modules(args.app)

    # Step 2: Definitions

    required_vars = [
        "SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_PASSWORD",
        "SNOWFLAKE_ROLE", "SNOWFLAKE_WAREHOUSE", "SNOWFLAKE_DATABASE"
    ]

    # print(f"📁 Changed working directory to: {app_path}")

    # Step 3: Validate environment variables
    creds = get_snowflake_credentials()
    validate_env_vars(required_vars)
    print_env_summary(required_vars)

   # Step 4: Extract credentials and check command line arguments

    account = creds["account"]
    user = creds["user"]
    password = creds["password"]
    role = creds["role"]
    warehouse = creds["warehouse"]
    database = creds["database"]
    schema = creds["schema"]

    # Step 5: Build Snowpark Project
    build_cmd = [
        "snow", "snowpark", "build",
        "--project",  str(APPS_DIR / app_name),
        "--temporary-connection",
        "--account", account,
        "--user", user,
        # "--password", password,  Rely on snowflake CLI config (config.toml)
        "--role", role,
        "--warehouse", warehouse,
        "--database", database,
        "--schema", schema,
        "--allow-shared-libraries"
    ]

    run_command(build_cmd, f"Building Snowpark project for app: {args.app}")

    # Step 6: Zip source code

    print(f"📦 Zipping source code in: {app_path}")
    zip_source_code(app_path)

    try:
        session = get_session()
    except Exception as e:
        print(f"❌ Failed to initialize Snowflake session: {e}")
        sys.exit(1)

    root = Root(session)

    # This guarantees the zip is refreshed in the stage before deployment.
    # session.file.put("app.zip", "@dev_deployment/app/", overwrite=True)

    # Step 7: Deploy Snowpark app
    deploy_cmd = [
        "snow", "snowpark", "deploy", "--replace", "--temporary-connection",
        "--project", str(APPS_DIR / app_name),
        "--account", account,
        "--user", user,
        # "--password", password,  Rely on snowflake CLI config (config.toml)
        "--role", role,
        "--warehouse", warehouse,
        "--database", database,
        "--schema", schema
    ]
    run_command(deploy_cmd, f"Deploying Snowpark project for app: {args.app}")

    #  Step 7B: Register Stored Procedures
    # Register procedures manually if needed
    try:
        register_module = importlib.import_module(
            f"{app_name}.app.python.register_procs")
        register_module.register_all_procs(session)
        print(f"✅ Registered manual procedures for app: {app_name}")
    except ModuleNotFoundError:
        print(f"ℹ️ No manual procedure registration found for app: {app_name}")

    # ✅ Step 8: Deploy DAG
    target_db = database
    schema_name = schema
    snowflake_schema = root.databases[target_db].schemas[schema_name]

    if not args.skip_dag:
        if dag:
            from snowflake.snowpark.stored_procedure import CreateMode  # type: ignore
            dag_op = DAGOperation(snowflake_schema)
            dag_op.deploy(dag, CreateMode.or_replace)
            print(f"✅ DAG deployed for app: {args.app}")
        else:
            print(
                f"ℹ️ No DAG found for app '{args.app}'. Skipping DAG deployment.")
    else:
        print(f"⏭️ DAG deployment skipped via CLI flag.")


if __name__ == "__main__":
    main()
