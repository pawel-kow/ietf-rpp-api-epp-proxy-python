"""The data-driven integration cases: loading a case file and running it in a test environment.

`conftest.py` of this directory collects this file as the root of a tree: one branch per test environment, then one
per group (`test_case_data/<group>/`), then the cases (`<case>.json`). Every environment of the run gets an app of its
own, composed from its config, with its credentials and its pacer, so one run tests every backend.
"""
import datetime
import functools
import json
import os
import re
import uuid
from pathlib import Path

import pytest
from dotenv import load_dotenv

from main import compose
from settings.load_settings import load_settings
from tests.helper import durations, selectors
from tests.helper.idn_labels import replace_idn_placeholders
from tests.helper.integration_api_test import endpoint_test, replace_pad_placeholders, replace_upper_placeholders
from tests.helper.pacer import Pacer
from tests.helper.test_environment import (
    REPOSITORY, Credentials, EnvironmentError, TestEnvironment, environment_names, load, replace_fact, replace_values,
    selected_names,
)

CASE_DATA = Path(__file__).parent / "test_case_data"
GROUP_FILE = "_group.json"

# The credentials of the test environments come from .env in the repository root, or from the process environment,
# which wins. The proxy never reads .env.
load_dotenv(REPOSITORY / ".env", override=False)
workers = int(os.getenv("PYTEST_XDIST_WORKER_COUNT", "1"))

random_name = str(uuid.uuid4()) # Generate a random name for testing
random_id_10 = str(uuid.uuid4())[:10]


class EnvironmentRun:
    """One test environment in this run. Its facts are known at collection; its app, credentials and pacer are
    made when its first case runs. It is inactive when `RPP_TEST_ENV` does not select it or a credential is
    missing, and then every case of it is skipped."""

    def __init__(self, name: str, selected: list[str]):
        self.name = name
        descriptor = load(name, with_credentials=False)
        # The longest wait of this run, and the buffer of each wait (tests/helper/durations.py).
        self.facts = selectors.Facts(descriptor.profile, descriptor.facts, durations.max_wait(),
                                     durations.buffer_percent())
        # The same facts waiting without limit, so a long wait does not make a case look as if it ran nowhere.
        self.unlimited_facts = selectors.Facts(descriptor.profile, descriptor.facts, None, durations.buffer_percent())
        self.environment: TestEnvironment | None = None
        self.inactive_reason: str | None = None
        if name not in selected:
            self.inactive_reason = f"{name} is not selected: RPP_TEST_ENV={os.getenv('RPP_TEST_ENV')}"
            return
        try:
            self.environment = load(name)
        except EnvironmentError as exc:
            self.inactive_reason = str(exc)
            return
        if workers > self.environment.max_workers:
            raise EnvironmentError(
                f"{name} allows at most {self.environment.max_workers} workers, the run has {workers}")

    @functools.cached_property
    def app(self):
        app = compose(load_settings(str(REPOSITORY / self.environment.config))).app
        app.app.config.update({"TESTING": True})
        return app

    @functools.cached_property
    def credentials(self):
        return Credentials(self.environment)

    @functools.cached_property
    def pacer(self):
        return Pacer(self.environment.rpp_requests_per_minute, workers, self.credentials.slot)


@functools.cache
def environment_runs() -> dict[str, EnvironmentRun]:
    selected = selected_names()
    return {name: EnvironmentRun(name, selected) for name in environment_names()}


def _all_facts():
    return [facts for run in environment_runs().values() for facts in (run.facts, run.unlimited_facts)]


def natural_key(path: Path):
    """Sort key that orders test2 before test10 (numeric-aware)."""
    return [int(part) if part.isdigit() else part.lower()
            for part in re.split(r"(\d+)", path.stem)]


def _read_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def groups() -> list[Path]:
    return sorted((p for p in CASE_DATA.iterdir() if p.is_dir()), key=lambda p: p.name.lower())


def case_files(group_dir: Path) -> list[Path]:
    return sorted((p for p in group_dir.glob("*.json") if p.name != GROUP_FILE), key=natural_key)


