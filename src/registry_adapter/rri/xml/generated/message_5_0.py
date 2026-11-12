from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from xsdata.models.datatype import XmlDateTime

from registry_adapter.rri.xml.generated.domain_5_0 import StatusType
from registry_adapter.rri.xml.generated.transaction_5_0 import (
    MessageType as Transaction50MessageType,
)

__NAMESPACE__ = "http://registry.denic.de/msg/5.0"


@dataclass
class ContactType:
    class Meta:
        name = "contactType"

    handle: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
            "required": True,
            "max_length": 32,
            "pattern": r"[dD][eE][nN][iI][cC]\-[1-9][0-9]*\-[\-\.a-zA-Z0-9]+",
        },
    )


@dataclass
class ContactsType:
    class Meta:
        name = "contactsType"

    handle: list[str] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
            "min_occurs": 1,
            "max_occurs": 100,
            "max_length": 32,
            "pattern": r"[dD][eE][nN][iI][cC]\-[1-9][0-9]*\-[\-\.a-zA-Z0-9]+",
        },
    )


@dataclass
class DomainType:
    class Meta:
        name = "domainType"

    handle: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
            "required": True,
            "min_length": 4,
            "max_length": 66,
            "pattern": r"[\p{IsBasicLatin}\p{IsLatin-1Supplement}\p{IsLatinExtended-A}]*",
        },
    )
    ace: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
            "required": True,
            "min_length": 1,
            "max_length": 254,
            "pattern": r"[0-9a-zA-Z][0-9a-zA-Z\-]{0,62}\.[dD][eE]",
        },
    )


@dataclass
class DomainWithExpireType:
    class Meta:
        name = "domainWithExpireType"

    handle: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
            "required": True,
            "min_length": 4,
            "max_length": 66,
            "pattern": r"[\p{IsBasicLatin}\p{IsLatin-1Supplement}\p{IsLatinExtended-A}]*",
        },
    )
    ace: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
            "required": True,
            "min_length": 1,
            "max_length": 254,
            "pattern": r"[0-9a-zA-Z][0-9a-zA-Z\-]{0,62}\.[dD][eE]",
        },
    )
    expire: Optional[XmlDateTime] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
            "required": True,
        },
    )


class EmptyType(Enum):
    VALUE = ""


class MsgTypeType(Enum):
    EXPIRE_WARNING = "expireWarning"
    EXPIRE = "expire"
    AUTH_INFO_EXPIRE = "authInfoExpire"
    AUTH_INFO2_NOTIFY = "authInfo2Notify"
    CHPROV_AUTH_INFO = "chprovAuthInfo"
    DOMAIN_DELETE = "domainDelete"
    AUTH_INFO2_DELETE = "authInfo2Delete"
    LOCK_CREATE = "lockCreate"
    LOCK_DELETE = "lockDelete"
    DOMAIN_UPDATE = "domainUpdate"
    DOMAIN_TRANSIT = "domainTransit"
    CONTACT_UPDATE = "contactUpdate"
    CONTACT_DELETE = "contactDelete"
    DOMAIN_STATUS_UPDATE = "domainStatusUpdate"
    CONTACT_VERIFICATION_REQUIRED = "contactVerificationRequired"


@dataclass
class VerifiedClaimsType:
    class Meta:
        name = "verifiedClaimsType"

    claim: list[str] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
            "min_occurs": 1,
        },
    )


@dataclass
class AuthInfo2DeleteType:
    class Meta:
        name = "authInfo2DeleteType"

    domain: Optional[DomainType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
            "required": True,
        },
    )
    message: list[Transaction50MessageType] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
            "min_occurs": 1,
        },
    )


@dataclass
class AuthInfo2NotifyType:
    class Meta:
        name = "authInfo2NotifyType"

    domain: Optional[DomainType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
            "required": True,
        },
    )


@dataclass
class AuthInfoExpireType:
    class Meta:
        name = "authInfoExpireType"

    domain: Optional[DomainType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
            "required": True,
        },
    )
    authinfoexpire: Optional[XmlDateTime] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
            "required": True,
        },
    )


@dataclass
class ChprovAuthInfoType:
    class Meta:
        name = "chprovAuthInfoType"

    domain: Optional[DomainType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
            "required": True,
        },
    )
    new: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
            "required": True,
        },
    )
    old: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
            "required": True,
        },
    )


