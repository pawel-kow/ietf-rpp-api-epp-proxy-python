from dataclasses_json.undefined import UndefinedParameterError

from .not_supported_by_epp import NotSupportedByEpp
from .rpp_models import RPPPatchOperation, RPPPeriod


def parse_rpp(rpp_class, rpp: dict):
    """Builds the RPP object, rejecting undeclared properties (json draft §4.9.1)."""
    try:
        return rpp_class.from_dict(rpp)
    except UndefinedParameterError as e:
        raise ValueError(f"Undeclared property: {e}") from e


def period_duration(period: RPPPeriod | None) -> str | None:
    """A period as the duration the model holds."""
    return f"P{period.value}{period.unit.upper()}" if period else None


def reject_set(**members):
    """Rejects the named members, which EPP has no place for, when the request gives them a value."""
    for name, value in members.items():
        if value:
            raise NotSupportedByEpp(f"'{name}'")


def reject_operation(operation: RPPPatchOperation):
    """An operation EPP has no place for."""
    raise NotSupportedByEpp(f"'{operation.op}' on '{operation.path}'")
