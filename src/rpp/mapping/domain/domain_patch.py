from core.model.contact.contacts import ContactMinimal
from core.model.domain.domain_replacement import DomainReplacement
from core.model.domain.domains import (
    ContactReferenceNew, DomainUpdate, DomainUpdateAdd, DomainUpdateChange, DomainUpdateRemove, HostObj, NS,
)
from core.capabilities.backend_profile import BackendProfile
from rpp.schema.validator import validate_schema
from rpp.mapping.domain import domain_wanted
from rpp.mapping.shared import auth_info, include_elements, json_patch, patch_statuses
from rpp.mapping.shared.common import parse_rpp
from rpp.mapping.shared.dns_records import DNS_PARENTS
from rpp.mapping.domain.domains import REGISTRANT, check_contact_label
from rpp.mapping.shared.needs_current_state import NeedsCurrentState
from rpp.dto.rpp_auth_info import RPPAuthInfo
from rpp.dto.rpp_contact_reference import RPPContactReference
from rpp.dto.rpp_host_reference import RPPHostReference
from rpp.dto.rpp_labelled_contact import RPPLabelledContact
from rpp.dto.rpp_patch_operation import RPPPatchOperation

ARRAY_PATHS = ("/nameservers", "/contacts")
READ_ARRAY_PATHS = ARRAY_PATHS + ("/status", "/dns/records")
OBJECT_PATHS = ("/registrant", "/authInfo")
STATE_PATHS = ("/status", "/dns", "/dns/records", "/dns/controls")
AUTH_INFO_PATH = "/authInfo"
OBJECT = "domainName"


def _validated(member: str, value):
    """Validates a patch value as a member of a domain update."""
    validate_schema("domainName.update", {"@type": "domainName", member: value})
    return value


def _contact(label: str, contact_id: str) -> ContactReferenceNew:
    return ContactReferenceNew(type=label, contact=ContactMinimal(id=contact_id))


def _matched_contact(match: dict, profile: BackendProfile) -> ContactReferenceNew | None:
    """EPP removes a contact by role and id, so the match must name both."""
    target = match.get("object")
    if "label" not in match or not isinstance(target, dict) or "id" not in target:
        return None
    return _contact(check_contact_label(match["label"], profile), target["id"])


class _PatchedUpdate:
    """Collects the effect of the patch operations on a DomainUpdate."""

    def __init__(self, profile: BackendProfile):
        self.profile = profile
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
            self.add_contacts.append(_contact(check_contact_label(contact.label, self.profile), contact.object.id))

    def _remove_element(self, operation: RPPPatchOperation):
        if operation.path == "/nameservers":
            if "hostName" not in operation.match:
                raise NeedsCurrentState()
            self.remove_hosts.append(HostObj(id=operation.match["hostName"]))
        else:
            contact = _matched_contact(operation.match, self.profile)
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


def rpp_to_model(domain_name: str, rpp: list, *, profile: BackendProfile) -> DomainUpdate | None:
    """Converts a partial update (JSON Patch, json draft §5.2) to a DomainUpdate.

    None when an operation needs the current domain, then `rpp_to_model_with_current` converts it.
    """
    update = _PatchedUpdate(profile)
    try:
        for operation in _operations(rpp):
            update.apply(operation)
    except NeedsCurrentState:
        return None
    return update.to_domain_update(domain_name)


def rpp_to_model_with_current(domain_name: str, rpp: list, current: dict, *, profile: BackendProfile) -> DomainReplacement:
    """Applies the patch to the current domain (its read representation) and returns the domain it asks for.

    A read need not show a data element with onDemand Visibility (`authInfo`), so its operations are converted as
    without the current domain, and one that no operation names is left as it is.
    """
    operations = _operations(rpp)
    patched = json_patch.apply(
        patch_statuses.without_server_statuses(current), operations, READ_ARRAY_PATHS,
        ignored_paths=include_elements.on_demand_paths(OBJECT), absent_parents=DNS_PARENTS,
    )
    patched = patch_statuses.with_server_statuses(patched, current, "domainStatus")
    validate_schema("domainName.read", patched)
    domain_wanted.reject_other_changes(current, patched)
    auth_info_update = _PatchedUpdate(profile)
    for operation in operations:
        if operation.path == AUTH_INFO_PATH:
            auth_info_update.apply(operation)
    unchanged = include_elements.left_alone_by_patch(OBJECT, [operation.path for operation in operations])
    return domain_wanted.rpp_to_model(domain_name, patched, auth_info_update.auth_info, unchanged, profile=profile)
