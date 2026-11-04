from models import (
    ContactMinimal, ContactReferenceNew, DomainUpdate, DomainUpdateAdd, DomainUpdateChange,
    DomainUpdateRemove, HostObj, NS,
)
from rpp_schema_validator import validate_schema
from .common import parse_rpp, reject_operation, rpp_to_auth_info
from .domains import REGISTRANT, check_contact_label
from .rpp_models import (
    RPPAuthInfo, RPPContactReference, RPPHostReference, RPPLabelledContact, RPPPatchOperation,
)

ARRAY_PATHS = ("/nameservers", "/contacts")
OBJECT_PATHS = ("/registrant", "/authInfo")
UNSUPPORTED_PATHS = ("/status", "/dns")


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

    def apply(self, operation: RPPPatchOperation):
        if operation.op not in ("add", "remove", "replace"):
            raise ValueError(f"Operation '{operation.op}' is not allowed")
        if operation.path in UNSUPPORTED_PATHS:
            reject_operation(operation)
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
            reject_operation(operation)

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
                reject_operation(operation)
            self.remove_hosts.append(HostObj(id=operation.match["hostName"]))
        else:
            contact = _matched_contact(operation.match)
            if contact is None:
                reject_operation(operation)
            self.remove_contacts.append(contact)

    def _apply_to_object(self, operation: RPPPatchOperation):
        if operation.match is not None:
            raise ValueError("'match' can only be used on an array")
        if operation.path == "/registrant":
            self._apply_to_registrant(operation)
        elif operation.op == "remove":
            reject_operation(operation)
        else:
            _validated("authInfo", operation.value)
            self.auth_info = rpp_to_auth_info(parse_rpp(RPPAuthInfo, operation.value))

    def _apply_to_registrant(self, operation: RPPPatchOperation):
        if operation.op == "remove":
            self.remove_contacts.append(_contact(REGISTRANT, ""))
        else:
            _validated("registrant", operation.value)
            registrant = parse_rpp(RPPContactReference, operation.value)
            self.add_contacts.append(_contact(REGISTRANT, registrant.id))

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
            change=DomainUpdateChange(authInfo=self.auth_info) if self.auth_info else None,
        )


def rpp_to_domain_update(domain_name: str, rpp: list) -> DomainUpdate:
    """Converts a partial update (JSON Patch, json draft §5.2) to a DomainUpdate."""
    update = _PatchedUpdate()
    for operation in rpp:
        update.apply(parse_rpp(RPPPatchOperation, operation))
    return update.to_domain_update(domain_name)
