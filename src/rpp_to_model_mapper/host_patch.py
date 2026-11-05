from models import HostUpdate, HostUpdateChanges
from rpp_schema_validator import validate_schema
from . import host_dns
from .common import parse_rpp, reject_operation
from .hosts import add_rpp_status
from .rpp_models import RPPDnsRecord, RPPPatchOperation, RPPStatus

HOST_NAME_PATH = "/hostName"
STATUS_PATH = "/status"
RECORDS_PATH = "/dns/records"
UNSUPPORTED_PATHS = ("/dns", "/dns/controls")


class _PatchedHostUpdate:
    """Collects the effect of the patch operations on a HostUpdate."""

    def __init__(self, host_name: str):
        self.host_name = host_name
        self.new_name = None
        self.add = HostUpdateChanges()
        self.remove = HostUpdateChanges()

    def apply(self, operation: RPPPatchOperation):
        if operation.op not in ("add", "remove", "replace"):
            raise ValueError(f"Operation '{operation.op}' is not allowed")
        if operation.path in UNSUPPORTED_PATHS:
            reject_operation(operation)
        if operation.path == HOST_NAME_PATH:
            self._apply_to_host_name(operation)
        elif operation.path in (STATUS_PATH, RECORDS_PATH):
            self._apply_to_array(operation)
        else:
            raise ValueError(f"Path '{operation.path}' cannot be changed")

    def _apply_to_host_name(self, operation: RPPPatchOperation):
        if operation.match is not None:
            raise ValueError("'match' can only be used on an array")
        if operation.op == "remove":
            reject_operation(operation)
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
            reject_operation(operation)

    def _remove_element(self, operation: RPPPatchOperation):
        match = operation.match
        if operation.path == STATUS_PATH:
            if "label" not in match:
                reject_operation(operation)
            self.remove.status.append(match["label"])
        else:
            if "type" not in match or "rdata" not in match:
                reject_operation(operation)
            self._change(operation, {"@type": "dnsRecord", "name": "@", **match}, self.remove)

    def _change(self, operation: RPPPatchOperation, element: dict, changes: HostUpdateChanges):
        if operation.path == STATUS_PATH:
            validate_schema("hostStatus.create", element)
            add_rpp_status(parse_rpp(RPPStatus, element), changes)
            return
        validate_schema("dnsRecord.create", element)
        address = host_dns.rpp_to_model(self.host_name, parse_rpp(RPPDnsRecord, element))
        if address is None:
            reject_operation(operation)
        family, value = address
        getattr(changes, family).append(value)

    def to_host_update(self) -> HostUpdate:
        return HostUpdate(
            name=self.host_name,
            new_name=self.new_name,
            add=self.add or None,
            remove=self.remove or None,
        )


def rpp_to_model(host_name: str, rpp: list) -> HostUpdate:
    """Converts a partial update (JSON Patch, json draft §5.2) to a HostUpdate."""
    update = _PatchedHostUpdate(host_name)
    for operation in rpp:
        update.apply(parse_rpp(RPPPatchOperation, operation))
    return update.to_host_update()
