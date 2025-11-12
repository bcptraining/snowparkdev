import pytest
from snowflake.snowpark.types import StructType, StringType, DateType
from app.common.helpers import load_schema_from_json


@pytest.fixture
def schema_path():
    return "/workspaces/snowparkdev/apps/DE_PROJECT_1/app/schemas/schemas.json"


def test_emp_stg_schema_udemy(schema_path):
    schema = load_schema_from_json(schema_path, "emp_stg_schema_udemy")

    assert isinstance(schema, StructType)
    assert schema.names == ["FIRST_NAME", "LAST_NAME",
                            "EMAIL", "ADDRESS", "CITY", "DOJ"]
    assert schema.fields[0].datatype.__class__.__name__ == "StringType"
    assert schema.fields[5].datatype.__class__.__name__ == "DateType"
