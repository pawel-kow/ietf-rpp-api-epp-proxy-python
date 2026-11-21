"""Includes of the case files: a named step sequence with parameters, in `<case data>/_includes/<name>.json`.

An include file is `{"comment": …, "parameters": {"<name>": {"comment": …, "default": …}}, "steps": [items]}`. A
parameter without `default` is required. An item of a case uses it as
`{"comment": …, "include": "<name>", "with": {"<name>": value}, "when": …}`.

`expand` replaces each such item, when the case is loaded, by a block of the include's items:
`{"block": [items], "origin": "<name>", "when": …, "comment": …}`. In the include, `{param:<name>}` stands for the
value of the parameter: a string that is `{param:<name>}` alone takes the value as it is (any JSON value), one that
holds it within takes the value as text. A default may use the other parameters the same way, so a member can
default to one built from another parameter. The other placeholders in a value are resolved later, as in any step. An
include may use includes; their `with` may use the parameters of the outer one.
"""
import copy
import json
import re
from pathlib import Path

PARAM = re.compile(r"\{param:([A-Za-z_][A-Za-z0-9_]*)\}")
PARAM_ANY = re.compile(r"\{param:[^{}]*\}")
PHASES = ("setup", "steps", "teardown")


class IncludeError(ValueError):
    """An include that cannot be expanded: unknown, a parameter missing, unknown or not declared, or a cycle."""


def expand(case: dict, include_dir: Path) -> dict:
    """The case with every include of its phases expanded into a block."""
    return {k: expand_items(v, include_dir, ()) if k in PHASES else v for k, v in case.items()}


def expand_items(items: list, include_dir: Path, stack: tuple) -> list:
    if not isinstance(items, list):
        raise IncludeError(f"a step list is a list, not {items!r}")
    return [_expand_item(item, include_dir, stack) for item in items]


def _expand_item(item, include_dir: Path, stack: tuple):
    if not isinstance(item, dict):
        return item
    if "include" in item:
        return _block(item, include_dir, stack)
    if "loop" in item:
        return {**item, "loop": expand_items(item["loop"], include_dir, stack)}
    if "block" in item:
        return {**item, "block": expand_items(item["block"], include_dir, stack)}
    return item


def _block(item: dict, include_dir: Path, stack: tuple) -> dict:
    name = item["include"]
    unknown_keys = set(item) - {"include", "with", "when", "comment"}
    if unknown_keys:
        raise IncludeError(f"include {name!r}: unknown keys {sorted(unknown_keys)}")
    if name in stack:
        raise IncludeError(f"include {name!r} includes itself: {' > '.join((*stack, name))}")
    definition = load_include(name, include_dir)
    values = _arguments(name, definition.get("parameters", {}), item.get("with", {}))
    steps = substitute(copy.deepcopy(definition["steps"]), values, name)
    block = {"block": expand_items(steps, include_dir, (*stack, name)), "origin": name}
    return {**{k: v for k, v in item.items() if k in ("when", "comment")}, **block}


def load_include(name, include_dir: Path) -> dict:
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", name):
        raise IncludeError(f"an include is named by letters, digits, _ and -: {name!r}")
    path = include_dir / f"{name}.json"
    if not path.is_file():
        raise IncludeError(f"unknown include {name!r}: no {path.name} in {include_dir}")
    with open(path, encoding="utf-8") as f:
        definition = json.load(f)
    if not isinstance(definition, dict) or not isinstance(definition.get("steps"), list):
        raise IncludeError(f"include {name!r}: an include file has a list of steps")
    if not isinstance(definition.get("parameters", {}), dict):
        raise IncludeError(f"include {name!r}: parameters is an object of name to its comment and default")
    return definition


def _arguments(name: str, parameters: dict, given) -> dict:
    if not isinstance(given, dict):
        raise IncludeError(f"include {name!r}: with is an object of parameter name to value")
    unknown = sorted(set(given) - set(parameters))
    if unknown:
        raise IncludeError(f"include {name!r}: unknown parameter {', '.join(unknown)}")
    values, defaulted = {}, []
    for parameter, spec in parameters.items():
        if parameter in given:
            values[parameter] = given[parameter]
        elif isinstance(spec, dict) and "default" in spec:
            values[parameter] = spec["default"]
            defaulted.append(parameter)
        else:
            raise IncludeError(f"include {name!r}: parameter {parameter} is missing")
    # A default may use the other parameters, `{param:name}`, also defaults that use parameters in turn.
    for _ in range(len(defaulted)):
        resolved = {p: substitute(values[p], values, name) for p in defaulted}
        if resolved == {p: values[p] for p in defaulted}:
            break
        values.update(resolved)
    for parameter in defaulted:
        if PARAM_ANY.search(json.dumps(values[parameter])):
            raise IncludeError(f"include {name!r}: the default of {parameter} uses itself")
    return values


def substitute(value, values: dict, name: str):
    """Replaces `{param:<name>}` in every string of the value. A parameter the include does not declare fails."""
    if isinstance(value, dict):
        return {k: substitute(v, values, name) for k, v in value.items()}
    if isinstance(value, list):
        return [substitute(v, values, name) for v in value]
    if not isinstance(value, str):
        return value
    whole = PARAM.fullmatch(value)
    if whole is not None:
        return _value(whole, values, name)

    def replace(match):
        found = _value(match, values, name)
        if isinstance(found, (dict, list)):
            raise IncludeError(f"include {name!r}: parameter {match.group(1)} is an object or list, which is a whole "
                               f"value, not part of {value!r}")
        return str(found)

    replaced = PARAM.sub(replace, value)
    malformed = PARAM_ANY.search(replaced)
    if malformed is not None:
        raise IncludeError(f"include {name!r}: malformed parameter {malformed.group(0)}")
    return replaced


def _value(match, values: dict, name: str):
    parameter = match.group(1)
    if parameter not in values:
        raise IncludeError(f"include {name!r}: parameter {parameter} is not declared")
    return values[parameter]