@dataclass
class ContactUpdateType:
    class Meta:
        name = "contactUpdateType"

    contact: Optional[ContactType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
            "required": True,
        },
    )
    message: list[Transaction50MessageType] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
            "min_occurs": 1,
        },
    )


@dataclass
class ContactsDeleteType:
    class Meta:
        name = "contactsDeleteType"

    handles: Optional[ContactsType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
            "required": True,
        },
    )


@dataclass
class DeleteType:
    class Meta:
        name = "deleteType"

    value: Optional[EmptyType] = field(
        default=None,
        metadata={
            "required": True,
        },
    )
    msgid: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "required": True,
            "min_length": 3,
            "max_length": 64,
        },
    )
    msg_type: Optional[MsgTypeType] = field(
        default=None,
        metadata={
            "name": "msgType",
            "type": "Attribute",
        },
    )


@dataclass
class DomainDeleteType:
    class Meta:
        name = "domainDeleteType"

    domain: Optional[DomainType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
            "required": True,
        },
    )
    message: list[Transaction50MessageType] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
            "min_occurs": 1,
        },
    )


@dataclass
class DomainStatusUpdateType:
    class Meta:
        name = "domainStatusUpdateType"

    domain: Optional[DomainType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
            "required": True,
        },
    )
    holders: Optional[ContactsType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
            "required": True,
        },
    )
    status: Optional[StatusType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
            "required": True,
        },
    )
    verification_deadline_before_dedelegation: Optional[XmlDateTime] = field(
        default=None,
        metadata={
            "name": "verificationDeadlineBeforeDedelegation",
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
        },
    )
    verification_deadline_before_deletion: Optional[XmlDateTime] = field(
        default=None,
        metadata={
            "name": "verificationDeadlineBeforeDeletion",
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
        },
    )
    message: list[Transaction50MessageType] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
        },
    )


@dataclass
class DomainTransitType:
    class Meta:
        name = "domainTransitType"

    domain: Optional[DomainType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
            "required": True,
        },
    )
    message: list[Transaction50MessageType] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
            "min_occurs": 1,
        },
    )


@dataclass
class DomainUpdateType:
    class Meta:
        name = "domainUpdateType"

    domain: Optional[DomainType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
            "required": True,
        },
    )
    message: list[Transaction50MessageType] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
            "min_occurs": 1,
        },
    )


@dataclass
class DomainWithExpireListType:
    class Meta:
        name = "domainWithExpireListType"

    domain: list[DomainWithExpireType] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
            "min_occurs": 1,
        },
    )


@dataclass
class EarliestDomainBeforeDedelegationType:
    class Meta:
        name = "earliestDomainBeforeDedelegationType"

    domain: Optional[DomainType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
            "required": True,
        },
    )
    verification_deadline: Optional[XmlDateTime] = field(
        default=None,
        metadata={
            "name": "verificationDeadline",
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
            "required": True,
        },
    )


@dataclass
class EarliestDomainBeforeDeletionType:
    class Meta:
        name = "earliestDomainBeforeDeletionType"

    domain: Optional[DomainType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
            "required": True,
        },
    )
    verification_deadline: Optional[XmlDateTime] = field(
        default=None,
        metadata={
            "name": "verificationDeadline",
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
            "required": True,
        },
    )


@dataclass
class LockCreateType:
    class Meta:
        name = "lockCreateType"

    domain: Optional[DomainType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
            "required": True,
        },
    )
    message: list[Transaction50MessageType] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
            "min_occurs": 1,
        },
    )


@dataclass
class LockDeleteType:
    class Meta:
        name = "lockDeleteType"

    domain: Optional[DomainType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
            "required": True,
        },
    )
    message: list[Transaction50MessageType] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
            "min_occurs": 1,
        },
    )


@dataclass
class ReadType:
    class Meta:
        name = "readType"

    value: Optional[EmptyType] = field(
        default=None,
        metadata={
            "required": True,
        },
    )
    msg_type: Optional[MsgTypeType] = field(
        default=None,
        metadata={
            "name": "msgType",
            "type": "Attribute",
        },
    )


@dataclass
class ContactDelete(ContactsDeleteType):
    class Meta:
        name = "contactDelete"
        namespace = "http://registry.denic.de/msg/5.0"


