import sys
import os

directory_path = sys.argv[1]
os.chdir(directory_path)

required_vars = [
    "SNOWFLAKE_ACCOUNT",
    "SNOWFLAKE_USER",
    "SNOWFLAKE_PASSWORD",
    "SNOWFLAKE_ROLE",
    "SNOWFLAKE_WAREHOUSE",
    "SNOWFLAKE_DATABASE"
]

for var in required_vars:
    if var not in os.environ or not os.environ[var]:
        raise EnvironmentError(f"Missing required environment variable: {var}")

print("Using Snowflake connection:")
for var in required_vars:
    print(f"{var}: {'***' if 'PASSWORD' in var else os.environ[var]}")

# Build the Snowpark app with full connection info
build_command = (
    f"snow snowpark build --temporary-connection "
    f"--account {os.environ['SNOWFLAKE_ACCOUNT']} "
    f"--user {os.environ['SNOWFLAKE_USER']} "
    f"--password {os.environ['SNOWFLAKE_PASSWORD']} "
    f"--role {os.environ['SNOWFLAKE_ROLE']} "
    f"--warehouse {os.environ['SNOWFLAKE_WAREHOUSE']} "
    f"--database {os.environ['SNOWFLAKE_DATABASE']}"
)
os.system(build_command)

# Deploy with all required parameters explicitly passed
deploy_command = (
    f"snow snowpark deploy --replace --temporary-connection "
    f"--account {os.environ['SNOWFLAKE_ACCOUNT']} "
    f"--user {os.environ['SNOWFLAKE_USER']} "
    f"--password {os.environ['SNOWFLAKE_PASSWORD']} "
    f"--role {os.environ['SNOWFLAKE_ROLE']} "
    f"--warehouse {os.environ['SNOWFLAKE_WAREHOUSE']} "
    f"--database {os.environ['SNOWFLAKE_DATABASE']}"
)
os.system(deploy_command)
