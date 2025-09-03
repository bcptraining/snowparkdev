# app/python/session.py
from snowflake.snowpark import Session
import os


def get_session() -> Session:
    connection_parameters = {
        "account": os.getenv("SNOWFLAKE_ACCOUNT"),
        "user": os.getenv("SNOWFLAKE_USER"),
        "password": os.getenv("SNOWFLAKE_PASSWORD"),
        "role": os.getenv("SNOWFLAKE_ROLE"),
        "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
        "database": os.getenv("SNOWFLAKE_DATABASE"),
        "schema": os.getenv("SNOWFLAKE_SCHEMA_DEV", "PUBLIC")
    }
    # print("🔐 SNOWFLAKE_ACCOUNT_DEV:", os.getenv("SNOWFLAKE_ACCOUNT_DEV"),
    #       "🔐 SNOWFLAKE_ACCOUNT:", os.getenv("SNOWFLAKE_ACCOUNT"))
    # print("👤 USER:", repr(os.getenv("SNOWFLAKE_USER_DEV")))
    # print("🔑 PASSWORD:", repr(os.getenv("SNOWFLAKE_PASSWORD_DEV")))

    return Session.builder.configs(connection_parameters).create()
