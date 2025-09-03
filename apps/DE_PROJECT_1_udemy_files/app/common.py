def print_hello(name: str):
    return f"Hello {name}!"


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
