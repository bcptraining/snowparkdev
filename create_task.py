from dotenv import load_dotenv
import snowflake.connector
import os
from datetime import timedelta
from snowflake.snowpark.types import StringType
from snowflake.core import Root
from snowflake.core.task import Task, StoredProcedureCall
from snowflake.core.task.dagv1 import DAG, DAGTask, DAGOperation, CreateMode

# Load environment variables
load_dotenv()

# Connect to Snowflake
conn = snowflake.connector.connect(
    account=os.getenv("SNOWFLAKE_ACCOUNT"),
    user=os.getenv("SNOWFLAKE_USER"),
    password=os.getenv("SNOWFLAKE_PASSWORD"),
    role=os.getenv("SNOWFLAKE_ROLE"),
    warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
    database=os.getenv("SNOWFLAKE_DATABASE"),
    schema="PUBLIC"
)

root = Root(conn)
print(root)

schema = root.databases["demo_db"].schemas["public"]

# Define callable wrapper for hello_procedure


def call_hello_procedure(session):
    return session.call("DEMO_DB.PUBLIC.HELLO_PROCEDURE", ["__world__"])


# Create scheduled task
my_task = Task(
    "my_task",
    StoredProcedureCall(
        call_hello_procedure,
        return_type=StringType(),
        stage_location="@DEV_DEPLOYMENT",
        packages=["snowflake-snowpark-python==1.35.0"]
    ),
    schedule=timedelta(hours=4),
    warehouse="COMPUTE_WH"
)

# Drop and create task
conn.cursor().execute("DROP TASK IF EXISTS DEMO_DB.PUBLIC.my_task")
# schema.tasks.create(my_task)
schema.tasks.create(my_task, mode=CreateMode.or_replace)
schema.tasks["my_task"].resume()


# Define DAG procedure wrappers


def call_hello_procedure_dag(session):
    return session.call("DEMO_DB.PUBLIC.HELLO_PROCEDURE", ["world"])


def call_test_procedure(session):
    return session.call("DEMO_DB.PUBLIC.TEST_PROCEDURE", [])


# Create DAG
with DAG("my_new_dag", schedule=timedelta(days=1)) as new_dag:
    new_dag_task_1 = DAGTask(
        "my_new_task",
        StoredProcedureCall(
            call_hello_procedure_dag,
            args=[],
            return_type=StringType(),
            packages=["snowflake-snowpark-python"],
            stage_location="@DEV_DEPLOYMENT"
        )
    )

    new_dag_task_2 = DAGTask(
        "my_new_test_task",
        StoredProcedureCall(
            call_test_procedure,
            args=[],
            return_type=StringType(),
            packages=["snowflake-snowpark-python"],
            stage_location="@DEV_DEPLOYMENT"
        )
    )

    new_dag_task_1 >> new_dag_task_2

    dag_op = DAGOperation(schema)
    dag_op.deploy(new_dag, CreateMode.or_replace)
