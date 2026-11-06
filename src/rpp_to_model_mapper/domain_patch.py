from models import (
    ContactMinimal, ContactReferenceNew, DomainUpdate, DomainUpdateAdd, DomainUpdateChange,
    DomainUpdateRemove, HostObj, NS,
)
from rpp_schema_validator import validate_schema
from . import auth_info, domain_patch_difference, json_patch
from .common import parse_rpp
from .domains import REGISTRANT, check_contact_label
from .needs_current_state import NeedsCurrentState
from .rpp_models import (
    RPPAuthInfo, RPPContactReference, RPPHostReference, RPPLabelledContact, RPPPatchOperation,
)

ARRAY_PATHS = ("/nameservers", "/contacts")
READ_ARRAY_PATHS = ARRAY_PATHS + ("/status", "/dns/records")
OBJECT_PATHS = ("/registrant", "/authInfo")
STATE_PATHS = ("/status", "/dns")
AUTH_INFO_PATH = "/authInfo"


def _validated(member: str, value):
    """Validates a patch value as a member of a domain update."""
    validate_schema("domainName.update", {"@type": "domainName", member: value})
    return value


def _contact(label: str, contact_id: str) -> ContactReferenceNew:
    return ContactReferenceNew(type=label, contact=ContactMinimal(id=contact_id))


def _matched_contact(match: dict) -> ContactReferenceNew | None:
    """EPP removes a contact by role and id, so the match must name both."""
    target = match.get("object")
    if "label" not in match or not isinstance(target, dict) or "id" not in target:
        return None
    return _contact(check_contact_label(match["label"]), target["id"])


class _PatchedUpdate:
    """Collects the effect of the patch operations on a DomainUpdate."""

    def __init__(self):
        self.add_hosts: list[HostObj] = []
        self.remove_hosts: list[HostObj] = []
        self.add_contacts: list[ContactReferenceNew] = []
        self.remove_contacts: list[ContactReferenceNew] = []
        self.auth_info = None
        self.clear_auth_info = False

    def apply(self, operation: RPPPatchOperation):
        if operation.op not in ("add", "remove", "replace"):
            raise ValueError(f"Operation '{operation.op}' is not allowed")
        if operation.path in STATE_PATHS:
            raise NeedsCurrentState()
        if operation.path in ARRAY_PATHS:
            self._apply_to_array(operation)
        elif operation.path in OBJECT_PATHS:
            self._apply_to_object(operation)
        else:
            raise ValueError(f"Path '{operation.path}' cannot be changed")

    def _apply_to_array(self, operation: RPPPatchOperation):
        if operation.op == "add":
            if operation.match is not None:
                raise ValueError("'add' cannot be used together with 'match'")
            self._add_element(operation)
        elif operation.op == "remove" and operation.match is not None:
            self._remove_element(operation)
        else:
            raise NeedsCurrentState()

    def _add_element(self, operation: RPPPatchOperation):
        if operation.path == "/nameservers":
            _validated("nameservers", [operation.value])
            host = parse_rpp(RPPHostReference, operation.value)
            self.add_hosts.append(HostObj(id=host.hostName))
        else:
            _validated("contacts", [operation.value])
            contact = parse_rpp(RPPLabelledContact, operation.value)
            self.add_contacts.append(_contact(check_contact_label(contact.label), contact.object.id))

    def _remove_element(self, operation: RPPPatchOperation):
        if operation.path == "/nameservers":
            if "hostName" not in operation.match:
                raise NeedsCurrentState()
            self.remove_hosts.append(HostObj(id=operation.match["hostName"]))
        else:
            contact = _matched_contact(operation.match)
            if contact is None:
                raise NeedsCurrentState()
            self.remove_contacts.append(contact)

    def _apply_to_object(self, operation: RPPPatchOperation):
        if operation.match is not None:
            raise ValueError("'match' can only be used on an array")
        if operation.path == "/registrant":
            self._apply_to_registrant(operation)
        elif operation.op == "remove":
            self.auth_info, self.clear_auth_info = None, True
        else:
            _validated("authInfo", operation.value)
            self.auth_info, self.clear_auth_info = auth_info.rpp_to_model(parse_rpp(RPPAuthInfo, operation.value)), False

    def _apply_to_registrant(self, operation: RPPPatchOperation):
        if operation.op == "remove":
            self.remove_contacts.append(_contact(REGISTRANT, ""))
        else:
            _validated("registrant", operation.value)
            registrant = parse_rpp(RPPContactReference, operation.value)
            self.add_contacts.append(_contact(REGISTRANT, registrant.id))

    def _change(self) -> DomainUpdateChange | None:
        if self.auth_info or self.clear_auth_info:
            return DomainUpdateChange(authInfo=self.auth_info, clear_auth_info=self.clear_auth_info)
        return None

    def to_domain_update(self, domain_name: str) -> DomainUpdate:
        add = DomainUpdateAdd(
            ns=NS(host_objs=self.add_hosts, host_attrs=None) if self.add_hosts else None,
            contacts=self.add_contacts or None,
        )
        remove = DomainUpdateRemove(
            ns=NS(host_objs=self.remove_hosts, host_attrs=None) if self.remove_hosts else None,
            contacts=self.remove_contacts or None,
        )
        return DomainUpdate(
            name=domain_name,
            add=add if add.ns or add.contacts else None,
            remove=remove if remove.ns or remove.contacts else None,
            change=self._change(),
        )


def _operations(rpp: list) -> list[RPPPatchOperation]:
    return [parse_rpp(RPPPatchOperation, operation) for operation in rpp]


def rpp_to_model(domain_name: str, rpp: list) -> DomainUpdate | None:
    """Converts a partial update (JSON Patch, json draft §5.2) to a DomainUpdate.

    None when an operation needs the current domain, then `rpp_to_model_with_current` converts it.
    """
    update = _PatchedUpdate()
    try:
        for operation in _operations(rpp):
            update.apply(operation)
    except NeedsCurrentState:
        return None
    return update.to_domain_update(domain_name)


def rpp_to_model_with_current(domain_name: str, rpp: list, current: dict) -> DomainUpdate:
    """Applies the patch to the current domain (its read representation) and returns the difference as an update.

    `authInfo` is not part of a read, so its operations are converted as without the current domain.
    """
    operations = _operations(rpp)
    patched = json_patch.apply(current, operations, READ_ARRAY_PATHS, ignored_path=AUTH_INFO_PATH)
    validate_schema("domainName.read", patched)
    update = domain_patch_difference.difference(domain_name, current, patched)
    auth_info_update = _PatchedUpdate()
    for operation in operations:
        if operation.path == AUTH_INFO_PATH:
            auth_info_update.apply(operation)
    update.change = auth_info_update.to_domain_update(domain_name).change
    return update
