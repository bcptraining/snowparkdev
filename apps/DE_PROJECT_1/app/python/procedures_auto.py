from snowflake.snowpark import Session
from snowflake.snowpark.functions import udf
from snowflake.snowpark.types import StringType


def register_procs(session: Session, app_name: str, stage_name: str, zip_name: str):
    print(
        f"📡 Registering auto procedures for {app_name} in stage {stage_name}")

    # Procedure 1
    def hello_procedure(name: str) -> str:
        return f"Hello, {name}!"

    udf(
        func=hello_procedure,
        input_types=[StringType()],
        return_type=StringType(),
        name="hello_procedure",
        stage_location=f"@{stage_name}",
        replace=True
    ).register(session)  # type: ignore[attr-defined]

    # Procedure 2
    def hello_procedure2(name: str) -> str:
        return f"Hi there, {name}!"

    udf(
        func=hello_procedure2,
        input_types=[StringType()],
        return_type=StringType(),
        name="hello_procedure2",
        stage_location=f"@{stage_name}",
        replace=True
    ).register(session)  # type: ignore[attr-defined]

    # Procedure 3
    def test_procedure() -> str:
        return "Test procedure executed."

    udf(
        func=test_procedure,
        input_types=[],
        return_type=StringType(),
        name="test_procedure",
        stage_location=f"@{stage_name}",
        replace=True
    ).register(session)  # type: ignore[attr-defined]

    # Procedure 4
    def test_procedure_two() -> str:
        return "Second test procedure executed."

    udf(
        func=test_procedure_two,
        input_types=[],
        return_type=StringType(),
        name="test_procedure_two",
        stage_location=f"@{stage_name}",
        replace=True
    ).register(session)  # type: ignore[attr-defined]

    # Function
    def hello_function(name: str) -> str:
        return f"Echo: {name}"

    udf(
        func=hello_function,
        input_types=[StringType()],
        return_type=StringType(),
        name="hello_function",
        stage_location=f"@{stage_name}",
        replace=True
    ).register(session)  # type: ignore[attr-defined]

    print("✅ Auto procedures registered successfully.")
