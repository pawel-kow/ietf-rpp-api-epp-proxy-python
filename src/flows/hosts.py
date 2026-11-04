import ipaddress

from eppclient.epp_hosts import epp_hosts_Create, epp_hosts_Info, epp_hosts_Update
from eppclient.eppclient import EPPClient
from models import ErrorResponse, Host, HostUpdate, HostUpdateChanges, OperationResponse
from .host_mutation_result import HostMutationResult

CLIENT_STATUS_PREFIX = "client"


def _read_back(epp_client: EPPClient, host_name: str, mutation: OperationResponse) -> HostMutationResult:
    """Reads the host after a mutation the registry has already applied.

    A failed readback must not look like a failed mutation. It uses its own clTRID: the client's is spent.
    """
    try:
        info = epp_hosts_Info(epp_client, host_name)
    except Exception:
        return HostMutationResult(mutation=mutation)
    if isinstance(info, ErrorResponse):
        return HostMutationResult(mutation=mutation)
    return HostMutationResult(mutation=mutation, host=info.host)


def create_host(epp_client: EPPClient, host: Host, client_transaction_id) -> HostMutationResult | ErrorResponse:
    created = epp_hosts_Create(epp_client, host, client_transaction_id=client_transaction_id)
    if isinstance(created, ErrorResponse):
        return created
    return _read_back(epp_client, created.host.name, created)


def update_host(epp_client: EPPClient, update: HostUpdate, client_transaction_id) -> HostMutationResult | ErrorResponse:
    updated = epp_hosts_Update(epp_client, update, client_transaction_id=client_transaction_id)
    if isinstance(updated, ErrorResponse):
        return updated
    return _read_back(epp_client, update.new_name or update.name, updated)


def _addresses_missing_from(addresses: list[str] | None, others: list[str] | None) -> list[str]:
    known = {ipaddress.ip_address(address) for address in others or []}
    return [address for address in addresses or [] if ipaddress.ip_address(address) not in known]


def _client_statuses(host: Host) -> set[str]:
    return {label for label in host.status or [] if label.startswith(CLIENT_STATUS_PREFIX)}


def _statuses_with_a_new_reason(current: Host, wanted: Host) -> set[str]:
    """EPP cannot change a reason, so these statuses are removed and added again."""
    return {
        label for label in _client_statuses(current) & _client_statuses(wanted)
        if current.status_reasons.get(label) != wanted.status_reasons.get(label)
    }


def _difference(host_name: str, current: Host, wanted: Host) -> HostUpdate:
    """The update that turns the current host into the wanted one (core §16.8: what is omitted is cleared)."""
    new_reason = _statuses_with_a_new_reason(current, wanted)
    add_status = sorted(_client_statuses(wanted) - _client_statuses(current) | new_reason)
    add = HostUpdateChanges(
        ipv4=_addresses_missing_from(wanted.ipv4, current.ipv4),
        ipv6=_addresses_missing_from(wanted.ipv6, current.ipv6),
        status=add_status,
        status_reasons={label: wanted.status_reasons[label] for label in add_status if label in wanted.status_reasons},
    )
    remove = HostUpdateChanges(
        ipv4=_addresses_missing_from(current.ipv4, wanted.ipv4),
        ipv6=_addresses_missing_from(current.ipv6, wanted.ipv6),
        status=sorted(_client_statuses(current) - _client_statuses(wanted) | new_reason),
    )
    return HostUpdate(
        name=host_name,
        new_name=wanted.name if wanted.name.lower() != current.name.lower() else None,
        add=add or None,
        remove=remove or None,
    )


def replace_host(epp_client: EPPClient, host_name: str, wanted: Host, client_transaction_id) -> HostMutationResult | ErrorResponse:
    """A full update: EPP has none, so it reads the host and sends the difference."""
    current = epp_hosts_Info(epp_client, host_name)
    if isinstance(current, ErrorResponse):
        return current
    return update_host(epp_client, _difference(host_name, current.host, wanted), client_transaction_id)
