class ProcRegistrar:
    def __init__(self, verbose: bool = True, dry_run: bool = False, tags: list[str] = None):
        self.verbose = verbose
        self.dry_run = dry_run
        self.tags = set(tags or [])
        self.registered = []

    def register_auto(self, stage: str):
        scanned_procs = self._scan_stage(stage)

        for proc in scanned_procs:
            if self._passes_tag_filter(proc):
                self._register(proc)

        if self.verbose:
            self._summarize()

    def _scan_stage(self, stage: str) -> list[dict]:
        # Stub: Replace with your actual scanning logic
        return [
            {"name": "proc_a", "tags": ["core"]},
            {"name": "proc_b", "tags": ["daily", "dag"]},
            {"name": "proc_c", "tags": ["experimental"]},
        ]

    def _passes_tag_filter(self, proc: dict) -> bool:
        if not self.tags:
            return True
        return bool(self.tags.intersection(proc["tags"]))

    def _register(self, proc: dict):
        if self.verbose:
            print(
                f"Registering procedure: {proc['name']} (tags: {proc['tags']})")
        if not self.dry_run:
            # TODO: Replace with actual registration logic
            pass
        self.registered.append(proc)

    def _summarize(self):
        print("\n✅ Auto-registration summary:")
        for proc in self.registered:
            print(f" - {proc['name']} (tags: {proc['tags']})")
