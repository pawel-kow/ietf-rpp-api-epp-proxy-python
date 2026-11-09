from models import Contact, ContactUpdate, ContactUpdateChange, ContactUpdateChanges
from rpp_schema_validator import validate_schema
from . import auth_info, contact_difference, contact_replacement, contacts, json_patch, patch_statuses
from .common import parse_rpp, reject_operation, reject_set
from .needs_current_state import NeedsCurrentState
from .not_supported_by_proxy import NotSupportedByProxy
from .rpp_models import RPPAuthInfo, RPPContact, RPPPatchOperation, RPPStatus

CONTACT_INFO_PATH = "/contactInfo"
KIND_PATHS = (CONTACT_INFO_PATH, f"{CONTACT_INFO_PATH}/kind")
STATUS_PATH = "/status"
AUTH_INFO_PATH = "/authInfo"
DISCLOSE_PATH = "/disclose"
ARRAY_PATHS = (STATUS_PATH,)
# Objects the schema allows below the Card (json §5.2.2 step 2), which a read leaves out when they are empty.
ABSENT_PARENTS = {
    f"{CONTACT_INFO_PATH}/{member}": {} for member in ("organizations", "addresses", "phones", "emails", "localizations")
}
READ_ONLY_MEMBERS = ("provMetadata", "processes")


def _check(operation: RPPPatchOperation):
    if operation.op not in ("add", "remove", "replace"):
        raise ValueError(f"Operation '{operation.op}' is not allowed")
    if operation.path not in (STATUS_PATH, AUTH_INFO_PATH, DISCLOSE_PATH) and not operation.path.startswith(f"{CONTACT_INFO_PATH}/") and operation.path != CONTACT_INFO_PATH:
        raise ValueError(f"Path '{operation.path}' cannot be changed")
    if operation.path == DISCLOSE_PATH:
        raise NotSupportedByProxy("'disclose'")


class _PatchedUpdate:
    """Collects the effect of the patch operations that need no read on a ContactUpdate."""

    def __init__(self):
        self.add = ContactUpdateChanges()
        self.remove = ContactUpdateChanges()
        self.auth_info = None

    def apply(self, operation: RPPPatchOperation):
        _check(operation)
        if operation.path == AUTH_INFO_PATH:
            self._apply_to_auth_info(operation)
        elif operation.path == STATUS_PATH:
            self._apply_to_status(operation)
        else:
            raise NeedsCurrentState()

    def _apply_to_auth_info(self, operation: RPPPatchOperation):
        if operation.match is not None:
            raise ValueError("'match' can only be used on an array")
        if operation.op == "remove":
            reject_operation(operation)  # RFC 5733 has no null element, and a contact is created with one
        validate_schema("contact.update", {"@type": "contact", "contactInfo": {"@type": "Card", "version": "2.0"}, "authInfo": operation.value})
        self.auth_info = auth_info.rpp_to_model(parse_rpp(RPPAuthInfo, operation.value))

    def _apply_to_status(self, operation: RPPPatchOperation):
        if operation.op == "add" and operation.match is None:
            validate_schema("contactStatus.create", operation.value)
            status = parse_rpp(RPPStatus, operation.value)
            reject_set(due=status.due)
            self._require_one_operation_on(status.label)
            self.add.status.append(status.label)
            if status.reason:
                self.add.status_reasons[status.label] = status.reason
        elif operation.op == "remove" and operation.match is not None:
            match = operation.match
            if match.keys() != {"label"} or not patch_statuses.is_client_label(match["label"]):
                raise NeedsCurrentState()
            self._require_one_operation_on(match["label"])
            self.remove.status.append(match["label"])
        else:
            raise NeedsCurrentState()

    def _require_one_operation_on(self, label: str):
        """An add and a remove of one status are not sent together: their order would be lost."""
        if label in self.add.status or label in self.remove.status:
            raise NeedsCurrentState()

    def to_contact_update(self, contact_id: str) -> ContactUpdate:
        return ContactUpdate(
            id=contact_id,
            add=self.add or None,
            remove=self.remove or None,
            change=ContactUpdateChange(authInfo=self.auth_info) if self.auth_info else None,
        )


def _operations(rpp: list) -> list[RPPPatchOperation]:
    return [parse_rpp(RPPPatchOperation, operation) for operation in rpp]


def rpp_to_model(contact_id: str, rpp: list) -> ContactUpdate | None:
    """Converts a partial update (JSON Patch, json draft §5.2) to a ContactUpdate.

    None when an operation needs the current contact, then `rpp_to_model_with_current` converts it.
    """
    update = _PatchedUpdate()
    try:
        for operation in _operations(rpp):
            update.apply(operation)
    except NeedsCurrentState:
        return None
    return update.to_contact_update(contact_id)


def _has_organisation(card: dict) -> bool:
    localizations = (card.get("localizations") or {}).values()
    return bool(card.get("organizations")) or any(localization.get("organizations") for localization in localizations)


def _with_derived_kind(patched: dict, operations: list[RPPPatchOperation]) -> dict:
    """EPP has no kind, so a read derives it from the organisation. Unless the patch names it, it follows the end state."""
    if any(operation.path in KIND_PATHS for operation in operations):
        return patched
    card = {**patched["contactInfo"], "kind": "org" if _has_organisation(patched["contactInfo"]) else "individual"}
    return {**patched, "contactInfo": card}


def rpp_to_model_with_current(contact_id: str, rpp: list, current: Contact) -> ContactUpdate:
    """Applies the patch to the current contact (its read representation) and returns the difference as an update.

    `authInfo` is sent as the patch says and not compared, see `contact_replacement`.
    """
    operations = _operations(rpp)
    for operation in operations:
        _check(operation)
    read = contacts.model_to_rpp(current)
    patched = json_patch.apply(
        patch_statuses.without_server_statuses(read), operations, ARRAY_PATHS,
        ignored_path=AUTH_INFO_PATH, absent_parents=ABSENT_PARENTS,
    )
    patched = patch_statuses.with_server_statuses(patched, read, "contactStatus")
    validate_schema("contact.read", patched)
    requested = {member: value for member, value in _with_derived_kind(patched, operations).items() if member not in READ_ONLY_MEMBERS}
    contact_rpp = parse_rpp(RPPContact, requested)
    wanted = contact_replacement.wanted_statuses(contacts.contact_from_rpp(contact_rpp), contact_rpp)
    auth_info_update = _PatchedUpdate()
    for operation in operations:
        if operation.path == AUTH_INFO_PATH:
            auth_info_update.apply(operation)
    wanted.authInfo = auth_info_update.auth_info
    return contact_difference.difference(contact_id, current, contact_difference.with_stored_localization(wanted, current))
