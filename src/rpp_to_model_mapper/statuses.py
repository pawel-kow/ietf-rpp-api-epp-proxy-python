from core.model.shared.common import ProvisioningObject
from .rpp_models import RPPStatus


def model_to_rpp(obj: ProvisioningObject, status_type: str) -> list[RPPStatus]:
    reasons = getattr(obj, "status_reasons", {})
    return [RPPStatus(at_type=status_type, label=label, reason=reasons.get(label)) for label in obj.status or []]
