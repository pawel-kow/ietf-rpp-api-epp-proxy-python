"""What the RRI parts of the extensions that build on the messages extension share, to read an RRI message: the references to a
domain name (by its A-label, `msg:ace`) and to a contact (by its handle), and the notices of the registry. Nothing but names,
dates, codes and the notices' texts is taken: the rest of a message can be personal data."""
from extensions.messages.core.model.object_reference import ObjectReference
from extensions.messages.core.model.registry_notice import RegistryNotice

DOMAIN = "domainName"

CONTACT = "contact"


def domain_reference(domain, date=None) -> ObjectReference:
    return ObjectReference(object_type=DOMAIN, object_id=domain.ace, date=date)


def contact_reference(handle: str, date=None) -> ObjectReference:
    return ObjectReference(object_type=CONTACT, object_id=handle, date=date)


def registry_notices(notices) -> tuple[RegistryNotice, ...]:
    """The `level` of a notice is not represented."""
    return tuple(RegistryNotice(code=str(notice.code), text=notice.text, arguments=tuple(notice.argument)) for notice in notices)
