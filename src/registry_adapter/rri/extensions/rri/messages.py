"""The notifications of the registry (QUEUE-READ) that the rri extension has a message type for (docs/rri/rri-extension.md, Mapping to
DENIC RRI): each `msgType` the extension reads, with the event of the extension's core the XML message becomes. The domain is
referred to by its A-label (`msg:ace`), a contact by its handle. Nothing but names, dates, codes and the notices' texts is
taken: the rest of a message can be personal data."""
from core.model.message.extension_event import ExtensionEvent
from extensions.rri.core.model.auth_info_message_event import AuthInfoMessageEvent
from extensions.rri.core.model.bulk_message_event import BulkMessageEvent
from extensions.rri.core.model.contact_verification_message_event import ContactVerificationMessageEvent
from extensions.rri.core.model.domain_status_message_event import DomainStatusMessageEvent
from extensions.rri.core.model.message_kind import RriMessageKind
from extensions.rri.core.model.notice_message_event import NoticeMessageEvent
from extensions.rri.core.ports.rri_gateways import EXTENSION_ID
from registry_adapter.rri.commands.shared.rri_time import utc_time
from registry_adapter.rri.extensions.messages.references import contact_reference, domain_reference, registry_notices
from registry_adapter.rri.message_type import RriMessageType
from registry_adapter.rri.statuses import status_labels
from registry_adapter.rri.xml.generated.message_5_0 import Message, MsgTypeType


def _expiry(message: Message, kind: RriMessageKind, element) -> BulkMessageEvent:
    return BulkMessageEvent(kind=kind, objects=tuple(domain_reference(domain, utc_time(domain.expire)) for domain in element.domain))


def _notice_event(kind: RriMessageKind, element, subject) -> NoticeMessageEvent:
    return NoticeMessageEvent(kind=kind, object=subject, notices=registry_notices(element.message))


def _domain_notice(kind: RriMessageKind, attribute: str):
    def translate(message: Message):
        element = getattr(message, attribute)
        return _notice_event(kind, element, domain_reference(element.domain))
    return translate


def _auth_info_expiry(message: Message):
    element = message.auth_info_expire
    return AuthInfoMessageEvent(kind=RriMessageKind.AUTH_INFO_EXPIRE, object=domain_reference(element.domain),
                                expiry_date=utc_time(element.authinfoexpire))


def _auth_info_issue(message: Message):
    return AuthInfoMessageEvent(kind=RriMessageKind.AUTH_INFO2_NOTIFY, object=domain_reference(message.auth_info2_notify.domain))


def _domain_status(message: Message):
    element = message.domain_status_update
    return DomainStatusMessageEvent(
        object=domain_reference(element.domain), status=tuple(status_labels(element.status)),
        holders=tuple(contact_reference(handle) for handle in element.holders.handle),
        hold_deadline=utc_time(element.verification_deadline_before_dedelegation)
        if element.verification_deadline_before_dedelegation else None,
        deletion_deadline=utc_time(element.verification_deadline_before_deletion)
        if element.verification_deadline_before_deletion else None,
        notices=registry_notices(element.message))


def _contact_verification(message: Message):
    element = message.contact_verification_required
    hold = element.earliest_domain_for_dedelegation
    deletion = element.earliest_domain_for_deletion
    return ContactVerificationMessageEvent(
        object=contact_reference(element.handle), claims=tuple(element.verification_claims.claim),
        referenced_domains=element.number_of_referenced_domains_total,
        earliest_hold=domain_reference(hold.domain, utc_time(hold.verification_deadline)) if hold else None,
        earliest_deletion=domain_reference(deletion.domain, utc_time(deletion.verification_deadline)),
        notices=registry_notices(element.message))


def _extension(kind: RriMessageKind, msg_type: MsgTypeType, translate) -> RriMessageType:
    return RriMessageType(msg_type=msg_type, identifier=kind.identifier,
                          translate=lambda message: ExtensionEvent(extension_id=EXTENSION_ID, event=translate(message)))


MESSAGE_TYPES = (
    _extension(RriMessageKind.EXPIRE_WARNING, MsgTypeType.EXPIRE_WARNING,
               lambda m: _expiry(m, RriMessageKind.EXPIRE_WARNING, m.expire_warning)),
    _extension(RriMessageKind.EXPIRE, MsgTypeType.EXPIRE, lambda m: _expiry(m, RriMessageKind.EXPIRE, m.expire)),
    _extension(RriMessageKind.AUTH_INFO_EXPIRE, MsgTypeType.AUTH_INFO_EXPIRE, _auth_info_expiry),
    _extension(RriMessageKind.AUTH_INFO2_NOTIFY, MsgTypeType.AUTH_INFO2_NOTIFY, _auth_info_issue),
    _extension(RriMessageKind.AUTH_INFO2_DELETE, MsgTypeType.AUTH_INFO2_DELETE,
               _domain_notice(RriMessageKind.AUTH_INFO2_DELETE, "auth_info2_delete")),
    _extension(RriMessageKind.DOMAIN_TRANSIT, MsgTypeType.DOMAIN_TRANSIT,
               _domain_notice(RriMessageKind.DOMAIN_TRANSIT, "domain_transit")),
    _extension(RriMessageKind.DOMAIN_STATUS_UPDATE, MsgTypeType.DOMAIN_STATUS_UPDATE, _domain_status),
    _extension(RriMessageKind.CONTACT_VERIFICATION_REQUIRED, MsgTypeType.CONTACT_VERIFICATION_REQUIRED, _contact_verification),
)
