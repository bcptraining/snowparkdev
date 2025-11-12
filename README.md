# Snowpark App Registration Framework

## 1. Project Overview

This repository implements a Snowpark-native application registration and deployment framework for Snowflake data engineering projects. It is designed to enable robust, repeatable, and environment-aware deployment of both declarative (auto-registered) and manual (Python-based) Snowpark stored procedures, with strong support for configuration-driven workflows, schema-agnostic data handling, and CI/CD integration.

**Key goals:**
- Provide a scalable, maintainable scaffold for Snowpark-based data apps.
- Support both declarative and manual procedure registration with tagging and environment filtering.
- Enable robust reject handling and schema validation for data pipelines.
- Integrate seamlessly with CI/CD pipelines and the Snowflake CLI.
- Promote best practices for configuration, code organization, and deployment automation.

**Intended audience:**
Data engineering teams, platform engineers, and technical leads seeking a modern, extensible approach to Snowflake app development and deployment.

## 2. High-Level Architecture

This repository is organized to support modular, scalable Snowpark app development and deployment. The major components are:

- **`apps/`** — Application packages. Each app (e.g., `DE_PROJECT_1`) follows a standard scaffold, containing its own source code, configs, schemas, and manual procedure definitions.
- **`deploy/`** — Deployment tooling. Includes scripts for building, packaging, uploading, and registering both declarative and manual procedures. Key files:
  - `deploy/deploy_snowflake_app.py` — Orchestrates build, zip, deploy, and registration steps.
  - `deploy/deploy_manager.py` — Handles manual procedure registration, dry-run logic, and summary artifact creation.
  - `deploy/constants.py`, `deploy/tag_registry.py` — Canonical tag lists, environment defaults, and trigger file suffixes.
- **`common/`** — Shared helper modules, such as `common/registry.py`, for code reuse across apps.
- **`snowflake-cli/`** — Bundled CLI implementation and CI/CD workflow integration.
- **`.github/workflows/`** — GitHub Actions for automated build, test, and deploy.

**Typical flow:**
1. Build Snowpark package for the app.
2. Zip and upload to Snowflake stage.
3. Run `snow snowpark deploy` for declarative procedures.
4. Register manual procedures via `DeployManager` (with tag and environment filtering).
5. CI/CD workflows validate, summarize, and report deployment status.

This structure enables clear separation of concerns, easy extension for new apps, and robust automation for enterprise data engineering teams.

## 3. Key Features & Conventions

- **Config-driven deployments:**
  All application and schema configuration is managed via JSON files, enabling flexible, environment-specific deployments without code changes.

- **Manual and declarative procedure registration:**
  Supports both declarative (auto-registered via manifest files) and manual (Python-defined) Snowpark stored procedures. Manual procedures are registered using a standardized API and can be filtered by tags and environment.

- **Tagging and environment support:**
  Procedures and apps are tagged for environment-based filtering and deployment control. Tag normalization and validation are enforced using canonical lists in `deploy/constants.py` and `deploy/tag_registry.py`.
  → See [`tagging.md`](./docs/tagging.md) for full details.

- **Generic reject handling:**
  Data pipelines use a schema-agnostic reject table pattern, storing failed records as JSON (`VARIANT`) along with error metadata. This enables robust error auditing and simplifies onboarding of new data sources.

- **Changed-files triggering:**
  Manual procedure registration is triggered only when relevant files change, as defined by `MANUAL_PROC_TRIGGER_SUFFIXES` in `deploy/constants.py`. This optimizes CI/CD runs and avoids unnecessary redeployments.

- **Dry-run and summary artifacts:**
  The deployment system supports dry-run mode for safe testing, and always produces summary artifacts (`deploy_summary.json`, `deploy_summary.md`) for downstream CI/CD steps and auditability.

- **Coding and deployment conventions:**
  All apps follow a standard scaffold. Import paths and sys.path manipulation are handled to ensure reliable module resolution during CLI and CI runs. Tag filtering, procedure enrichment, and summary reporting follow consistent patterns across the codebase.

## 4. Deployment & CI/CD

This framework is designed for robust, automated deployment in both local and CI/CD environments.

