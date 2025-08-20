from first_snowpark_project.app.python.session import get_session
from snowflake.core import Root
import snowflake.connector
# from app.python.session import get_session
from dotenv import load_dotenv
from datetime import timedelta
from snowflake.snowpark.types import StringType
# from app.python import procedures
from first_snowpark_project.app.python import procedures

from snowflake.core.task import Task, StoredProcedureCall
from snowflake.core.task.dagv1 import DAG, DAGTask, DAGOperation, CreateMode
import sys
import os
# from first_snowpark_project.app.python.common import print_hello

# Add the parent of 'first_snowpark_project' to sys.path
project_root = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "../../.."))
sys.path.insert(0, project_root)

# Now this import should work
print("Current sys.path:")
for p in sys.path:
    print("  ", p)

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

conn = snowflake.connector.connect(
    # account=os.getenv("SNOWFLAKE_ACCOUNT"),
    # user=os.getenv("SNOWFLAKE_USER"),
    # password=os.getenv("SNOWFLAKE_PASSWORD"),
    # role=os.getenv("SNOWFLAKE_ROLE"),
    # warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
    # database=os.getenv("SNOWFLAKE_DATABASE"),
    # schema="PUBLIC"
)

root = Root(conn)
print(root)

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
