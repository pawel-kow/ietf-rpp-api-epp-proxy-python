"""Collects the data-driven cases as a tree: `file_cases.py` › environment › group › case.

Every case file (`test_case_data/<group>/<case>.json`) is a case in the branch of every test environment. A case
whose selectors do not hold in an environment, or of an environment that is not selected or lacks a credential, is
marked skipped there while collecting. A file that cannot be loaded, or a case that runs in no environment, is still
listed and fails when run, so it does not vanish. The environment and group nodes are `pytest.Class` nodes, because
that is what the VS Code test explorer nests. The runner is in `file_cases.py`.

A case's path is its JSON file, so the editor opens it. VS Code runs a test as `<path>::<environment>::<group>::<case>`,
so a case file named on the command line is collected as a tree of its own, of that one case; a run of a directory
does not collect it, so no case runs twice.
"""
from pathlib import Path

import pytest

CASE_TREE = Path(__file__).parent / "file_cases.py"
CASE_DATA = Path(__file__).parent / "test_case_data"


def pytest_collect_file(file_path: Path, parent: pytest.Collector):
    if file_path == CASE_TREE:
        return CaseTree.from_parent(parent, path=file_path)
    if (file_path.suffix == ".json" and file_path.parent.parent == CASE_DATA and file_path.name != "_group.json"
            and parent.session.isinitpath(file_path)):
        return CaseTree.from_parent(parent, path=file_path, only=file_path)
    return None


def pytest_sessionfinish(session):
    """Logs out the registry sessions of this process, in each xdist worker too, also after a Ctrl-C."""
    import sys

    file_cases = sys.modules.get("tests.integration.file_cases")
    if file_cases is not None:
        for run in file_cases.environment_runs().values():
            run.close()


class CaseTree(pytest.File):
    """The root: one branch per test environment. `only` is the one case file of a tree of a case file."""

    def __init__(self, *, only=None, **kwargs):
        super().__init__(**kwargs)
        self.only = only

    def collect(self):
        from tests.integration import file_cases  # loads the test environments, only when cases are collected

        for name, run in file_cases.environment_runs().items():
            yield EnvironmentNode.from_parent(self, name=name, run=run, only=self.only)


class _Node(pytest.Class):
    """A branch of the tree with no Python class behind it."""

    def _getobj(self):
        return type(self.name, (), {})


class EnvironmentNode(_Node):
    def __init__(self, *, run, only, **kwargs):
        super().__init__(**kwargs)
        self.run = run
        self.only = only

    def collect(self):
        from tests.integration import file_cases

        for group_dir in file_cases.groups() if self.only is None else [self.only.parent]:
            yield GroupNode.from_parent(self, name=group_dir.name, group_dir=group_dir, run=self.run, only=self.only)


class GroupNode(_Node):
    def __init__(self, *, group_dir, run, only, **kwargs):
        super().__init__(**kwargs)
        self.group_dir = group_dir
        self.run = run
        self.only = only

    def collect(self):
        from tests.integration import file_cases

        for path in file_cases.case_files(self.group_dir) if self.only is None else [self.only]:
            case, error = None, None
            try:
                case = file_cases.load_case(path)
            except Exception as exc:  # noqa: BLE001 - surface, don't swallow
                error = f"{type(exc).__name__}: {exc}"
            name = case["test_id"] if case is not None else path.stem
            yield Case.from_parent(self, name=name, path=path, case=case, load_error=error, run=self.run)


class Case(pytest.Item):
    """One case in one environment. `-k <group>-<test_id>` selects it in every environment, as the id did when the
    cases were parameters of one test."""

    def __init__(self, *, case, load_error, run, **kwargs):
        super().__init__(**kwargs)
        from tests.integration import file_cases

        self.case = case
        self.run = run
        self.extra_keyword_matches.add(f"{self.path.parent.name}-{self.name}")
        self.failure = None  # why the case fails without running
        try:
            for marker in (case or {}).get("markers", []):  # registered in pyproject.toml, as --strict-markers requires
                self.add_marker(marker)
        except (Exception, pytest.fail.Exception) as exc:  # noqa: BLE001 - an unknown marker fails the case only
            load_error = f"{type(exc).__name__}: {exc}"
        if load_error is not None:
            self.failure = f"Could not load test case file: {load_error}"
        elif file_cases.runs_nowhere(case):
            self.failure = (f"The selectors skip this case in every environment "
                            f"({', '.join(file_cases.environment_runs())}), so it never runs")
        else:
            reason = file_cases.skip_reason(case, run)
            if reason is not None:
                self.add_marker(pytest.mark.skip(reason=reason))

    def runtest(self):
        if self.failure is not None:
            pytest.fail(self.failure)
        from tests.integration import file_cases

        file_cases.run_case(self.case, self.run)

    def reportinfo(self):
        return self.path, 0, f"{self.run.name}/{self.path.parent.name}/{self.name}"
