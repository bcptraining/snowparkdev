import inspect
import re
import yaml
# -- supports an experimental refactor to use a class-based approach
# from orchestration.proc_registrar import ProcRegistrar
from deploy.orchestration.proc_registrar import ProcRegistrar
from deploy.tag_registry import TAG_SETS
import pytz
from datetime import datetime
import importlib
import zipfile
import subprocess
import shutil
import sys
import os
import json
import time
import argparse
from pathlib import Path
from snowflake.core import Root
from snowflake.core.task.dagv1 import DAGOperation
import re  # for regex operations
# Defines set of tags applicable to each environment
from deploy.constants import VALID_TAGS


# tags = TAG_SETS[args.env] if 'env_name' in locals() else []  # Example usage
from deploy.deploy_manager import DeployManager
from deploy.utils.change_detection import get_changed_files_for_app
from deploy.utils.tag_validation import validate_tags_for_env

print(f"__name__ = {__name__}")
print(f"cwd = {os.getcwd()}")
print(f"sys.path = {sys.path}")


def vprint(msg: str, verbosity: str):
    if verbosity == "verbose":
        print(msg)


# Global constants
APPS_DIR = Path("apps")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# env_tag_defaults = {  # moved from inside parse_cli_args() to be a global constant
#     "dev": ["core", "experimental", "diagnostic"],
#     "qa": ["core", "diagnostic"],
#     "prod": ["core", "!experimental", "!diagnostic"]
# }


def validate_tags(tags: list[str], proc_name: str | None = None) -> list[str]:
    invalid = [t for t in tags if t not in VALID_TAGS]
    if invalid:
        raise ValueError(
            f"❌ Procedure '{proc_name}' has invalid tags: {invalid}")
    return tags


# These functions are not currently used but might be helpful for future enhancements to compare existing procedure definitions.
# def get_current_def(session, proc_name):
#     ddl_query = f"SELECT GET_DDL('procedure', '{proc_name}')"
#     result = session.sql(ddl_query).collect()
#     return result[0][0] if result else None


# def extract_python_body(ddl_text):
#     match = re.search(r"AS\s+\$\$\s+(.*?)\s+\$\$", ddl_text, re.DOTALL)
#     return match.group(1).strip() if match else None


def get_snowflake_credentials():
    return {
        "account": os.environ["SNOWFLAKE_ACCOUNT"],
        "user": os.environ["SNOWFLAKE_USER"],
        "password": os.environ["SNOWFLAKE_PASSWORD"],
        "role": os.environ["SNOWFLAKE_ROLE"],
        "warehouse": os.environ["SNOWFLAKE_WAREHOUSE"],
        "database": os.environ["SNOWFLAKE_DATABASE"],
        "schema": os.environ.get("SNOWFLAKE_SCHEMA", "public")
    }


def ensure_init_files(app_path: Path):
    for subdir in ["", "app", "app/python"]:
        init_path = app_path / subdir / "__init__.py"
        if not init_path.exists():
            raise FileNotFoundError(
                f"Missing __init__.py in {init_path.parent}")


def load_app_modules(app_name):
    app_path = APPS_DIR / app_name
    ensure_init_files(app_path)
    session_module = importlib.import_module(
        f"apps.{app_name}.app.python.session")
    try:
        dags_module = importlib.import_module(
            f"apps.{app_name}.app.python.dags")
        dag_list = getattr(dags_module, "dags", [])
    except ModuleNotFoundError:
        dag_list = []
    return session_module.get_session, dag_list


def get_branch_env() -> str:
    return (
        os.getenv("GITHUB_REF_NAME") or
        subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True
        ).stdout.strip()
    )


def validate_env_consistency(cli_env: str, branch_env: str):
    if branch_env and branch_env != cli_env:
        print(
            f"⚠️ Environment mismatch: CLI says '{cli_env}', but branch is '{branch_env}'")


