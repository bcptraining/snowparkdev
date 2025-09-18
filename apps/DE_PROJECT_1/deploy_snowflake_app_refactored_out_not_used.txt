import zipfile
import subprocess
from snowflake.core import Root
from snowflake.core.task.dagv1 import DAGOperation, CreateMode
from first_snowpark_project.app.python.session import get_session
from first_snowpark_project.app.python.dags import dag
import sys
import os
# added due to an import issue from first_snowpark_project
sys.path.append('/home/runner/work/snowparkdev/snowparkdev')
# Dynamically add the project root to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# assuming your DAG is defined as `dag = DAG(...)`
# from first_snowpark_project.app.python.dags import dag


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


def zip_source_code(project_dir):
    print("Preparing artifacts for source code")

    app_dir = os.path.join(project_dir, "app")
    zip_path = os.path.join(project_dir, "app.zip")
    if not os.path.exists(app_dir):
        raise FileNotFoundError(
            f"Expected app directory at {app_dir}, but it was not found.")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(app_dir):
            for file in files:
                full_path = os.path.join(root, file)
                # ✅ Preserve 'app/' in the zip structure
                relative_path = os.path.relpath(full_path, project_dir)
                zipf.write(full_path, relative_path)

    print(f"✅ Created zip at {zip_path}")


def main():
    # Step 1: Definitions
    required_vars = [
        "SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_PASSWORD",
        "SNOWFLAKE_ROLE", "SNOWFLAKE_WAREHOUSE", "SNOWFLAKE_DATABASE"
    ]

    directory_path = sys.argv[1]
    os.chdir(directory_path)

    account = os.environ["SNOWFLAKE_ACCOUNT"]
    user = os.environ["SNOWFLAKE_USER"]
    password = os.environ["SNOWFLAKE_PASSWORD"]
    role = os.environ["SNOWFLAKE_ROLE"]
    warehouse = os.environ["SNOWFLAKE_WAREHOUSE"]
    database = os.environ["SNOWFLAKE_DATABASE"]

    # Step 2: Validate environment variables
    validate_env_vars(required_vars)
    print_env_summary(required_vars)

   # Step 3: Check command line arguments
    if len(sys.argv) < 2:
        raise ValueError(
            "Usage: python deploy_snowflake_app.py <project_directory>")

    # run_command([
    #     "snow", "snowpark", "build",
    #     "--connection", "default",
    #     "--warehouse", os.environ["SNOWFLAKE_WAREHOUSE"]
    # ], "Building Snowpark project")

    # Step 4: Build Snowpark Project
    build_cmd = [
        "snow", "snowpark", "build",
        "--temporary-connection",
        "--account", account,
        "--user", user,
        "--password", password,
        "--role", role,
        "--warehouse", warehouse,
        "--database", database,
        "--schema", "PUBLIC"
    ]

    run_command(build_cmd, "Building Snowpark project")

    # Step 5: Zip source code
    # directory_path = sys.argv[1]
    # os.chdir(directory_path)
    print(f"Changed directory to {directory_path}")
    zip_source_code(directory_path)

    from snowflake.snowpark import Session

    session = Session.builder.configs({
        "account": account,
        "user": user,
        "password": password,
        "role": role,
        "warehouse": warehouse,
        "database": database,
        "schema": "PUBLIC"
    }).create()
    root = Root(session)

    # This guarantees the zip is refreshed in the stage before deployment.
    # session.file.put("app.zip", "@dev_deployment/app/", overwrite=True)

    # Step 6: Deploy Snowpark app
    deploy_cmd = [
        "snow", "snowpark", "deploy", "--replace", "--temporary-connection",
        "--account", account,
        "--user", user,
        "--password", password,
        "--role", role,
        "--warehouse", warehouse,
        "--database", database,
        "--schema", "PUBLIC"
    ]
    run_command(deploy_cmd, "Deploying Snowpark app")

    # ✅ Step 7: Deploy DAG manually
    schema = root.databases["demo_db"].schemas["public"]
    dag_op = DAGOperation(schema)
    dag_op.deploy(dag, CreateMode.or_replace)


if __name__ == "__main__":
    main()
