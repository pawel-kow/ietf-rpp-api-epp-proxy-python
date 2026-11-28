from core.model.message.message_error_response import MessageErrorResponse
from core.model.message.message_queue import MessageQueue
from core.model.message.queue_message import QueueMessage
from core.model.message.transfer_event import TransferEvent
from core.model.shared.contact_transfer_process import ContactTransferProcess
from core.result.operation_response import OperationResponse
from core.result.result_code import ResultCode
from registry_adapter.sqlite.clock import new_server_transaction_id
from registry_adapter.sqlite.models.message_row import MessageRow
from registry_adapter.sqlite.sqlite_context import SqliteContext


def _is_id(message_id) -> bool:
    """A message id is the decimal digits of ASCII: `isdecimal` alone takes those of other scripts."""
    text = str(message_id)
    return text.isascii() and text.isdecimal()


def _message(row: MessageRow) -> QueueMessage:
    process = ContactTransferProcess(
        id=row.object_id, trStatus=row.tr_status, reqClientId=row.requesting_client, requestDate=row.request_date,
        actClientId=row.acting_client, actionDate=row.action_date)
    event = TransferEvent(
        objectType=row.object_type, objectId=row.object_id, trStatus=row.tr_status, requestDate=row.request_date,
        actionDate=row.action_date, process=process)
    return QueueMessage(id=str(row.id), creationDate=row.created, lang=row.lang, text=row.text, event=event)


class SqliteMessageGateway:
    """The message queue of the client of the session, held in the database."""

    def __init__(self, context: SqliteContext):
        self._context = context

    def _answer(self, code: ResultCode, msg: str, payload, client_transaction_id) -> OperationResponse:
        return OperationResponse(code=code, msg=msg, server_transaction_id=new_server_transaction_id(),
                                 client_transaction_id=client_transaction_id, payload=payload)

    def poll(self, client_transaction_id=None, message_types=None):
        client, store = self._context.sponsor_id, self._context.messages
        with self._context.database.transaction() as session:
            row, size = store.head(session, client), store.size(session, client)
            message = None if row is None else _message(row)
        if message is None:
            return self._answer(ResultCode.COMMAND_COMPLETED_NO_MESSAGES, "Command completed successfully; no messages",
                                MessageQueue(queue_size=0), client_transaction_id)
        return self._answer(ResultCode.COMMAND_COMPLETED_ACK_TO_DEQUEUE, "Command completed successfully; ack to dequeue",
                            MessageQueue(queue_size=size, message=message), client_transaction_id)

    def find(self, message_id, client_transaction_id=None):
        return None

    def ack(self, message_id, client_transaction_id=None):
        client, store = self._context.sponsor_id, self._context.messages
        with self._context.database.transaction() as session:
            row = session.get(MessageRow, int(message_id)) if _is_id(message_id) else None
            if row is None or row.client != client:
                return MessageErrorResponse(
                    queue_size=store.size(session, client), code=ResultCode.OBJECT_DOES_NOT_EXIST,
                    msg=f"Message {message_id} does not exist", server_transaction_id=new_server_transaction_id(),
                    client_transaction_id=client_transaction_id)
            session.delete(row)
            session.flush()
            size = store.size(session, client)
        return self._answer(ResultCode.COMMAND_COMPLETED_SUCCESSFULLY, "Command completed successfully",
                            MessageQueue(queue_size=size), client_transaction_id)
