"""`chprovAuthInfo`, the notification of the losing RegAcc that a domain was moved away by CHPROV, is the transfer outcome of RPP:
approved by the server, the process with the gaining client (docs/rri/rri-extension.md, Mapping to DENIC RRI). It needs no extension."""
from core.model.message.transfer_event import TransferEvent
from core.model.shared.domain_transfer_process import DomainTransferProcess
from registry_adapter.rri.commands.shared.rri_time import utc_time
from registry_adapter.rri.message_type import RriMessageType
from registry_adapter.rri.xml.generated.message_5_0 import Message, MsgTypeType

SERVER_APPROVED = "serverApproved"


def _transfer_outcome(message: Message) -> TransferEvent:
    """The request date and the action date are the time of the message, the gaining client (`msg:new`) requested and acted.
    `msg:old`, the receiving RegAcc, is not represented."""
    element = message.chprov_auth_info
    moment = utc_time(message.msgtime)
    process = DomainTransferProcess(name=element.domain.ace, trStatus=SERVER_APPROVED, reqClientId=element.new, requestDate=moment,
                                    actClientId=element.new, actionDate=moment)
    return TransferEvent(objectType="domainName", objectId=element.domain.ace, trStatus=SERVER_APPROVED,
                         requestDate=moment, actionDate=moment, process=process)


TRANSFER_OUTCOME = RriMessageType(msg_type=MsgTypeType.CHPROV_AUTH_INFO, identifier="transferOutcomeMessage",
                                  translate=_transfer_outcome)
