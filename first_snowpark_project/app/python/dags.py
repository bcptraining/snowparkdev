
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
            procedures.hello_procedure,
            args=["Snowpark"],
            return_type=StringType(),
            stage_location="@dev_deployment"
        )
    )

    task_test = DAGTask(
        name="task_test",
        dag=dag,
        definition=StoredProcedureCall(
            procedures.test_procedure_two,
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
# Create a task that runs every 4 hours and calls hello_procedure with a string argument
# my_task_GreetTheDay = Task(
#     name="my_task_GreetTheDay",
#     definition=StoredProcedureCall(
#         hello_procedure,
#         # You can replace this with dynamic logic later
#         args=["__world_with_args__"],
#         stage_location="@dev_deployment",
#         return_type=StringType()
#     ),
#     schedule=timedelta(hours=4)
# )


# def register_tasks():
#     return [my_task_GreetTheDay]


# from first_snowpark_project.app.python.session import get_session
# from snowflake.core import Root
# import snowflake.connector
# # from app.python.session import get_session
# from dotenv import load_dotenv
# from datetime import timedelta
# from snowflake.snowpark.types import StringType
# # from app.python import procedures
# from first_snowpark_project.app.python import procedures

# from snowflake.core.task import Task, StoredProcedureCall
# from snowflake.core.task.dagv1 import DAG, DAGTask, DAGOperation, CreateMode
# import sys
# import os
# # from first_snowpark_project.app.python.common import print_hello

# # Add the parent of 'first_snowpark_project' to sys.path
# project_root = os.path.abspath(os.path.join(
#     os.path.dirname(__file__), "../../.."))
# sys.path.insert(0, project_root)

# # Now this import should work
# print("Current sys.path:")
# for p in sys.path:
#     print("  ", p)

# # Add the project root to sys.path
# sys.path.append(os.path.abspath(os.path.join(
#     os.path.dirname(__file__), "../../../")))


# Load environment variables
# load_dotenv()

# Connect to Snowflake
# conn = snowflake.connector.connect(
#     account=os.getenv("SNOWFLAKE_ACCOUNT"),
#     user=os.getenv("SNOWFLAKE_USER"),
#     password=os.getenv("SNOWFLAKE_PASSWORD"),
#     role=os.getenv("SNOWFLAKE_ROLE"),
#     warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
#     database=os.getenv("SNOWFLAKE_DATABASE"),
#     schema="PUBLIC"
# )

# conn = snowflake.connector.connect(
# account=os.getenv("SNOWFLAKE_ACCOUNT"),
# user=os.getenv("SNOWFLAKE_USER"),
# password=os.getenv("SNOWFLAKE_PASSWORD"),
# role=os.getenv("SNOWFLAKE_ROLE"),
# warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
# database=os.getenv("SNOWFLAKE_DATABASE"),
# schema="PUBLIC"
# )


# root = Root(conn)
# print(root)

# # Create a task that wraps the hello_procedure
# my_task = Task(
#     name="my_task",
#     # 👈 SQL string
#     definition="CALL DEMO_DB.PUBLIC.HELLO_PROCEDURE('Canucks')",
#     schedule=timedelta(hours=4)
#     # warehouse="COMPUTE_WH"
# )

# # Create a task #2 with args that wraps the hello_procedure
# # my_task_with_args = Task(
# #     name="my_task_with_args",
# #     definition=StoredProcedureCall(procedures.hello_procedure2, args=["__world_with_args__"],  # ✅ Pass args here
# #                                    stage_location="@dev_deployment",
# #                                    return_type=StringType()
# #                                    ),
# #     schedule=timedelta(hours=4)
# # )

# my_task_with_args = Task(
#     name="y_task_with_args",
#     # 👈 SQL string
#     definition="CALL DEMO_DB.PUBLIC.HELLO_PROCEDURE2('Canucks_args')",
#     schedule=timedelta(hours=4)
#     # warehouse="COMPUTE_WH"
# )
# print("Task name:", my_task_with_args.name)
# print("Task type:", type(my_task_with_args))


# #         args=["__world_with_args__"],  # ✅ Pass args here
# #         stage_location="@dev_deployment",
# #         return_type=StringType()
# #     ),
# #     schedule=timedelta(hours=4)
# # )


# tasks = root.databases["demo_db"].schemas["public"].tasks
# tasks.create(my_task_with_args, mode=CreateMode.or_replace)

# # Define DAG procedure wrappers

# # with DAG("my_dag", schedule=timedelta(days=1)) as dag:
# #     dag_task_1 = DAGTask(
# #         name="my_hello_task",
# #         # 👈 SQL string
# #         definition="CALL DEMO_DB.PUBLIC.HELLO_PROCEDURE('Canucks')"
# #         # warehouse="COMPUTE_WH"
# #     )

# #     dag_task_2 = DAGTask(
# #         name="my_test_task",
# #         # 👈 SQL string
# #         definition="CALL DEMO_DB.PUBLIC.TEST_PROCEDURE()"
# #         # warehouse="COMPUTE_WH"
# #     )

# #     dag_task_1 >> dag_task_2

# #     schema = root.databases["demo_db"].schemas["public"]
# #     dag_op = DAGOperation(schema)
# #     dag_op.deploy(dag, CreateMode.or_replace)
# # commentblock below
# # def call_hello_procedure_dag(session):
# #     return session.call("DEMO_DB.PUBLIC.HELLO_PROCEDURE", ["world"])


# # def call_test_procedure(session):
# #     return session.call("DEMO_DB.PUBLIC.TEST_PROCEDURE", [])


# # # Create DAG
# # with DAG("my_new_dag", schedule=timedelta(days=1)) as new_dag:
# #     new_dag_task_1 = DAGTask(
# #         "my_new_task",
# #         StoredProcedureCall(
# #             call_hello_procedure_dag,
# #             args=[],
# #             return_type=StringType(),
# #             packages=["snowflake-snowpark-python"],
# #             stage_location="@DEV_DEPLOYMENT"
# #         )
# #     )

# #     new_dag_task_2 = DAGTask(
# #         "my_new_test_task",
# #         StoredProcedureCall(
# #             call_test_procedure,
# #             args=[],
# #             return_type=StringType(),
# #             packages=["snowflake-snowpark-python"],
# #             stage_location="@DEV_DEPLOYMENT"
# #         )
# #     )

# #     new_dag_task_1 >> new_dag_task_2

# #     dag_op = DAGOperation(schema)
# #     dag_op.deploy(new_dag, CreateMode.or_replace)
