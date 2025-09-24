# Common functions and utilities for the DE_PROJECT_1 application
from snowflake.snowpark.types import StructType
from snowflake.snowpark.types import StructType, StructField, StringType, IntegerType, FloatType, BooleanType, DateType
import os
import sys
# ✅ Type mapping for schema conversion (helper for json_to_struct_type)

TYPE_MAP = {
    "string": StringType(),
    "StringType": StringType(),
    "int": IntegerType(),
    "integer": IntegerType(),
    "IntegerType": IntegerType(),
    "float": FloatType(),
    "FloatType": FloatType(),
    "boolean": BooleanType(),
    "BooleanType": BooleanType(),
    "date": DateType(),
    "DateType": DateType()
}

# ✅ Simple hello world function


def print_hello(name: str):
    return f"Hello {name}!"

# ✅ Function to copy data from source to target table based on config and schema


def copy_to_table(session, config_file: dict, schema: StructType) -> tuple:
    database_name = config_file.get("Database_name")
    Schema_name = config_file.get("Schema_name")
    Target_table = config_file.get("Target_table")
    target_columns = config_file.get("target_columns")
    on_error = config_file.get("on_error")
    Source_location = config_file.get("Source_location")

    # 🧪 Validate file type and apply schema
    if config_file.get("Source_file_type") == 'csv':
        df = session.read.schema(schema).csv(f"'{Source_location}'")
    else:
        raise ValueError(
            f"Unsupported file type: {config_file.get('Source_file_type')}")

    # 🧠 Track query history to extract COPY query ID
    with session.query_history() as query_history:
        copied_into_result = df.copy_into_table(
            f"{database_name}.{Schema_name}.{Target_table}",
            target_columns=target_columns,
            force=True,
            on_error=on_error
        )

    qid = None
    for id in query_history.queries:
        if "COPY" in id.sql_text:
            qid = id.query_id
            break

    return copied_into_result, qid


# ✅ Function to convert JSON schema to StructType

def json_to_struct_type(schema_json: list) -> StructType:
    fields = []
    for field in schema_json:
        field_type = TYPE_MAP.get(field["type"])
        if not field_type:
            raise ValueError(f"Unsupported type: {field['type']}")
        fields.append(StructField(field["name"], field_type))
    return StructType(fields)
