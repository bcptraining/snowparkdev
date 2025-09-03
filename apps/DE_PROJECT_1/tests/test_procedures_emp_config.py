import pytest
from app.common.helpers import load_named_config
from snowflake.snowpark.types import StructType, StringType


@pytest.fixture
def config_name():
    return "copy_to_snowstg_udemy"


def test_load_named_config(config_name):
    config = load_named_config(config_name)

    assert isinstance(config, dict)
    assert "Target_table" in config
    assert config["Target_table"] == "EMPLOYEE"
    assert config["Source_file_type"] == "csv"
    assert isinstance(config["target_columns"], list)
