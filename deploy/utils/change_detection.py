from pathlib import Path
from typing import List


# In CI here was the problem with this test for change:
# ["git", "diff", "--name-only", "HEAD"]
# detects changes between the working directory and the last commit — not between two commits.

# So in CI, where the merge commit is already checked out and clean, this returns[].
# def get_changed_files_for_app(app_name: str) -> List[str]:
#     """
#     Detects changed files within a given app folder.
#     Assumes a Git repo and uses `git diff --name-only HEAD` to find changes.
#     """
#     import subprocess

#     app_root = Path(f"apps/{app_name}/app")
#     try:
#         result = subprocess.run(
#             ["git", "diff", "--name-only", "HEAD"],
#             capture_output=True,
#             text=True,
#             check=True
#         )
#         all_changed = result.stdout.strip().split("\n")
#         return [f for f in all_changed if f.startswith(str(app_root))]
#     except Exception as e:
#         print(f"⚠️ Failed to detect changed files: {e}")
#         return []

# THIS CHANGE COMPARES 2 COMMITS EXPLICITLY
def get_changed_files_for_app(app_name: str, previous_commit: str, current_commit: str) -> List[str]:
    import subprocess
    app_root = Path(f"apps/{app_name}/app")
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", previous_commit, current_commit],
            capture_output=True,
            text=True,
            check=True
        )
        all_changed = result.stdout.strip().split("\n")
        return [f for f in all_changed if f.startswith(str(app_root))]
    except Exception as e:
        print(f"⚠️ Failed to detect changed files: {e}")
        return []
