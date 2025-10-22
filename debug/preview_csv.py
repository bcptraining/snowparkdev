# python REPL or script
from snowflake.snowpark import Session
import os
import json
import sys

# build connection by preferring DEV env vars but falling back to regular names
conn = {
    "account": os.environ.get("SNOWFLAKE_ACCOUNT_DEV") or os.environ.get("SNOWFLAKE_ACCOUNT"),
    "user": os.environ.get("SNOWFLAKE_USER_DEV") or os.environ.get("SNOWFLAKE_USER"),
    "password": os.environ.get("SNOWFLAKE_PASSWORD_DEV") or os.environ.get("SNOWFLAKE_PASSWORD"),
    "role": os.environ.get("SNOWFLAKE_ROLE_DEV") or os.environ.get("SNOWFLAKE_ROLE"),
    "warehouse": os.environ.get("SNOWFLAKE_WAREHOUSE_DEV") or os.environ.get("SNOWFLAKE_WAREHOUSE"),
    "database": os.environ.get("SNOWFLAKE_DATABASE_DEV") or os.environ.get("SNOWFLAKE_DATABASE"),
    "schema": os.environ.get("SNOWFLAKE_SCHEMA", "PUBLIC")
}
missing = [k for k in ("account", "user", "password") if not conn.get(k)]
if missing:
    print("Missing Snowflake credentials:", missing, file=sys.stderr)
    sys.exit(1)

session = Session.builder.configs(conn).create()
try:
    session.sql("""
    CREATE OR REPLACE FILE FORMAT debug_csv_fmt
      TYPE='CSV'
      FIELD_DELIMITER=','
      FIELD_OPTIONALLY_ENCLOSED_BY='"'
      SKIP_HEADER=1
      NULL_IF=('','NULL')
      ENCODING='UTF8';
    """).collect()

    copy_sql = """
    COPY INTO DEMO_DB.PUBLIC.EMPLOYEE2
      FROM @my_s3_stage
      FILES = ('employees02.csv')
      FILE_FORMAT = (FORMAT_NAME = 'debug_csv_fmt')
      VALIDATION_MODE = 'RETURN_ERRORS'
      ON_ERROR = 'CONTINUE'
      FORCE = TRUE;
    """
    print("Running COPY ...")
    session.sql(copy_sql).collect()

    print("\nFetching RESULT_SCAN (immediate; may be empty):")
    rs = session.sql(
        "SELECT * FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()));").collect()
    if not rs:
        print("RESULT_SCAN returned no rows.")
    else:
        for r in rs:
            print(json.dumps(dict(r.asDict()), default=str))

    # Create debug table with all VARCHARs and load to inspect parsed values
    session.sql("""
    CREATE OR REPLACE TABLE DEMO_DB.PUBLIC.EMPLOYEE2_DEBUG (
      FIRST_NAME VARCHAR, LAST_NAME VARCHAR, EMAIL VARCHAR,
      ADDRESS VARCHAR, CITY VARCHAR, DOJ VARCHAR
    );
    """).collect()
    session.sql("""
        COPY INTO DEMO_DB.PUBLIC.EMPLOYEE2_DEBUG
        FROM @my_s3_stage
        FILES = ('employees02.csv')
        FILE_FORMAT = (FORMAT_NAME = 'debug_csv_fmt')
        VALIDATION_MODE = 'RETURN_ERRORS'
        ON_ERROR = 'CONTINUE'
        FORCE = TRUE;
        """).collect()

    cnt = session.sql(
        "SELECT COUNT(*) AS c FROM DEMO_DB.PUBLIC.EMPLOYEE2_DEBUG").collect()[0]["C"]
    print("\nEMPLOYEE2_DEBUG row count:", cnt)
    if cnt:
        rows = session.sql(
            "SELECT * FROM DEMO_DB.PUBLIC.EMPLOYEE2_DEBUG LIMIT 20").collect()
        for r in rows:
            print(r.asDict())
finally:
    session.close()
# -----------------
# conn = {
#     "account": os.environ.get("SNOWFLAKE_ACCOUNT_DEV"),
#     "user": os.environ.get("SNOWFLAKE_USER_DEV"),
#     "password": os.environ.get("SNOWFLAKE_PASSWORD_DEV"),
#     "role": os.environ.get("SNOWFLAKE_ROLE_DEV"),
#     "warehouse": os.environ.get("SNOWFLAKE_WAREHOUSE_DEV"),
#     "database": os.environ.get("SNOWFLAKE_DATABASE_DEV"),
#     "schema": "PUBLIC",
# }
# session = Session.builder.configs(conn).create()
# try:
#     df = session.read.option("SKIP_HEADER", 1).csv(
#         "@my_s3_stage/employees02.csv")
#     df.show(20)
#     print("count:", df.count())
# finally:
#     session.close()
