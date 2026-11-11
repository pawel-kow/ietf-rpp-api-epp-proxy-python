import ipaddress

from .client_statuses import client_statuses, status_changes
from .host import Host
from .host_replacement import HostReplacement
from .host_update import HostUpdate
from .host_update_changes import HostUpdateChanges


def _addresses_missing_from(addresses: list[str] | None, others: list[str] | None) -> list[str]:
    known = {ipaddress.ip_address(address) for address in others or []}
    return [address for address in addresses or [] if ipaddress.ip_address(address) not in known]


def difference(current: Host, wanted: HostReplacement) -> HostUpdate:
    """The update that turns the current host into the wanted one (core §16.8: what is omitted is cleared)."""
    before = client_statuses(current.status, current.status_reasons)
    after = client_statuses(wanted.status, wanted.status_reasons)
    add_status, remove_status = status_changes(before, after)
    add = HostUpdateChanges(
        ipv4=_addresses_missing_from(wanted.ipv4, current.ipv4),
        ipv6=_addresses_missing_from(wanted.ipv6, current.ipv6),
        status=add_status,
        status_reasons={label: after[label] for label in add_status if after[label]},
    )
    remove = HostUpdateChanges(
        ipv4=_addresses_missing_from(current.ipv4, wanted.ipv4),
        ipv6=_addresses_missing_from(current.ipv6, wanted.ipv6),
        status=remove_status,
    )
    return HostUpdate(
        name=wanted.name,
        new_name=wanted.new_name if wanted.new_name.lower() != current.name.lower() else None,
        add=add or None,
        remove=remove or None,
    )


def changes_nothing(update: HostUpdate) -> bool:
    return update.new_name is None and update.add is None and update.remove is None
