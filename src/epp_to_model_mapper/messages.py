import logging

from models import (
    AckResponse, ContactTransferProcess, DomainTransferProcess, PendingActionEvent, PollResponse, QueueMessage,
    ResultCode, TransferEvent,
)
from .commands.helper import epp_to_str, str_to_epp
from .commands.messages import poll_ack, poll_request
from .epp_model import contact_1_0, domain_1_0, host_1_0
from .epp_model.epp_1_0 import Epp
from .epp_response import cl_trid, epp_datetime, parse_epp_response_header

logger = logging.getLogger("uvicorn.error")

DOMAIN_NAME = "domainName"
CONTACT = "contact"
HOST = "host"


def poll_request_xml(client_request_id=None) -> str:
    return epp_to_str(poll_request(cl_trid(client_request_id)))


def poll_ack_xml(message_id: str, client_request_id=None) -> str:
    return epp_to_str(poll_ack(message_id, cl_trid(client_request_id)))


def _text(msg) -> str:
    """The text of a message, which EPP allows to hold markup: its text nodes, in order."""
    if msg is None:
        return ""
    return " ".join(part.strip() for part in _text_nodes(msg.content) if part.strip())


def _text_nodes(content):
    for item in content:
        if isinstance(item, str):
            yield item
        else:
            if getattr(item, "text", None):
                yield item.text
            yield from _text_nodes(getattr(item, "children", None) or [])
            if getattr(item, "tail", None):
                yield item.tail


def _domain_process(data) -> DomainTransferProcess:
    return DomainTransferProcess(
        name=data.name,
        trStatus=data.tr_status.value,
        reqClientId=data.re_id,
        requestDate=epp_datetime(data.re_date),
        actClientId=data.ac_id,
        actionDate=epp_datetime(data.ac_date),
        expiryDate=epp_datetime(data.ex_date),
    )


def _contact_process(data) -> ContactTransferProcess:
    return ContactTransferProcess(
        id=data.id,
        trStatus=data.tr_status.value,
        reqClientId=data.re_id,
        requestDate=epp_datetime(data.re_date),
        actClientId=data.ac_id,
        actionDate=epp_datetime(data.ac_date),
    )


def _transfer_event(object_type, object_id, process, data) -> TransferEvent:
    return TransferEvent(
        objectType=object_type,
        objectId=object_id,
        trStatus=data.tr_status.value,
        requestDate=epp_datetime(data.re_date),
        actionDate=epp_datetime(data.ac_date),
        expiryDate=epp_datetime(getattr(data, "ex_date", None)),
        process=process,
    )


def _pending_action_event(object_type, id_element, data) -> PendingActionEvent:
    return PendingActionEvent(
        objectType=object_type,
        objectId=id_element.value,
        approved=bool(id_element.pa_result),
        clientTransactionId=data.pa_trid.cl_trid,
        serverTransactionId=data.pa_trid.sv_trid,
        completionDate=epp_datetime(data.pa_date),
    )


def _event(data):
    """The event of a known resData element."""
    if isinstance(data, domain_1_0.TrnData):
        return _transfer_event(DOMAIN_NAME, data.name, _domain_process(data), data)
    if isinstance(data, contact_1_0.TrnData):
        return _transfer_event(CONTACT, data.id, _contact_process(data), data)
    if isinstance(data, domain_1_0.PanData):
        return _pending_action_event(DOMAIN_NAME, data.name, data)
    if isinstance(data, contact_1_0.PanData):
        return _pending_action_event(CONTACT, data.id, data)
    if isinstance(data, host_1_0.PanData):
        return _pending_action_event(HOST, data.name, data)
    return None


def _describe(item) -> str:
    """The qualified name of an element the proxy does not translate. Never its content."""
    qname = getattr(item, "qname", None)
    if qname:
        return qname
    name = getattr(getattr(item, "Meta", None), "name", None)
    namespace = getattr(getattr(item, "Meta", None), "namespace", None)
    return f"{{{namespace}}}{name}" if namespace else type(item).__name__


def _translate(epp: Epp):
    """The event of a message and what was left out: (event, unmapped), at most one of them set."""
    response = epp.response
    res_data = list(response.res_data.other_element) if response.res_data is not None else []
    extension = list(response.extension.other_element) if response.extension is not None else []
    if not res_data and not extension:
        return None, None
    left_out = [_describe(item) for item in res_data + extension]
    if len(res_data) != 1 or extension:
        return None, ", ".join(left_out)
    try:
        event = _event(res_data[0])
    except Exception as e:  # a malformed element must not keep the message from being read
        logger.warning("Poll message data %s is not translated: %s", left_out[0], type(e).__name__)
        return None, left_out[0]
    return (event, None) if event is not None else (None, left_out[0])


def parse_poll_response(xml_string: str, client_transaction_id: str | None) -> PollResponse:
    """Parses the reply to poll req: 1300 has no message, 1301 has the head of the queue."""
    epp = str_to_epp(xml_string)
    header = parse_epp_response_header(epp)
    if client_transaction_id is None:
        header["client_transaction_id"] = None
    msg_q = epp.response.msg_q
    if msg_q is None or msg_q.id is None:
        empty = msg_q is None and header["code"] == ResultCode.COMMAND_COMPLETED_NO_MESSAGES
        return PollResponse(queue_size=0 if empty else (msg_q.count if msg_q else None), message=None, **header)
    event, unmapped = _translate(epp)
    message = QueueMessage(
        id=msg_q.id,
        creationDate=epp_datetime(msg_q.q_date),
        lang=msg_q.msg.lang if msg_q.msg is not None else None,
        text=_text(msg_q.msg),
        event=event,
        unmapped=unmapped,
    )
    return PollResponse(queue_size=msg_q.count, message=message, **header)


def parse_ack_response(xml_string: str, client_transaction_id: str | None) -> AckResponse:
    """Parses the reply to poll ack, whose msgQ, when present, counts what is left."""
    epp = str_to_epp(xml_string)
    header = parse_epp_response_header(epp)
    if client_transaction_id is None:
        header["client_transaction_id"] = None
    msg_q = epp.response.msg_q
    return AckResponse(queue_size=None if msg_q is None else msg_q.count, **header)
