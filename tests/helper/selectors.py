"""Selectors in the case files: which backends a case, a step or an expected value is for (docs/rri/refactoring.md
§5.2).

A selector is a JSON object whose keys name facts and which holds when every key holds. `profile.<path>` is a leaf of
the `BackendProfile` the app under test was composed with, `env.<path>` one of the facts of the test environment; the
path is dotted (`profile.contact.fax.supported`, `env.contact.postcode.min_count`). `wait.<path>` names a period of the
environment's facts (an ISO 8601 duration) a case waits for: it holds when the server has that transition (null: it has
none; a transition that is immediate is `PT0S`) and the period, with the buffer, is within the longest wait of the run. A list of selectors holds when one of them holds.
"""
from core.capabilities.backend_profile import BackendProfile
from tests.helper.durations import seconds


class SelectorError(ValueError):
    """A selector that cannot be evaluated: a key that names no fact, or a value of the wrong form."""


def env_fact(facts: dict, path: str):
    """The leaf of the environment's facts at a dotted path. A path that names no leaf is a `KeyError`."""
    node = facts
    for key in path.split("."):
        if not isinstance(node, dict) or key not in node:
            raise KeyError(path)
        node = node[key]
    if isinstance(node, dict):
        raise KeyError(path)
    return node


class Facts:
    def __init__(self, profile: BackendProfile, env_facts: dict, max_wait: int | None = None,
                 buffer_percent: float = 0):
        """`max_wait` is the longest wait of the run in seconds, None for no limit (to find a case that runs
        nowhere); `buffer_percent` the share of a period added to its wait."""
        if not isinstance(profile, BackendProfile):
            raise SelectorError("the profile is not a BackendProfile")
        self.profile = profile
        self.env_facts = env_facts
        self.max_wait = max_wait
        self.buffer_percent = buffer_percent

    def period(self, path: str) -> int | None:
        """The seconds of a period of the facts, None where the server has no such transition."""
        try:
            value = env_fact(self.env_facts, path)
        except KeyError:
            raise SelectorError(f"selector key 'wait.{path}' names no fact") from None
        try:
            return None if value is None else seconds(value)
        except ValueError as e:
            raise SelectorError(f"wait.{path}: {e}") from None

    def wait_seconds(self, path: str) -> int:
        """How long a step waits for a period: the period and the buffer."""
        period = self.period(path)
        if period is None:
            raise SelectorError(f"wait.{path}: the server has no such transition")
        return round(period * (1 + self.buffer_percent / 100))

    def wait_unmet(self, path: str) -> str | None:
        if self.period(path) is None:
            return f"wait.{path}: the server has no such transition"
        wait = self.wait_seconds(path)
        if self.max_wait is not None and wait > self.max_wait:
            return f"wait.{path} needs {wait} s, the run waits at most {self.max_wait} s (RPP_TEST_MAX_WAIT)"
        return None

    def value(self, key: str):
        """The leaf a key names. A key that names no leaf, or a node with leaves under it, names no fact."""
        scope, _, path = key.partition(".")
        try:
            if scope == "profile":
                return self.profile.fact(path)
            if scope == "env":
                return env_fact(self.env_facts, path)
        except KeyError:
            pass
        raise SelectorError(f"selector key {key!r} names no fact")


def _value_holds(actual, expected) -> bool:
    if isinstance(expected, dict):
        if len(expected) != 1:
            raise SelectorError(f"a condition has exactly one of contains, min, max, not: {expected!r}")
        (op, operand), = expected.items()
        if op == "contains":
            if not isinstance(actual, (tuple, list, set, frozenset)):
                raise SelectorError(f"contains needs a collection, the fact is {actual!r}")
            return operand in actual
        if op == "min":
            return actual >= operand
        if op == "max":
            return actual <= operand
        if op == "not":
            return not _value_holds(actual, operand)
        raise SelectorError(f"unknown condition {op!r}")
    return actual == expected


