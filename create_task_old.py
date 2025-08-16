"""
create_task.py

This script connects to a Snowflake environment and creates a scheduled task
that wraps a stored procedure (`hello_procedure`) defined in the project.

It performs the following steps:
- Loads environment variables from a `.env` file for credentials and config
- Establishes a connection to Snowflake using `snowflake.connector`
- Uses the Snowflake Core SDK (`snowflake.core`) to manage tasks
- Wraps the Python procedure in a `Task` object
- Deploys the task to the `@dev_deployment` stage
- Drops any existing task with the same name and creates a new one

Dependencies:
- python-dotenv
- snowflake-connector-python
- snowflake-core
- first_snowpark_project.app.python.procedures

Note:
This script is intended for development use and assumes the presence of a `.env` file.
"""
from snowflake.snowpark.types import StringType

# Load environment variables from a .env file
from dotenv import load_dotenv
import snowflake.connector
import os
from datetime import timedelta

# Import Snowflake task management classes
from snowflake.core import Root  # Import Root to manage Snowflake resources
from snowflake.core.task import Task, StoredProcedureCall
# from snowflake.core import procedures  # this auto-loads deployed procedures
from snowflake.core.task.dagv1 import DAG, DAGTask, DAGOperation, CreateMode

# Import the Python procedure to be wrapped in a task
# from first_snowpark_project.app.python import procedures
# Import the procedure to be called
from first_snowpark_project.app.python.procedures import hello_procedure

# .procedures.app.python.procedures import hello_procedure

# 📦 Load environment variables (e.g., credentials, config)
load_dotenv()

# 🔐 Establish a connection to Snowflake using credentials from .env
conn = snowflake.connector.connect(
    account=os.getenv("SNOWFLAKE_ACCOUNT"),
    user=os.getenv("SNOWFLAKE_USER"),
    password=os.getenv("SNOWFLAKE_PASSWORD"),
    role=os.getenv("SNOWFLAKE_ROLE"),
    warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
    database=os.getenv("SNOWFLAKE_DATABASE"),
    schema="PUBLIC",  # You can change this to use a different schema
)

# 🌲 Create a Root object to manage Snowflake resources (databases, schemas, tasks)
root = Root(conn)

# 🖨️ Print the root object for debugging or confirmation
print(root)

# 🧠 Define a task named "my_task" that wraps the hello_procedure
# The procedure is bundled and deployed to the @dev_deployment stage
# This doesn't work because the path is only valid on my local machine — not inside Snowflake.
# So when Snowflake tries to run the task, it fails because it can’t find first_snowpark_project.
# my_task = Task(
#     "my_task",
#     StoredProcedureCall(
#         procedures.hello_procedure, args=["__world__"],
#         stage_location="@dev_deployment"
#     ),
#     schedule=timedelta(hours=4),  # Run every 4 minutes
# )

# So instead we'll create a task that calls the procedure directly (no that doesn't work either because "procedures isn’t exposed directly from snowflake.core, even though it’s used internally by the SDK." )
# my_task = Task(
#     "my_task",
#     StoredProcedureCall(
#         procedures.hello_procedure, args=["world from the direct proc"],
#         # Ensure the required package is included
#         packages=["snowflake-snowpark-python"],
#         stage_location="@dev_deployment"  # Specify the stage for deployment
#     ),
#     schedule=timedelta(hours=4)  # Set the task to run every 4 hours
# )
# Final Fix: Use StoredProcedureCall with a Callable Wrapper


# def call_hello_procedure(session):
#     return session.call("DEMO_DB.PUBLIC.HELLO_PROCEDURE", ["__world__"])


# from snowflake.core.task import Task, StoredProcedureCall

# 🔧 Step 1: Define a Python function that calls your deployed procedure
# def call_hello_procedure(session):
#     return session.call("DEMO_DB.PUBLIC.HELLO_PROCEDURE", ["__world__"])


# 🔧 Step 2: Use StoredProcedureCall with the callable
my_task = Task(
    "my_task",
    StoredProcedureCall(
        hello_procedure,
        return_type=StringType(),  # ✅ Specify return type
        args=["__world__"],
        stage_location="@dev_deployment",
        packages=["snowflake-snowpark-python"]
    ),
    schedule=timedelta(hours=4)
)
# 🔧 Step 3: Deploy the Task
schema = root.databases["demo_db"].schemas["public"]
conn.cursor().execute("DROP TASK IF EXISTS DEMO_DB.PUBLIC.MY_TASK")
schema.tasks.create(my_task)

# # 🚀 Create the task in Snowflake
schema = root.databases["demo_db"].schemas["public"]


# # Create DAG to manage task dependencies
# with DAG("my_new_dag", schedule=timedelta(days=1)) as new_dag:
#     from snowflake.snowpark.types import StringType

# new_dag_task_1 = DAGTask(
#     "my_new_task",
#     StoredProcedureCall(
#         call_hello_procedure_dag,
#         args=[],
#         return_type=StringType(),
#         packages=["snowflake-snowpark-python"],
#         stage_location="@dev_deployment"
#     )
# )


# def call_test_procedure(session):
#     return session.call("DEMO_DB.PUBLIC.TEST_PROCEDURE", [])


# new_dag_task_2 = DAGTask(
#     "my_new_test_task",
#     StoredProcedureCall(
#         call_test_procedure,
#         args=[],
#         return_type=StringType(),
#         packages=["snowflake-snowpark-python"],
#         stage_location="@dev_deployment"
#     )
# )
