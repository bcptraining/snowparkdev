from snowflake.snowpark.types import IntegerType, StringType, StructField, StructType, DateType, LongType, DoubleType


class schemas:
    emp_stg_schema = StructType([StructField("FIRST_NAME", StringType()),
                                 StructField("LAST_NAME", StringType()),
                                 StructField("EMAIL", StringType()),
                                 StructField("ADDRESS", StringType()),
                                 StructField("CITY", StringType()),
                                 StructField("DOJ", DateType())])
