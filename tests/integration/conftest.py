"""Collects the data-driven cases as a tree that follows their files: `test_case_data/<group>/<case>.json` is a case.

A group directory reads its `_group.json` once and lists its files in natural order (test2 before test10). A file that
cannot be loaded is still a case, which fails when run, so a broken file shows up instead of vanishing. The runner
is in `file_cases.py`.
"""
from pathlib import Path

import pytest

CASE_DATA = Path(__file__).parent / "test_case_data"


def pytest_collect_directory(path: Path, parent: pytest.Collector):
    if path.parent == CASE_DATA:
        return CaseGroup.from_parent(parent, path=path)
    return None


class CaseGroup(pytest.Directory):
    """A directory of cases: one group."""

    def collect(self):
        from tests.integration import file_cases  # loads the test environment, only when cases are collected

        group_when, group_error = None, None
        try:
            group_when = file_cases.load_group_when(self.path)
        except Exception as exc:  # noqa: BLE001 - surface, don't swallow
            group_error = f"{file_cases.GROUP_FILE}: {type(exc).__name__}: {exc}"
        for path in sorted(self.path.glob("*.json"), key=file_cases.natural_key):
            if path.name != file_cases.GROUP_FILE:
                yield CaseFile.from_parent(self, path=path, group_when=group_when, group_error=group_error)


class CaseFile(pytest.File):
    """A case file, which holds one case."""

    def __init__(self, *, group_when=None, group_error=None, **kwargs):
        super().__init__(**kwargs)
        self.group_when = group_when
        self.group_error = group_error

    def collect(self):
        from tests.integration import file_cases

        group = self.path.parent.name
        case, error = None, self.group_error
        if error is None:
            try:
                case = file_cases.load_case(self.path, self.group_when)
            except Exception as exc:  # noqa: BLE001 - surface, don't swallow
                error = f"{type(exc).__name__}: {exc}"
        name = case["test_id"] if case is not None else self.path.stem
        yield Case.from_parent(self, name=name, group=group, case=case, load_error=error)


class Case(pytest.Item):
    """One case. `-k <group>-<test_id>` selects it, as the id did when the cases were parameters of one test."""

    def __init__(self, *, group, case, load_error, **kwargs):
        super().__init__(**kwargs)
        self.group = group
        self.case = case
        self.load_error = load_error
        self.extra_keyword_matches.add(f"{group}-{self.name}")

    def runtest(self):
        if self.load_error is not None:
            pytest.fail(f"Could not load test case file: {self.load_error}")
        from tests.integration import file_cases

        file_cases.run_case(self.case)

    def reportinfo(self):
        return self.path, None, f"{self.group}/{self.name}"
