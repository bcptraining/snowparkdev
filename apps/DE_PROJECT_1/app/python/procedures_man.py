from snowflake.snowpark import Session
from snowflake.snowpark.types import StringType
from python.session import get_session
from python.procedures_man import copy_to_table_proc


def register_manual_procs(session: Session):
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
    print("✅ Manually registered: copy_to_table_proc")


if __name__ == "__main__":
    session = get_session()
    register_manual_procs(session)
