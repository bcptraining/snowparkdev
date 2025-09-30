import importlib
import inspect


def resolve_handler(proc):
    try:
        module_path, func_name = proc["handler"].rsplit(".", 1)
        module = importlib.import_module(module_path)
        handler_fn = getattr(module, func_name)
        proc["handler_fn"] = handler_fn
        return True
    except Exception as e:
        proc["excluded"] = True
        proc["exclusion_reason"] = f"Handler resolution failed: {e}"
        return False


def validate_signature(proc, expected_params):
    try:
        sig = inspect.signature(proc["handler_fn"])
        actual_params = list(sig.parameters.keys())
        proc["params"] = actual_params or ["—"]
        if actual_params != expected_params:
            proc["excluded"] = True
            proc["exclusion_reason"] = f"Expected params {expected_params}, got {actual_params}"
            return False
        return True
    except Exception as e:
        proc["excluded"] = True
        proc["exclusion_reason"] = f"Signature validation failed: {e}"
        return False


def validate_return_type(proc, expected_type="string"):
    try:
        # You can lift this to use type hints or runtime checks
        proc["returns"] = expected_type
        return True
    except Exception as e:
        proc["excluded"] = True
        proc["exclusion_reason"] = f"Return type validation failed: {e}"
        return False
