# Attempt to discover any `pytest_plugins` defined in nested conftest.py files
# and expose or load them so pytest can load plugins correctly.
import ast
import glob
import importlib
import importlib.util
import sys
from pathlib import Path

# Ensure repo root is on sys.path so imports like `import app.*` and `import tests.*`
# resolve reliably during pytest collection (helpful in CI/dev containers).
repo_root = Path(__file__).resolve().parent
repo_root_str = str(repo_root)
if repo_root_str not in sys.path:
    sys.path.insert(0, repo_root_str)

# Ensure any apps/* (that contain an `app/` package) and any repo-local `tests/`
# parents are on sys.path so imports like `import app.python...` and
# `import tests.conftest` resolve during pytest collection.
# Add these early so subsequent plugin discovery/import works.
# repo_root = Path(__file__).resolve().parent

# Add all app parents (e.g. /.../apps/DE_PROJECT_1) to sys.path
for app_parent in sorted(repo_root.glob("apps/*")):
    if (app_parent / "app").is_dir():
        p = str(app_parent.resolve())
        if p not in sys.path:
            sys.path.insert(0, p)

# Add any top-level directories (e.g. app_deprecated) that contain an `app` package
for child in sorted(repo_root.iterdir()):
    if child.is_dir() and (child / "app").is_dir():
        p = str(child.resolve())
        if p not in sys.path:
            sys.path.insert(0, p)

# Add any directory that contains a `tests/` folder (so `import tests.*` works)
for tests_dir in sorted(repo_root.glob("**/tests")):
    parent = str(tests_dir.resolve().parent)
    if parent not in sys.path:
        sys.path.insert(0, parent)

_plugins = []
for path in glob.glob("**/conftest.py", recursive=True):
    if path == "conftest.py":
        continue
    try:
        src = open(path, "r", encoding="utf-8").read()
        tree = ast.parse(src, filename=path)
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    # accept both `pytest_plugins` and a renamed `_pytest_plugins`
                    if getattr(target, "id", None) in ("pytest_plugins", "_pytest_plugins"):
                        val = node.value
                        if isinstance(val, (ast.List, ast.Tuple)):
                            for elt in val.elts:
                                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                    if elt.value not in _plugins:
                                        _plugins.append(elt.value)
    except Exception:
        # ignore parse/read errors — best-effort discovery only
        pass

# We'll attempt to import the discovered plugin specs; if import fails,
# try to load the plugin module directly from a matching file path.
_loaded_plugins = []
for i, spec in enumerate(_plugins):
    try:
        mod = importlib.import_module(spec)
        _loaded_plugins.append(mod)
    except Exception:
        # Try to locate a corresponding .py file and load it under a unique name
        needle = spec.replace(".", "/") + ".py"
        matches = list(Path(".").glob(f"**/{needle}"))
        if matches:
            path = matches[0].resolve()
            name = f"pytest_plugin_{i}"
            try:
                spec_obj = importlib.util.spec_from_file_location(
                    name, str(path))
                if spec_obj is not None and spec_obj.loader is not None:
                    mod = importlib.util.module_from_spec(spec_obj)
                    sys.modules[name] = mod
                    spec_obj.loader.exec_module(mod)
                    _loaded_plugins.append(mod)
            except Exception:
                # best-effort; skip on failure
                pass

# Don't expose string specs (would cause pytest to re-import); register loaded
# module objects later during pytest_configure.
pytest_plugins = []


def pytest_configure(config):
    for mod in _loaded_plugins:
        try:
            config.pluginmanager.register(mod, mod.__name__)
        except Exception:
            # ignore registration failures; best-effort only
            pass
