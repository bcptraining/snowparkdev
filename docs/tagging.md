# 🏷️ Tagging — current behavior (updated)

This document describes the canonical tagging rules used by the deploy tooling so behavior is unambiguous and reproducible.

---

## Summary
- Tags are normalized to lower-case and validated against `deploy/constants.VALID_TAGS`.
- A procedure is included for deployment only when at least one positive tag on the procedure is present in **both**:
  1. the app’s declared tags (derived from app sidecars / tags files), and
  2. the environment’s allowed tags (`deploy/tag_registry.py` / `TAG_SETS`).
- Procedures may declare negative tags prefixed with `!` to explicitly exclude them if the negative tag matches the app or environment tag set.
- Procedures with no positive tags are conservatively excluded.

---

## Where app tags come from
Priority order:
1. `apps/<APP>/tags.json` (preferred)
   - Supported shapes:
     - Top-level list: `["core","experimental"]`
     - Per-entity mapping:
       ```
       {
         "procedures": { "pname": ["core"] },
         "functions": { ... }
       }
       ```
     - Explicit app list field: `{"__app_tags__": ["core","experimental"]}`
   - When no explicit app-level list exists, the deploy derives the app-declared tag set from per-entity sections (`procedures`, `functions`, `dags`).
2. `apps/<APP>/tags.txt` — fallback: one tag per line, `#` comments allowed.

Logs (verbose) print the derived app-declared tags: `🧾 App-declared tags: [...]`.

---

## Where environment tags come from
- Canonical mapping: `deploy/tag_registry.py` (`TAG_SETS`).
- Values in `TAG_SETS` must be valid tokens in `deploy/constants.VALID_TAGS`.

---

## How procedure tags are declared
- Declarative (Snowpark / YAML): `meta.tags` in `snowflake.yml` or via sidecar `apps/<APP>/tags.json` under `procedures`.
- Manual (Python): declared in the app manifest (e.g., `MANUAL_PROCS` in `procedures_man.py`) or extracted from docstrings; `DeployManager` expects a list of tags per proc.

---

## Exact filter order applied during deploy
1. Load and normalize app-declared tags (lower-case).
2. Load and normalize environment allowed tags from `TAG_SETS`.
3. For each procedure:
   - Normalize its declared tags.
   - If any negative tag (starts with `!`) matches the app-declared set or the environment set → **exclude**.
   - Otherwise, collect positive tags (non-`!`).
   - If at least one positive tag exists in **both** app-declared tags **and** environment allowed tags → **include**.
   - Otherwise → **exclude**.
4. Excluded procedures are recorded in `deploy_summary.md` / `deploy_summary.json`.

---

## Negative-tag semantics (examples)
- `["!qa"]` → excluded in any environment where `qa` appears in app tags or environment tags.
- `["core", "!experimental"]` → included only if `core` is present in both app and env and `experimental` does not match app or env (if it does, `!experimental` excludes).

---

## Example (DE_PROJECT_1)
- App-declared tags derived: `["core", "example", "experimental"]`
- `TAG_SETS["dev"]`: `["core", "experimental", "diagnostic"]`
- Outcome:
  - `core` → included
  - `experimental` → included
  - `example` → excluded (app declares it but `dev` does not allow it)
  - `diagnostic` → excluded (env allows but app didn’t declare)

---

## Dry-run & deployment notes
- Preview behavior with a verbose dry-run:
  ```
  deployapp --app DE_PROJECT_1 --env dev --dry-run --verbosity verbose
  ```
- Deploy writes `deploy_summary.md` and `deploy_summary.json` that list included/excluded procedures.
- Some historical tool versions may still execute declarative Snowpark deploys under `--dry-run`. Look for the console line `🧪 Dry-run: Skipping Snowpark deploy` to confirm suppression.

---

## How to change what gets deployed
- Add/remove tags from the app: edit `apps/<APP>/tags.json` (preferred) or `apps/<APP>/tags.txt`.
- Change environment allowances: edit `deploy/tag_registry.py` (`TAG_SETS`) — update with caution.
- Change filtering semantics: modify `is_proc_allowed()` in `deploy/deploy_snowflake_app.py` (if you alter semantics, update this document).
- Change per-procedure tags: update `meta.tags` in `snowflake.yml` or the manual procedure manifest/docstring.

---

## Troubleshooting checklist
- If a proc is unexpectedly included:
  - Verify the procedure’s tags (sidecar `tags.json` or docstring).
  - Confirm derived app-declared tags (check verbose deploy logs).
  - Confirm `TAG_SETS` for the target environment contains (or does not contain) the tag.
- Quick diagnostic: run a verbose dry-run and inspect the "🚫 Excluded Procedures" block in `deploy_summary.md`.

---

## Appendix — recommended tag hygiene
- Keep `deploy/constants.VALID_TAGS` authoritative; limit tag set size.
- Prefer app-level sidecar (`tags.json`) for clarity and CI reproducibility.
- Use negative tags sparingly and document rationale in the procedure docstring.

---

