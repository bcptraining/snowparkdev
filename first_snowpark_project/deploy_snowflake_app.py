import sys
import os
import yaml

# os.system(f"conda init")
# os.system(f"conda activate snowpark")
directory_path = sys.argv[1]
os.chdir(f"{directory_path}")

# Check for missing variables
required_vars = [
    "SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_PASSWORD",
    "SNOWFLAKE_ROLE", "SNOWFLAKE_WAREHOUSE", "SNOWFLAKE_DATABASE"
]

for var in required_vars:
    if var not in os.environ or not os.environ[var]:
        raise EnvironmentError(f"Missing required environment variable: {var}")

# Optional: print to confirm environment variables
print("Using Snowflake connection --------:")
print("SNOWFLAKE_ACCOUNT:", os.environ["SNOWFLAKE_ACCOUNT"])
print("SNOWFLAKE_USER:", os.environ["SNOWFLAKE_USER"])
print("SNOWFLAKE_ROLE:", os.environ["SNOWFLAKE_ROLE"])
print("SNOWFLAKE_WAREHOUSE:", os.environ["SNOWFLAKE_WAREHOUSE"])
print("SNOWFLAKE_DATABASE:", os.environ["SNOWFLAKE_DATABASE"])
print("Attempting to use warehouse:", os.environ["SNOWFLAKE_WAREHOUSE"])


# Debug print to confirm environment variables are visible
print("Using Snowflake connection:")
for var in required_vars:
    print(f"{var}: {'***' if 'PASSWORD' in var else os.environ[var]}")

# Activate the warehouse explicitly
warehouse = os.environ["SNOWFLAKE_WAREHOUSE"]
os.system(f'snow sql --connection default -q "USE WAREHOUSE {warehouse}"')

# Make sure all 6 SNOWFLAKE_ environment variables are set
# SnowCLI accesses the passowrd directly from the SNOWFLAKE_PASSWORD environmnet variable
os.system(f"snow snowpark build")
os.system("snow snowpark deploy")
# os.system(
#     f"snow snowpark deploy --replace --temporary-connection "
#     f"--account {os.environ['SNOWFLAKE_ACCOUNT']} "
#     f"--user {os.environ['SNOWFLAKE_USER']} "
#     f"--password {os.environ['SNOWFLAKE_PASSWORD']} "
#     f"--role {os.environ['SNOWFLAKE_ROLE']} "
#     f"--warehouse {os.environ['SNOWFLAKE_WAREHOUSE']} "
#     f"--database {os.environ['SNOWFLAKE_DATABASE']}"
# )
