import sys
import pickle
# Note: This is just for reference. You must define zip_safe_pickle() directly inside the app-local file — no external imports allowed during deserialization.


def zip_safe_pickle(func, alias_path: str, verbosity: str = "summary"):
    sys.modules[alias_path] = sys.modules[func.__module__]
    if verbosity == "verbose":
        print(f"🔗 Patched alias: {alias_path} → {func.__module__}")
    return pickle.loads(pickle.dumps(func))