If you want, I can open a patch that replaces the existing `docs/tagging.md` with this file.// filepath: /workspaces/snowparkdev/docs/tagging.md
# 🏷️ Tagging — current behavior (updated)

This document describes the canonical tagging rules used by the deploy tooling so behavior is unambiguous and reproducible.

---

## Summary
- Tags are normalized to lower-case and validated against `deploy/constants.VALID_TAGS`.
- A procedure is included for deployment only when at least one positive tag on the procedure is present in **both**:
  1. the app’s declared tags (derived from app sidecars / tags files), and
  2. the environment’s allowed tags (`deploy/tag_registry.py` / `TAG_SETS`).
- Procedures may declare negative tags prefixed with `!` to explicitly exclude them if the negative tag matches the app or environment tag set.
- Procedures with no positive tags are conservatively excluded.

---

## Where app tags come from
Priority order:
1. `apps/<APP>/tags.json` (preferred)
   - Supported shapes:
     - Top-level list: `["core","experimental"]`
     - Per-entity mapping:
       ```
       {
         "procedures": { "pname": ["core"] },
         "functions": { ... }
       }
       ```
     - Explicit app list field: `{"__app_tags__": ["core","experimental"]}`
   - When no explicit app-level list exists, the deploy derives the app-declared tag set from per-entity sections (`procedures`, `functions`, `dags`).
2. `apps/<APP>/tags.txt` — fallback: one tag per line, `#` comments allowed.

Logs (verbose) print the derived app-declared tags: `🧾 App-declared tags: [...]`.

---

## Where environment tags come from
- Canonical mapping: `deploy/tag_registry.py` (`TAG_SETS`).
- Values in `TAG_SETS` must be valid tokens in `deploy/constants.VALID_TAGS`.

---

## How procedure tags are declared
- Declarative (Snowpark / YAML): `meta.tags` in `snowflake.yml` or via sidecar `apps/<APP>/tags.json` under `procedures`.
- Manual (Python): declared in the app manifest (e.g., `MANUAL_PROCS` in `procedures_man.py`) or extracted from docstrings; `DeployManager` expects a list of tags per proc.

---

## Exact filter order applied during deploy
1. Load and normalize app-declared tags (lower-case).
2. Load and normalize environment allowed tags from `TAG_SETS`.
3. For each procedure:
   - Normalize its declared tags.
   - If any negative tag (starts with `!`) matches the app-declared set or the environment set → **exclude**.
   - Otherwise, collect positive tags (non-`!`).
   - If at least one positive tag exists in **both** app-declared tags **and** environment allowed tags → **include**.
   - Otherwise → **exclude**.
4. Excluded procedures are recorded in `deploy_summary.md` / `deploy_summary.json`.

---

## Negative-tag semantics (examples)
- `["!qa"]` → excluded in any environment where `qa` appears in app tags or environment tags.
- `["core", "!experimental"]` → included only if `core` is present in both app and env and `experimental` does not match app or env (if it does, `!experimental` excludes).

---

## Example (DE_PROJECT_1)
- App-declared tags derived: `["core", "example", "experimental"]`
- `TAG_SETS["dev"]`: `["core", "experimental", "diagnostic"]`
- Outcome:
  - `core` → included
  - `experimental` → included
  - `example` → excluded (app declares it but `dev` does not allow it)
  - `diagnostic` → excluded (env allows but app didn’t declare)

---

## Dry-run & deployment notes
- Preview behavior with a verbose dry-run:
  ```
  deployapp --app DE_PROJECT_1 --env dev --dry-run --verbosity verbose
  ```
- Deploy writes `deploy_summary.md` and `deploy_summary.json` that list included/excluded procedures.
- Some historical tool versions may still execute declarative Snowpark deploys under `--dry-run`. Look for the console line `🧪 Dry-run: Skipping Snowpark deploy` to confirm suppression.

---

## How to change what gets deployed
- Add/remove tags from the app: edit `apps/<APP>/tags.json` (preferred) or `apps/<APP>/tags.txt`.
- Change environment allowances: edit `deploy/tag_registry.py` (`TAG_SETS`) — update with caution.
- Change filtering semantics: modify `is_proc_allowed()` in `deploy/deploy_snowflake_app.py` (if you alter semantics, update this document).
- Change per-procedure tags: update `meta.tags` in `snowflake.yml` or the manual procedure manifest/docstring.

---

## Troubleshooting checklist
- If a proc is unexpectedly included:
  - Verify the procedure’s tags (sidecar `tags.json` or docstring).
  - Confirm derived app-declared tags (check verbose deploy logs).
  - Confirm `TAG_SETS` for the target environment contains (or does not contain) the tag.
- Quick diagnostic: run a verbose dry-run and inspect the "🚫 Excluded Procedures" block in `deploy_summary.md`.

---

## Appendix — recommended tag hygiene
- Keep `deploy/constants.VALID_TAGS` authoritative; limit tag set size.
- Prefer app-level sidecar (`tags.json`) for clarity and CI reproducibility.
- Use negative tags sparingly and document rationale in the procedure docstring.

---

If you want, I can open a patch that replaces the existing `docs/tagging.md` with this file.
