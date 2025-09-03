import sys
import os
import yaml

# os.system(f"conda init")
# os.system(f"conda activate snowpark")
directory_path = sys.argv[1]

os.chdir(f"{directory_path}")
# Make sure all 6 SNOWFLAKE_ environment variables are set
# SnowCLI accesses the passowrd directly from the SNOWFLAKE_PASSWORD environmnet variable
os.system(f"snow connection add --account $SNOWFLAKE_ACCOUNT --user $SNOWFLAKE_USER --warehouse $SNOWFLAKE_WAREHOUSE --database $SNOWFLAKE_DATABASE --schema $SNOWFLAKE_SCHEMA --role $SNOWFLAKE_ROLE --connection-name default")
