import copy
from typing import Any

from .patch_not_applicable import PatchNotApplicable
from .rpp_models import RPPPatchOperation

OPERATIONS = ("add", "remove", "replace")


def _pointer(path: str) -> list[str]:
    """The keys of a JSON Pointer (RFC 6901)."""
    if not path.startswith("/") or path == "/":
        raise ValueError(f"'{path}' is not a path to a property")
    return [key.replace("~1", "/").replace("~0", "~") for key in path[1:].split("/")]


def _is_primitive(value: Any) -> bool:
    return isinstance(value, (str, int, float, bool))


def _same_value(left: Any, right: Any) -> bool:
    return type(left) is type(right) and left == right


def _check_match(match: Any):
    """json draft §5.2.1: the server MUST reject a match it cannot compare."""
    if not isinstance(match, dict):
        raise ValueError("'match' must be an object")
    for value in match.values():
        if isinstance(value, dict):
            _check_match(value)
        elif isinstance(value, list):
            if not all(_is_primitive(item) for item in value):
                raise ValueError("A list in 'match' can only hold strings, numbers or booleans")
        elif not _is_primitive(value):
            raise ValueError("'match' holds a value that cannot be compared")


def _matches(element: Any, match: Any) -> bool:
    """json draft §5.2.1. A list of primitives matches regardless of order."""
    if isinstance(match, dict):
        return isinstance(element, dict) and all(
            key in element and _matches(element[key], value) for key, value in match.items()
        )
    if isinstance(match, list):
        return (
            isinstance(element, list)
            and len(element) == len(match)
            and all(any(_same_value(item, other) for other in match) for item in element)
            and all(any(_same_value(item, other) for other in element) for item in match)
        )
    return _same_value(element, match)


def _required_value(operation: RPPPatchOperation) -> Any:
    if operation.value is None:
        raise ValueError(f"'{operation.op}' needs a 'value'")
    return copy.deepcopy(operation.value)


def _apply_to_array(parent: dict, key: str, operation: RPPPatchOperation):
    elements = parent.get(key, [])
    if operation.match is None:
        if operation.op == "add":
            parent[key] = elements + [_required_value(operation)]
        elif operation.op == "replace":
            value = _required_value(operation)
            if not isinstance(value, list):
                raise ValueError("'replace' of a whole array needs a list as 'value'")
            parent[key] = value
        else:
            parent.pop(key, None)
        return
    if operation.op == "add":
        raise ValueError("'add' cannot be used together with 'match'")
    _check_match(operation.match)
    found = [index for index, element in enumerate(elements) if _matches(element, operation.match)]
    if not found:
        raise PatchNotApplicable("no element matches")
    if operation.op == "remove":
        parent[key] = [element for index, element in enumerate(elements) if index not in found]
    elif len(found) > 1:
        raise PatchNotApplicable(f"{len(found)} elements match, so the replacement is ambiguous")
    else:
        elements[found[0]] = _required_value(operation)


def _apply_to_property(parent: dict, key: str, operation: RPPPatchOperation):
    if operation.match is not None:
        raise ValueError("'match' can only be used on an array")
    if operation.op == "remove":
        if key not in parent:
            raise PatchNotApplicable("the property does not exist")
        del parent[key]
    else:
        parent[key] = _required_value(operation)


def _apply(document: dict, operation: RPPPatchOperation, array_paths: tuple[str, ...], absent_parents: dict[str, dict]):
    if operation.op not in OPERATIONS:
        raise ValueError(f"Operation '{operation.op}' is not allowed")
    keys = _pointer(operation.path)
    parent = document
    walked = ""
    for key in keys[:-1]:
        walked += f"/{key}"
        if isinstance(parent, dict) and key not in parent and walked in absent_parents:
            parent[key] = copy.deepcopy(absent_parents[walked])
        if not isinstance(parent, dict) or key not in parent:
            raise ValueError(f"Path '{operation.path}' does not exist")
        parent = parent[key]
    if not isinstance(parent, dict):
        raise ValueError(f"Path '{operation.path}' does not point to a property")
    key = keys[-1]
    if operation.path in array_paths or isinstance(parent.get(key), list):
        _apply_to_array(parent, key, operation)
    else:
        _apply_to_property(parent, key, operation)


def apply(
    document: dict,
    operations: list[RPPPatchOperation],
    array_paths: tuple[str, ...],
    ignored_paths: tuple[str, ...] = (),
    absent_parents: dict[str, dict] | None = None,
) -> dict:
    """Applies a patch (json draft §5.2.2, steps 1 to 5) to a copy of the document, in order.

    `array_paths` are the properties that are arrays even when absent. Operations on `ignored_paths` are left to the caller.
    `absent_parents` gives the objects the schema allows on a path (step 2), to use when the document does not have them.
    A failure names the operation by its position.
    """
    patched = copy.deepcopy(document)
    for number, operation in enumerate(operations, start=1):
        if operation.path in ignored_paths:
            continue
        try:
            _apply(patched, operation, array_paths, absent_parents or {})
        except (ValueError, PatchNotApplicable) as e:
            raise type(e)(f"Operation {number} ('{operation.op}' on '{operation.path}'): {e}") from e
    return patched
