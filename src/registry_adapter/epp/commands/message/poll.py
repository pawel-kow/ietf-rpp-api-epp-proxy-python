import logging
from typing import Union

from xsdata.models.datatype import XmlDateTime

from core.model.message.message_queue import MessageQueue
from core.model.message.pending_action_event import PendingActionEvent
from core.model.message.queue_message import QueueMessage
from core.model.message.transfer_event import TransferEvent
from core.model.shared.contact_transfer_process import ContactTransferProcess
from core.model.shared.domain_transfer_process import DomainTransferProcess
from core.result.error_response import ErrorResponse
from core.result.operation_response import OperationResponse
from core.result.result_code import ResultCode
from registry_adapter.epp.commands.message.common import (
    count_of, decode, EPP_NS, parse_error_response, raw_header, unreadable,
)
from registry_adapter.epp.commands.shared.epp_response import cl_trid, epp_datetime, parse_epp_response_header
from registry_adapter.epp.session.epp_client import EPPClient
from registry_adapter.epp.xml.codec import epp_to_str, str_to_epp
from registry_adapter.epp.xml.generated import contact_1_0, domain_1_0, host_1_0
from registry_adapter.epp.xml.generated.epp_1_0 import CommandType, Epp, PollOpType, PollType

logger = logging.getLogger("uvicorn.error")


def poll_request(rpp_cl_trid: str) -> Epp:
    return Epp(command=CommandType(poll=PollType(op=PollOpType.REQ), cl_trid=rpp_cl_trid))


DOMAIN_NAME = "domainName"


CONTACT = "contact"


HOST = "host"


def poll_request_xml(client_request_id=None, *, ns_map: dict[str, str]) -> str:
    return epp_to_str(poll_request(cl_trid(client_request_id)), ns_map)


def _describe(item) -> str:
    """The qualified name of an element the proxy does not translate. Never its content."""
    qname = getattr(item, "qname", None)
    if qname:
        return qname
    name = getattr(getattr(item, "Meta", None), "name", None)
    namespace = getattr(getattr(item, "Meta", None), "namespace", None)
    return f"{{{namespace}}}{name}" if namespace else type(item).__name__


def _text_nodes(content, lost):
    for item in content:
        if isinstance(item, str):
            yield item
            continue
        if getattr(item, "attributes", None) or getattr(item, "qname", None) is None:
            lost.append(_describe(item))  # an attribute or a typed object has no place in plain text
        if getattr(item, "text", None):
            yield item.text
        yield from _text_nodes(getattr(item, "children", None) or [], lost)
        if getattr(item, "tail", None):
            yield item.tail


def _text(msg) -> tuple[str, list[str]]:
    """The text of a message, which EPP allows to hold markup, and the markup that has no place in it."""
    if msg is None:
        return "", []
    lost: list[str] = []
    return "".join(_text_nodes(msg.content, lost)).strip(), lost


def _safe_datetime(value) -> str | None:
    """EPP leaves qDate optional and a server may send a value that is no date. Both count as missing."""
    if value is None:
        return None
    try:
        return epp_datetime(value)
    except Exception as e:
        logger.warning("Poll message has a date the proxy cannot read: %s", type(e).__name__)
        return None


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


def _object_id(value) -> str:
    """Data-objects §9.19.1: objectType is only used with an objectId."""
    if not isinstance(value, str) or not value:
        raise ValueError("The message has no object id")
    return value


def _transfer_event(object_type, object_id, process, data) -> TransferEvent:
    return TransferEvent(
        objectType=object_type,
        objectId=_object_id(object_id),
        trStatus=data.tr_status.value,
        requestDate=epp_datetime(data.re_date),
        actionDate=epp_datetime(data.ac_date),
        expiryDate=epp_datetime(getattr(data, "ex_date", None)),
        process=process,
    )


