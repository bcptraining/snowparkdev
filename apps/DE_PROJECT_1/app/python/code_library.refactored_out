# This code was developeed earlier (section 10) and needfs a proper home in the app

from snowflake.snowpark import Session
from snowflake.snowpark.functions import col, to_timestamp


def snowconnection(connection_config):
    session = Session.builder.configs(connection_config).create()
    session_details = session.create_dataframe([[session._session_id, session.sql("select current_user();").collect()[0][0], str(
        session.get_current_warehouse()).replace('"', ''), str(session.get_current_role()).replace('"', '')]], schema=["session_id", "user_name", "warehouse", "role"])
    session_details.write.mode("append").save_as_table("session_audit")
    return session


def copy_to_table(session, config_file, schema='NA'):
    database_name = config_file.get("Database_name")
    Schema_name = config_file.get("Schema_name")
    Target_table = config_file.get("Target_table")
    target_columns = config_file.get("target_columns")
    on_error = config_file.get("on_error")
    Source_location = config_file.get("Source_location")

    if config_file.get("Source_file_type") == 'csv':
        schema = schema
        df = session.read.schema(schema).csv("'"+Source_location+"'")

    with session.query_history() as query_history:
        copied_into_result = df.copy_into_table(
            database_name+"."+Schema_name+"."+Target_table, target_columns=target_columns, force=True, on_error=on_error)
    query = query_history.queries
    # Mention command to collect query id of copy command executed.
    for id in query:
        if "COPY" in id.sql_text:
            qid = id.query_id
    return copied_into_result, qid


def collect_rejects(session, qid, config_file):
    database_name = config_file.get("Database_name")
    Schema_name = config_file.get("Schema_name")
    Target_table = config_file.get("Target_table")
    Reject_table = config_file.get("Reject_table")
    rejects = session.sql("select *  from table(validate("+database_name +
                          "."+Schema_name+"."+Target_table+" , job_id =>" + "'" + qid + "'))")
    rejects.write.mode("append").save_as_table(Reject_table)
    return rejects


def map_columns(df, map_columns):
    # Remove double qoutes from the column names and drop unwanted columns
    cols = df.columns
    map_keys = [key.upper() for key in map_columns.keys()]
    for c in cols:
        df = df.with_column_renamed(c, c.replace('"', ''))
    cols = df.columns
    for c in cols:
        if c.upper() not in map_keys:
            print("Dropped column,"+" "+c.upper())
            df = df.drop(c.upper())

    # Rename the dataframe column names
    for k, v in map_columns.items():
        df = df.with_column_renamed(k.upper(), v.upper())
    return df


def copy_to_table_semi_struct_data(session, config_file, schema='NA'):
    database_name = config_file.get("Database_name")
    Schema_name = config_file.get("Schema_name")
    Target_table = config_file.get("Target_table")
    target_columns = config_file.get("target_columns")
    on_error = config_file.get("on_error")
    Source_location = config_file.get("Source_location")
    transformations = config_file.get("transformations")
    maped_columns = config_file.get("map_columns")

    if config_file.get("Source_file_type") == 'csv':
        return "Expecting semi structured data but got csv"
    elif config_file.get("Source_file_type") == 'avro':
        df = session.read.avro(Source_location)

    # Map columns in df to target table
    df = map_columns(df, maped_columns)

    # Create temporary stage
    _ = session.sql(
        "create or replace temp stage demo_db.public.mystage").collect()
    remote_file_path = '@demo_db.public.mystage/'+Target_table+'/'
    # Write df to temporary internal stage location
    df.write.copy_into_location(remote_file_path, file_format_type="csv", format_type_options={
                                "FIELD_OPTIONALLY_ENCLOSED_BY": '"'}, header=False, overwrite=True)

    # Read the file from temp stage location
    df = session.read.schema(schema).csv("'"+remote_file_path+"'")
    with session.query_history() as query_history:
        copied_into_result = df.copy_into_table(database_name+"."+Schema_name+"."+Target_table, target_columns=target_columns,
                                                force=True, on_error=on_error, format_type_options={"FIELD_OPTIONALLY_ENCLOSED_BY": '"'})
    query = query_history.queries
    # Mention command to collect query id of copy command executed.
    for id in query:
        if "COPY" in id.sql_text:
            qid = id.query_id
    return copied_into_result, qid
