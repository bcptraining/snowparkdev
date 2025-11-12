from snowflake.snowpark import Session
from snowflake.snowpark.functions import col, lit, when, current_timestamp
from snowflake.snowpark.types import StringType
from typing import List, Optional
import json
import sys
from pathlib import Path
from datetime import datetime


def load_named_config(config_name: str) -> dict:
    """Load configuration by name following framework patterns with hardcoded fallback"""
    try:
        # Try direct config file first (framework pattern)
        config_path = Path(__file__).parent.parent / \
            "config" / f"{config_name}.json"
        if config_path.exists():
            with open(config_path, 'r') as f:
                return json.load(f)

        # Framework pattern: hardcoded fallback for production deployment
        hardcoded_configs = {
            "copy_to_snowstg_udemy": {
                "Database_name": "DEMO_DB",
                "Schema_name": "PUBLIC",
                "Target_table": "EMPLOYEE2",
                "Reject_table": "EMPLOYEE_REJECTS",
                "persist_all_copy_results": True,
                "target_columns": ["FIRST_NAME", "LAST_NAME", "EMAIL", "ADDRESS", "CITY", "DOJ"],
                "on_error": "CONTINUE",
                "Source_location_real": "@my_s3_stage",
                "Source_location": "@DEMO_DB.PUBLIC.DEV_INTERNAL_STAGE",
                "Source_file_type": "csv",
                "file_format": {
                    "type": "CSV",
                    "field_delimiter": ",",
                    "skip_header": 0,
                    "field_optionally_enclosed_by": "\"",
                    "null_if": ["", "NULL"],
                    "encoding": "UTF8"
                }
            }
        }

        if config_name in hardcoded_configs:
            return hardcoded_configs[config_name]

        raise FileNotFoundError(
            f"Configuration '{config_name}' not found at {config_path}")

    except FileNotFoundError:
        raise
    except (json.JSONDecodeError, IOError) as e:
        raise RuntimeError(f"Failed to load config '{config_name}': {str(e)}")


def copy_to_table_proc(session: Session, schema_key: str = "copy_to_snowstg_udemy"):
    """Copy data with reject handling integrated - following framework patterns"""

    # Load config from JSON file following framework config patterns
    config = load_named_config(schema_key)

    database_name = config["Database_name"]
    schema_name = config["Schema_name"]
    target_table = config["Target_table"]
    reject_table = config["Reject_table"]
    source_location = config["Source_location"]
    file_format = config["file_format"]

    # Create full table names following framework patterns
    target_full_name = f"{database_name}.{schema_name}.{target_table}"
    reject_full_name = f"{database_name}.{schema_name}.{reject_table}"

    try:
        # Try to read data from stage with error handling
        try:
            df_raw = session.read.option("FIELD_DELIMITER", file_format["field_delimiter"]) \
                .option("SKIP_HEADER", file_format["skip_header"]) \
                .option("FIELD_OPTIONALLY_ENCLOSED_BY", file_format.get("field_optionally_enclosed_by", "\"")) \
                .csv(source_location)
        except Exception as read_err:
            # Fallback: try reading without enclosing character (tolerant)
            try:
                df_raw = session.read.option("FIELD_DELIMITER", file_format["field_delimiter"]) \
                    .option("SKIP_HEADER", file_format["skip_header"]) \
                    .option("FIELD_OPTIONALLY_ENCLOSED_BY", "") \
                    .csv(source_location)
            except Exception as fallback_err:
                # Final fallback: record parse failure to reject table
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
                err_text = str(fallback_err).replace("'", "''")
                session.sql(
                    f"INSERT INTO {reject_full_name} (REJECT_REASON) SELECT '{err_text}'").collect()
                return f"FAILED: CSV parse error; wrote error to {reject_full_name}: {err_text}"

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

        # Return framework-compatible result (following manual procs API)
        return f"SUCCESS: Processed {valid_count + reject_count} records. Loaded {valid_count} valid, rejected {reject_count}. Target: {target_full_name}, Rejects: {reject_full_name if reject_count > 0 else 'None'}"

    except Exception as e:
        # Return framework-compatible error (following manual procs API)
        return f"FAILED: {str(e)} - Target: {target_full_name}"


