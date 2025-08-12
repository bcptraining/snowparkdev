from __future__ import annotations

import sys

from app.python.common import print_hello


def hello_function(name="World") -> str:
    return print_hello(name)


# For local debugging
# Be aware you may need to type-convert arguments if you add input parameters
if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "World"
    print(hello_function(name))
