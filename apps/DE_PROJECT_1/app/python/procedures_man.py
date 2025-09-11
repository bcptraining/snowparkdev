from snowflake.snowpark import Session
from snowflake.snowpark.types import StringType
from python.session import get_session
# from python.procedures_man import copy_to_table_proc
# stage_name = f"{env_name}_deployment"

# Define your procedure here


def copy_to_table_proc(session: Session, source_table: str, target_table: str) -> str:
    # Your procedure logic goes here
    return f"Copied from {source_table} to {target_table}"


def register_manual_procs(session: Session, stage_name: str):
    session.sproc.register(
        func=copy_to_table_proc,
        name="copy_to_table_proc",
        input_types=[StringType(), StringType()],
        return_type=StringType(),
        is_permanent=True,
        stage_location=f"@{stage_name}",
        imports=[f"@{stage_name}/{stage_name}.zip"],
        packages=["snowflake-snowpark-python==1.33.0", "cloudpickle==3.0.0"],
        replace=True
    )
    print("✅ Manually registered: copy_to_table_proc")


# if __name__ == "__main__":
#     def main():
#         session = get_session()
#         # stage_name = f"{env_name}_deployment"
#         register_manual_procs(session, stage_name = stage_name)
#     main()
