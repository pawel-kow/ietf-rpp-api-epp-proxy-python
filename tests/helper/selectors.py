"""Selectors in the case files: which backends a case, a step or an expected value is for (docs/rri/refactoring.md
§5.2).

A selector is a JSON object whose keys name facts and which holds when every key holds. `profile.<fact>` is a fact of
the `BackendProfile` the app under test was composed with, `env.<fact>` a fact of the test environment. A list of
selectors holds when one of them holds.
"""
from dataclasses import fields, is_dataclass


class SelectorError(ValueError):
    """A selector that cannot be evaluated: a key that names no fact, or a value of the wrong form."""


class Facts:
    def __init__(self, profile, env_facts: dict):
        if not is_dataclass(profile):
            raise SelectorError("the profile is not a dataclass")
        self.profile = profile
        self.profile_names = {f.name for f in fields(profile)}
        self.env_facts = env_facts

    def value(self, key: str):
        scope, _, name = key.partition(".")
        if scope == "profile" and name in self.profile_names:
            return getattr(self.profile, name)
        if scope == "env" and name in self.env_facts:
            return self.env_facts[name]
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
        actual = facts.value(key)
        if not _value_holds(actual, expected):
            failed.append(f"{key} is {actual!r}, not {expected!r}")
    return failed


def holds(selector, facts: Facts) -> bool:
    return not unmet(selector, facts)


def _is_select(value) -> bool:
    return isinstance(value, dict) and set(value) == {"select"}


def resolve(value, facts: Facts):
    """Replaces every `{"select": [{"when": …, "then": …}, …, {"then": …}]}` by the `then` of its first entry that
    holds, recursively."""
    if _is_select(value):
        entries = value["select"]
        for entry in entries:
            if "when" not in entry or holds(entry["when"], facts):
                return resolve(entry["then"], facts)
        raise SelectorError("no entry of a select holds")
    if isinstance(value, dict):
        return {k: resolve(v, facts) for k, v in value.items()}
    if isinstance(value, list):
        return [resolve(v, facts) for v in value]
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
                if not isinstance(entry, dict) or "then" not in entry or set(entry) - {"when", "then"}:
                    raise SelectorError(f"{path}: select entry {i} needs then and at most when")
                if "when" in entry:
                    unmet(entry["when"], facts)
                elif i != len(entries) - 1:
                    raise SelectorError(f"{path}: only the last select entry may lack when")
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
    for i, step in enumerate(case.get("steps", [])):
        if "when" in step:
            unmet(step["when"], facts)
            if step.get("capture"):
                raise SelectorError(f"step {i} has a when and a capture, which a later step may need")
        walk({k: v for k, v in step.items() if k != "when"}, f"steps[{i}]")