def _pending_action_event(object_type, id_element, data) -> PendingActionEvent:
    if not isinstance(id_element.pa_result, bool):
        raise ValueError("paResult is not a boolean")
    return PendingActionEvent(
        objectType=object_type,
        objectId=_object_id(id_element.value),
        approved=id_element.pa_result,
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


def _translate(epp: Epp, message_id: str):
    """The event of a message, what was left out, and the name of the data: (event, unmapped, data_name)."""
    response = epp.response
    res_data = list(response.res_data.other_element) if response.res_data is not None else []
    extension = list(response.extension.other_element) if response.extension is not None else []
    if not res_data and not extension:
        return None, None, None
    left_out = [_describe(item) for item in res_data + extension]
    if len(res_data) != 1 or extension:
        logger.warning("Poll message %r has data the proxy does not translate: %s", message_id, ", ".join(left_out))
        return None, ", ".join(left_out), None
    try:
        event = _event(res_data[0])
    except Exception as e:  # a malformed element must not keep the message from being read
        logger.warning("Poll message %r has data that does not map: %s, %s", message_id, left_out[0], type(e).__name__)
        return None, left_out[0], None
    if event is None:
        logger.warning("Poll message %r has data the proxy does not translate: %s", message_id, left_out[0])
        return None, left_out[0], None
    return event, None, left_out[0]


def _qnames(root, parent: str) -> list[str]:
    element = root.find(f"./epp:response/epp:{parent}", EPP_NS)
    return [] if element is None else [child.tag for child in element if isinstance(child.tag, str)]


def _no_message(header, size) -> OperationResponse[MessageQueue]:
    return OperationResponse(payload=MessageQueue(queue_size=size, message=None), **header)


def _poll_from_markup(xml_string: str, client_transaction_id) -> OperationResponse[MessageQueue] | ErrorResponse:
    """What can be read of a reply the typed parser rejects: the message as a notice that names its data."""
    root = decode(xml_string)
    header = raw_header(root, client_transaction_id)
    if header is None:
        return unreadable(header, client_transaction_id)
    msg_q = root.find("./epp:response/epp:msgQ", EPP_NS)
    if msg_q is None or not msg_q.get("id"):
        if header["code"] == ResultCode.COMMAND_COMPLETED_ACK_TO_DEQUEUE:
            return unreadable(header, client_transaction_id)
        return _no_message(header, 0 if header["code"] == ResultCode.COMMAND_COMPLETED_NO_MESSAGES else None)
    left_out = _qnames(root, "resData") + _qnames(root, "extension")
    msg = msg_q.find("epp:msg", EPP_NS)
    q_date = msg_q.find("epp:qDate", EPP_NS)
    try:
        created = _safe_datetime(XmlDateTime.from_string((q_date.text or "").strip())) if q_date is not None else None
    except Exception:
        created = None
    if msg is not None:
        left_out += [child.tag for child in msg.iter() if child is not msg and isinstance(child.tag, str) and child.attrib]
    logger.warning(
        "Poll message %r was not read as typed data, its data is not translated: %s", msg_q.get("id"), ", ".join(left_out),
    )
    message = QueueMessage(
        id=msg_q.get("id"),
        creationDate=created,
        lang=(msg.get("lang") or "en") if msg is not None else None,
        text="".join(msg.itertext()).strip() if msg is not None else "",
        unmapped=", ".join(left_out) or "the reply, which does not follow the EPP schema",
    )
    return OperationResponse(payload=MessageQueue(queue_size=count_of(msg_q), message=message), **header)


def parse_poll_response(xml_string: str, client_transaction_id: str | None) -> OperationResponse[MessageQueue] | ErrorResponse:
    """Parses the reply to poll req: 1300 has no message, 1301 has the head of the queue.

    A reply that does not follow the EPP schema still gives its message, as a notice, because a
    message that cannot be read cannot be acknowledged, and the queue would stay blocked behind it.
    """
    try:
        epp = str_to_epp(xml_string)
        header = parse_epp_response_header(epp)
        if client_transaction_id is None:
            header["client_transaction_id"] = None
        msg_q = epp.response.msg_q
        if msg_q is None or not msg_q.id:
            if header["code"] == ResultCode.COMMAND_COMPLETED_ACK_TO_DEQUEUE:
                return unreadable(header, client_transaction_id)
            empty = msg_q is None and header["code"] == ResultCode.COMMAND_COMPLETED_NO_MESSAGES
            return _no_message(header, 0 if empty else (msg_q.count if msg_q else None))
        event, unmapped, data_name = _translate(epp, msg_q.id)
        text, lost = _text(msg_q.msg)
        if lost:
            logger.warning("Poll message %r has markup in its text: %s", msg_q.id, ", ".join(lost))
            unmapped = ", ".join(filter(None, [unmapped, *lost]))
        message = QueueMessage(
            id=msg_q.id,
            creationDate=_safe_datetime(msg_q.q_date),
            lang=msg_q.msg.lang if msg_q.msg is not None else None,
            text=text,
            event=event,
            unmapped=unmapped,
            data_name=data_name,
        )
        return OperationResponse(payload=MessageQueue(queue_size=msg_q.count, message=message), **header)
    except Exception as e:
        logger.warning("Poll reply does not follow the EPP schema: %s", type(e).__name__)
        return _poll_from_markup(xml_string, client_transaction_id)


def epp_messages_Poll(epp_client: EPPClient, client_transaction_id=None, *, ns_map: dict[str, str]) -> Union[OperationResponse[MessageQueue], ErrorResponse]:
    """
    Reads the message at the head of the queue of the registrar, with EPP poll req.
    Args:
        epp_client (EPPClient): The EPP client instance.
        client_transaction_id (str): The client transaction ID for the request.
    Returns:
        OperationResponse[MessageQueue]: The message, or none when the queue is empty.
    """
    success, code, response = epp_client.send_and_get_response(poll_request_xml(client_transaction_id, ns_map=ns_map))
    if success:
        return parse_poll_response(response, client_transaction_id=client_transaction_id)
    return parse_error_response(response, client_transaction_id)
