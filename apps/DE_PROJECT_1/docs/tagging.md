# 🏷️ Tagging System Overview

This document explains how tags are used to control procedure deployment across environments in the SnowparkDev project. It covers environment-level tag policies, app-level tag declarations, and how they interact during deploy.

---

## 📦 App-Level Tag Declaration (`tags.txt`)

Each app declares the tags it supports via a `tags.txt` file located in its root directory:

```
/apps/APP_NAME/tags.txt
```

This file contains a newline-delimited list of tags:

```
core
experimental
qa
critical
```

These tags define which procedures are eligible for deployment from this app.

---

## 🌐 Environment-Level Tag Policy (`tag_registry.py`)

The file `deploy/tag_registry.py` defines which tags are allowed in each environment:

```python
TAG_SETS = {
    "dev": ["core", "experimental", "diagnostic"],
    "qa": ["core", "stable"],
    "prod": ["core", "stable", "secure"]
}
```

These policies ensure that only safe, approved tags are deployed in each environment.

---

## 🔁 How Tag Filtering Works

During deployment:

1. Each procedure is annotated with a tag (e.g. `@tag("experimental")`)
2. The procedure is included **only if**:
   - The tag is listed in the app’s `tags.txt`
   - The tag is allowed in the target environment (`TAG_SETS`)
3. Procedures failing either check are excluded and narrated in the summary

---

## 🧪 Example

If `tags.txt` contains:

```
core
experimental
qa
critical
```

And you're deploying to `dev`, which allows:

```python
TAG_SETS["dev"] = ["core", "experimental", "diagnostic"]
```

Then:

- ✅ `core`, `experimental` procedures are deployed
- ❌ `qa`, `critical` procedures are excluded (not allowed in `dev`)
- ❌ `diagnostic` procedures are excluded (not declared by the app)

---

## 🧠 Best Practices

- Keep `tags.txt` tightly scoped to what the app actually supports
- Use `tag_registry.py` to enforce environment safety
- Narrate exclusions clearly in deploy summaries
- Validate tags early to avoid silent skips

---

## 🧬 How to Tag Procedures

There are two ways to tag procedures depending on how they’re registered:

### 🔹 Declarative Procedures (via `snowflake.yml`)

Tags are declared under `meta.tags` in the YAML config:

```yaml
meta:
  tags:
    - core
    - experimental
```

These tags are parsed during deploy and used to determine whether the procedure is eligible for the current environment.

### 🔸 Manual Procedures (via Python)

Tags are declared in the function’s docstring using a `tags:` line:

```python
def copy_to_table_proc(session: Session, schema_key: str) -> str:
    """
    tags: core
    description: Copies staged data into a target table.
    """
```

These tags are extracted during deploy and filtered using the same logic as declarative procedures.

---

### ✅ Tag Eligibility

For a procedure to be deployed:
- Its tag must be listed in the app’s `tags.txt`
- Its tag must be allowed in the current environment (`TAG_SETS`)

Procedures failing either check are excluded and narrated in the deploy summary.