def parse_cli_args():

    valid_apps = sorted([p.name for p in APPS_DIR.iterdir() if p.is_dir()])
    valid_envs = ["dev", "qa", "prod"]
    parser = argparse.ArgumentParser(description="Deploy Snowpark app")
    parser.add_argument("--app", required=True)
    parser.add_argument("--env", required=True, choices=valid_envs)
    parser.add_argument("--skip-dag", action="store_true")
    parser.add_argument("--include-manual-procs", action="store_true")
    parser.add_argument("--tags", nargs="*", default=None)
    parser.add_argument(
        "--verbosity",
        choices=["summary", "verbose"],
        default="verbose",
        help="Control output verbosity: 'verbose' shows full logs, 'summary' shows final deployment summary only"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Simulate deployment without executing Snowflake commands")
    parser.add_argument("--branch-env", default=None,
                        help="(Internal) Environment inferred from branch name")

    args = parser.parse_args()

    # set branch_env based on current branch (if the branch is dev then shouldn't the environment be the same?)
    args.branch_env = get_branch_env()
    validate_env_consistency(args.env, args.branch_env)

    # env_tag_defaults = {  <-- moved to be a global vonstant (see top)
    #     "dev": ["core", "experimental", "diagnostic"],
    #     "qa": ["core", "diagnostic"],
    #     "prod": ["core", "!experimental", "!diagnostic"]
    # }

    # if not args.tags:
    #     args.tags = env_tag_defaults.get(args.env, [])
    #     print(
    #         f"🧠 No tags provided. Using default tags for '{args.env}': {', '.join(args.tags)}")

    if args.app not in valid_apps:
        suggestion = next((a for a in valid_apps if a.lower()
                          == args.app.lower()), None)
        if suggestion:
            print(f"⚠️ Did you mean: '{suggestion}'?")
        print(
            f"❌ Invalid app name: '{args.app}'. Available apps: {', '.join(valid_apps)}")
        sys.exit(1)

    if not args.tags:
        args.tags = [tag.strip().lower() for tag in TAG_SETS.get(args.env, [])]
        print(
            f"🧠 No tags provided via CLI. Using normalized default tags from tag_registry.py for '{args.env}': {', '.join(args.tags)}")

    return args


def validate_env_vars(required_vars):
    missing = [v for v in required_vars if not os.environ.get(v)]
    if missing:
        raise EnvironmentError(
            f"Missing required env vars: {', '.join(missing)}")


def print_env_summary(required_vars):
    print("\n🔗 Using Snowflake connection:")
    for var in required_vars:
        val = "***" if "PASSWORD" in var else os.environ[var]
        print(f"{var}: {val}")
    print()


def run_command(command, description):
    print(f"🚀 {description}...")
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Error during {description}:\n{result.stderr}")
        raise RuntimeError(f"{description} failed")
    else:
        print(f"✅ {description} succeeded\n{result.stdout}")


def inject_shared_modules(app_path: Path):
    # Thnis fn copies a shared registry.py file into a specific location inside an app structure.
    shared_registry = Path("common/registry.py")
    target_path = app_path / "app/common/registry.py"
    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(shared_registry, target_path)
    print(f"🔗 Injected shared registry.py into {target_path}")


def zip_source_code(source_dir: Path, zip_name: str = "app.zip", verbosity: str = "verbose") -> Path:
    print(
        f"📦 zip_source_code Zipping source code from: {source_dir} (excluding __pycache__, .pyc, .pyo)")
    zip_path = source_dir / zip_name
    for artifact in ["app.zip", "dependencies.zip"]:
        artifact_path = source_dir / artifact
        if artifact_path.exists():
            artifact_path.unlink()
            if verbosity == "verbose":
                print(f"🧹 Removed old artifact: {artifact_path.name}")

    app_dir = source_dir / "app"
    if not app_dir.exists():
        raise FileNotFoundError(f"Missing app directory: {app_dir}")

    def should_include(file_path: Path) -> bool:
        return not ("__pycache__" in file_path.parts or file_path.suffix in [".pyc", ".pyo"])

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file_path in app_dir.rglob("*"):
            if file_path.is_file() and should_include(file_path):
                zipf.write(file_path, file_path.relative_to(source_dir))

    print(f"✅ Created zip at {zip_path}")
    if verbosity == "verbose":
        with zipfile.ZipFile(zip_path, "r") as zipf:
            print("📦 Contents of zip:")
            for name in sorted(zipf.namelist()):
                print(f"  - {name}")
    vprint(f"end of zip_source_code: {zip_path}", verbosity)
    return zip_path


def is_tag_allowed(proc_tags: list[str], env_tags: list[str]) -> bool:
    if not proc_tags:
        return True  # No tags means always allowed

    allowed = set(t for t in env_tags if not t.startswith("!"))
    blocked = set(t[1:] for t in env_tags if t.startswith("!"))

    return any(tag in allowed for tag in proc_tags) and not any(tag in blocked for tag in proc_tags)


# ------------------------------------------- Class testing ProcRegistrar


def load_snowflake_yml(app_path: Path):
    yml_path = app_path / "snowflake.yml"
    if not yml_path.exists():
        raise FileNotFoundError(f"Missing snowflake.yml at {yml_path}")
    with open(yml_path, "r") as f:
        return yaml.safe_load(f)


# print("Testing ProcRegistrar class...")
# args = parse_cli_args()
# app_name = args.app
# app_path = APPS_DIR / app_name

# registrar = ProcRegistrar(
#     app_path=app_path,
#     verbose=args.verbosity == "verbose",
#     dry_run=args.dry_run
# )

# registrar.load_declarative_procs()
# # Ensure app/python is importable as 'app.python'
# sys.path.insert(0, str((APPS_DIR / app_name).resolve()))

# registrar.validate_handlers()  # This will print validation results
# registrar.validate_signatures()
# registrar.validate_returns()
# registrar.summarize_validation()
# validated_declarative_procs = registrar.validated_procs  # ← new accessor


# if registrar.verbose and not registrar.dry_run:
#     registrar.emit_final_summary()


# config = load_snowflake_yml(app_path)
# declared_names = [e["identifier"]["name"] for e in config.get(
#     "entities", {}).values() if e.get("type") == "procedure"]
# print(f"📜 snowflake.yml loaded. Declarative procedures: {declared_names}")

# print("Testing completed.")


def build_markdown_summary(summary_artifact, tag_validation_structured, excluded_procs):
    lines = [
        f"## {summary_artifact['summary_title']}",
        f"**App:** `{summary_artifact['app']}`",
        f"**Environment:** `{summary_artifact['env']}`",
        f"**Tags:** {', '.join(summary_artifact['tags'])}",
        "",
        summary_artifact["tag_validation"],
        "",
        f"**Changed Files:** {', '.join(summary_artifact['changed_files']) or '—'}",
        f"**Procedures:** {summary_artifact['total_procedures']}",
        f"**DAGs:** {summary_artifact['total_dags']}",
        f"**Dry Run:** `{summary_artifact['dry_run']}`",
        f"**Duration:** `{summary_artifact['duration_seconds']}s`",
        f"**Timestamp:** `{summary_artifact['timestamp']}`",
        "",
        f"**Procedures Excluded Due to Tags:** {len(excluded_procs)}",
        f"**Valid Tags Used:** {', '.join(tag_validation_structured['valid']) or 'None'}",
        f"**Invalid Tags Supplied:** {', '.join(t[0] for t in tag_validation_structured['invalid']) or 'None'}"

    ]
    return "\n".join(lines)


def write_github_output(line: str):
    """
    Safely writes a line to the GitHub Actions output file if available.

    This function checks for the presence of the GITHUB_OUTPUT environment variable,
    which is automatically set by GitHub Actions when using `echo "name=value" >> $GITHUB_OUTPUT`.
    If running locally (outside CI), the variable won't exist, and this function will silently skip.

    Args:
        line (str): The line to write, typically in the format "key=value".
    """
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        # Append the line to the GitHub output file for downstream steps
        with open(path, "a") as f:
            f.write(line + "\n")


def build_manual_proc_narration(manual_procs, changed_files, dry_run=True):
    lines = [
        "\n### 🧪 Manual Procedure Deployment Summary",
        "| Name | Status | Reason |",
        "|------|--------|--------|"
    ]

    for proc in manual_procs:
        name = proc.get("name", "—")
        handler = proc.get("handler", "—")
        # Optional: attach this during registration
        source_file = proc.get("source_file", "")
        valid = proc.get("status") == "valid"
        excluded = proc.get("excluded", False)
        simulated = dry_run

        if excluded:
            lines.append(
                f"| {name} | ❌ Excluded | {proc.get('exclusion_reason', 'Validation failed')} |")
        elif source_file and source_file not in changed_files:
            lines.append(f"| {name} | 🚫 Skipped | No relevant code changes |")
        elif simulated:
            lines.append(f"| {name} | 🧪 Simulated | Dry-run only |")
        else:
            lines.append(f"| {name} | ✅ Deployed | Live deployment |")

    return "\n".join(lines)


def main():

    # Define helper fiunctions for main() which are not intended for re-use elsewere

    def build_procedure_table(procs):
        lines = [
            "\n### Registered Procedures",
            "| Name | Source | Handler | Returns | Status |",
            "|------|--------|---------|---------|--------|"
        ]
        for proc in procs:
            name = escape_md(proc.get("name", "—"))
            source = escape_md(proc.get("source", "—"))
            handler = escape_md(proc.get("handler", "—"))
            returns = escape_md(proc.get("return_type", "—"))
            status = escape_md(proc.get("status", "—"))
            lines.append(
                f"| {name} | {source} | {handler} | {returns} | {status} |")

        return "\n".join(lines)

    def build_excluded_procs_list(excluded_procs):
        if not excluded_procs:
            return "\n### 🚫 Excluded Procedures\n- None\n"

        lines = ["\n### 🚫 Excluded Procedures"]
        for proc in excluded_procs:
            name = escape_md(proc.get("name", "unknown"))
            tags = proc.get("tags", [])
            tag_str = ", ".join(escape_md(tag)
                                for tag in tags) if tags else "None"
            lines.append(f"- `{name}` excluded due to tags: `{tag_str}`")
        return "\n".join(lines)

    def register_exclusion(proc, reason):
        proc["status"] = "excluded"
        proc["reason"] = reason
        return proc

    def validate_cli_version(min_required="3.0.0"):
        import subprocess
        import re

        def version_tuple(v):
            return tuple(map(int, v.split(".")))

        try:
            result = subprocess.run(
                ["snow", "--help"], capture_output=True, text=True)
            first_line = result.stdout.splitlines()[0]
            match = re.search(r"\[v(\d +\.\d +\.\d+)\]", first_line)
            if match:
                current_version = match.group(1)
                print(f"🧠 Snowflake CLI version detected: {current_version}")
                if version_tuple(current_version) < version_tuple(min_required):
                    print(
                        f"❌ CLI version {current_version} is below required minimum {min_required}.")
                    return False
                print(
                    f"✅ CLI version {current_version} meets minimum requirement {min_required}.")
                return True
            else:
                print("⚠️ CLI version not found in help output. Trying pip fallback...")

        except Exception as e:
            print(f"⚠️ Error running snow --help: {e}. Trying pip fallback...")

        # Fallback to pip show
        try:
            result = subprocess.run(
                ["pip", "show", "snowflake-cli-labs"], capture_output=True, text=True)
            for line in result.stdout.splitlines():
                if line.startswith("Version:"):
                    current_version = line.split(":")[1].strip()
                    print(f"🧠 Snowflake CLI version (pip): {current_version}")
                    if version_tuple(current_version) < version_tuple(min_required):
                        print(
                            f"❌ CLI version {current_version} is below required minimum {min_required}.")
                        return False
                    print(
                        f"✅ CLI version {current_version} meets minimum requirement {min_required}.")
                    return True
            print("❌ Could not find CLI version via pip.")
            return False

        except Exception as e:
            print(f"❌ Error checking CLI version via pip: {e}")
            return False

    def build_tag_coverage_table(included_procs, excluded_procs):
        from collections import Counter

        def extract_tags(procs):
            return [tag for proc in procs for tag in proc.get("tags", [])]

        included_counts = Counter(extract_tags(included_procs))
        excluded_counts = Counter(extract_tags(excluded_procs))
        all_tags = sorted(set(included_counts) | set(excluded_counts))

        lines = ["\n### 🏷️ Tag Coverage", "| Tag | Included | Excluded |",
                 "|------|----------|----------|"]
        for tag in all_tags:
            included = included_counts.get(tag, 0)
            excluded = excluded_counts.get(tag, 0)
            lines.append(f"| {tag} | {included} | {excluded} |")
        return "\n".join(lines)

    def tag_coverage_dict(included_procs, excluded_procs):
        from collections import Counter

        def extract_tags(procs):
            return [tag for proc in procs for tag in proc.get("tags", [])]

        included_counts = Counter(extract_tags(included_procs))
        excluded_counts = Counter(extract_tags(excluded_procs))
        all_tags = sorted(set(included_counts) | set(excluded_counts))

        return {
            tag: {
                "included": included_counts.get(tag, 0),
                "excluded": excluded_counts.get(tag, 0)
            }
            for tag in all_tags
        }

    def build_environment_context_block():
        import platform
        import sys
        import shutil

        python_version = platform.python_version()
        python_exec = sys.executable
        snow_cli_path = shutil.which("snow")

        lines = [
            "\n### 🧠 Environment Context",
            f"- Python Version: `{python_version}`",
            f"- Python Executable: `{python_exec}`",
            f"- Snow CLI Path: `{snow_cli_path or 'Not found'}`"
        ]
        return "\n".join(lines)

    def load_sidecar_tags(app_path):
        # This tags "sidecar" is just a json file which has the tags for procs that get declarative (auto) deployed from snowflake.yml.
        # This approach is temporary as we learned that v2 does not support metadata such as tags (or description/other) in the snowflake.yml.
        tags_path = app_path / "tags.json"
        default_tags = {"procedures": {}, "functions": {}, "dags": {}}

        if not tags_path.exists():
            print(
                f"⚠️ No tags.json found at {tags_path}. Auto procedures, functions, and DAGs will not be tagged.")
            return default_tags

        try:
            with open(tags_path) as f:
                sidecar_tags = json.load(f)
            # Ensure all expected keys exist
            for key in default_tags:
                sidecar_tags.setdefault(key, {})
            return sidecar_tags
        except Exception as e:
            print(f"❌ Failed to load tags.json: {e}")
            return default_tags

    def validate_sidecar_tag_coverage(procs, sidecar_tags, entity_type="procedures"):
        tag_map = sidecar_tags.get(entity_type, {})
        missing = []

        for proc in procs:
            name = proc.get("name")
            tags = tag_map.get(name)

            if not tags or not isinstance(tags, list) or all(t.strip() == "" for t in tags):
                missing.append(name)

        if missing:
            print(
                f"⚠️ {len(missing)} {entity_type} missing or empty tag mappings in tags.json:")
            for name in missing:
                print(f"  - {name}")
        else:
            print(f"✅ All {entity_type} have valid tag mappings in tags.json.")

    def build_auto_proc_tag_table(procs):
        lines = [
            "\n### 🏷️ Auto Procedure Tags",
            "| Procedure Name | Tags |",
            "|----------------|------|"
        ]
        for proc in procs:
            name = proc.get("name", "—")
            tags = ", ".join(proc.get("tags", [])) or "—"
            lines.append(f"| {name} | {tags} |")
        return "\n".join(lines)

    def write_github_output(line: str):
        """
        Safely writes a line to the GitHub Actions output file if available.

        This is used to pass data between workflow steps in GitHub Actions.
        Locally, GITHUB_OUTPUT is not set, so this function silently skips.

        Args:
            line (str): The line to write, typically in the format "key=value".
        """
        path = os.environ.get("GITHUB_OUTPUT")
        if path:
            with open(path, "a") as f:
                f.write(line + "\n")

    def enrich_manual_proc(proc, verbosity):
        """
        Enriches a validated manual procedure with fallback fields for summary rendering.

        - Ensures 'handler' and 'returns' fields are present for markdown summary blocks.
        - Emits verbose narration confirming handler resolution and signature match.
        - Used during dry-run or deploy to maintain parity with declarative procedure narration.

        Args:
            proc (dict): The manual procedure dictionary to enrich.
            verbosity (str): Verbosity level; emits narration if set to 'verbose'.
        """
        proc["handler"] = proc.get("handler", "—")
        proc["returns"] = proc.get("returns", "—")
        if verbosity == "verbose":
            print(f"✅ {proc['name']} resolved handler: {proc['handler']}")
            print(
                f"✅ {proc['name']} matches expected signature: {proc['params']}")

    def _git_commit_exists(commit: str) -> bool:
        """Return True if the given commit/ref exists locally as a commit object."""
        if not commit:
            return False
        c = commit.strip().strip('"').strip("'")
        try:
            subprocess.run(
                ["git", "rev-parse", "--verify", f"{c}^{{commit}}"],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except Exception:
            return False

    def _sanitize_or_fallback_commit(raw_commit: str, fallback: str = "HEAD") -> str:
        """
        Normalize a raw commit string (strip surrounding quotes) and fall back to `fallback`
        if the commit is not present locally.
        """
        if not raw_commit:
            return fallback
        commit = raw_commit.strip().strip('"').strip("'")
        if _git_commit_exists(commit):
            return commit
        print(
            f"⚠️ Commit {commit!r} not available locally — falling back to {fallback}")
        return fallback

        # Step 0:  Validate CLI version before anything else
        if not validate_cli_version(min_required="3.0.0"):
            raise RuntimeError(
                "Snowflake CLI version is too old. Please upgrade to 3.0.0 or later.")

        # Step 1: Parse CLI arguments and initialize context
    args = parse_cli_args()
    app_name = args.app
    env_name = args.env
    verbosity = args.verbosity
    dry_run = args.dry_run
    app_path = APPS_DIR / app_name
    # tags = TAG_SETS.get(env_name, [])
    tags = args.tags  # These are the tags the user actually passed in
    tag_check = validate_tags_for_env(env_name, tags)
    print(tag_check["narration"])  # or emit to Markdown/JSON summary
    # Save this tag info so it can leter be inserted into summary_artifact in step 12 (summary)
    tag_validation_narration = tag_check["narration"]
    tag_validation_structured = {
        "valid": tag_check["valid"],
        "invalid": tag_check["invalid"]
    }

    # Commit info context needed to determine if code or config for manual proc has changed and so needs to be deployed
    # previous_commit = os.getenv("previous_commit") or subprocess.check_output([
    #     "git", "rev-parse", "HEAD~1"]).decode().strip()
    # current_commit = os.getenv("current_commit") or subprocess.check_output([
    #     "git", "rev-parse", "HEAD"]).decode().strip()
    # previous_commit = _sanitize_or_fallback_commit(os.environ.get(
    #     "PREV_COMMIT", "") or previous_commit if 'previous_commit' in globals() else "")

    # current_commit = _sanitize_or_fallback_commit(os.environ.get(
    #     "CURR_COMMIT", "") or current_commit if 'current_commit' in globals() else "")

    # compute raw values (prefer CI envs, else local rev-parse)
    raw_prev = (
        os.getenv("PREV_COMMIT")
        or os.getenv("previous_commit")
        or os.getenv("GITHUB_PREV_COMMIT")
        or ""
    )
    raw_curr = (
        os.getenv("CURR_COMMIT")
        or os.getenv("current_commit")
        or os.getenv("GITHUB_SHA")
        or ""
    )
    # Strip accidental surrounding quotes immediately
    raw_prev = raw_prev.strip().strip('"').strip("'")
    raw_curr = raw_curr.strip().strip('"').strip("'")

    # compute raw values (prefer CI envs, else local rev-parse)
    if not raw_prev:
        try:
            raw_prev = subprocess.check_output(
                ["git", "rev-parse", "HEAD~1"]).decode().strip()
        except Exception:
            raw_prev = ""

    if not raw_curr:
        try:
            raw_curr = subprocess.check_output(
                ["git", "rev-parse", "HEAD"]).decode().strip()
        except Exception:
            raw_curr = ""

    # Use HEAD~1 as previous-fallback when available, otherwise HEAD
    prev_fallback = "HEAD~1" if _git_commit_exists("HEAD~1") else "HEAD"
    previous_commit = _sanitize_or_fallback_commit(
        raw_prev, fallback=prev_fallback)
    current_commit = _sanitize_or_fallback_commit(raw_curr, fallback="HEAD")

    print(
        f"🔍 Using commits: previous={previous_commit!r}, current={current_commit!r}", file=sys.stderr)

    # Step 1.1: Ensure app/python is importable as 'app.python'
    # sys.path.insert(0, str((APPS_DIR / app_name).resolve()))
    sys.path.insert(0, str((APPS_DIR / app_name / "app").resolve()))

    # Step 2: 🔍 Validate declarative procedures via ProcRegistrar
    # Step 2.1: Ensure app/python is importable as 'app.python'
    sys.path.insert(0, str((APPS_DIR / app_name).resolve()))

    from app.common.validation import resolve_handler, validate_signature, validate_return_type
    sidecar_tags = load_sidecar_tags(app_path)
    # Step 2.2: Perform validations
    registrar = ProcRegistrar(
        app_path=app_path,
        verbose=verbosity == "verbose",
        dry_run=dry_run
    )
    registrar.load_declarative_procs()
    registrar.validate_handlers()
    registrar.validate_signatures()
    registrar.validate_returns()
    registrar.summarize_validation()

    # Step 3: Filter declarative procs by tag relevance defined for the environment
    #  This version of step 3 is for use when snowflake.yml version supports metadata. The sidecar solution is just a stop-gap.
    # validated_declarative_procs = [
    #     proc for proc in registrar.validated_procs
    #     if is_tag_allowed(proc.get("tags", []), tags)
    # ]
    # for proc in validated_declarative_procs:
    #     proc["source"] = "auto"

    # excluded_declarative = [
    #     register_exclusion(proc, "Tag not allowed in environment")
    #     for proc in registrar.validated_procs
    #     if not is_tag_allowed(proc.get("tags", []), tags)
    # ]

    # if verbosity == "verbose" and excluded_declarative:
    #     print(
    #         f"🚫 {len(excluded_declarative)} declarative procedures excluded due to tag filtering for env '{env_name}'")

    # This replaces the old metadata-based tagging and ensures every auto proc is tagged from the sidecar.
    validated_declarative_procs = []
    excluded_declarative = []

    for proc in registrar.validated_procs:
        proc_name = proc.get("name")
        proc["tags"] = sidecar_tags.get("procedures", {}).get(proc_name, [])
        if is_tag_allowed(proc["tags"], tags):
            proc["source"] = "auto"
            proc["status"] = "valid"
            validated_declarative_procs.append(proc)
        else:
            excluded_declarative.append(register_exclusion(
                proc, "Tag not allowed in environment"))
        if verbosity == "verbose":
            print(f"✅ Injected tags for {proc_name}: {proc['tags']}")

    # Narrate procedures that aren’t tagged in tags.json
    validate_sidecar_tag_coverage(
        registrar.validated_procs, sidecar_tags, "procedures")

    # Step 4: Detect changed files and narrate context
    start_time = time.time()
    # tags = TAG_SETS.get(env_name, [])
    # manual_registered = []
    manual_registered: list[dict] = []

    # validate_env_consistency(env_name)
    # Default to empty list; in real use, populate with actual changed files if available
    changed_apps = []
    changed_files = get_changed_files_for_app(
        app_name, previous_commit, current_commit)

    print(f"🔍 Changed files detected for app '{app_name}': {changed_files}")

    print(
        f"🧭 Verbosity: {verbosity} — detailed logs {'enabled' if verbosity == 'verbose' else 'suppressed'}")
    print(f"🧠 Using tags for env '{env_name}': {tags}")

    print(
        f"\n🚀 Starting deployment for app: {app_name} in environment: {env_name}")

    # Step 5: Load app modules and validate environment variables
    get_session, dag_list = load_app_modules(app_name)

    required_vars = [
        "SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_PASSWORD",
        "SNOWFLAKE_ROLE", "SNOWFLAKE_WAREHOUSE", "SNOWFLAKE_DATABASE"
    ]
    validate_env_vars(required_vars)
    creds = get_snowflake_credentials()
    print_env_summary(required_vars)

    # Step 6: Initialize Snowflake session and root object
    account, user, password, role = creds["account"], creds["user"], creds["password"], creds["role"]
    warehouse, database, schema = creds["warehouse"], creds["database"], creds["schema"]

    try:
        session = get_session()
        session.sql(f"USE DATABASE {database}").collect()
        root = Root(session)
    except Exception as e:
        print(f"❌ Failed to initialize Snowflake session: {e}")
        sys.exit(1)

    # Step 7: Build Snowpark project and inject shared modules
    build_cmd = [
        "snow", "snowpark", "build",
        "--project", str(APPS_DIR / app_name),
        "--temporary-connection",
        "--account", account,
        "--user", user,
        "--role", role,
        "--warehouse", warehouse,
        "--database", database,
        "--schema", schema,
        "--allow-shared-libraries"
    ]
    run_command(build_cmd, f"Building Snowpark project for app: {app_name}")
    inject_shared_modules(app_path)

    # Step 8: Zip source code and upload to stage
    stage_name = f"{env_name}_deployment"
    stage_target = f"@{stage_name}/apps/{app_name}"
    zip_file = zip_source_code(
        app_path, zip_name="app.zip", verbosity=verbosity)
    # print(f"📦 Zipping source code in: {app_path}") # redundant
    # print(f"📦 Created zip: {zip_file}") # redundant

    if not args.dry_run:
        vprint(f"📂 Files on stage @dev_deployment before upload:", verbosity)
        session.file.put(str(zip_file), stage_target,
                         overwrite=True, source_compression="NONE")
        # files = session.sql(
        #     "LIST @dev_deployment/apps/DE_PROJECT_1/").collect()
        files = session.sql(f"LIST {stage_target}/").collect()

        vprint(f"📂 Files on stage @dev_deployment  after upload:", verbosity)
        for f in files:
            vprint(f"📦 {f['name']}", verbosity)

    else:

        vprint("🧪 Dry-run: Skipping actual execution of session.file.put", verbosity)

    print(f"📦 Uploaded app.zip to {stage_target}")
    vprint(f"📦 Stage target: {stage_target}", verbosity)

    # Step 9: Deploy Snowpark App
    deploy_cmd = [
        "snow", "snowpark", "deploy", "--replace", "--temporary-connection",
        "--project", str(APPS_DIR / app_name),
        "--account", account,
        "--user", user,
        "--role", role,
        "--warehouse", warehouse,
        "--database", database,
        "--schema", schema
    ]
    # run_command(deploy_cmd, f"Deploying Snowpark project for app: {app_name}")
    try:
        run_command(
            deploy_cmd, f"Deploying Snowpark project for app: {app_name}")

    except Exception as e:
        print(f"❌ Snowpark deploy failed: {e}")
        sys.exit(1)

    print("⚠️ Note: Declarative procedures were deployed live. Dry-run mode does not simulate Snowpark deploy.")

    # Step 10: Register manual procedures and apply tag filtering
# ...existing code...
    # Step 10: Register manual procedures and apply tag filtering
    if args.include_manual_procs:
        manager = DeployManager(
            session=session,
            app_name=app_name,
            stage_name=stage_name,
            changed_files=changed_files,
            include_tags=tags,
            dry_run=dry_run,
            verbosity=verbosity
        )

        # Load manual procs (may be None)
        raw_manual_procs = manager.register_manual() or []

        manual_registered = []
        excluded_manual = []

        for proc in raw_manual_procs:
            # If register_manual_procs already performed registration it returns
            # a minimal summary dict (status == "registered" or "dry_run").
            # Accept those directly to avoid re-resolving handlers that no longer exist
            # on the returned shape.
            if proc.get("status") in ("registered", "dry_run"):
                proc["tags"] = [t.lower() for t in proc.get("tags", [])]
                proc.setdefault("kind", "procedure")
                proc.setdefault("source", "manual")
                # Ensure we have a handler value for summaries (best-effort)
                proc.setdefault(
                    "handler", f"app.python.manual_procs.{proc.get('name','')}")
                manual_registered.append(proc)
                continue

            # Otherwise treat proc as a raw definition and run validations/enrichment
            proc["tags"] = [t.lower() for t in proc.get("tags", [])]

            # Tag filtering
            if not is_tag_allowed(proc.get("tags", []), tags):
                excluded_manual.append(register_exclusion(
                    proc, "Tag not allowed in environment"))
                continue

            # Resolve handler (returns truthy on success)
            if not resolve_handler(proc):
                excluded_manual.append(register_exclusion(
                    proc, "Handler resolution failed"))
                continue

            # Signature and return-type validation (expected params may be empty list)
            expected_params = proc.get("expected_params", [])
            if not validate_signature(proc, expected_params):
                excluded_manual.append(
                    register_exclusion(proc, "Signature mismatch"))
                continue

            if not validate_return_type(proc):
                excluded_manual.append(register_exclusion(
                    proc, "Return type mismatch"))
                continue

            # Enrich for summary output and mark as valid
            enrich_manual_proc(proc, verbosity)
            proc["status"] = "valid"
            manual_registered.append(proc)

        if verbosity == "verbose" and excluded_manual:
            print(
                f"🚫 {len(excluded_manual)} manual procedures excluded due to validation or tag filtering for env '{env_name}'")

        if verbosity == "verbose":
            print(build_manual_proc_narration(manual_registered +
                  excluded_manual, changed_files, dry_run=dry_run))

        manager.emit_summary()
    else:
        print("⏭️ Manual procedure registration skipped via --include-manual-procs flag.")

    # Step 11: Deploy Dags
    # ✅ Unified procedure list
    all_procs = validated_declarative_procs + manual_registered

    if len(all_procs) == 0 and (dry_run or verbosity == "verbose"):
        print("⚠️ No procedures were registered or simulated.")

    target_db = database
    schema_name = schema
    snowflake_schema = root.databases[target_db].schemas[schema_name]

    if not args.skip_dag:
        if dag_list:
            vprint(f"📡 DAGs detected: {len(dag_list)}", verbosity)
            from snowflake.snowpark.stored_procedure import CreateMode  # type: ignore
            dag_op = DAGOperation(snowflake_schema)

            for dag in dag_list:
                try:
                    vprint(
                        f"📡 Deploying DAG handler: {dag.__name__}", verbosity)
                    # dag_op.deploy(dag, CreateMode.or_replace)
                    if not dry_run:
                        dag_op.deploy(dag, CreateMode.or_replace)
                        print(
                            f"✅ DAG '{dag.__name__}' deployed for app: {args.app}")
                    else:
                        print(
                            f"🧪 Dry-run: Skipping DAG deployment for '{dag.__name__}'")

                    # print(
                    #     f"✅ DAG '{dag.__name__}' deployed for app: {args.app}")
                except Exception as e:
                    print(f"❌ DAG '{dag.__name__}' deployment failed: {e}")
                    sys.exit(1)
        else:
            print(
                f"⚠️ No DAGs defined for app '{app_name}'. Skipping DAG deployment.")

    else:
        print(f"⏭️ DAG deployment skipped via CLI flag.")

    print(
        f"\n✅ Deployment completed successfully for app '{app_name}' in environment '{env_name}'.")


#  Step 12: Summary and Validation

    # Escape Markdown-sensitive characters for safe table rendering

    def escape_md(value):
        return str(value).replace("|", "\\|").replace("`", "\\`")

    # Compute summary metadata
    duration = round(time.time() - start_time, 2)
    tag_summary = ", ".join(args.tags) if args.tags else "None"
    summary_time = datetime.now(pytz.timezone(
        "America/Vancouver")).strftime("%Y-%m-%d %H:%M %Z")
    auto_count = len(validated_declarative_procs)
    manual_simulated = (
        sum(1 for proc in manual_registered if proc.get("status") == "dry_run")
        if dry_run else None
    )
    excluded_procs = excluded_declarative + excluded_manual

    if not validated_declarative_procs and not manual_registered:
        print(f"⏭️ All procedures skipped for {app_name} due to tag mismatch.")

    # Emit human-readable summary to console
    if dry_run and verbosity in ["summary", "verbose"]:
        print(
            f"🧪 Dry-Run Summary\n"
            f"  App: {app_name}\n"
            f"  Environment: {env_name}\n"
            f"  Stage: {stage_name}\n"
            f"  Tags Used: {tag_summary}\n"
            f"  Auto Procedures: Not simulated — {auto_count} procs were deployed live via Snowpark\n"
            f"  Manual Procedures Simulated: {manual_simulated}\n"
            f"  Total Procedures Simulated: {manual_simulated} (manual only)\n"
            f"  DAGs: Skipped\n"
            f"  Artifacts Uploaded: Simulated\n"
            f"🕒 Dry-run finished at: {summary_time}\n"
            f"⏱️ Total dry-run duration: {duration:.2f} seconds\n"
            f"✅ Dry-run completed. Manual and custom procedures were simulated only. Declarative procedures were deployed live via Snowpark."
        )
    else:
        manual_count = len(manual_registered)
        print(
            f"\n📦 Deployment Summary\n"
            f"  App: {app_name}\n"
            f"  Environment: {env_name}\n"
            f"  Stage: {stage_name}\n"
            f"  Tags Used: {tag_summary}\n"
            f"  Auto Procedures Registered: {auto_count}\n"
            f"  Manual Procedures Registered: {manual_count if manual_count > 0 else 'Skipped'}\n"
            f"  Total Procedures Registered: {len(all_procs)}\n"
            f"  DAGs: {'Deployed' if dag_list else 'None found'}\n"
            f"🕒 Deployment finished at: {summary_time}\n"
            f"⏱️ Total duration: {duration:.2f} seconds\n"
            f"✅ Deployment completed successfully for app '{app_name}' in environment '{env_name}'."
        )

    # Emit tabular summary of registered procedures to console
    print("\n📊 Registered Procedure Summary:\n")
    header = f"{'Name':<20} {'Source':<12} {'Handler':<50} {'Returns':<10} {'Status':<10}"
    print(header)
    print("-" * len(header))
    for proc in all_procs:
        name = proc.get("name", "—")
        source = proc.get("source", "—")
        handler = proc.get("handler", "—")
        returns = proc.get("return_type", "—")
        status = proc.get("status", "—")
        print(f"{name:<20} {source:<12} {handler:<50} {returns:<10} {status:<10}")

    # print(build_procedure_table(all_procs))
    # Already emitted to Markdown file—no need to duplicate here

    # 🔹 Prepare JSON summary artifact for CI, Slack, GitHub, etc.
    summary_title = "🧪 Dry-Run Summary" if dry_run else "✅ Deployment Summary"
    summary_artifact = {
        "app": app_name,
        "env": env_name,
        "changed_files": changed_files,
        "stage": stage_name,
        "tags": args.tags,
        "tag_validation": tag_validation_narration,
        "tags_validated": tag_validation_structured,
        "tag_coverage": tag_coverage_dict(validated_declarative_procs + manual_registered, excluded_procs),
        "sidecar_tags": sidecar_tags,
        "dry_run": dry_run,
        "summary_title": summary_title,
        "status": "dry_run" if dry_run else "deployed",
        "verbosity": verbosity,
        "duration_seconds": duration,
        "timestamp": summary_time,
        "auto_count": auto_count,
        "manual_count": len(manual_registered),
        "manual_simulated": manual_simulated,
        "total_procedures": len(all_procs),
        "total_dags": len(dag_list) if dag_list else 0,
        "dags": [dag.__name__ for dag in dag_list] if dag_list else [],
        "auto_proc_tags": {
            proc["name"]: proc.get("tags", [])
            for proc in validated_declarative_procs
        },
        "dag_tags": {
            dag.__name__: getattr(dag, "tags", [])
            for dag in dag_list
        },
        #  Placeholder to add later
        # "function_tags": {
        #     func["name"]: func.get("tags", [])
        #     for func in validated_functions  # if you have this list
        # },
        "procedures": [
            {
                "name": proc.get("name", "—"),
                "source": proc.get("source", "—"),
                "handler": proc.get("handler", "—"),
                "returns": proc.get("return_type", "—"),
                "status": proc.get("status", "—")
            }
            for proc in all_procs
        ],
        "excluded_procs": [
            {
                "name": proc.get("name", "unknown"),
                "tags": proc.get("tags", []),
                "reason": proc.get("reason", "Not specified")
            }
            for proc in excluded_procs
        ]

    }

    # 🔹 Optional Markdown summary block for Slack, GitHub, etc.

    markdown_summary = build_markdown_summary(
        summary_artifact,
        tag_validation_structured,
        excluded_procs
    )

    # 🔹 Emit JSON artifact to GitHub Actions output
    # json_output = json.dumps(summary_artifact).replace("\n", "\\n")
    # with open(os.environ["GITHUB_OUTPUT"], "a") as f:
    #     f.write(f"deploy_summary={json_output}\n")

    # Emit summary artifact to GitHub Actions output (if available)
    json_output = json.dumps(summary_artifact).replace("\n", "\\n")
    write_github_output(f"deploy_summary={json_output}")

    # 🔹 Emit JSON artifact to local file for debugging
    with open("deploy_summary.json", "w") as f:
        json.dump(summary_artifact, f, indent=2)

    # 🔸 Prepare and emit Markdown summary artifact for human-readable audit
    with open("deploy_summary.md", "w") as f:
        f.write(f"# {summary_title} — {app_name}\n")
        f.write(f"- Environment: `{env_name}`\n")
        f.write(
            f"- Changed Files: `{', '.join(changed_files) if changed_files else 'None'}`\n")
        f.write(f"- Stage: `{stage_name}`\n")
        f.write(f"- Tags: `{tag_summary}`\n")
        f.write(f"- Auto Procedures: `{auto_count}`\n")
        f.write(f"- Manual Procedures: `{len(manual_registered)}`\n")
        f.write(f"- DAGs: `{len(dag_list) if dag_list else 0}`\n")
        f.write(f"- Duration: `{duration:.2f} seconds`\n")
        f.write(f"- Timestamp: `{summary_time}`\n")

        f.write(build_procedure_table(all_procs))

        f.write("\n### 🚫 Excluded Procedures\n")
        if excluded_procs:
            f.write("| Name | Tags | Reason |\n")
            f.write("|------|------|--------|\n")
            for proc in excluded_procs:
                name = escape_md(proc.get("name", "unknown"))
                tags = escape_md(", ".join(proc.get("tags", [])))
                reason = escape_md(proc.get("reason", "Not specified"))
                f.write(f"| {name} | {tags} | {reason} |\n")
        else:
            f.write("- None\n")
        f.write(build_tag_coverage_table(
            validated_declarative_procs + manual_registered, excluded_procs))
        f.write(build_auto_proc_tag_table(validated_declarative_procs))
        f.write(build_environment_context_block())

    # 🔸 Emit Markdown artifact to console (only in verbose mode outside CI)
    if verbosity == "verbose" and not os.getenv("CI"):
        with open("deploy_summary.md") as f:
            print(f.read())


if __name__ == "__main__":
    main()
