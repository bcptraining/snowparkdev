# from __future__ import annotations
# from python.common.helpers import print_hello
from ..common.helpers import print_hello
from ..common.helpers import copy_to_table, prepare_copy_inputs
from snowflake.snowpark import Session
import sys
import os
import json
from pathlib import Path
# from ..config_refactored_out_not_used import configs
# from ..schema import schemas
from snowflake.snowpark.types import StructType, StructField, StringType, IntegerType, FloatType, DateType, BooleanType, TimestampType
# from snowflake.snowpark.stored_procedure import procedure
# from snowflake.snowpark import stored_procedure
# from snowflake.snowpark.stored_procedure import procedure


#  ---- Functions ----


# def load_schema_from_json(json_path: str, schema_name: str) -> StructType:
#     with open(json_path, "r") as f:
#         all_schemas = json.load(f)
#     fields = all_schemas.get(schema_name)
#     if not fields:
#         raise ValueError(f"Schema '{schema_name}' not found in {json_path}")
#     return StructType([
#         StructField(field["name"], TYPE_MAP[field["type"]])
#         for field in fields
#     ])


# def load_named_config(config_name: str, config_dir: str | Path = "app/config") -> dict:
#     config_dir = Path(config_dir)
#     config_file = config_dir / f"{config_name}.json"

#     if not config_file.exists():
#         raise FileNotFoundError(f"Config file not found: {config_file}")

#     with open(config_file, "r") as f:
#         config = json.load(f)

#     if not isinstance(config, dict):
#         raise ValueError(
#             f"Expected a JSON object at root of {config_file}, got {type(config)}")

#     return config


# def prepare_copy_inputs(schema_file: str, schema_key: str, config_name: str):
#     schema = load_schema_from_json(schema_file, schema_key)
#     config = load_named_config(config_name)
#     return config, schema


# Step 0. Define paths and directories containing schemas and configs
# emp_schema_path = "app/schemas/schemas.json"  # All schemas are in this file
# config_dir = "app/config/"  # Directory containing config JSON files

# Step 1. Load schema and config for employee table
# emp_schema = load_schema_from_json(
#     emp_schema_path, "emp_stg_schema_udemy")

# copy_config = load_named_config("copy_to_snowstg_udemy")


# Dynamically add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), "../../../..")))
# from app.python.common import print_hello


# def hello_procedure(session: Session, name: str) -> str:
#     return f"Hello, {name}"
# @procedure(name="HELLO_PROCEDURE2", is_permanent=True, stage_location="@dev_deployment", return_type=StringType())

def hello_procedure2(session: Session, name="World2") -> str:
    return print_hello(name)


def hello_procedure(session: Session, name: str) -> str:
    return f"Hello, {name}! Hope you're having a great day!"


def test_procedure(session: Session) -> str:
    return "Test procedure"


def test_procedure_two(session: Session) -> str:
    return "Test procedure"


# @procedure(name="COPY_EMPLOYEE_PROC", is_permanent=True, stage_location="@dev_deployment", return_type=StringType)
# def copy_employee_stg_udemy_proc(session: Session) -> str:
#     config, schema = prepare_copy_inputs(
#         "app/schemas/schemas.json", "emp_stg_schema_udemy", "copy_to_snowstg_udemy"
#     )
#     copied_into_result, qid = copy_to_table(session, config, schema)
#     return f"✅ Copy completed. Query ID: {qid}"


# , config_file: str, schema: str = 'NA'):
# def copy_to_table_proc(session: Session) -> str:
#     copied_into_result, qid = copy_to_table(
#         # session, configs.employee_config, "EMP_STG_SCHEMA_UDEMY")
#         session, copy_config, emp_schema)
#     return "something"

# def copy_to_table_proc(session: Session, config: dict, schema: StructType) -> str:

#     copied_into_result, qid = copy_to_table(session, config, schema)
#     return f"✅ Copy completed. Query ID: {qid}"

# copy_config, emp_schema = prepare_copy_inputs(
#     "app/schemas/schemas.json", "emp_stg_schema_udemy", "copy_to_snowstg_udemy"
# )
