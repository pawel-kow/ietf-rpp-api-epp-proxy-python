import logging
from dataclasses import replace
from datetime import datetime, timezone

from core.model.message.extension_event import ExtensionEvent
from core.model.message.pending_action_event import PendingActionEvent
from core.model.message.queue_message import QueueMessage
from core.model.message.transfer_event import TransferEvent
from core.model.shared.contact_transfer_process import ContactTransferProcess
from rpp.dto.rpp_message import RPPMessage
from rpp.dto.rpp_review_response_message import RPPReviewResponseMessage
from rpp.dto.rpp_service_notice_message import RPPServiceNoticeMessage
from rpp.dto.rpp_transfer_outcome_message import RPPTransferOutcomeMessage
from rpp.dto.rpp_transfer_request_message import RPPTransferRequestMessage
from rpp.mapping.contact import contact_transfer_process
from rpp.mapping.domain import domain_transfer_process
from rpp.mapping.message.message_mappers import MESSAGE_MAPPERS
from rpp.schema.validator import validate_schema

logger = logging.getLogger("uvicorn.error")

QUEUED = "queued"  # core §16.10.1: in the EPP Compatibility Profile the messages remain queued

PENDING = "pending"


def _process(process) -> dict | None:
    if process is None:
        return None
    if isinstance(process, ContactTransferProcess):
        return contact_transfer_process.model_to_rpp(process)
    return domain_transfer_process.model_to_rpp(process)


def _transfer(event: TransferEvent):
    if event.trStatus == PENDING:
        return RPPTransferRequestMessage(
            objectType=event.objectType, objectId=event.objectId, status=event.trStatus,
            requestDate=event.requestDate, actionDate=event.actionDate, process=_process(event.process),
        )
    return RPPTransferOutcomeMessage(
        objectType=event.objectType, objectId=event.objectId, trStatus=event.trStatus,
        requestDate=event.requestDate, actionDate=event.actionDate, expiryDate=event.expiryDate,
        process=_process(event.process),
    )


def _extension_data(event: ExtensionEvent, extensions) -> dict:
    """The data an extension's mapper makes of its event, for a response preset that has the extension: any other has no
    definition for it, and the message is a service notice."""
    mapper = MESSAGE_MAPPERS.of(event.extension_id)
    if mapper is None or event.extension_id not in extensions:
        raise ValueError("The extension of the message is not in the preset of the response")
    return mapper.to_rpp(event.event)


def _typed(message: QueueMessage):
    event = message.event
    if isinstance(event, TransferEvent):
        return _transfer(event)
    return RPPReviewResponseMessage(
        objectType=event.objectType, objectId=event.objectId, approved=event.approved,
        clientTransactionId=event.clientTransactionId, serverTransactionId=event.serverTransactionId,
        completionDate=event.completionDate, message=message.text,
    )


def _notice(message: QueueMessage, unmapped: str | None, backend_name: str) -> RPPServiceNoticeMessage:
    text = message.text
    if unmapped:
        text = f"{text} (The {backend_name} message carried data the proxy cannot translate: {unmapped}.)".strip()
    return RPPServiceNoticeMessage(message=text)


def _created(message: QueueMessage) -> str:
    """creationDate is required in RPP and qDate optional in EPP. The date of the event stands in, else the
    time of the read, so without a qDate the value can differ between two reads of the message."""
    if message.creationDate:
        return message.creationDate
    if isinstance(message.event, TransferEvent) and message.event.requestDate:
        return message.event.requestDate
    if isinstance(message.event, PendingActionEvent) and message.event.completionDate:
        return message.event.completionDate
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _envelope(message: QueueMessage, created: str, data) -> dict:
    return RPPMessage(id=message.id, creationDate=created, status=QUEUED, data=data if isinstance(data, dict) else data.to_rpp()).to_rpp()


def model_to_rpp(message: QueueMessage, *, backend_name: str, extensions: tuple[str, ...] = ()) -> dict:
    """A message that cannot become a valid typed message becomes a service notice, so that it can
    still be read and acknowledged, which a client cannot do past a message that fails. The notice names the backend
    the message came from. `extensions` are those of the preset the response is under: the message types of an extension
    are in its schema only."""
    created = _created(message)
    if message.event is not None:
        try:
            data = _extension_data(message.event, extensions) if isinstance(message.event, ExtensionEvent) else _typed(message)
            rpp = _envelope(message, created, data)
            validate_schema("message.read", rpp, extensions)
            return rpp
        except Exception as e:
            name = message.data_name or "data"
            logger.warning("Poll message %r is a service notice, its data %s does not map: %s", message.id, name, type(e).__name__)
            message = replace(message, event=None, unmapped=f"{name}, which failed validation")
    rpp = _envelope(message, created, _notice(message, message.unmapped, backend_name))
    validate_schema("message.read", rpp, extensions)
    return rpp
