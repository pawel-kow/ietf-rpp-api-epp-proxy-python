from dataclasses import dataclass, field

from dataclasses_json import config


def type_field(value: str):
    """The '@type' member, fixed to the given value by default."""
    return field(default=value, metadata=config(field_name="@type"))


def _without_none(value):
    if isinstance(value, dict):
        return {k: _without_none(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [_without_none(v) for v in value]
    return value


@dataclass(kw_only=True)
class RPPObject:
    def to_rpp(self) -> dict:
        """The JSON representation, without the members that have no value."""
        return _without_none(self.to_dict())  # type: ignore
