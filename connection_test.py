from snowflake.snowpark import Session
import os

os.environ["SF_OCSP_RESPONSE_CACHE_SERVER_ENABLED"] = "false"

session = Session.builder.configs(
    {
        "account": os.getenv("SNOWFLAKE_ACCOUNT", "JREFROJ-VDB55393"),
        "user": os.getenv("SNOWFLAKE_USER", "admin"),
        # or whichever secret you want
        "password": os.getenv("SNOWFLAKE_PASSWORD"),
        "role": os.getenv("SNOWFLAKE_ROLE", "ACCOUNTADMIN"),
        "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
        "database": os.getenv("SNOWFLAKE_DATABASE", "DEMO_DB"),
        "schema": os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC"),
    }
).create()

result = session.sql("SELECT CURRENT_REGION(), CURRENT_ACCOUNT();").collect()
for row in result:
    print(row)
