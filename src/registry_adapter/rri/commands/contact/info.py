from core.result.result_code import ResultCode
from registry_adapter.rri.commands.contact.common import CONTACT_CODES, REQUEST, contact_from_rri
from registry_adapter.rri.commands.shared.rri_command import data_of, refused, run
from registry_adapter.rri.xml.generated.contact_5_0 import Info, InfoData


def rri_info(client, handle: str, client_transaction_id=None):
    """Contact INFO, of the RegAcc's own handles only, with the `InfoData` as its payload: a contact of any type. Its reply
    can hold verification information, so it is not printed."""
    return run(client, client_transaction_id, codes=CONTACT_CODES, write=False, loggable=False,
               payload_of=lambda t: data_of(t, InfoData), info=Info(handle=handle))


def is_request(data: InfoData) -> bool:
    return data.type_value is not None and data.type_value.value == REQUEST


def not_found(handle: str, what: str, client_transaction_id):
    """A handle of the other kind: RRI's contacts and request contacts share one namespace, RPP's do not."""
    return refused(ResultCode.OBJECT_DOES_NOT_EXIST, f"{handle} is not {what}", client_transaction_id)


def rri_contact_info(client, handle: str, client_transaction_id=None, members: dict | None = None):
    """Contact INFO of a PERSON or an ORG. A REQUEST contact is a request contact, not a contact (gap Q2). `members` are
    the contact members of the extensions (`RriExtensionPart.contact_members`, by extension id), which read what they add."""
    resp = rri_info(client, handle, client_transaction_id)
    data = getattr(resp, "payload", None)
    if data is None:
        return resp
    if is_request(data):
        return not_found(handle, "a contact", client_transaction_id)
    resp.payload = contact_from_rri(data)
    resp.payload.extensions = {extension_id: member.read(data) for extension_id, member in (members or {}).items()}
    return resp
