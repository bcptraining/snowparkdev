# src/utils/hello_snowpark.py
from snowflake.snowpark import Session


def hello():
    print("👋 Hello from Snowpark!")


if __name__ == "__main__":
    hello()
