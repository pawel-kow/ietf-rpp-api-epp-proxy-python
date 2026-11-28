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

from dotenv import load_dotenv
from starlette.testclient import TestClient

from main import compose
from settings.load_settings import load_settings
from tests.helper import durations, includes, selectors
from tests.helper.case_data import case_data_dir
from tests.helper.idn_labels import replace_idn_placeholders
from tests.helper.integration_api_test import (
    endpoint_test, replace_date_placeholders, replace_pad_placeholders, replace_upper_placeholders,
)
from tests.helper.pacer import Pacer
from tests.helper.run_directory import run_directory, run_once
from tests.helper.step_runner import StepRunner
from tests.helper.test_environment import (
    REPOSITORY, Credentials, EnvironmentError, TestEnvironment, environment_names, load, replace_fact, replace_values,
    selected_names, with_rpp_headers,
)

CASE_DATA = case_data_dir()
GROUP_FILE = "_group.json"
INCLUDES = CASE_DATA / "_includes"
RUN_HOOKS = CASE_DATA / "_run.json"
RUN_SETUP = "run-setup"

# The credentials of the test environments come from .env in the repository root, or from the process environment,
# which wins. The proxy never reads .env.
load_dotenv(REPOSITORY / ".env", override=False)
workers = int(os.getenv("PYTEST_XDIST_WORKER_COUNT", "1"))

# The random parts of the names and handles a process creates, one pair per environment: environments over the same
# server (`server` of the descriptor) run the same cases, and a case must not meet its twin's objects.
_randoms: dict[str, tuple[str, str]] = {}


def randoms(environment_name: str) -> tuple[str, str]:
    """`{random_name}` and `{random_id_10}` of this process in the environment."""
    return _randoms.setdefault(environment_name, (str(uuid.uuid4()), str(uuid.uuid4())[:10]))


class EnvironmentRun:
    """One test environment in this run. Its facts are known at collection; its app, credentials and pacer are
    made when its first case runs. It is inactive when `RPP_TEST_ENV` does not select it or a credential is
    missing, and then every case of it is skipped."""

    def __init__(self, name: str, selected: list[str]):
        self.name = name
        descriptor = load(name, with_credentials=False)
        # The backend server: environments over the same one share its mutexes, run setup and teardown, and sessions.
        self.server = descriptor.server
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
        sharing = [other for other in selected if load(other, with_credentials=False).server == self.server]
        if workers * len(sharing) > self.environment.max_workers:
            raise EnvironmentError(
                f"{name} allows at most {self.environment.max_workers} workers on its server {self.server}, the run has "
                f"{workers} for each of {', '.join(sharing)}")

    @functools.cached_property
    def composition(self):
        composition = compose(load_settings(str(REPOSITORY / self.environment.config)))
        composition.rpp_app.app.config.update({"TESTING": True})
        return composition

    @property
    def app(self):
        return self.composition.app

    def close(self):
        """Logs out the sessions of the environment's app, if it was built, so the next run finds the server's
        session slots free (MTEST allows 4 a RegAcc and counts a dropped session until its idle timeout)."""
        if "composition" in self.__dict__:
            self.composition.sessions.close()

    @functools.cached_property
    def credentials(self):
        return Credentials(self.environment)

    @functools.cached_property
    def pacer(self):
        return Pacer(self.environment.rpp_requests_per_minute, workers, self.credentials.slot)

    @functools.cached_property
    def full_rate_pacer(self):
        """The pacer of the run setup and teardown: the other workers of the environment wait for the run setup, and
        the run teardown runs after them, so each has the registrar's whole rate."""
        return Pacer(self.environment.rpp_requests_per_minute, 1, self.credentials.slot)

    def ensure_run_setup(self) -> None:
        """Runs the run setup of this environment's server, once per run across the workers and the environments over
        the server; fails if it failed."""
        failure = run_once(run_directory(), f"{self.server}.{RUN_SETUP}", lambda: self._run_hook("setup"))
        if failure is not None:
            raise RuntimeError(f"The run setup of {self.server} failed: {failure}")

    def run_teardown(self) -> list[str]:
        """Runs the run teardown of this environment; what failed in it."""
        return self._run_hook("teardown")

    def _run_hook(self, phase: str) -> list[str]:
        items = load_run_hooks().get(phase, [])
        hooks = {"test_group": "_run", "test_id": "run"}
        with TestClient(self.app) as client:
            runner = StepRunner(client, preparer(hooks, self, datetime.datetime.now(datetime.UTC)), "run",
                                self.environment.preset_signalling, self.credentials, self.full_rate_pacer)
            if phase == "teardown":
                return runner.run_teardown(items)
            runner.run(items, phase)
            return []


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
    """The group directories; `_includes` and any other name starting with `_` is not a group."""
    return sorted((p for p in CASE_DATA.iterdir() if p.is_dir() and not p.name.startswith("_")),
                  key=lambda p: p.name.lower())


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
    data = includes.expand(_read_json(path), INCLUDES)
    for env_facts in _all_facts():
        selectors.check(data, env_facts)
    data["test_group"] = path.parent.name
    data.setdefault("test_id", path.stem)
    if group_when is not None:
        data["_group_when"] = group_when
    return data


