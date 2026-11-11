from dataclasses_json.undefined import UndefinedParameterError

from core.capabilities.not_supported_by_backend import NotSupportedByBackend
from rpp.dto.rpp_patch_operation import RPPPatchOperation
from rpp.dto.rpp_period import RPPPeriod
from rpp.schema.validator import validate_schema


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
            raise NotSupportedByBackend(f"'{name}'")


def reject_operation(operation: RPPPatchOperation):
    """An operation EPP has no place for."""
    raise NotSupportedByBackend(f"'{operation.op}' on '{operation.path}'")


PULL = "pull"


def reject_push(transfer_dir: str | None, gaining_client_id: str | None):
    """EPP knows only pull transfers, and has no place for the gaining client."""
    if transfer_dir not in (None, PULL):
        raise NotSupportedByBackend(f"Transfer direction '{transfer_dir}'")
    reject_set(gainingClientId=gaining_client_id)


def reject_reason(schema: str, rpp_class, rpp: dict):
    """Validates the content of an approve or a reject, which EPP gives no reason (data-objects §10.1.1.5)."""
    validate_schema(schema, rpp)
    reject_set(reason=parse_rpp(rpp_class, rpp).reason)
