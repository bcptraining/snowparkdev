from __future__ import annotations
from first_snowpark_project.app.python.common import print_hello
from snowflake.snowpark import Session
import sys
# Dynamically add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), "../../../..")))
# from app.python.common import print_hello


# def hello_procedure(session: Session, name: str) -> str:
#     return f"Hello, {name}"

def hello_procedure2(session: Session, name="World") -> str:
    return print_hello(name)


def test_procedure(session: Session) -> str:
    return "Test procedure"


def test_procedure_two(session: Session) -> str:
    return "Test procedure"


# # For local debugging
# # Beware you may need to type-convert arguments if you add input parameters
# if __name__ == "__main__":
#     # Create a local Snowpark session
#     with Session.builder.config("local_testing", True).getOrCreate() as session:
#         print(hello_procedure(session, *sys.argv[1:]))  # type: ignore
