from snowflake.snowpark import Session
from snowflake import connector
import os

os.environ["SF_OCSP_RESPONSE_CACHE_SERVER_ENABLED"] = "false"


connector.connection._OCSP_MODE = False  # <- undocumented but effective


session = Session.builder.configs(
    {
        "account": "DNLAXPS-DEV_ACCT",
        "user": "admin",
        "password": "Kr@k3n@dm1nDEA-Co2",
        "role": "ACCOUNTADMIN",
        "warehouse": "COMPUTE_WH",
        "database": "DEMO_DB",
        "schema": "PUBLIC",
    }
).create()

# session = Session.builder.configs(
#     {
#         "account": "DNLAXPS-NQB74584",
#         "user": "admin",
#         "password": "Kr@k3n@dm1nDEA-Co2",
#         "role": "ACCOUNTADMIN",
#         "warehouse": "COMPUTE_WH",
#         "database": "DEMO_DB",
#         "schema": "PUBLIC",
#     }
# ).create()

result = session.sql("SELECT CURRENT_REGION(), CURRENT_ACCOUNT();").collect()
for row in result:
    print(row)
