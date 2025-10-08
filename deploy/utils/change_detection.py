from pathlib import Path
from typing import List
import subprocess

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
# def get_changed_files_for_app(app_name: str, previous_commit: str, current_commit: str) -> List[str]:
#     import subprocess
#     app_root = Path(f"apps/{app_name}/app")
#     try:
#         result = subprocess.run(
#             ["git", "diff", "--name-only", previous_commit, current_commit],
#             capture_output=True,
#             text=True,
#             check=True
#         )
#         all_changed = result.stdout.strip().split("\n")
#         return [f for f in all_changed if f.startswith(str(app_root))]
#     except Exception as e:
#         print(f"⚠️ Failed to detect changed files: {e}")
#         return []


def _sanitize_commit(c: str) -> str:
    return (c or "").strip().strip('"').strip("'")


def _commit_exists(c: str) -> bool:
    if not c:
        return False
    try:
        subprocess.run(
            ["git", "cat-file", "-e", c],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except Exception:
        return False


def get_changed_files_for_app(app_name: str, previous_commit: str, current_commit: str) -> List[str]:
    """
    Return list of changed file paths for `app_name` between two commits.
    Defensive: strip quotes, verify commits exist locally, fallback to HEAD~1..HEAD diff.
    """
    previous_commit = _sanitize_commit(previous_commit)
    current_commit = _sanitize_commit(current_commit)

    # If either commit is absent locally, fallback to recent history
    if not (_commit_exists(previous_commit) and _commit_exists(current_commit)):
        try:
            out = subprocess.check_output(
                ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
                stderr=subprocess.DEVNULL,
            ).decode().splitlines()
        except Exception:
            return []
    else:
        try:
            out = subprocess.check_output(
                ["git", "diff", "--name-only", previous_commit, current_commit],
                stderr=subprocess.DEVNULL,
            ).decode().splitlines()
        except Exception:
            return []

    prefix = f"apps/{app_name}/"
    return [p for p in out if p.startswith(prefix)]
