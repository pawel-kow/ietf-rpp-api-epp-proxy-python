from registry_adapter.rri.commands.organisation.common import organisation_from_rri
from registry_adapter.rri.commands.shared.rri_command import data_of, run
from registry_adapter.rri.xml.generated.regacc_5_0 import Info, InfoData


def rri_organisation_info(client, handle: str, client_transaction_id=None, parts=()):
    """regacc INFO of any RegAcc, with its `Organisation` as the payload. It costs no write: it has no CTID."""
    resp = run(client, client_transaction_id, write=False, payload_of=lambda t: data_of(t, InfoData), info_2=Info(handle=handle))
    data = getattr(resp, "payload", None)
    if data is not None:
        resp.payload = organisation_from_rri(data, parts)
    return resp
