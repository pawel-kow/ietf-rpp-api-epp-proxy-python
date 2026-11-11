from rpp_schema_validator import visibility_of

ON_DEMAND = "onDemand"


def _on_demand(object_identifier: str) -> set[str]:
    return {element for element, visibility in visibility_of(object_identifier).items() if visibility == ON_DEMAND}


def rpp_to_model(object_identifier: str, identifiers: list[str]) -> frozenset[str]:
    """The data elements a request asks to include (data-objects §2.7.3), one Identifier per repeated `includeElements`
    parameter (core §16.1.7). An Identifier that is not a top-level data element of the object is rejected."""
    elements = visibility_of(object_identifier)
    for identifier in identifiers:
        if identifier not in elements:
            raise ValueError(f"'{identifier}' is not a data element of the {object_identifier} object")
    return frozenset(identifiers)


def visible(object_identifier: str, rpp: dict, requested: frozenset[str]) -> dict:
    """The output of an object: a data element with onDemand Visibility only when it is requested."""
    hidden = _on_demand(object_identifier) - requested
    return {member: value for member, value in rpp.items() if member not in hidden}


def left_alone(object_identifier: str, rpp: dict, requested: frozenset[str]) -> frozenset[str]:
    """The data elements a full update leaves as they are: those with onDemand Visibility that the request does not
    ask to include. Such an element is not part of the representation, so a request that sends it is rejected. A
    requested one is part of it, and is cleared when it is omitted (see spec-issues.md)."""
    unrequested = _on_demand(object_identifier) - requested
    sent = sorted(unrequested & rpp.keys())
    if sent:
        raise ValueError(f"'{sent[0]}' needs 'includeElements={sent[0]}' in a full update")
    return frozenset(unrequested)
