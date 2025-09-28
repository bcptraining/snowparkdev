from typing import List, Optional
from snowflake.snowpark import Session
from pathlib import Path
import pickle
import sys
import os
from datetime import datetime
from tabulate import tabulate


class DeployManager:
    """
    DeployManager handles manual procedure registration and emits unified summaries.
    Declarative procedures are validated and registered via ProcRegistrar.
    procedures_auto.py provides handlers only — not registration logic.
    """

    def __init__(
        self,
        session: Session,
        app_name: str,
        stage_name: str,
        changed_files: Optional[List[str]] = None,
        include_tags: Optional[List[str]] = None,
        dry_run: bool = False,
        verbosity: str = "summary"
    ):
        self.session = session
        self.app_name = app_name
        self.stage_name = stage_name
        self.changed_files = changed_files or []
        self.include_tags = [tag.lower()
                             for tag in include_tags] if include_tags else None
        self.dry_run = dry_run
        self.verbosity = verbosity
        self.manual_procs = []

    def vprint(self, msg: str):
        if self.verbosity == "verbose":
            print(msg)

    def should_register_manual(self) -> bool:
        manual_files = [
            f"apps/{self.app_name}/app/python/procedures_man.py",
            f"apps/{self.app_name}/app/schemas/schemas.json",
            f"apps/{self.app_name}/app/common/common.py"
        ]
        return any(f in self.changed_files for f in manual_files)

    def load_manual_procs(self):
        try:
            manual_module = __import__(
                f"apps.{self.app_name}.app.python.procedures_man",
                fromlist=["register_manual_procs"]
            )
            return manual_module.register_manual_procs
        except ModuleNotFoundError:
            print(f"ℹ️ procedures_man.py not found for app: {self.app_name}")
        except AttributeError:
            print(f"⚠️ register_manual_procs() missing in procedures_man.py")
        return None

    def register_manual(self):
        if not self.should_register_manual():
            print("⏭️ Manual registration skipped — no relevant code changes.")
            return []

        register_fn = self.load_manual_procs()
        if not register_fn:
            return []

        result = register_fn(
            session=self.session,
            stage_name=self.stage_name,
            app_name=self.app_name,
            include_tags=self.include_tags,
            dry_run=self.dry_run,
            verbosity=self.verbosity
        )

        self.manual_procs = result or []
        print(f"✅ Registered {len(self.manual_procs)} manual procedures.")
        return self.manual_procs

    def emit_summary(self):
        if not self.manual_procs:
            print("ℹ️ No manual procedures registered.")
            return

        print("\n📜 Manual Procedure Summary:")
        headers = ["Name", "Type", "Tags", "Source", "Status"]
        rows = [
            [p["name"], p["kind"], ", ".join(
                p["tags"]), p["source"], p["status"]]
            for p in self.manual_procs
        ]
        print(tabulate(rows, headers=headers, tablefmt="github"))
        print(
            f"🧠 Manual registration completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
