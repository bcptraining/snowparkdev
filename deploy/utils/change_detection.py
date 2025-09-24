from pathlib import Path
from typing import List


def get_changed_files_for_app(app_name: str) -> List[str]:
    """
    Detects changed files within a given app folder.
    Assumes a Git repo and uses `git diff --name-only HEAD` to find changes.
    """
    import subprocess

    app_root = Path(f"apps/{app_name}/app")
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True,
            text=True,
            check=True
        )
        all_changed = result.stdout.strip().split("\n")
        return [f for f in all_changed if f.startswith(str(app_root))]
    except Exception as e:
        print(f"⚠️ Failed to detect changed files: {e}")
        return []
