from __future__ import annotations

import sys

from app.common.helpers import print_hello


def hello_function(name="World") -> str:
    """
    This is a Snowflake user-defined function (UDF) that takes a single string input (name) and returns a personalized greeting.
    It's tagged as core, meaning it's intended for core environments like dev or prod.
    """

    return print_hello(name)


# For local debugging
# Be aware you may need to type-convert arguments if you add input parameters
if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "World"
    print(hello_function(name))
