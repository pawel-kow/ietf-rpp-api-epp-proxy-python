"""The message types of the rri extension (docs/rri/rri-extension.md, Message Types): the events of its core as the `data` of a
message, for the definitions `rpp:messages` of its schema maps."""
from extensions.rri.core.model.auth_info_message_event import AuthInfoMessageEvent
from extensions.rri.core.model.bulk_message_event import BulkMessageEvent
from extensions.rri.core.model.contact_verification_message_event import ContactVerificationMessageEvent
from extensions.rri.core.model.domain_status_message_event import DomainStatusMessageEvent
from extensions.rri.core.model.notice_message_event import NoticeMessageEvent
from extensions.rri.core.model.object_reference import ObjectReference
from extensions.rri.core.model.registry_notice import RegistryNotice
from extensions.rri.core.ports.rri_gateways import EXTENSION_ID


def _reference(reference: ObjectReference) -> dict:
    """An Object Reference Object, a Dated Object Reference Object where the reference has a date."""
    if reference.date is None:
        return {"@type": "objectReference", "objectType": reference.object_type, "objectId": reference.object_id}
    return {"@type": "datedObjectReference", "objectType": reference.object_type, "objectId": reference.object_id,
            "date": reference.date}


def _notice(notice: RegistryNotice) -> dict:
    rpp = {"@type": "registryNotice", "code": notice.code, "text": notice.text}
    if notice.arguments:
        rpp["arguments"] = list(notice.arguments)
    return rpp


def _subject(reference: ObjectReference) -> dict:
    return {"objectType": reference.object_type, "objectId": reference.object_id}


def _bulk(event: BulkMessageEvent) -> dict:
    return {"objects": [_reference(reference) for reference in event.objects]}


def _notices(event: NoticeMessageEvent) -> dict:
    return {**_subject(event.object), "notices": [_notice(notice) for notice in event.notices]}


def _auth_info(event: AuthInfoMessageEvent) -> dict:
    return {**_subject(event.object), **({"expiryDate": event.expiry_date} if event.expiry_date else {})}


def _domain_status(event: DomainStatusMessageEvent) -> dict:
    rpp = {**_subject(event.object), "status": [{"@type": "domainStatus", "label": label} for label in event.status],
           "holders": [_reference(reference) for reference in event.holders]}
    if event.hold_deadline:
        rpp["holdDeadline"] = event.hold_deadline
    if event.deletion_deadline:
        rpp["deletionDeadline"] = event.deletion_deadline
    if event.notices:
        rpp["notices"] = [_notice(notice) for notice in event.notices]
    return rpp


def _contact_verification(event: ContactVerificationMessageEvent) -> dict:
    rpp = {**_subject(event.object), "claims": list(event.claims), "referencedDomains": event.referenced_domains,
           "earliestDeletion": _reference(event.earliest_deletion), "notices": [_notice(notice) for notice in event.notices]}
    if event.earliest_hold is not None:
        rpp["earliestHold"] = _reference(event.earliest_hold)
    return rpp


class RriMessageMapper:
    """Maps the events of the rri extension to the data of its message types."""
    extension_id = EXTENSION_ID

    def to_rpp(self, event) -> dict:
        if isinstance(event, BulkMessageEvent):
            members = _bulk(event)
        elif isinstance(event, NoticeMessageEvent):
            members = _notices(event)
        elif isinstance(event, AuthInfoMessageEvent):
            members = _auth_info(event)
        elif isinstance(event, DomainStatusMessageEvent):
            return {"@type": "domainStatusMessage", **_domain_status(event)}
        elif isinstance(event, ContactVerificationMessageEvent):
            return {"@type": "contactVerificationMessage", **_contact_verification(event)}
        else:
            raise ValueError(f"No message type of the rri extension for {type(event).__name__}")
        return {"@type": event.kind.identifier, **members}
