from snowflake.snowpark import Session
import os
import sys
import traceback

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
    print("CURRENT CONTEXT:")
    for r in session.sql("SELECT CURRENT_ROLE() AS role, CURRENT_USER() AS user, CURRENT_DATABASE() AS db, CURRENT_SCHEMA() AS schema").collect():
        print(r.asDict())

    print("\nLIST @my_s3_stage and @my_s3_stage/emp:")
    for r in session.sql("LIST @my_s3_stage").collect():
        print(r.asDict())
    for r in session.sql("LIST @my_s3_stage/emp").collect():
        print(r.asDict())

    print("\nDESCRIBE STAGE my_s3_stage:")
    for r in session.sql("DESCRIBE STAGE my_s3_stage").collect():
        print(r.asDict())

    print("\nRecent COPY_HISTORY for employees files (may lag):")
    q = """SELECT *
           FROM SNOWFLAKE.ACCOUNT_USAGE.COPY_HISTORY
           WHERE FILE_NAME ILIKE '%employees%' AND LAST_LOAD_TIME >= DATEADD(day,-7,CURRENT_TIMESTAMP())
           ORDER BY LAST_LOAD_TIME DESC
           LIMIT 50"""
    try:
        for r in session.sql(q).collect():
            print(r.asDict())
    except Exception as e:
        # likely lack of privileges to read SNOWFLAKE.ACCOUNT_USAGE
        print("Could not query SNOWFLAKE.ACCOUNT_USAGE.COPY_HISTORY:",
              str(e), file=sys.stderr)
        try:
            current_role = session.sql(
                "SELECT CURRENT_ROLE() AS role").collect()[0].asDict()
        except Exception:
            current_role = {"role": "unknown"}
        print("Current role:", current_role, file=sys.stderr)
        print("If you need COPY history access, ask an ACCOUNTADMIN to grant imported privileges and schema access (noted as guidance only). Continuing without COPY_HISTORY.", file=sys.stderr)

    # Try COPY with ABORT to surface an error
    print("\nAttempting COPY with ON_ERROR='ABORT_STATEMENT' to surface any error...")
    copy_sql = '''COPY INTO DEMO_DB.PUBLIC.EMPLOYEE2
        FROM @my_s3_stage
        FILES = ('employees02.csv')
        FILE_FORMAT = (TYPE='CSV' FIELD_DELIMITER=',' FIELD_OPTIONALLY_ENCLOSED_BY='"' SKIP_HEADER=1 NULL_IF=('','NULL') ENCODING='UTF8')
        ON_ERROR='ABORT_STATEMENT'
        FORCE=TRUE;'''
    try:
        session.sql(copy_sql).collect()
        print("COPY completed without raising an error.")
    except Exception:
        print("COPY raised exception:", file=sys.stderr)
        traceback.print_exc()

    # Force debug load (VARCHAR) with ABORT to show errors — handle insufficient privileges by falling back
    print("\nCreating debug table and running debug COPY with ABORT...")
    try:
        session.sql(
            "CREATE OR REPLACE TABLE DEMO_DB.PUBLIC.EMPLOYEE2_DEBUG (FIRST_NAME VARCHAR, LAST_NAME VARCHAR, EMAIL VARCHAR, ADDRESS VARCHAR, CITY VARCHAR, DOJ VARCHAR)"
        ).collect()
        try:
            session.sql('''COPY INTO DEMO_DB.PUBLIC.EMPLOYEE2_DEBUG
              FROM @my_s3_stage
              FILES = ('employees02.csv')
              FILE_FORMAT = (FORMAT_NAME='debug_csv_fmt')
              ON_ERROR='ABORT_STATEMENT'
              FORCE=TRUE;''').collect()
            print("Debug COPY completed without raising an error.")
        except Exception:
            print("Debug COPY raised exception:", file=sys.stderr)
            traceback.print_exc()

        print("\nEMPLOYEE2_DEBUG count and sample:")
        c = session.sql(
            "SELECT COUNT(*) AS c FROM DEMO_DB.PUBLIC.EMPLOYEE2_DEBUG").collect()[0]["C"]
        print("count:", c)
        if c:
            for r in session.sql("SELECT * FROM DEMO_DB.PUBLIC.EMPLOYEE2_DEBUG LIMIT 20").collect():
                print(r.asDict())
    except Exception as e:
        # Insufficient privileges: fallback to reading the staged CSV into a DataFrame
        print("Could not create/operate on EMPLOYEE2_DEBUG (insufficient privileges). Falling back to reading staged file.", file=sys.stderr)
        print("Error:", str(e), file=sys.stderr)
        try:
            df = session.read.option("SKIP_HEADER", 1).option(
                "FIELD_OPTIONALLY_ENCLOSED_BY", '"').csv("@my_s3_stage/employees02.csv")
            print("Preview rows (first 20):")
            df.show(20)
            print("count:", df.count())
            for r in df.limit(20).collect():
                print(r.asDict())
        except Exception:
            print("Failed to read staged CSV via session.read.csv():", file=sys.stderr)
            traceback.print_exc()

finally:
    session.close()
