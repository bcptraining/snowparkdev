# ✅ Deployment Summary — DE_PROJECT_1
- Environment: `dev`
- Changed Files: `apps/DE_PROJECT_1/app/python/manual_procs.py, apps/DE_PROJECT_1/app/python/procedures_man.py`
- Stage: `dev_deployment`
- Tags: `core, experimental, diagnostic`
- Auto Procedures: `2`
- Manual Procedures: `2`
- DAGs: `0`
- Duration: `18.40 seconds`
- Timestamp: `2025-11-11 16:48 PST`

### Registered Procedures
| Name | Source | Handler | Returns | Status |
|------|--------|---------|---------|--------|
| hello_procedure | auto | app.python.procedures_auto.hello_procedure | string | valid |
| test_procedure | auto | app.python.procedures_auto.test_procedure | string | valid |
| copy_to_table_proc | manual | app.python.manual_procs.copy_to_table_proc | string | registered |
| test_manual_proc | manual | app.python.manual_procs.test_manual_proc | string | registered |
### 🚫 Excluded Procedures
| Name | Tags | Reason |
|------|------|--------|
| hello_procedure2 | example | Tag not allowed in environment or not declared by app |
| test_procedure_two | example | Tag not allowed in environment or not declared by app |

### 🏷️ Tag Coverage
| Tag | Included | Excluded |
|------|----------|----------|
| core | 2 | 0 |
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