def unmet(selector, facts: Facts) -> list[str]:
    """What does not hold of the selector, empty when it holds. Raises `SelectorError` for a key that names no fact."""
    if isinstance(selector, list):
        if not selector:
            raise SelectorError("an empty list of selectors")
        results = [unmet(s, facts) for s in selector]
        if any(not r for r in results):
            return []
        return [" or ".join("; ".join(r) for r in results)]
    if not isinstance(selector, dict) or not selector:
        raise SelectorError(f"a selector is a non-empty object or a list of them: {selector!r}")
    failed = []
    for key, expected in selector.items():
        if key.startswith("wait."):
            if expected is not True:
                raise SelectorError(f"{key}: a wait selector is true, not {expected!r}")
            reason = facts.wait_unmet(key[len("wait."):])
            if reason:
                failed.append(reason)
            continue
        actual = facts.value(key)
        if not _value_holds(actual, expected):
            failed.append(f"{key} is {actual!r}, not {expected!r}")
    return failed


def holds(selector, facts: Facts) -> bool:
    return not unmet(selector, facts)


# What an entry `{"omit": true}` of a select gives: the member or list element that holds the select is left out.
OMIT = object()


def _is_select(value) -> bool:
    return isinstance(value, dict) and set(value) == {"select"}


def resolve(value, facts: Facts):
    """Replaces every `{"select": [{"when": …, "then": …}, …, {"then": …}]}` by the `then` of its first entry that
    holds, recursively. An entry `{"omit": true}` instead of `then` leaves the member or list element out."""
    resolved = _resolve(value, facts)
    if resolved is OMIT:
        raise SelectorError("a select at the top of a step value cannot omit it")
    return resolved


def _resolve(value, facts: Facts):
    if _is_select(value):
        for entry in value["select"]:
            if "when" not in entry or holds(entry["when"], facts):
                return OMIT if entry.get("omit") else _resolve(entry["then"], facts)
        raise SelectorError("no entry of a select holds")
    if isinstance(value, dict):
        items = {k: _resolve(v, facts) for k, v in value.items()}
        return {k: v for k, v in items.items() if v is not OMIT}
    if isinstance(value, list):
        return [item for item in (_resolve(v, facts) for v in value) if item is not OMIT]
    return value


def check(case: dict, facts: Facts) -> None:
    """Checks every selector of a case when it is loaded: every key names a fact, every select ends in a default
    without `when`, and a step with `when` captures nothing, since a later step could use the capture."""
    def walk(value, path):
        if _is_select(value):
            entries = value["select"]
            if not isinstance(entries, list) or not entries:
                raise SelectorError(f"{path}: select needs a list of entries")
            for i, entry in enumerate(entries):
                if not isinstance(entry, dict) or ("then" in entry) == (entry.get("omit") is True) \
                        or set(entry) - {"when", "then", "omit"}:
                    raise SelectorError(f"{path}: select entry {i} needs then or omit, and at most when")
                if "when" in entry:
                    unmet(entry["when"], facts)
                elif i != len(entries) - 1:
                    raise SelectorError(f"{path}: only the last select entry may lack when")
                if "then" in entry:
                    walk(entry["then"], f"{path}.select[{i}]")
            if "when" in entries[-1]:
                raise SelectorError(f"{path}: the last select entry is the default and has no when")
            return
        if isinstance(value, dict):
            for k, v in value.items():
                walk(v, f"{path}.{k}")
        elif isinstance(value, list):
            for i, v in enumerate(value):
                walk(v, f"{path}[{i}]")

    if "when" in case:
        unmet(case["when"], facts)
    waits = {key[len("wait."):] for key in (case.get("when") if isinstance(case.get("when"), dict) else {})
             if key.startswith("wait.")}
    for i, step in enumerate(case.get("steps", [])):
        if "delay_seconds" in step:
            raise SelectorError(f"step {i}: a case waits for a period of the facts (wait), not for seconds")
        for path in wait_paths(step):
            if path not in waits:
                raise SelectorError(f"step {i} waits for {path}, which the case's when does not select (wait.{path})")
        if "when" in step:
            unmet(step["when"], facts)
            if step.get("capture"):
                raise SelectorError(f"step {i} has a when and a capture, which a later step may need")
        walk({k: v for k, v in step.items() if k != "when"}, f"steps[{i}]")


def wait_paths(step: dict) -> list[str]:
    """The periods a step waits for before its request: `"wait": "<path>"`, or a list of them, which add up."""
    wait = step.get("wait", [])
    paths = [wait] if isinstance(wait, str) else wait
    if not isinstance(paths, list) or not all(isinstance(p, str) for p in paths):
        raise SelectorError(f"a step's wait is a fact path or a list of them: {wait!r}")
    return paths
