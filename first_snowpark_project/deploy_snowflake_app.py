import sys
import os
import subprocess


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

    # Build the Snowpark project
    run_command(["snow", "snowpark", "build"], "Building Snowpark project")

    # Deploy with full connection parameters
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