- **How to deploy:**
  - Use the CLI or GitHub Actions to trigger builds and deployments.
  - The typical flow is: build Snowpark package → zip and upload to Snowflake stage → run `snow snowpark deploy` for declarative procedures → register manual procedures via `DeployManager`.
  - All configuration and schema files are staged automatically as part of the deployment process.
  - For rapid local iteration and testing (bypassing full CI/CD), you can use the CLI alias:
    ```
    deployapp --app DE_PROJECT_1 --env dev
    ```
    This command builds, packages, and deploys the specified app to the target environment, streamlining the development cycle.

- **CI/CD integration:**
  - GitHub Actions workflows (in [workflows](http://_vscodecontentref_/0)) automate build, test, and deploy steps.
  - The deploy scripts write summary artifacts ([deploy_summary.json](http://_vscodecontentref_/1), [deploy_summary.md](http://_vscodecontentref_/2)) for downstream CI steps and auditability.
  - Tag filtering and changed-files detection ensure only relevant procedures are deployed for each environment.
  - Environment variables such as `SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_USER`, `SNOWFLAKE_PASSWORD`, `SNOWFLAKE_ROLE`, `SNOWFLAKE_WAREHOUSE`, and `SNOWFLAKE_DATABASE` are required for deployment and are managed securely in CI.

- **Dry-run support:**
  - The deployment system supports a dry-run mode (`--dry-run`) to simulate uploads and registration without making changes to Snowflake, allowing safe validation of changes before production deployment.

## 5. Example: Adding a New App or Procedure

Follow these steps to add a new Snowpark app or register a new procedure:

1. **Scaffold a new app:**
   - Create a new directory under `apps/` following the structure of `DE_PROJECT_1`.
   - Add your source code, configuration files (`config/*.json`), and schema definitions (`schemas/*.json`).

2. **Add configs and schemas:**
   - Define your application’s configuration in JSON files under the `config/` directory.
   - Specify table schemas in the `schemas/` directory for use in validation and deployment.

3. **Register manual procedures:**
   - Implement your manual procedures in `app/python/procedures_man.py` (or `manual_procs.py`).
   - Ensure you provide a `register_manual_procs()` function that returns a list of procedure definitions, following the framework’s API.
   - Tag your procedures appropriately for environment-based filtering.

4. **Update manifests and tags:**
   - Add or update `snowflake.yml` and `tags.json` to declare your procedures and their tags for declarative registration.

5. **Deploy and test:**
   - Use the CLI alias for rapid iteration:
     ```
     deployapp app-- <YOUR_APP_NAME> --env dev
     ```
   - Or trigger a full CI/CD workflow via GitHub Actions.

This process ensures your new app or procedure is registered, tagged, and deployed in a consistent, automated manner.

For a detailed guide on defining, tagging, validating, and registering manual procedures,
see [`docs/procedure_registration.md`](./docs/procedure_registration.md).

## 6. Testing & Validation

> **Note:** This repository includes a few example tests for illustration purposes only. These tests are not comprehensive and are not currently integrated with CI/CD workflows. They are intended to demonstrate basic testing patterns for Snowpark procedures and deployment logic.

- **Unit and integration tests:**
  - Example tests are located under `snowflake-cli/tests` and other `tests/` directories.
  - Run tests using the project’s test runner (the repository uses `pytest` in CI workflows).
  - Always verify that your changes pass all tests before merging or deploying.

- **Validation scripts and outputs:**
  - Deployment scripts generate summary artifacts such as `deploy_summary.json` and `deploy_summary.md`.
  - These artifacts provide a detailed record of what was built, registered, and deployed, and are used for downstream CI/CD steps and auditability.
  - When editing deployment logic, it is recommended to run a dry-run first (`--dry-run`) and verify that the summary artifacts are produced and accurate.

- **Best practices:**
  - Use dry-run mode to safely validate changes before production deployment.
  - Review summary artifacts and logs to ensure correct procedure registration and tagging.
  - Follow coding standards and conventions as outlined in this repository for consistency and maintainability.

## 7. Contributing & Extending

> **Note:** This project is not currently open for external contributions.
> The section is included as a placeholder for future updates.
> If you have questions or feedback, please contact the maintainers directly.
