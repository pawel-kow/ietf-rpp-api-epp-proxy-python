from core.model.shared.common import ProvisioningObject
from rpp.dto.rpp_status import RPPStatus


def model_to_rpp(obj: ProvisioningObject, status_type: str) -> list[RPPStatus]:
    reasons = getattr(obj, "status_reasons", {})
    due = getattr(obj, "status_due", {})
    return [RPPStatus(at_type=status_type, label=label, reason=reasons.get(label), due=due.get(label))
            for label in obj.status or []]