@functools.cache
def load_group_when(group_dir: Path):
    """The `when` of the group's `_group.json`, checked against every environment, or None without one.

    Raises when the file cannot be read or names a fact no environment has; every case of the group then fails.
    """
    if not (group_dir / GROUP_FILE).exists():
        return None
    try:
        group_when = _read_json(group_dir / GROUP_FILE)["when"]
        for env_facts in _all_facts():
            selectors.unmet(group_when, env_facts)
    except Exception as exc:  # noqa: BLE001 - surface, don't swallow
        raise ValueError(f"{GROUP_FILE}: {type(exc).__name__}: {exc}") from exc
    return group_when


@functools.cache
def load_case(path: Path):
    """The case of a file, with its `test_group`, `test_id` and the `when` of its group.

    Raises when the file cannot be read or a selector names no fact; the case then fails when run, so a broken file
    still shows up instead of vanishing. The case is shared by the environments and is not changed after this.
    """
    group_when = load_group_when(path.parent)
    data = _read_json(path)
    for env_facts in _all_facts():
        selectors.check(data, env_facts)
    data["test_group"] = path.parent.name
    data.setdefault("test_id", path.stem)
    if group_when is not None:
        data["_group_when"] = group_when
    return data


def _case_selectors(case):
    return [w for w in (case.get("_group_when"), case.get("when")) if w is not None]


def unmet_case_selectors(case, case_facts) -> list[str]:
    return [reason for when in _case_selectors(case) for reason in selectors.unmet(when, case_facts)]


def runs_nowhere(case) -> bool:
    """Whether the selectors skip the case in every known environment, so it never runs."""
    return all(unmet_case_selectors(case, run.unlimited_facts) for run in environment_runs().values())


def skip_reason(case, run: EnvironmentRun) -> str | None:
    """Why the case does not run in the environment, or None when it does."""
    if run.inactive_reason is not None:
        return run.inactive_reason
    unmet = unmet_case_selectors(case, run.facts)
    return f"skipped in {run.name}: {'; '.join(unmet)}" if unmet else None


def process_placeholders(json_data, environment: TestEnvironment, obj=None, started=None):
    """
    Recursively replace placeholders in the JSON data with actual values.
    """
    if obj is None and isinstance(json_data, dict) and "test_id" in json_data:
        obj = json_data
    if isinstance(json_data, dict):
        return {k: process_placeholders(v, environment, obj, started) for k, v in json_data.items()} # type: ignore
    elif isinstance(json_data, list):
        return [process_placeholders(item, environment, obj, started) for item in json_data] # type: ignore
    elif isinstance(json_data, str):
        one_of = replace_fact(json_data, environment)
        if not isinstance(one_of, str):
            return one_of
        replaced = json_data\
            .replace("{random_name}", f"{obj['test_group'].replace('_', '-')}-{random_name}" if "test_group" in obj else random_name)\
            .replace("{random_id_10}", f"{random_id_10}")\
            .replace("{test_start}", started.isoformat())# type: ignore
        replaced = replace_values(replaced, environment, random_id_10)
        replaced = replace_upper_placeholders(replace_pad_placeholders(replace_idn_placeholders(replaced, random_id_10)))
        return replaced.replace("{unique_cltrid}", str(uuid.uuid4())) # RPP-Cltrid is unique per request
    else:
        return json_data


def _with_wait(step, facts):
    """A step's `wait`, the periods it waits for, as the seconds the runner sleeps before its request."""
    paths = selectors.wait_paths(step)
    step = {k: v for k, v in step.items() if k != "wait"}
    if paths:
        step["delay_seconds"] = sum(facts.wait_seconds(path) for path in paths)
    return step


def select(case, facts):
    """The case as the environment under test runs it: the steps whose `when` holds, each `select` resolved."""
    steps = [_with_wait(selectors.resolve({k: v for k, v in step.items() if k != "when"}, facts), facts)
             for step in case["steps"] if "when" not in step or selectors.holds(step["when"], facts)]
    return {**{k: v for k, v in case.items() if k not in ("when", "_group_when")}, "steps": steps}


def run_case(case, run: EnvironmentRun):
    """Runs a loaded case in the environment, in a test client of its own."""
    # The selectors are resolved first, then the placeholders, then the captures.
    # {test_start} is the start of this case, so the time windows in the data do not depend on suite length.
    with run.app.test_client() as client:
        endpoint_test(client, process_placeholders(select(case, run.facts), run.environment,
                                                   started=datetime.datetime.now(datetime.UTC)),
                      credentials=run.credentials, pacer=run.pacer)