def test_manual_proc(session: Session, test_input: str = "test"):
    """Test procedure for manual registration following framework patterns"""
    return f"Manual procedure test result: {test_input}"


# Manual procs API implementation following framework patterns from deploy/deploy_manager.py
def register_manual_procs(
    session: Optional[Session],
    stage_name: str,
    app_name: str,
    include_tags: Optional[List[str]] = None,
    dry_run: bool = False,
    verbosity: str = "summary"
) -> List[dict]:
    """Register manual procedures following framework manual procs API patterns"""

    print(
        f"📡 Manual-registering procedures for {app_name} in stage {stage_name}")

    # Define manual procedures following framework MANUAL_PROCS pattern
    manual_procedures = [
        {
            "func": copy_to_table_proc,
            "name": "copy_to_table_proc",
            "input_types": [StringType()],  # schema_key parameter
            "return_type": StringType(),
            "tags": ["core"],  # Valid for dev environment
            "source": "manual"
        },
        {
            "func": test_manual_proc,
            "name": "test_manual_proc",
            "input_types": [StringType()],  # test_input parameter
            "return_type": StringType(),
            "tags": ["experimental"],  # Valid for dev environment
            "source": "manual"
        }
    ]

    # Normalize tag case following framework tag normalization patterns
    normalized_tags = [tag.lower()
                       for tag in include_tags] if include_tags else None
    registered = []

    for proc in manual_procedures:
        proc["tags"] = [tag.lower() for tag in proc.get("tags", [])]

        # Tag filtering following framework tag validation patterns
        if normalized_tags and not any(tag in normalized_tags for tag in proc["tags"]):
            print(f"⏭️ Skipping {proc['name']} due to tag filter.")
            continue

        if dry_run:
            param_types = ", ".join(
                t.__class__.__name__ for t in proc["input_types"])
            return_type = proc["return_type"].__class__.__name__
            print(
                f"📝 Would register: {proc['name']}({param_types}) → {return_type}")
            registered.append({
                "name": proc["name"],
                "kind": "procedure",
                "tags": proc["tags"],
                "source": "manual",
                "status": "dry_run"
            })
            continue

        # Handle privilege issues following framework privilege handling patterns
        if session:
            try:
                # First attempt: try to drop existing procedure that may have privilege issues
                drop_sql = f"DROP PROCEDURE IF EXISTS {proc['name']}(VARCHAR)"
                session.sql(drop_sql).collect()
                print(f"🗑️ Dropped existing procedure: {proc['name']}")
            except Exception as drop_error:
                print(
                    f"⚠️ Could not drop existing procedure {proc['name']}: {drop_error}")
                # Continue anyway - maybe it doesn't exist

        # Set module alias for Snowflake handler resolution following framework patterns
        alias_path = "app.python.manual_procs"
        sys.modules[alias_path] = sys.modules[__name__]

        # Register procedure following framework manual procs registration patterns
        if session:
            orig_module = getattr(proc["func"], "__module__", None)
            try:
                proc["func"].__module__ = alias_path

                session.sproc.register(
                    func=proc["func"],
                    name=proc["name"],
                    input_types=proc["input_types"],
                    return_type=proc["return_type"],
                    is_permanent=True,
                    stage_location=f"@{stage_name}",
                    imports=[f"@{stage_name}/apps/{app_name}/app.zip"],
                    packages=["snowflake-snowpark-python==1.33.0",
                              "cloudpickle==3.0.0", "requests"],
                    replace=True,
                    is_pandas=False
                )

                print(f"✅ Manually registered: {proc['name']}")
                registered.append({
                    "name": proc["name"],
                    "kind": "procedure",
                    "tags": proc["tags"],
                    "source": "manual",
                    "status": "registered"
                })

            except Exception as reg_error:
                print(f"❌ Failed to register {proc['name']}: {reg_error}")
                registered.append({
                    "name": proc["name"],
                    "kind": "procedure",
                    "tags": proc["tags"],
                    "source": "manual",
                    "status": "failed",
                    "error": str(reg_error)
                })
            finally:
                if orig_module:
                    proc["func"].__module__ = orig_module

    # Summary reporting following framework patterns
    print(
        f"\n✅ Included {len(registered)} manual procedures based on tag filter")

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"🧠 Manual registration completed at {ts}")

    return registered
