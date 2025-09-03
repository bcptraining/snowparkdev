from apps.DE_PROJECT_1.app.python.procedures_auto import copy_to_table_proc
from session import get_session
from snowflake.snowpark.types import StringType
from snowflake.snowpark import Session
import sys
from pathlib import Path

# Add the /apps/DE_PROJECT_1/app directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))


# from snowflake.snowpark import Session
# from apps.DE_PROJECT_1.app.python.session import get_session
# from apps.DE_PROJECT_1.app.python.procedures import copy_to_table_proc


# from pathlib import Path
# sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def register_all_procs(session: Session):
    session.sproc.register(
        func=copy_to_table_proc,
        name="copy_to_table_proc",
        input_types=[StringType(), StringType()],
        return_type=StringType(),
        is_permanent=True,
        stage_location="@dev_deployment",
        imports=["@dev_deployment/app.zip"],
        packages=["snowflake-snowpark-python==1.33.0", "cloudpickle==3.0.0"],
        replace=True
    )
    print("✅ Procedure registered successfully.")


if __name__ == "__main__":
    session = get_session()
    register_all_procs(session)
