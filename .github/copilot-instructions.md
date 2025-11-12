Short, focused instructions to help an AI code agent be productive in this repository.

1. High-level architecture (what to change)
   - This repo is a Snowpark-native app registration framework. Major components:
     - `apps/` — application packages. Each app follows the scaffold used by `DE_PROJECT_1`.
     - `deploy/` — deployment tooling (see `deploy/deploy_snowflake_app.py`, `deploy/deploy_manager.py`, `deploy/orchestration/`).
     - `common/` — shared helper modules (e.g. `common/registry.py`).
     - `snowflake-cli/` — a bundled CLI implementation and CI workflows.
   - Typical flow: build snowpark package -> zip and upload to stage -> `snow snowpark deploy` -> register manual procs via `DeployManager`.

2. Key files to inspect when making changes
   - `deploy/deploy_manager.py` — manual procedure registration, dry-run behavior, and summary artifact creation (`deploy_summary.json`, `deploy_summary.md`).
   - `deploy/deploy_snowflake_app.py` — CLI parsing, environment validation, snowpack build and deploy steps, and orchestration of declarative (auto) vs manual procs.
   - `deploy/constants.py` and `deploy/tag_registry.py` — canonical tag lists and trigger filenames; use these when validating tags or checking changed-files logic.
   - `apps/<APP>/app/python/procedures_man.py` (or `manual_procs.py`) — manual procedure definitions and `register_manual_procs()` API expected by `DeployManager`.
   - `apps/<APP>/snowflake.yml` and `apps/<APP>/tags.json` — declarative procedure manifests and sidecar tags used for auto-proc tagging.

3. Conventions and patterns to follow
   - Tag normalization: tags are lower-cased and compared against `deploy/constants.VALID_TAGS`. Use `deploy/tag_registry.TAG_SETS` for environment defaults.
   - Manual procs API: `register_manual_procs(session, stage_name, app_name, include_tags, dry_run, verbosity)` returns a list of proc dicts. Each proc dict is enriched by `DeployManager` with fields: `source_file`, `source`, `tags`, `status`, `handler`, `name`.
   - Changed-files triggering: `MANUAL_PROC_TRIGGER_SUFFIXES` (in `deploy/constants.py`) lists files that cause manual registration. Use `deploy/utils/change_detection.get_changed_files_for_app()` when computing changed files.
   - Dry-run mode: `--dry-run` simulates uploads and registration; declarative Snowpark deploys are currently live even under dry-run in `deploy_snowflake_app.py`. Be cautious modifying deploy semantics.
   - Import paths: during CLI runs the code inserts `apps/<APP>/app` and repository root into `sys.path`. Prefer relative imports inside app packages and ensure `__init__.py` exists (see `load_app_modules()`).

4. CI and environment notes
   - GitHub Actions live in `.github/workflows/` (several `build_and_deploy_*.yml` files) and expect the `snow` CLI and certain environment variables: `SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_USER`, `SNOWFLAKE_PASSWORD`, `SNOWFLAKE_ROLE`, `SNOWFLAKE_WAREHOUSE`, `SNOWFLAKE_DATABASE`.
   - The CLI determines branch/environment via `GITHUB_REF_NAME` or `git rev-parse --abbrev-ref HEAD` and warns on mismatches with `--env`.
   - The deploy scripts write `deploy_summary.json` and `deploy_summary.md` for downstream CI steps. If adding outputs, append to `GITHUB_OUTPUT` when running in Actions.

5. Examples of code patterns to mirror
   - Procedure enrichment in `deploy/deploy_manager.py`: procedures are translated to summary-friendly dicts and printed with `tabulate`.
   - Tag filtering: `is_tag_allowed(proc_tags, env_tags)` in `deploy/deploy_snowflake_app.py` — follow its semantics (support for "!tag" negative filters).
   - Zipping/uploading: `zip_source_code()` excludes `__pycache__` and `.pyc` files and places `app.zip` at the app root before `session.file.put()`.

6. Editing and testing guidance for AI edits
   - When editing deployment logic, run a dry-run first (`--dry-run`) and verify `deploy_summary.json` is produced.
   - For unit-level verification, tests live under `snowflake-cli/tests` and other `tests/` folders; run them via the project's test runner if available. The repo uses pytest in CI workflows.
   - Avoid changing Snowpark deploy invocation semantics unless you also update CI workflow YAML in `.github/workflows/`.

7. What to avoid or be careful about
   - Do not assume dry-run prevents Snowpark builds/deploys — declarative deploys may be executed live.
   - Don't change tagging semantics without updating `deploy/tag_registry.py` and the tag validation logic in `deploy/utils/tag_validation.py`.
   - Be mindful of sys.path manipulation in `deploy/deploy_snowflake_app.py`; adding conflicting imports can break app module resolution.

If anything in these instructions is unclear or you'd like more examples (e.g., a sample `register_manual_procs()` implementation), tell me which area to expand and I will iterate.
