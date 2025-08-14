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

# Load environment variables from a .env file
from dotenv import load_dotenv
import snowflake.connector
import os
from datetime import timedelta

# Import Snowflake task management classes
from snowflake.core import Root  # Import Root to manage Snowflake resources
from snowflake.core.task import Task, StoredProcedureCall

# Import the Python procedure to be wrapped in a task
from first_snowpark_project.app.python import procedures

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
my_task = Task(
    "my_task",
    StoredProcedureCall(
        procedures.hello_procedure,
        stage_location="@dev_deployment"
    ),
    schedule=timedelta(hours=4),  # Run every 4 minutes
)

# 📂 Access the task manager for the target schema
tasks = root.databases["demo_db"].schemas["public"].tasks

# # 🚀 Create the task in Snowflake
conn.cursor().execute("DROP TASK IF EXISTS DEMO_DB.PUBLIC.MY_TASK")
tasks.create(my_task)
