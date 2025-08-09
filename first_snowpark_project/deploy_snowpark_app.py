import sys
import os
import yaml
import subprocess

required_env_vars = [
    "SNOWFLAKE_ACCOUNT_DEV",
    "SNOWFLAKE_USER_DEV",
    "SNOWFLAKE_ROLE_DEV",
    "SNOWFLAKE_WAREHOUSE_DEV",
    "SNOWFLAKE_DATABASE_DEV",
    "SNOWFLAKE_PASSWORD_DEV"  # Even if not passed directly, SnowCLI expects it
]

missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    print(
        f"❌ Missing required environment variables: {', '.join(missing_vars)}")
    sys.exit(1)

directory_path = sys.argv[1]
os.chdir(directory_path)

print("📦 Building Snowpark app...")
subprocess.run(["snow", "snowpark", "build"], check=True)

print("🚀 Deploying Snowpark app...")
subprocess.run([
    "snow", "snowpark", "deploy",
    "--replace",
    "--temporary-connection",
    "--account", os.getenv("SNOWFLAKE_ACCOUNT"),
    "--user", os.getenv("SNOWFLAKE_USER"),
    "--role", os.getenv("SNOWFLAKE_ROLE"),
    "--warehouse", os.getenv("SNOWFLAKE_WAREHOUSE"),
    "--database", os.getenv("SNOWFLAKE_DATABASE")
], check=True)

print("🔍 Environment configuration:")
for var in required_env_vars:
    if var != "SNOWFLAKE_PASSWORD":
        print(f"{var}: {os.getenv(var)}")

print("✅ Snowpark app deployed successfully!")


# Make sure all 6 SNOWFLAKE_ environment variables are set
# SnowCLI accesses the passowrd directly from the SNOWFLAKE_PASSWORD environmnet variable
# os.system(f"snow snowpark build")
# os.system(f"snow snowpark deploy --replace --temporary-connection --account $SNOWFLAKE_ACCOUNT --user $SNOWFLAKE_USER --role $SNOWFLAKE_ROLE --warehouse $SNOWFLAKE_WAREHOUSE --database $SNOWFLAKE_DATABASE")
