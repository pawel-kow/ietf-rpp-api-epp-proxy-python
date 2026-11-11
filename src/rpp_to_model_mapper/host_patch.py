from models import HostReplacement, HostUpdate, HostUpdateChanges
from rpp_schema_validator import validate_schema
from . import host_dns, json_patch, patch_statuses
from .common import parse_rpp, reject_operation
from .dns_records import ADDRESS_RECORDS, DNS_PARENTS
from .hosts import add_rpp_status, has_own_ns, replacement_from_rpp
from .needs_current_state import NeedsCurrentState
from .not_supported_by_epp import NotSupportedByEpp
from .rpp_models import RPPDnsRecord, RPPHost, RPPPatchOperation, RPPStatus

HOST_NAME_PATH = "/hostName"
STATUS_PATH = "/status"
RECORDS_PATH = "/dns/records"
ARRAY_PATHS = (STATUS_PATH, RECORDS_PATH)
STATE_PATHS = ("/dns", "/dns/controls")
READ_ONLY_MEMBER = "provMetadata"


def _check(operation: RPPPatchOperation):
    if operation.op not in ("add", "remove", "replace"):
        raise ValueError(f"Operation '{operation.op}' is not allowed")
    if operation.path not in (HOST_NAME_PATH, *ARRAY_PATHS, *STATE_PATHS):
        raise ValueError(f"Path '{operation.path}' cannot be changed")
    if operation.path == HOST_NAME_PATH and operation.op == "remove":
        reject_operation(operation)


class _PatchedHostUpdate:
    """Collects the effect of the patch operations on a HostUpdate."""

    def __init__(self, host_name: str):
        self.host_name = host_name
        self.new_name = None
        self.add = HostUpdateChanges()
        self.remove = HostUpdateChanges()

    def apply(self, operation: RPPPatchOperation):
        _check(operation)
        if operation.path in STATE_PATHS:
            raise NeedsCurrentState()
        if operation.path == HOST_NAME_PATH:
            self._apply_to_host_name(operation)
        else:
            self._apply_to_array(operation)

    def _apply_to_host_name(self, operation: RPPPatchOperation):
        if operation.match is not None:
            raise ValueError("'match' can only be used on an array")
        validate_schema("host.update", {"@type": "host", "hostName": operation.value})
        self.new_name = operation.value

    def _apply_to_array(self, operation: RPPPatchOperation):
        if operation.op == "add":
            if operation.match is not None:
                raise ValueError("'add' cannot be used together with 'match'")
            self._change(operation, operation.value, self.add)
        elif operation.op == "remove" and operation.match is not None:
            self._remove_element(operation)
        else:
            raise NeedsCurrentState()

    def _remove_element(self, operation: RPPPatchOperation):
        match = operation.match
        if operation.path == STATUS_PATH:
            if match.keys() != {"label"} or not patch_statuses.is_client_label(match["label"]):
                raise NeedsCurrentState()
            self.remove.status.append(match["label"])
        else:
            if "rdata" not in match or str(match.get("type")).lower() not in ADDRESS_RECORDS:
                raise NeedsCurrentState()
            self._change(operation, {"@type": "dnsRecord", "name": "@", **match}, self.remove)

    def _change(self, operation: RPPPatchOperation, element: dict, changes: HostUpdateChanges):
        if operation.path == STATUS_PATH:
            validate_schema("hostStatus.create", element)
            add_rpp_status(parse_rpp(RPPStatus, element), changes)
            return
        validate_schema("dnsRecord.create", element)
        address = host_dns.rpp_to_model(self.host_name, parse_rpp(RPPDnsRecord, element))
        if address is not None:
            family, value = address
            getattr(changes, family).append(value)

    def to_host_update(self) -> HostUpdate:
        return HostUpdate(
            name=self.host_name,
            new_name=self.new_name,
            add=self.add or None,
            remove=self.remove or None,
        )


def _operations(rpp: list) -> list[RPPPatchOperation]:
    return [parse_rpp(RPPPatchOperation, operation) for operation in rpp]


def rpp_to_model(host_name: str, rpp: list) -> HostUpdate | None:
    """Converts a partial update (JSON Patch, json draft §5.2) to a HostUpdate.

    None when an operation needs the current host, then `rpp_to_model_with_current` converts it.
    """
    update = _PatchedHostUpdate(host_name)
    try:
        for operation in _operations(rpp):
            update.apply(operation)
    except NeedsCurrentState:
        return None
    return update.to_host_update()


def rpp_to_model_with_current(host_name: str, rpp: list, current: dict) -> HostReplacement:
    """Applies the patch to the current host (its read representation) and returns the host it asks for.

    The records of the host stay under the name it has now, also when the patch renames it.
    """
    operations = _operations(rpp)
    for operation in operations:
        _check(operation)
    patched = json_patch.apply(
        patch_statuses.without_server_statuses(current), operations, ARRAY_PATHS, absent_parents=DNS_PARENTS,
    )
    patched = patch_statuses.with_server_statuses(patched, current, "hostStatus")
    validate_schema("host.read", patched)
    requested = {member: value for member, value in patched.items() if member != READ_ONLY_MEMBER}
    host_rpp = parse_rpp(RPPHost, {**requested, "hostName": current["hostName"]})
    wanted = replacement_from_rpp(host_name, host_rpp)
    if not has_own_ns(host_rpp):
        raise NotSupportedByEpp("Removing the 'ns' record of the host")
    wanted.new_name = patched["hostName"]
    return wanted
