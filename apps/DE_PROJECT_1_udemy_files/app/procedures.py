from __future__ import annotations

import sys

from common import print_hello
from common import copy_to_table
from config import configs
from schema import schemas
from snowflake.snowpark import Session


def hello_procedure(session: Session, name: str) -> str:
    return print_hello(name)


def test_procedure(session: Session) -> str:
    return "Test procedure"


def copy_to_table_proc(session: Session) -> str:
    copied_into_result, qid = copy_to_table(
        session, configs.employee_config, schemas.emp_stg_schema)


def execute_sql_statements(session: Session) -> None:
    session.sql(
        "EXECUTE IMMEDIATE FROM @dev_deployment/de_project_1/load_to_emp_tgt.sql").collect()


# For local debugging
# Beware you may need to type-convert arguments if you add input parameters
if __name__ == "__main__":
    # Create a local Snowpark session
    with Session.builder.config("local_testing", True).getOrCreate() as session:
        print(hello_procedure(session, *sys.argv[1:]))  # type: ignore
