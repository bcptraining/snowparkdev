from app.python.session import get_session
from dotenv import load_dotenv
import os
from pathlib import Path
from snowflake.snowpark.functions import col


from snowflake.snowpark.types import StructType, StructField, StringType, DoubleType, IntegerType

stock_value_summary_schema = StructType([
    StructField("Stock", StringType()),
    StructField("Date", StringType()),
    StructField("Party", StringType()),
    StructField("Category", StringType()),
    StructField("Txntype", StringType()),
    StructField("Quantity", IntegerType()),
    StructField("Value traded", DoubleType()),
    StructField("Avgtradeprice", DoubleType()),
])


def clean_numeric_column(col):
    # Remove commas, strip units like 'L', 'Cr', etc., and convert to float
    return (
        col.replace({r"[^\d\.]": ""}, regex=True)
        .replace("", pd.NA)
        .astype(float)
    )

# def upload_file_to_stage(session, local_path, stage_path):
#     session.file.put(
#         local_path,
#         stage_path,
#         overwrite=True
#     )
#     print(f"✅ Uploaded {local_path} to @{stage_path}")


def main():
    # Define path to .env file
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    load_dotenv(dotenv_path=env_path)

    # Retrieve variables pertaining to this script
    stage = os.getenv("DATA_STAGE", "default_stage")
    if not stage:
        raise ValueError("DATA_STAGE not set in environment")

    filename = os.getenv("DATA_FILE", "default.csv")
    output_table = os.getenv("OUTPUT_TABLE", "stock_value_summary_test_only")

    raw_csv = f"data/{filename}"
    cleaned_csv = f"data/cleaned_{filename}"

    session = get_session()

    try:
        session.sql(f"LIST @{stage}").show()
    except Exception as e:
        raise RuntimeError(f"❌ Cannot access stage @{stage}: {e}")

    import pandas as pd

    def clean_numeric_column(col):
        # Remove commas, strip units like 'L', 'Cr', etc., and convert to float
        return (
            col.replace({r"[^\d\.]": ""}, regex=True)
            .replace("", pd.NA)
            .astype(float)
        )

    # 1. Preprocess with pandas
    df_pd = pd.read_csv(raw_csv, thousands=",")
    df_pd["Value traded"] = clean_numeric_column(df_pd["Value traded"])
    df_pd["Avgtradeprice"] = clean_numeric_column(df_pd["Avgtradeprice"])
    df_pd.to_csv(cleaned_csv, index=False)

    # 2. Upload to stage
    upload_file_to_stage(session, cleaned_csv, f"@{stage}")

    # 3. Read with Snowpark using explicit schema
    df = session.read.schema(stock_value_summary_schema).option(
        "header", True).csv(f"@{stage}/cleaned_{filename}")

    # 4. Cast numeric columns
    df = df.with_column("Value traded", col("Value traded").cast("DOUBLE"))
    df = df.with_column("Avgtradeprice", col("Avgtradeprice").cast("DOUBLE"))

    # Total value traded per stock
    df_value_by_stock = df.group_by("Stock").agg({"Value traded": "sum"})
    df_value_by_stock.show()

    # Average trade price per category
    df_avg_price_by_category = df.group_by(
        "Category").agg({"Avgtradeprice": "avg"})
    df_avg_price_by_category.show()

    # Transaction type breakdown
    df_txn_type_counts = df.group_by("Txntype").count()
    df_txn_type_counts.show()

    # Save summary to configured output table
    df_value_by_stock.write.save_as_table(output_table, mode="overwrite")
    print(f"✅ Saved stock value summary to table: {output_table}")


if __name__ == "__main__":
    print("🚀 Starting stock sales data processing...")
    main()
