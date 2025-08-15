import sys
import os
import subprocess
import zipfile


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


def zip_source_code():
    print("Preparing artifacts for source code")

    # Dynamically resolve path relative to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    source_dir = os.path.join(
        script_dir, "first_snowpark_project")  # ✅ Adjusted
    zip_path = os.path.join(script_dir, "app.zip")

    if not os.path.isdir(source_dir):
        raise FileNotFoundError(f"Source directory not found: {source_dir}")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(source_dir):
            for file in files:
                full_path = os.path.join(root, file)
                relative_path = os.path.relpath(full_path, source_dir)
                zipf.write(full_path, os.path.join(
                    "first_snowpark_project", relative_path))

    print(f"✅ Created zip at {zip_path}")


def main():
    if len(sys.argv) < 2:
        raise ValueError(
            "Usage: python deploy_snowflake_app.py <project_directory>")

    directory_path = sys.argv[1]
    os.chdir(directory_path)

    required_vars = [
        "SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_PASSWORD",
        "SNOWFLAKE_ROLE", "SNOWFLAKE_WAREHOUSE", "SNOWFLAKE_DATABASE"
    ]

    validate_env_vars(required_vars)
    print_env_summary(required_vars)

    run_command([
        "snow", "snowpark", "build",
        "--connection", "default",
        "--warehouse", os.environ["SNOWFLAKE_WAREHOUSE"]
    ], "Building Snowpark project")

    zip_source_code()  # ✅ Add this step before deployment

    deploy_cmd = [
        "snow", "snowpark", "deploy", "--replace", "--temporary-connection",
        "--account", os.environ["SNOWFLAKE_ACCOUNT"],
        "--user", os.environ["SNOWFLAKE_USER"],
        "--password", os.environ["SNOWFLAKE_PASSWORD"],
        "--role", os.environ["SNOWFLAKE_ROLE"],
        "--warehouse", os.environ["SNOWFLAKE_WAREHOUSE"],
        "--database", os.environ["SNOWFLAKE_DATABASE"]
    ]
    run_command(deploy_cmd, "Deploying Snowpark app")


if __name__ == "__main__":
    main()
