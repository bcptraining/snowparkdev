from snowflake.snowpark import Session
from snowflake.snowpark.functions import col, lit, when, current_timestamp
from snowflake.snowpark.types import StringType
import json
from pathlib import Path


def load_named_config(config_name: str) -> dict:
    """Load configuration by name following framework patterns with schema fallback"""
    try:
        # Try direct config file first (framework pattern)
        config_path = Path(__file__).parent.parent / \
            "config" / f"{config_name}.json"
        if config_path.exists():
            with open(config_path, 'r') as f:
                return json.load(f)

        # Try common config location (framework pattern)
        common_config_path = Path(
            __file__).parent.parent.parent.parent / "common" / "config" / f"{config_name}.json"
        if common_config_path.exists():
            with open(common_config_path, 'r') as f:
                return json.load(f)

        # Check if this is a schema name and map to existing config
        schema_path = Path(__file__).parent.parent / "schemas" / "schemas.json"
        if schema_path.exists():
            with open(schema_path, 'r') as f:
                schemas = json.load(f)
                if config_name in schemas:
                    # Found schema, use the main config with this schema key
                    main_config_path = Path(
                        __file__).parent.parent / "config" / "copy_to_snowstg_udemy.json"
                    if main_config_path.exists():
                        with open(main_config_path, 'r') as f:
                            config = json.load(f)
                            # Add schema info to config
                            config["schema_key"] = config_name
                            config["schema_definition"] = schemas[config_name]
                            return config

        # Framework-style error with expected paths
        raise FileNotFoundError(
            f"Configuration '{config_name}' not found. Expected at {config_path} or as schema in {schema_path}")

    except Exception as e:
        raise RuntimeError(f"Failed to load config '{config_name}': {str(e)}")


def copy_to_table_proc(session: Session, schema_key: str = "copy_to_snowstg_udemy"):
    """Copy data with reject handling integrated - following framework patterns"""

    # Load config from JSON file (no hardcoded fallback)
    config = load_named_config(schema_key)

    database_name = config["Database_name"]
    schema_name = config["Schema_name"]
    target_table = config["Target_table"]
    reject_table = config["Reject_table"]
    # "@DEMO_DB.PUBLIC.DEV_INTERNAL_STAGE"
    source_location = config["Source_location"]
    file_format = config["file_format"]

    # Create full table names following framework patterns
    target_full_name = f"{database_name}.{schema_name}.{target_table}"
    reject_full_name = f"{database_name}.{schema_name}.{reject_table}"

    try:
        # Read data from stage using config values
        df_raw = session.read.option("FIELD_DELIMITER", file_format["field_delimiter"]) \
            .option("SKIP_HEADER", file_format["skip_header"]) \
            .option("FIELD_OPTIONALLY_ENCLOSED_BY", file_format["field_optionally_enclosed_by"]) \
            .csv(source_location)

        # Add validation - reject records with empty/null first name
        df_with_validation = df_raw.with_column(
            "is_valid",
            when(
                (col("$1").is_null()) |
                (col("$1") == "") |
                (col("$1") == "NULL"),
                False
            ).otherwise(True)
        )

        # Split into valid and rejected records
        df_valid = df_with_validation.filter(col("is_valid") == True)
        df_rejected = df_with_validation.filter(col("is_valid") == False)

        valid_count = df_valid.count()
        reject_count = df_rejected.count()

        # Process valid records
        if valid_count > 0:
            df_final = df_valid.select(
                col("$1").alias("FIRST_NAME"),
                col("$2").alias("LAST_NAME"),
                col("$3").alias("EMAIL"),
                col("$4").alias("ADDRESS"),
                col("$5").alias("CITY"),
                col("$6").alias("DOJ")
            )
            df_final.write.mode("append").save_as_table(target_full_name)

        # Handle rejected records
        if reject_count > 0:
            # Ensure reject table exists
            create_reject_table_sql = f"""
            CREATE TABLE IF NOT EXISTS {reject_full_name} (
                FIRST_NAME VARCHAR(100),
                LAST_NAME VARCHAR(100),
                EMAIL VARCHAR(200),
                ADDRESS VARCHAR(500),
                CITY VARCHAR(100),
                DOJ VARCHAR(50),
                REJECT_REASON VARCHAR(1000),
                REJECT_TIMESTAMP TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
            )
            """
            session.sql(create_reject_table_sql).collect()

            # Insert rejected records with metadata
            df_reject_output = df_rejected.select(
                col("$1").alias("FIRST_NAME"),
                col("$2").alias("LAST_NAME"),
                col("$3").alias("EMAIL"),
                col("$4").alias("ADDRESS"),
                col("$5").alias("CITY"),
                col("$6").alias("DOJ"),
                lit("Missing or empty first name").alias("REJECT_REASON"),
                current_timestamp().alias("REJECT_TIMESTAMP")
            )

            df_reject_output.write.mode(
                "append").save_as_table(reject_full_name)

        # Return framework-compatible result
        return f"SUCCESS: Processed {valid_count + reject_count} records. Loaded {valid_count} valid, rejected {reject_count}. Target: {target_full_name}, Rejects: {reject_full_name if reject_count > 0 else 'None'}"

    except Exception as e:
        # Return framework-compatible error
        return f"FAILED: {str(e)} - Target: {target_full_name}"


def test_manual_proc(session: Session, test_input: str = "test"):
    """Test procedure for manual registration following framework patterns"""
    return f"Manual procedure test result: {test_input}"
