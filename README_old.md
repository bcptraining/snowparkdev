# Snowpark Native App Registration Framework

## 🚀 Overview

This repository contains a modular, extensible framework for building and deploying Snowflake Snowpark-native applications using Python. It is designed to streamline the registration of stored procedures and user-defined functions (UDFs), allowing data engineers to focus on business logic while the framework handles deployment, tagging, and CI/CD integration.

The architecture supports multiple apps housed under `/apps`, with each app maintaining its own config, schema, and procedural logic. `DE_PROJECT_1` is one example implementation.

---

## 🧠 Why This Exists

As Snowflake adoption grows, so does the need for clean, maintainable procedural logic. This framework was built to:

- Centralize procedure registration logic across multiple apps
- Support both manual and declarative (auto) deployment paths
- Enforce tagging, metadata, and validation standards
- Enable CI/CD via GitHub Actions
- Reduce boilerplate for data engineers

It’s a vehicle for scaling Snowpark-native development across teams and projects.

---

## 🧰 Key Features

- **Multi-App Support**: Each app under `/apps` can define its own procedures, config, and schema.
- **Manual Procedure Registration**: Define procedures in `manual_procs.py` and register them via `register_procs.py`.
- **Auto Procedure Support**: Declarative procedures are handled via tagging and Snowflake-native YAML configuration.
- **UDF Registration (Planned)**: UDFs defined in `functions.py` will be registered via `register_udfs.py`.
- **Config + Schema Management**: Centralized JSON-based config and schema loading via `helpers.py`.
- **Validation Layer**: Signature and return-type validation for manual procedures.
- **CI/CD Integration**: GitHub Actions detect file changes and trigger deployments.
- **Tagging System**: Procedures are tagged for filtering, environment targeting, and documentation.
  → See [`tagging.md`](./docs/tagging.md) for full details.

---

## ⚙️ Auto vs Manual Procedures

**Auto Procedures**
- Defined declaratively via `snowflake.yml`
- Registered automatically by Snowflake during deployment
- Ideal for simple, stateless logic
- Tagged and filtered via metadata

**Manual Procedures**
- Defined imperatively in Python (`manual_procs.py`)
- Registered via `register_procs.py` and validated with `validation.py`
- Ideal for complex logic, dynamic inputs, or custom registration flows
- Supports tagging, dry-run, and CI/CD integration

Manual procs give developers full control over registration and validation, while auto procs offer simplicity and speed for lightweight use cases.

---

## 👩‍💻 For Developers: How to Create a New App

If you're onboarding a new Snowpark-native app into this framework, the fastest path is to copy the existing `DE_PROJECT_1` scaffold and customize it.

### Step-by-Step: Creating a New App

1. **Copy the scaffold**:
   ```bash
   cp -r apps/DE_PROJECT_1 apps/MY_NEW_APP
   ```

2. **Rename internal references**:
   - Update any mentions of `DE_PROJECT_1` in config files, schema files, and Python modules.
   - Adjust procedure names, tags, and descriptions to reflect your new app.

3. **Define your logic**:
   - Add new procedures to `app/python/manual_procs.py`
   - Add UDFs to `app/python/functions.py` (see section below)

4. **Create config and schema files**:
   - Place them in `app/config/` and `app/schemas/`

5. **Register your procedures and UDFs**:
   - Use `register_procs.py` for procedures
   - Use `register_udfs.py` for UDFs (stubbed, see below)

6. **Commit and push**:
   - GitHub Actions will detect changes and trigger deployments

---

## 🧩 Deployable Object Types

This framework supports multiple Snowflake object types. Each has its own deployment path:

### ✅ Procedures
- Defined in `manual_procs.py`
- Registered via `register_procs.py`
- Tagged and validated

### 🧪 UDFs *(Planned Enhancement)*
- Defined in `functions.py`
- Will be registered via `register_udfs.py` (stubbed and ready)
- Requires packaging and handler resolution

### 📦 Tables, Views, Stages *(External to this framework)*
- Managed via SQL or Snowflake-native YAML
- Not currently handled by this Python framework

Future enhancements will unify UDF registration with procedure handling, allowing developers to tag, validate, and deploy UDFs using the same workflow.

---

## 📦 Deployment Notes

- Manual procedures are registered via `register_manual_procs()` in `register_procs.py`
- UDFs will be registered via `register_udfs()` in `register_udfs.py`
- Auto procedures are handled via Snowflake YAML and tagging
- Dry-run mode is supported for safe testing
- All procedures are validated before registration

---

## 📚 Documentation

- [Tagging System](./docs/tagging.md)
- [Procedure Registration](./docs/procedure_registration.md) *(coming soon)*
- [Schema Format](./schemas/schemas.json)

---

## 🧪 Testing & Validation

To ensure reliability and maintainability, the following components are testable:

- `json_to_struct_type()` — validates schema conversion from JSON
- `load_named_config()` — ensures config files are parsed correctly
- `copy_to_table()` — verifies COPY INTO logic and query tracking
- `get_copy_query_id()` — confirms query ID extraction from history

Signature and return-type validation is built into `validation.py` and runs automatically during registration.

---

## 🧭 Future Enhancements

- **UDF Registration**
  UDFs are currently defined in `functions.py`, but registration is manual. A unified workflow via `register_udfs.py` will allow tagging, validation, and CI/CD deployment—just like procedures.

- **DAG Support**
  Extend tagging and registration logic to orchestrate DAGs (e.g., chained procedures or task graphs).

- **CLI Tooling**
  Build a command-line interface for onboarding new apps, validating metadata, and triggering deployments.

- **Docstring Linter**
  Enforce consistent tagging, descriptions, and metadata in procedure and UDF definitions.

---

## 🙌 Author

Built by Cory. This repo is a massive elaboration of some simple exercises from udemy course [Snowpark: Data Engineering with Snowflake](https://www.udemy.com/share/1088rA3@Q-z-B6dWzfKVPjxAsLd_OpxOsYjnT8XjV3O24wDLGYWlj38tc6nkO68uojrziuXUHg==/)

---
