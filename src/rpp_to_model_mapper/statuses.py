from models import ProvisioningObject
from .rpp_models import RPPStatus


def model_to_rpp(obj: ProvisioningObject, status_type: str) -> list[RPPStatus]:
    return [RPPStatus(at_type=status_type, label=label) for label in obj.status or []]
