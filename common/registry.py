# common/registry.py

AUTO_PROCS = []


def auto_proc(name=None, input_types=None, return_type=None, tags=None, kind="procedure"):
    """
    Decorator to register a function or procedure for automatic Snowflake deployment.

    Args:
        name (str): Optional name for the UDF. Defaults to function name.
        input_types (list): List of Snowpark DataTypes for input parameters.
        return_type (DataType): Snowpark DataType for return value.
        tags (list): Optional list of tags for filtering (e.g. ["core", "dev", "experimental"])
        kind (str): Either "procedure" or "function" to control registration logic.
    """
    def decorator(func):
        AUTO_PROCS.append({
            "func": func,
            "name": name or func.__name__,
            "input_types": input_types,
            "return_type": return_type,
            "tags": set(tags or []),
            "kind": kind  # 👈 NEW: distinguishes between procedure and function
        })
        return func
    return decorator
