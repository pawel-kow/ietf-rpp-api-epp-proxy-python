"""RRI domain status ↔ RPP status (gap-analysis Q5). RRI sets every status itself, so a client sets none."""
from registry_adapter.rri.xml.generated.domain_5_0 import StatusType

REDEMPTION_PERIOD = "redemptionPeriod"

# The RPP status labels of each RRI status. `failed`, a domain not in the zone that the registry deletes when not
# fixed by its `expire`, is `inactive` with that deadline as `due`.
STATUS_LABELS = {
    StatusType.CONNECT: ["ok"],
    StatusType.FAILED: ["inactive"],
    StatusType.PENDING_CREATE: ["pendingCreate"],
    StatusType.SERVER_HOLD: ["serverHold"],
    StatusType.REDEMPTION_PERIOD: ["pendingDelete"],
}


def status_labels(status: StatusType | None) -> list[str]:
    return list(STATUS_LABELS.get(status, [])) if status is not None else []


def rgp_status(status: StatusType | None) -> list[str]:
    """The RGP status (RFC 3915) of a domain in its redemption period."""
    return [REDEMPTION_PERIOD] if status == StatusType.REDEMPTION_PERIOD else []
