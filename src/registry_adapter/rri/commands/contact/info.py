from core.result.result_code import ResultCode
from registry_adapter.rri.commands.contact.common import CONTACT_CODES, REQUEST, contact_from_rri
from registry_adapter.rri.commands.shared.rri_command import data_of, refused, run
from registry_adapter.rri.xml.generated.contact_5_0 import Info, InfoData


def rri_contact_info(client, handle: str, client_transaction_id=None):
    """Contact INFO, of the RegAcc's own handles only. A REQUEST contact (a URI template for the General Request or
    Abuse role) has no form in RPP yet (gap Q2)."""
    resp = run(client, client_transaction_id, codes=CONTACT_CODES, write=False, payload_of=lambda t: data_of(t, InfoData),
               info=Info(handle=handle))
    data = getattr(resp, "payload", None)
    if data is None:
        return resp
    if data.type_value is not None and data.type_value.value == REQUEST:
        return refused(ResultCode.UNIMPLEMENTED_OPTION, "A REQUEST contact of RRI has no form in RPP",
                       client_transaction_id)
    resp.payload = contact_from_rri(data)
    return resp
