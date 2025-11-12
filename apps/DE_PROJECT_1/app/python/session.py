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

    session = Session.builder.configs(connection_parameters).create()

    # Explicitly set context for Snowpark operations
    try:
        if connection_parameters.get("warehouse"):
            session.sql(
                f"USE WAREHOUSE {connection_parameters['warehouse']}").collect()
            print(f"🏭 Set warehouse: {connection_parameters['warehouse']}")

        if connection_parameters.get("database"):
            session.sql(
                f"USE DATABASE {connection_parameters['database']}").collect()
            print(f"🗄️ Set database: {connection_parameters['database']}")

        if connection_parameters.get("schema"):
            session.sql(
                f"USE SCHEMA {connection_parameters['schema']}").collect()
            print(f"📂 Set schema: {connection_parameters['schema']}")

    except Exception as e:
        # Provide clear error message with available objects
        print(f"❌ Failed to set Snowflake context: {e}")

        try:
            warehouses = session.sql("SHOW WAREHOUSES").collect()
            available_wh = [w['name'] for w in warehouses]
            print(f"💡 Available warehouses: {available_wh}")

            if connection_parameters.get("warehouse") not in available_wh:
                print(
                    f"💡 Configured warehouse '{connection_parameters['warehouse']}' does not exist or lacks permissions")
                print(
                    f"💡 Update SNOWFLAKE_WAREHOUSE_DEV to one of: {available_wh}")

        except Exception as show_error:
            print(f"Could not list available objects: {show_error}")

        raise Exception(
            f"Snowflake context setup failed. Check warehouse configuration.")

    return session
