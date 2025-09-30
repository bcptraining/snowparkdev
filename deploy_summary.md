# 🧪 Dry-Run Summary — DE_PROJECT_1
- Environment: `dev`
- Changed Files: `apps/DE_PROJECT_1/app/python/procedures_man.py, apps/DE_PROJECT_1/app/tags.json`
- Stage: `dev_deployment`
- Tags: `core, experimental, diagnostic`
- Auto Procedures: `4`
- Manual Procedures: `0`
- DAGs: `0`
- Duration: `14.67 seconds`
- Timestamp: `2025-09-30 11:28 PDT`

### Registered Procedures
| Name | Source | Handler | Returns | Status |
|------|--------|---------|---------|--------|
| hello_procedure | auto | app.python.procedures_auto.hello_procedure | string | valid |
| hello_procedure2 | auto | app.python.procedures_auto.hello_procedure2 | string | valid |
| test_procedure | auto | app.python.procedures_auto.test_procedure | string | valid |
| test_procedure_two | auto | app.python.procedures_auto.test_procedure_two | string | valid |
### 🚫 Excluded Procedures
| Name | Tags | Reason |
|------|------|--------|
| copy_to_table_proc | experimental | Not specified |

### 🏷️ Tag Coverage
| Tag | Included | Excluded |
|------|----------|----------|
| core | 1 | 0 |
| experimental | 3 | 1 |
### 🏷️ Auto Procedure Tags
| Procedure Name | Tags |
|----------------|------|
| hello_procedure | core |
| hello_procedure2 | experimental |
| test_procedure | experimental |
| test_procedure_two | experimental |
### 🧠 Environment Context
- Python Version: `3.11.13`
- Python Executable: `/opt/conda/envs/py311_env/bin/python`
- Snow CLI Path: `/opt/conda/envs/py311_env/bin/snow`