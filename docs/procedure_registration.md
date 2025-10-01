# Procedure Registration Guide

## 📘 Purpose

This document explains how manual procedures are defined, tagged, validated, and registered within the Snowpark Native App Registration Framework. It complements the main `README.md` and assumes familiarity with the overall architecture.

---

## 🧩 What Is a Manual Procedure?

Manual procedures are Python functions that are registered to Snowflake using custom logic. They are ideal for:

- Complex business logic
- Dynamic input handling
- Custom validation and metadata
- CI/CD-driven deployments

They differ from auto procedures, which are defined declaratively in `snowflake.yml` and registered automatically by Snowflake.

---

## 🛠️ Where to Define Manual Procedures

Manual procedures are defined in:

```
apps/<APP_NAME>/app/python/manual_procs.py
```

Each procedure should follow this structure:

```python
def my_proc(session: Session, input: str) -> str:
    """
    tags: core
    description: This procedure does something useful.
    """
    ...
```

---

## 🏷️ Tagging and Metadata

Each procedure must include:

- `tags:` — used for filtering and environment targeting
- `description:` — used for documentation and discovery

See [`tagging.md`](./tagging.md) for full details on tag usage.

---

## ✅ Validation Workflow

Manual procedures are validated before registration using:

- `validation.py` — checks function signature and return type
- `register_procs.py` — orchestrates registration and emits summaries

Validation ensures that procedures conform to expected input/output formats and are safe to deploy.

---

## 🚀 Registration Workflow

To register manual procedures:

1. Ensure your procedure is defined in `manual_procs.py`
2. Add metadata to `procedures_man.py` or rely on auto-discovery
3. Run the registration script:
   ```bash
   python register_procs.py --dry-run
   python register_procs.py
   ```

4. Confirm deployment via GitHub Actions or Snowflake UI

---

## 🔍 Troubleshooting

Common issues:

- Missing tags or description
- Signature mismatch (e.g., wrong number of parameters)
- Handler resolution failure (e.g., incorrect module path)

Use verbose mode for detailed output:
```bash
python register_procs.py --verbosity verbose
```

---

## 📦 Future Additions

This guide will expand to include:

- UDF registration via `register_udfs.py`
- DAG orchestration and tagging
- CLI tooling for procedure discovery and validation

---

## 🙌 Maintainer

This framework and guide were created by Cory to support scalable, maintainable Snowpark-native development across teams.

---