@dataclass
class ContactVerificationRequiredType:
    class Meta:
        name = "contactVerificationRequiredType"

    handle: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
            "required": True,
            "max_length": 32,
            "pattern": r"[dD][eE][nN][iI][cC]\-[1-9][0-9]*\-[\-\.a-zA-Z0-9]+",
        },
    )
    verification_claims: Optional[VerifiedClaimsType] = field(
        default=None,
        metadata={
            "name": "verificationClaims",
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
            "required": True,
        },
    )
    number_of_referenced_domains_total: Optional[int] = field(
        default=None,
        metadata={
            "name": "numberOfReferencedDomainsTotal",
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
            "required": True,
        },
    )
    earliest_domain_for_dedelegation: Optional[
        EarliestDomainBeforeDedelegationType
    ] = field(
        default=None,
        metadata={
            "name": "earliestDomainForDedelegation",
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
        },
    )
    earliest_domain_for_deletion: Optional[
        EarliestDomainBeforeDeletionType
    ] = field(
        default=None,
        metadata={
            "name": "earliestDomainForDeletion",
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
            "required": True,
        },
    )
    message: list[Transaction50MessageType] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
            "min_occurs": 1,
        },
    )


@dataclass
class Delete(DeleteType):
    class Meta:
        name = "delete"
        namespace = "http://registry.denic.de/msg/5.0"


@dataclass
class QueueRead(ReadType):
    class Meta:
        name = "queue-read"
        namespace = "http://registry.denic.de/msg/5.0"


@dataclass
class MessageType:
    class Meta:
        name = "messageType"

    expire_warning: Optional[DomainWithExpireListType] = field(
        default=None,
        metadata={
            "name": "expireWarning",
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
        },
    )
    expire: Optional[DomainWithExpireListType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
        },
    )
    auth_info_expire: Optional[AuthInfoExpireType] = field(
        default=None,
        metadata={
            "name": "authInfoExpire",
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
        },
    )
    auth_info2_notify: Optional[AuthInfo2NotifyType] = field(
        default=None,
        metadata={
            "name": "authInfo2Notify",
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
        },
    )
    chprov_auth_info: Optional[ChprovAuthInfoType] = field(
        default=None,
        metadata={
            "name": "chprovAuthInfo",
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
        },
    )
    domain_delete: Optional[DomainDeleteType] = field(
        default=None,
        metadata={
            "name": "domainDelete",
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
        },
    )
    auth_info2_delete: Optional[AuthInfo2DeleteType] = field(
        default=None,
        metadata={
            "name": "authInfo2Delete",
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
        },
    )
    lock_create: Optional[LockCreateType] = field(
        default=None,
        metadata={
            "name": "lockCreate",
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
        },
    )
    lock_delete: Optional[LockDeleteType] = field(
        default=None,
        metadata={
            "name": "lockDelete",
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
        },
    )
    domain_update: Optional[DomainUpdateType] = field(
        default=None,
        metadata={
            "name": "domainUpdate",
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
        },
    )
    domain_transit: Optional[DomainTransitType] = field(
        default=None,
        metadata={
            "name": "domainTransit",
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
        },
    )
    contact_update: Optional[ContactUpdateType] = field(
        default=None,
        metadata={
            "name": "contactUpdate",
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
        },
    )
    contact_delete: Optional[ContactsDeleteType] = field(
        default=None,
        metadata={
            "name": "contactDelete",
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
        },
    )
    domain_status_update: Optional[DomainStatusUpdateType] = field(
        default=None,
        metadata={
            "name": "domainStatusUpdate",
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
        },
    )
    contact_verification_required: Optional[
        ContactVerificationRequiredType
    ] = field(
        default=None,
        metadata={
            "name": "contactVerificationRequired",
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
        },
    )
    msgid: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "required": True,
            "min_length": 3,
            "max_length": 64,
        },
    )
    msgcnt: Optional[int] = field(
        default=None,
        metadata={
            "type": "Attribute",
        },
    )
    msgtime: Optional[XmlDateTime] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "required": True,
        },
    )


@dataclass
class Message(MessageType):
    class Meta:
        name = "message"
        namespace = "http://registry.denic.de/msg/5.0"
