
#  Note: When running locally, ensure the parent directory of 'first_snowpark_project' is in sys.path
# from .procedures import hello_procedure  # Python-wrapped stored procedure
from dotenv import load_dotenv
from first_snowpark_project.app.python import procedures
from datetime import timedelta
from snowflake.core.task import Task, StoredProcedureCall
from snowflake.snowpark.types import StringType
from snowflake.core.task.dagv1 import DAG, DAGTask, DAGOperation, CreateMode
from first_snowpark_project.app.python.session import get_session
from snowflake.core import Root
import snowflake.connector
import sys
import os
project_root = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "../../../"))
sys.path.insert(0, project_root)
# -----------------------------------------
load_dotenv()

is_local = os.getenv("LOCAL_MODE", "false").lower(
) == "true"  # Set to "true" for local testing
session = get_session()

# if is_local:
#     conn = session._conn  # Access the underlying connection from the Snowpark session
# else:
#     conn = snowflake.connector.connect()

# root = Root(conn)
is_local = os.getenv("LOCAL_MODE", "false").strip().lower() == "true"
session = get_session()

root = Root(session)

schema = root.databases["demo_db"].schemas["public"]


# Define tasks using StoredProcedureCall

# Define DAG
with DAG("my_snowpark_dag", schedule=timedelta(days=1)) as dag:
    task_hello = DAGTask(
        name="task_hello",
        dag=dag,
        definition=StoredProcedureCall(
            handler="app.python.procedures.hello_procedure",
            args=["Snowpark"],
            return_type=StringType(),
            stage_location="@dev_deployment"
        )
    )

    task_test = DAGTask(
        name="task_test",
        dag=dag,
        definition=StoredProcedureCall(
            handler="app.python.procedures.test_procedure_two",
            args=[],
            return_type=StringType(),
            stage_location="@dev_deployment"
        )
    )

    dag.add_task(task_hello)
    dag.add_task(task_test)
    _ = task_hello >> task_test

# Deploy DAG
dag_op = DAGOperation(schema)
dag_op.deploy(dag, CreateMode.or_replace)

# For local testing without Snowflake


def test_local_procedures(session):
    # Create a mock session for local testing
    # session = Session.builder.configs({"local_testing": True}).create()

    # Call your procedures directly
    result_hello = procedures.hello_procedure(session, "Cory")
    result_test = procedures.test_procedure_two(session)

    print("hello_procedure result:", result_hello)
    print("test_procedure_two result:", result_test)


if __name__ == "__main__":
    session = get_session()  # Or use mock if testing offline
    test_local_procedures(session)
