class configs:
    employee_config_example = {
        "Database_name": "DEMO_DB",
        "Schema_name": "PUBLIC",
        "Target_table": "CUSTOMER_TEST_STG",
        "Reject_table": "CUSTOMER_TEST_STG_REJECTS",
        "target_columns": [],
        "on_error": "CONTINUE",
        "Source_location": "@VDW_DEV_INGEST.TF_DEFAULT.DATA/customer_test/",
        "Source_file_type": "csv"
    }
    employee_config = {"Database_name": "DEMO_DB",
                       "Schema_name": "PUBLIC",
                       "Target_table": "EMPLOYEE",
                       "Reject_table": "EMPLOYEE_REJECTS",
                       "target_columns": ["FIRST_NAME", "LAST_NAME", "EMAIL", "ADDRESS", "CITY", "DOJ"],
                       "on_error": "CONTINUE",
                       "Source_location": "@my_s3_stage/employee/",
                       "Source_file_type": "csv"
                       }
