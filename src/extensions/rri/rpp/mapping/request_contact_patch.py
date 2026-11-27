from extensions.rri.core.model.request_contact import RequestContact
from rpp.dto.rpp_patch_operation import RPPPatchOperation
from extensions.rri.rpp.mapping import request_contacts
from extensions.rri.rpp.mapping.request_contact_replacement import CHANGEABLE
from rpp.mapping.shared import json_patch
from rpp.mapping.shared.common import parse_rpp
from rpp.schema.validator import validate_request_schema

PATHS = tuple(f"/{member}" for member in CHANGEABLE)


def _check(operation: RPPPatchOperation):
    if operation.op not in ("add", "remove", "replace"):
        raise ValueError(f"Operation '{operation.op}' is not allowed")
    if operation.path not in PATHS:
        raise ValueError(f"Path '{operation.path}' cannot be changed")


def rpp_to_model_with_current(contact_id: str, rpp: list, current: RequestContact,
                              extensions: tuple[str, ...] = ()) -> RequestContact:
    """Applies the patch (json §5.2.2) to the current request contact, read for it, and returns the request
    contact it asks for. Only the template can change, and it cannot be removed."""
    operations = [parse_rpp(RPPPatchOperation, operation) for operation in rpp]
    for operation in operations:
        _check(operation)
    patched = json_patch.apply(request_contacts.model_to_rpp(current, extensions), operations, array_paths=())
    validate_request_schema("requestContact.read", patched, extensions, patched=True)
    return RequestContact(id=contact_id, uriTemplate=patched["uriTemplate"])
