from types import SimpleNamespace
import inspect
from typing import List, cast
import pytest

import app.python.procedures_man as pm


def make_dummy_proc(name: str, user_arg_count: int = 1):
    arg_names = ["session"] + [f"arg{i}" for i in range(1, user_arg_count + 1)]
    args_str = ", ".join(arg_names)
    src = f"def {name}({args_str}):\n    return 'ok'\n"
    ns = {}
    exec(src, ns)
    func = ns[name]
    func.__module__ = "app.python.manual_procs"
    return func


def make_proc_dict(func, name: str, tags: List[str], input_types: List[object]):
    return {
        "func": func,
        "name": name,
        "input_types": input_types,
        "return_type": pm.StringType(),
        "tags": tags,
        "source": "manual",
    }


def test_register_manual_procs_dry_run(monkeypatch):
    orig = pm.MANUAL_PROCS
    try:
        dummy = make_dummy_proc("dummy_proc", user_arg_count=1)
        proc = make_proc_dict(dummy, "dummy_proc", ["test"], [pm.StringType()])
        monkeypatch.setattr(pm, "MANUAL_PROCS", [proc])
        registered = pm.register_manual_procs(
            session=cast(pm.Session, None), stage_name="st", app_name="app", dry_run=True
        )
        assert isinstance(registered, list)
        assert len(registered) == 1
        assert registered[0]["name"] == "dummy_proc"
        assert registered[0]["status"] == "dry_run"
    finally:
        monkeypatch.setattr(pm, "MANUAL_PROCS", orig)


def test_register_manual_procs_tag_filter_skips(monkeypatch):
    orig = pm.MANUAL_PROCS
    try:
        dummy = make_dummy_proc("dummy_proc2", user_arg_count=1)
        proc = make_proc_dict(dummy, "dummy_proc2", [
                              "alpha"], [pm.StringType()])
        monkeypatch.setattr(pm, "MANUAL_PROCS", [proc])
        registered = pm.register_manual_procs(
            session=cast(pm.Session, None),
            stage_name="st",
            app_name="app",
            include_tags=["beta"],
            dry_run=False,
        )
        assert registered == []
    finally:
        monkeypatch.setattr(pm, "MANUAL_PROCS", orig)


def test_register_manual_procs_calls_session_sproc_register_and_restores_module(monkeypatch):
    orig = pm.MANUAL_PROCS
    try:
        d1 = make_dummy_proc("proc_one", user_arg_count=1)
        d2 = make_dummy_proc("proc_two", user_arg_count=1)
        proc1 = make_proc_dict(d1, "proc_one", ["t1"], [pm.StringType()])
        proc2 = make_proc_dict(d2, "proc_two", ["t2"], [pm.StringType()])
        monkeypatch.setattr(pm, "MANUAL_PROCS", [proc1, proc2])

        calls = []

        class FakeSproc:
            def register(self, **kwargs):
                calls.append(kwargs)

        fake_session = SimpleNamespace()
        fake_session.sproc = FakeSproc()

        orig_mod_d1 = d1.__module__
        orig_mod_d2 = d2.__module__

        registered = pm.register_manual_procs(
            session=cast(pm.Session, fake_session),
            stage_name="my_stage",
            app_name="my_app",
            dry_run=False,
            verbosity="summary",
        )

        assert len(calls) == 2
        assert calls[0]["name"] == "proc_one"
        assert calls[1]["name"] == "proc_two"
        expected_import = f"@my_stage/apps/my_app/app.zip"
        assert "imports" in calls[0] and calls[0]["imports"] == [
            expected_import]
        assert "func" in calls[0] and inspect.isfunction(calls[0]["func"])

        assert len(registered) == 2
        assert all(entry.get("status") == "registered" for entry in registered)

        assert d1.__module__ == orig_mod_d1
        assert d2.__module__ == orig_mod_d2
    finally:
        monkeypatch.setattr(pm, "MANUAL_PROCS", orig)
