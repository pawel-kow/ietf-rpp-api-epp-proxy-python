import uuid
from datetime import timezone

from .epp_core import map_epp_code
from .epp_model.epp_1_0 import Epp


def parse_epp_response_header(epp: Epp) -> dict:
    return {
        "code": map_epp_code(epp.response.result[0].code.value),
        "msg": epp.response.result[0].msg.value,
        "server_transaction_id": epp.response.tr_id.sv_trid,
        "client_transaction_id": epp.response.tr_id.cl_trid,
    }


def find_res_data(epp: Epp, *types):
    """Return the first res_data element matching one of the given xsdata types."""
    if epp.response is None or epp.response.res_data is None:
        return None
    for item in epp.response.res_data.other_element:
        if isinstance(item, types):
            return item
    return None


def find_extension(epp: Epp, extension_type):
    """Return the first response extension of the given xsdata type."""
    if epp.response is None or epp.response.extension is None:
        return None
    for item in epp.response.extension.other_element:
        if isinstance(item, extension_type):
            return item
    return None


def cl_trid(client_request_id) -> str:
    return client_request_id if client_request_id else str(uuid.uuid4())


def epp_datetime(value):
    """UTC ISO form with fractional seconds and a trailing "Z", matching the EPP wire format."""
    if value is None:
        return None
    return value.to_datetime().astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def status_reasons(data) -> dict[str, str]:
    """The status texts of an Info that say something: the backend repeats the label there (#54)."""
    return {s.s.value: s.value for s in getattr(data, "status", []) if s.value and s.value != s.s.value}
