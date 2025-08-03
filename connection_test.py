import os

os.environ["SF_OCSP_RESPONSE_CACHE_SERVER_ENABLED"] = "false"

from snowflake import connector

connector.connection._OCSP_MODE = False  # <- undocumented but effective

from snowflake.snowpark import Session

session = Session.builder.configs(
    {
        "account": "DNLAXPS-NQB74584",
        "user": "admin",
        "password": "Kr@k3n@dm1nDEA-Co2",
        "role": "ACCOUNTADMIN",
        "warehouse": "COMPUTE_WH",
        "database": "DEMO_DB",
        "schema": "PUBLIC",
    }
).create()

print(session.sql("select current_version()").collect())
