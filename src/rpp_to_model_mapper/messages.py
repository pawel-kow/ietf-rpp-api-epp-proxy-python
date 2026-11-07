import logging
from datetime import datetime, timezone

from models import ContactTransferProcess, PendingActionEvent, QueueMessage, TransferEvent
from rpp_schema_validator import validate_schema
from . import contact_transfer_process, domain_transfer_process
from .rpp_models import (
    RPPMessage, RPPReviewResponseMessage, RPPServiceNoticeMessage, RPPTransferOutcomeMessage,
    RPPTransferRequestMessage,
)

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


def _typed(message: QueueMessage):
    event = message.event
    if isinstance(event, TransferEvent):
        return _transfer(event)
    return RPPReviewResponseMessage(
        objectType=event.objectType, objectId=event.objectId, approved=event.approved,
        clientTransactionId=event.clientTransactionId, serverTransactionId=event.serverTransactionId,
        completionDate=event.completionDate, message=message.text,
    )


def _notice(message: QueueMessage, unmapped: str | None) -> RPPServiceNoticeMessage:
    text = message.text
    if unmapped:
        text = f"{text} (The EPP message carried data the proxy cannot translate: {unmapped}.)".strip()
    return RPPServiceNoticeMessage(message=text)


def _envelope(message: QueueMessage, data) -> dict:
    # EPP leaves qDate optional and RPP requires creationDate: the time of the read stands in.
    created = message.creationDate or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    return RPPMessage(id=message.id, creationDate=created, status=QUEUED, data=data.to_rpp()).to_rpp()


def model_to_rpp(message: QueueMessage) -> dict:
    """A message that cannot become a valid typed message becomes a service notice, so that it can
    still be read and acknowledged, which a client cannot do past a message that fails."""
    if message.event is not None:
        try:
            rpp = _envelope(message, _typed(message))
            validate_schema("message.read", rpp)
            return rpp
        except Exception as e:
            logger.warning("Poll message %s is a service notice, its data does not map: %s", message.id, type(e).__name__)
            message = QueueMessage(**{**message.__dict__, "event": None, "unmapped": "data that failed validation"})
    for candidate in (message, QueueMessage(**{**message.__dict__, "creationDate": None})):
        rpp = _envelope(candidate, _notice(candidate, candidate.unmapped))
        try:
            validate_schema("message.read", rpp)
            return rpp
        except Exception:
            continue
    raise ValueError("The message cannot be represented")
