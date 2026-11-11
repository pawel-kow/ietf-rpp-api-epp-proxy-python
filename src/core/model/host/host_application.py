import ipaddress

from core.model.shared.client_statuses import client_statuses
from core.model.host.host import Host
from core.model.host.host_replacement import HostReplacement
from core.model.host.host_update import HostUpdate


def _applied(addresses: list[str] | None, added: list[str], removed: list[str]) -> list[str] | None:
    gone = {ipaddress.ip_address(address) for address in removed}
    kept = [address for address in addresses or [] if ipaddress.ip_address(address) not in gone]
    known = {ipaddress.ip_address(address) for address in kept}
    return kept + [address for address in added if ipaddress.ip_address(address) not in known] or None


def apply(current: Host, delta: HostUpdate) -> HostReplacement:
    """The host the update asks for: the current host with the changes of the update."""
    add, remove = delta.add, delta.remove
    statuses = client_statuses(current.status, current.status_reasons)
    for label in remove.status if remove else []:
        statuses.pop(label, None)
    for label in add.status if add else []:
        statuses[label] = add.status_reasons.get(label) or None
    return HostReplacement(
        name=delta.name,
        new_name=delta.new_name or current.name,
        ipv4=_applied(current.ipv4, add.ipv4 if add else [], remove.ipv4 if remove else []),
        ipv6=_applied(current.ipv6, add.ipv6 if add else [], remove.ipv6 if remove else []),
        status=list(statuses),
        status_reasons={label: reason for label, reason in statuses.items() if reason},
    )
