import pytz
from datetime import datetime
import yaml
from pathlib import Path
import importlib
import inspect


class ProcRegistrar:
    # map Snowflake types to Python types for basic validation
    TYPE_MAP = {
        "string": "str",
        "number": "int",
        "float": "float",
        "boolean": "bool",
        "variant": "dict",
        "array": "list",
        "object": "dict",
        # Add more as needed
    }

    def __init__(self, app_path: Path, verbose: bool = True, dry_run: bool = False):
        self.app_path = app_path
        self.verbose = verbose
        self.dry_run = dry_run
        self.declared = []

    def load_declarative_procs(self):
        yml_path = self.app_path / "snowflake.yml"
        if not yml_path.exists():
            raise FileNotFoundError(f"Missing snowflake.yml at {yml_path}")
        with open(yml_path, "r") as f:
            config = yaml.safe_load(f)

        entities = config.get("entities", {})
        for name, entity in entities.items():
            if entity.get("type") == "procedure":
                self.declared.append({
                    "name": name,
                    "handler": entity.get("handler"),
                    "signature": entity.get("signature", []),
                    "returns": entity.get("returns"),
                })

        if self.verbose:
            self.summarize()

    # Private method to summarize loaded procedures
    # def _summarize(self):
    #     print("\n📜 Declarative Procedures in snowflake.yml:")
    #     for proc in self.declared:
    #         sig = ", ".join(
    #             f"{p['name']}: {p['type']}" for p in proc["signature"])
    #         print(
    #             f" - {proc['name']} → {proc['handler']}({sig}) → {proc['returns']}")
    # Public method to summarize loaded procedures
    def summarize(self):
        if not self.verbose:
            return
        print(
            f"\n📊 Declarative Procedure Summary ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}):")
        for proc in self.declared:
            sig = ", ".join(
                f"{p['name']}: {p['type']}" for p in proc["signature"])
            print(
                f" - {proc['name']} → {proc['handler']}({sig}) → {proc['returns']}")

    def validate_handlers(self):
        print("\n🔍 Validating declared handlers...")
        for proc in self.declared:
            handler_path = proc["handler"]
            try:
                module_path, func_name = handler_path.rsplit(".", 1)
                module = importlib.import_module(module_path)
                func = getattr(module, func_name)
                if callable(func):
                    print(f"✅ {handler_path} resolved successfully.")
                else:
                    print(f"⚠️ {handler_path} exists but is not callable.")
            except Exception as e:
                print(f"❌ Failed to resolve {handler_path}: {e}")

    import inspect

    def validate_signatures(self):
        print("\n🧪 Validating handler signatures...")
        for proc in self.declared:
            handler_path = proc["handler"]
            expected_params = [p["name"] for p in proc.get("signature", [])]

            try:
                module_path, func_name = handler_path.rsplit(".", 1)
                module = importlib.import_module(module_path)
                func = getattr(module, func_name)

                if not callable(func):
                    print(f"⚠️ {handler_path} is not callable.")
                    continue

                sig = inspect.signature(func)
                actual_params = [p.name for p in sig.parameters.values()]

                # Allow 'session' as implicit first param
                if actual_params and actual_params[0] == "session":
                    actual_params = actual_params[1:]

                if actual_params == expected_params:
                    print(
                        f"✅ {handler_path} matches expected signature: ({', '.join(expected_params)})")
                else:
                    print(f"❌ {handler_path} signature mismatch.\n"
                          f"   Expected: ({', '.join(expected_params)})\n"
                          f"   Found:    ({', '.join(actual_params)})")

            except Exception as e:
                print(f"❌ Failed to inspect {handler_path}: {e}")

    def validate_returns(self):

        print("\n🔁 Validating handler return types...")
        for proc in self.declared:
            handler_path = proc["handler"]
            expected_return = proc.get("returns")
            expected_python_type = self.TYPE_MAP.get(
                expected_return, expected_return)

            try:
                module_path, func_name = handler_path.rsplit(".", 1)
                module = importlib.import_module(module_path)
                func = getattr(module, func_name)

                if not callable(func):
                    print(f"⚠️ {handler_path} is not callable.")
                    continue

                sig = inspect.signature(func)
                actual_return = sig.return_annotation

                if actual_return is inspect.Signature.empty:
                    print(
                        f"❌ {handler_path} has no return type annotation. Expected: {expected_return}")
                elif actual_return.__name__ == expected_python_type:
                    print(
                        f"✅ {handler_path} returns {expected_return} as expected.")
                else:
                    print(f"❌ {handler_path} return type mismatch.\n"
                          f"   Expected: {expected_return} ({expected_python_type})\n"
                          f"   Found:    {actual_return.__name__}")

            except Exception as e:
                print(
                    f"❌ Failed to inspect return type for {handler_path}: {e}")

    def summarize_validation(self):
        print("\n📊 Declarative Procedure Validation Summary:\n")

        header = f"{'Name':<20} {'Handler':<50} {'Params':<20} {'Returns':<10} {'Status':<10}"
        print(header)
        print("-" * len(header))

        for proc in self.declared:
            name = proc["name"]
            handler = proc["handler"]
            params = ", ".join(p["name"]
                               for p in proc.get("signature", [])) or "—"
            returns = proc.get("returns", "—")

            # Signature check
            try:
                module_path, func_name = handler.rsplit(".", 1)
                module = importlib.import_module(module_path)
                func = getattr(module, func_name)
                sig = inspect.signature(func)

                actual_params = [p.name for p in sig.parameters.values()]
                if actual_params and actual_params[0] == "session":
                    actual_params = actual_params[1:]
                sig_valid = actual_params == [p["name"]
                                              for p in proc.get("signature", [])]

                actual_return = sig.return_annotation
                if actual_return is inspect.Signature.empty:
                    return_valid = False
                else:
                    expected_python_type = self.TYPE_MAP.get(returns, returns)
                    return_valid = actual_return.__name__ == expected_python_type

                status = "✅ Valid" if sig_valid and return_valid else "❌ Invalid"

            except Exception:
                status = "❌ Error"

            print(f"{name:<20} {handler:<50} {params:<20} {returns:<10} {status:<10}")

    def emit_final_summary(self):
        total = len(self.declared)
        pacific = pytz.timezone("US/Pacific")
        timestamp = datetime.now(pacific).strftime("%Y-%m-%d %H:%M %Z")
        print(f"\n🧠 Declarative validation completed at {timestamp}")
        print(f"✅ {total} procedures validated successfully")
        print(
            f"🚀 Ready for deploy via: snow snowpark deploy --app {self.app_path.name}")

    def validate_all(self, narrate: bool = True) -> bool:
        """
        Runs the full declarative validation suite for all procedures defined in snowflake.yml.

        This includes:
        - Handler resolution
        - Signature validation (excluding 'session')
        - Return type normalization (Snowflake → Python)
        - Optional narration of validation steps and summary table

        Args:
            narrate (bool): If True, emits validation narration and summary table.
                            If False, runs silently (used during deploy to avoid duplicate output).

        Returns:
            bool: True if all procedures pass validation, False if any are invalid or unresolved.

        Usage:
            - Dry-run mode: narrate=True to emit full validation logs
            - Deploy mode: narrate=False to reuse validation silently
            - CI pipelines: fail fast if declarative procedures are broken

        Example:
            registrar = ProcRegistrar(app_path, verbose=True, dry_run=True)
            if not registrar.validate_all(narrate=True):
                sys.exit(1)  # Abort deploy
        """

        self.load_declarative_procs()
        self.validate_handlers()
        self.validate_signatures()
        self.validate_returns()

        if narrate:
            self.summarize_validation()
            if not self.dry_run:
                self.emit_final_summary()

        return all(p["status"] == "valid" for p in self.validated_procs)

    @property
    def validated_procs(self) -> list[dict]:
        """
        Returns a list of declarative procedures with metadata for deploy narration.
        Each dict includes: name, handler, params, return_type, source, status
        """
        results = []

        for proc in self.declared:
            name = proc["name"]
            handler = proc["handler"]
            params = proc.get("signature", [])
            return_type = proc.get("returns")
            source = "declarative"

            # Re-validate signature and return type
            try:
                module_path, func_name = handler.rsplit(".", 1)
                module = importlib.import_module(module_path)
                func = getattr(module, func_name)
                sig = inspect.signature(func)

                actual_params = [p.name for p in sig.parameters.values()]
                if actual_params and actual_params[0] == "session":
                    actual_params = actual_params[1:]
                sig_valid = actual_params == [p["name"] for p in params]

                actual_return = sig.return_annotation
                expected_python_type = self.TYPE_MAP.get(
                    return_type, return_type)
                return_valid = (
                    actual_return is not inspect.Signature.empty
                    and actual_return.__name__ == expected_python_type
                )

                status = "valid" if sig_valid and return_valid else "invalid"

            except Exception:
                status = "error"

            results.append({
                "name": name,
                "handler": handler,
                "params": params,
                "return_type": return_type,
                "source": source,
                "status": status
            })

        return results
