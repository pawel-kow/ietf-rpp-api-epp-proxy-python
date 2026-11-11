from core.model.domain.domain_restore import DomainRestore
from rpp.mapping.domain import domain_restore_report
from rpp.mapping.shared import json_patch
from rpp.mapping.shared.common import parse_rpp
from rpp.dto.rpp_patch_operation import RPPPatchOperation

# EPP keeps no report, so a patch applies to a restore process that has none.
EMPTY = {"@type": "restoreProcess"}
ABSENT_PARENTS = {"/restoreReport": {"@type": "restoreReport"}}


def rpp_to_model(name: str, rpp: list) -> DomainRestore:
    """Converts a partial update (JSON Patch, json draft §5.2) of a restore process into a report."""
    operations = [parse_rpp(RPPPatchOperation, operation) for operation in rpp]
    patched = json_patch.apply(EMPTY, operations, (), absent_parents=ABSENT_PARENTS)
    return domain_restore_report.rpp_to_model(name, patched)
