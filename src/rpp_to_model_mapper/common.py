from dataclasses_json.undefined import UndefinedParameterError

from .rpp_models import RPPPatchOperation
from .unsupported_rpp_feature import UnsupportedRppFeature


def parse_rpp(rpp_class, rpp: dict):
    """Builds the RPP object, rejecting undeclared properties (json draft §4.9.1)."""
    try:
        return rpp_class.from_dict(rpp)
    except UndefinedParameterError as e:
        raise ValueError(f"Undeclared property: {e}") from e


def reject_set(**members):
    """Rejects the named members when the request gives them a value."""
    for name, value in members.items():
        if value:
            raise UnsupportedRppFeature(f"'{name}' is not supported")


def reject_operation(operation: RPPPatchOperation):
    raise UnsupportedRppFeature(f"'{operation.op}' on '{operation.path}' is not supported")
