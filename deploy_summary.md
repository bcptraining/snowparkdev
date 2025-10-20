# 🧪 Dry-Run Summary — DE_PROJECT_1
- Environment: `dev`
- Changed Files: `apps/DE_PROJECT_1/app/python/procedures_man.py`
- Stage: `dev_deployment`
- Tags: `core, experimental, diagnostic`
- Auto Procedures: `2`
- Manual Procedures: `1`
- DAGs: `0`
- Duration: `6.29 seconds`
- Timestamp: `2025-10-20 13:07 PDT`

### Registered Procedures
| Name | Source | Handler | Returns | Status |
|------|--------|---------|---------|--------|
| hello_procedure | auto | app.python.procedures_auto.hello_procedure | string | valid |
| test_procedure | auto | app.python.procedures_auto.test_procedure | string | valid |
| copy_to_table_proc | manual | app.python.manual_procs.copy_to_table_proc | string | dry_run |
### 🚫 Excluded Procedures
| Name | Tags | Reason |
|------|------|--------|
| hello_procedure2 | example | Tag not allowed in environment or not declared by app |
| test_procedure_two | example | Tag not allowed in environment or not declared by app |

### 🏷️ Tag Coverage
| Tag | Included | Excluded |
|------|----------|----------|
| core | 1 | 0 |
| example | 0 | 2 |
| experimental | 2 | 0 |
### 🏷️ Auto Procedure Tags
| Procedure Name | Tags |
|----------------|------|
| hello_procedure | core |
| test_procedure | experimental |
### 🧠 Environment Context
- Python Version: `3.11.13`
- Python Executable: `/opt/conda/envs/snowparkdev/bin/python`
- Snow CLI Path: `/opt/conda/envs/snowparkdev/bin/snow`