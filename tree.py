import os

# 🧑‍💻 Your authored top-level folders and files
AUTHORED_DIRS = {
    ".devcontainer", ".snowflake", "first_snowpark_project", "workspaces"
}
AUTHORED_FILES = {
    "environment.yml", "readme.MD", "requirements.txt", "setup_env.py"
}
MAX_DEPTH = 5


def print_tree(root, prefix="", depth=0):
    if depth > MAX_DEPTH:
        return

    try:
        entries = sorted(os.listdir(root))
    except PermissionError:
        return

    for i, entry in enumerate(entries):
        full_path = os.path.join(root, entry)

        # Skip __pycache__ directories
        if entry == "__pycache__":
            continue

        # Only include top-level authored items
        if depth == 0:
            if os.path.isdir(full_path) and entry not in AUTHORED_DIRS:
                continue
            if os.path.isfile(full_path) and entry not in AUTHORED_FILES:
                continue

        connector = "└── " if i == len(entries) - 1 else "├── "
        print(prefix + connector + entry)

        if os.path.isdir(full_path):
            extension = "    " if i == len(entries) - 1 else "│   "
            print_tree(full_path, prefix + extension, depth + 1)


if __name__ == "__main__":
    print("📦 Authored Project Tree\n")
    print_tree(".")
