from models import DomainRestore
from . import domain_restore_report, json_patch
from .common import parse_rpp
from .rpp_models import RPPPatchOperation

# EPP keeps no report, so a patch applies to a restore process that has none.
EMPTY = {"@type": "restoreProcess"}
ABSENT_PARENTS = {"/restoreReport": {"@type": "restoreReport"}}


def rpp_to_model(name: str, rpp: list) -> DomainRestore:
    """Converts a partial update (JSON Patch, json draft §5.2) of a restore process into a report."""
    operations = [parse_rpp(RPPPatchOperation, operation) for operation in rpp]
    patched = json_patch.apply(EMPTY, operations, (), absent_parents=ABSENT_PARENTS)
    return domain_restore_report.rpp_to_model(name, patched)