@functools.cache
def load_run_hooks() -> dict:
    """The run setup and teardown of `_run.json`, `{"setup": [items], "teardown": [items]}`, checked against every
    environment; empty without the file."""
    if not RUN_HOOKS.exists():
        return {}
    hooks = includes.expand(_read_json(RUN_HOOKS), INCLUDES)
    unknown = set(hooks) - {"comment", "setup", "teardown"}
    if unknown:
        raise ValueError(f"{RUN_HOOKS.name}: unknown keys {sorted(unknown)}")
    for env_facts in _all_facts():
        selectors.check(hooks, env_facts)
    return hooks


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
        random_name, random_id_10 = randoms(environment.name)
        replaced = json_data\
            .replace("{random_name}", f"{obj['test_group'].replace('_', '-')}-{random_name}" if "test_group" in obj else random_name)\
            .replace("{random_id_10}", f"{random_id_10}")\
            .replace("{test_start}", started.isoformat())# type: ignore
        replaced = replace_values(replaced, environment, random_id_10)
        replaced = replace_upper_placeholders(replace_pad_placeholders(replace_idn_placeholders(replaced, random_id_10)))
        replaced = replace_date_placeholders(replaced)
        replaced = replaced.replace("{unique_cltrid}", str(uuid.uuid4()))  # RPP-Cltrid is unique per request
        if "{rpp:" in replaced:
            # `with_rpp_headers` resolved the placeholders of the request headers, the only place they may stand
            raise EnvironmentError(f"{replaced!r}: a {{rpp:...}} placeholder is only a whole value of a request header")
        return replaced
    else:
        return json_data


def _with_wait(step, facts):
    """A step's `wait`, the periods it waits for, as the seconds the runner sleeps before its request."""
    paths = selectors.wait_paths(step)
    step = {k: v for k, v in step.items() if k != "wait"}
    if paths:
        step["delay_seconds"] = sum(facts.wait_seconds(path) for path in paths)
    return step


def preparer(case, run: EnvironmentRun, started):
    """What the step runner does to an item of the case right before it runs it, in the environment under test: None
    where its `when` does not hold; a block or loop as it is; a step with its selects resolved, its wait in seconds,
    its preset headers and then its placeholders replaced. The captures come last, in the runner."""
    def prepare(item):
        if "when" in item and not selectors.holds(item["when"], run.facts):
            return None
        item = {k: v for k, v in item.items() if k != "when"}
        if "block" in item or "loop" in item:
            return item
        step = _with_wait(selectors.resolve(item, run.facts), run.facts)
        step = with_rpp_headers({"steps": [step]}, run.environment)["steps"][0]
        return process_placeholders(step, run.environment, obj=case, started=started)
    return prepare
