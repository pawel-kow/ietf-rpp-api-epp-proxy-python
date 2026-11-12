from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from xsdata.models.datatype import XmlDateTime

from registry_adapter.rri.xml.generated.contact_5_0 import (
    EmailType,
    Handle,
    NameType,
    NillablePostalType,
    OrganisationType,
    PhoneType,
    RoleType,
    TypeType,
    UriTemplateType,
)
from registry_adapter.rri.xml.generated.dnsentry_5_0 import Dnsentry
from registry_adapter.rri.xml.generated.verification_5_0 import (
    VerificationInformation,
)

__NAMESPACE__ = "http://registry.denic.de/domain/5.0"


@dataclass
class CheckType:
    class Meta:
        name = "checkType"

    handle: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/domain/5.0",
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
            "namespace": "http://registry.denic.de/domain/5.0",
            "min_length": 1,
            "max_length": 254,
            "pattern": r"[0-9a-zA-Z][0-9a-zA-Z\-]{0,62}\.[dD][eE]",
        },
    )


@dataclass
class CreateAuthInfo1DataType:
    class Meta:
        name = "createAuthInfo1DataType"

    expire: Optional[XmlDateTime] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/domain/5.0",
        },
    )


@dataclass
class CreateAuthInfo1Type:
    class Meta:
        name = "createAuthInfo1Type"

    handle: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/domain/5.0",
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
            "namespace": "http://registry.denic.de/domain/5.0",
            "min_length": 1,
            "max_length": 254,
            "pattern": r"[0-9a-zA-Z][0-9a-zA-Z\-]{0,62}\.[dD][eE]",
        },
    )
    hash: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "pattern": r"[0-9a-fA-F]+",
        },
    )
    expire: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "pattern": r"[0-9]{8}",
        },
    )


@dataclass
class CreateAuthInfo2Type:
    class Meta:
        name = "createAuthInfo2Type"

    handle: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/domain/5.0",
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
            "namespace": "http://registry.denic.de/domain/5.0",
            "min_length": 1,
            "max_length": 254,
            "pattern": r"[0-9a-zA-Z][0-9a-zA-Z\-]{0,62}\.[dD][eE]",
        },
    )


@dataclass
class DeleteAuthInfo1Type:
    class Meta:
        name = "deleteAuthInfo1Type"

    handle: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/domain/5.0",
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
            "namespace": "http://registry.denic.de/domain/5.0",
            "min_length": 1,
            "max_length": 254,
            "pattern": r"[0-9a-zA-Z][0-9a-zA-Z\-]{0,62}\.[dD][eE]",
        },
    )


@dataclass
class ProviderName:
    class Meta:
        name = "providerName"

    value: str = field(
        default="",
        metadata={
            "required": True,
        },
    )


@dataclass
class RestoreType:
    class Meta:
        name = "restoreType"

    handle: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/domain/5.0",
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
            "namespace": "http://registry.denic.de/domain/5.0",
            "min_length": 1,
            "max_length": 254,
            "pattern": r"[0-9a-zA-Z][0-9a-zA-Z\-]{0,62}\.[dD][eE]",
        },
    )


class StatusType(Enum):
    FREE = "free"
    CONNECT = "connect"
    FAILED = "failed"
    INVALID = "invalid"
    REDEMPTION_PERIOD = "redemptionPeriod"
    PENDING_CREATE = "pendingCreate"
    SERVER_HOLD = "serverHold"


@dataclass
class TransitType:
    class Meta:
        name = "transitType"

    handle: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/domain/5.0",
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
            "namespace": "http://registry.denic.de/domain/5.0",
            "min_length": 1,
            "max_length": 254,
            "pattern": r"[0-9a-zA-Z][0-9a-zA-Z\-]{0,62}\.[dD][eE]",
        },
    )
    disconnect: Optional[bool] = field(
        default=None,
        metadata={
            "type": "Attribute",
        },
    )


@dataclass
class Check(CheckType):
    class Meta:
        name = "check"
        namespace = "http://registry.denic.de/domain/5.0"


@dataclass
class CheckDataType:
    class Meta:
        name = "checkDataType"

    handle: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/domain/5.0",
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
            "namespace": "http://registry.denic.de/domain/5.0",
            "required": True,
            "min_length": 1,
            "max_length": 254,
            "pattern": r"[0-9a-zA-Z][0-9a-zA-Z\-]{0,62}\.[dD][eE]",
        },
    )
    status: Optional[StatusType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/domain/5.0",
            "required": True,
        },
    )


@dataclass
class ContactInfoDataType:
    class Meta:
        name = "contactInfoDataType"

    handle: Optional[Handle] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/contact/5.0",
        },
    )
    type_value: Optional[TypeType] = field(
        default=None,
        metadata={
            "name": "type",
            "type": "Element",
            "namespace": "http://registry.denic.de/contact/5.0",
        },
    )
    name: Optional[NameType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/contact/5.0",
        },
    )
    organisation: list[OrganisationType] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/contact/5.0",
        },
    )
    postal: Optional[NillablePostalType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/contact/5.0",
        },
    )
    email: list[EmailType] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/contact/5.0",
        },
    )
    phone: Optional[PhoneType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/contact/5.0",
        },
    )
    dispute_reference: Optional[bool] = field(
        default=None,
        metadata={
            "name": "disputeReference",
            "type": "Element",
            "namespace": "http://registry.denic.de/contact/5.0",
        },
    )
    uri_template: Optional[UriTemplateType] = field(
        default=None,
        metadata={
            "name": "uri-template",
            "type": "Element",
            "namespace": "http://registry.denic.de/contact/5.0",
        },
    )
    changed: Optional[XmlDateTime] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/contact/5.0",
        },
    )
    verification_information: list[VerificationInformation] = field(
        default_factory=list,
        metadata={
            "name": "verificationInformation",
            "type": "Element",
            "namespace": "http://registry.denic.de/verification/5.0",
            "max_occurs": 5,
        },
    )
    role: Optional[RoleType] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "required": True,
        },
    )


@dataclass
class ContactType:
    class Meta:
        name = "contactType"

    value: str = field(
        default="",
        metadata={
            "required": True,
            "max_length": 32,
            "pattern": r"[dD][eE][nN][iI][cC]\-[1-9][0-9]*\-[\-\.a-zA-Z0-9]+",
        },
    )
    role: Optional[RoleType] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "required": True,
        },
    )


@dataclass
class CreateAuthInfo1(CreateAuthInfo1Type):
    class Meta:
        name = "createAuthInfo1"
        namespace = "http://registry.denic.de/domain/5.0"


@dataclass
class CreateAuthInfo1Data(CreateAuthInfo1DataType):
    class Meta:
        name = "createAuthInfo1Data"
        namespace = "http://registry.denic.de/domain/5.0"


@dataclass
class CreateAuthInfo2(CreateAuthInfo2Type):
    class Meta:
        name = "createAuthInfo2"
        namespace = "http://registry.denic.de/domain/5.0"


@dataclass
class DeleteAuthInfo1(DeleteAuthInfo1Type):
    class Meta:
        name = "deleteAuthInfo1"
        namespace = "http://registry.denic.de/domain/5.0"


@dataclass
class InfoType(CheckType):
    class Meta:
        name = "infoType"

    auth_info: Optional[str] = field(
        default=None,
        metadata={
            "name": "authInfo",
            "type": "Element",
            "namespace": "http://registry.denic.de/domain/5.0",
            "pattern": r"[\p{IsBasicLatin}\p{IsLatin-1Supplement}\p{IsLatinExtended-A}]*",
        },
    )
    recursive: Optional[bool] = field(
        default=None,
        metadata={
            "type": "Attribute",
        },
    )


@dataclass
class RegAccType:
    class Meta:
        name = "regAccType"

    reg_acc_id: Optional[str] = field(
        default=None,
        metadata={
            "name": "regAccId",
            "type": "Element",
            "namespace": "http://registry.denic.de/domain/5.0",
            "required": True,
            "pattern": r"DENIC\-[1-9][0-9]*",
        },
    )
    name: Optional[ProviderName] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/domain/5.0",
            "required": True,
        },
    )
    email: Optional[object] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/domain/5.0",
        },
    )
    phone: list[object] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/domain/5.0",
        },
    )
    changed: Optional[XmlDateTime] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/domain/5.0",
        },
    )


@dataclass
class Restore(RestoreType):
    class Meta:
        name = "restore"
        namespace = "http://registry.denic.de/domain/5.0"


@dataclass
class Transit(TransitType):
    class Meta:
        name = "transit"
        namespace = "http://registry.denic.de/domain/5.0"


@dataclass
class CheckData(CheckDataType):
    class Meta:
        name = "checkData"
        namespace = "http://registry.denic.de/domain/5.0"


@dataclass
class CreateType:
    class Meta:
        name = "createType"

    handle: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/domain/5.0",
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
            "namespace": "http://registry.denic.de/domain/5.0",
            "min_length": 1,
            "max_length": 254,
            "pattern": r"[0-9a-zA-Z][0-9a-zA-Z\-]{0,62}\.[dD][eE]",
        },
    )
    contact: list[ContactType] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/domain/5.0",
            "min_occurs": 1,
            "max_occurs": 7,
        },
    )
    dnsentry: list[Dnsentry] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/dnsentry/5.0",
            "min_occurs": 1,
            "max_occurs": 20,
        },
    )


@dataclass
class DeleteType:
    class Meta:
        name = "deleteType"

    handle: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/domain/5.0",
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
            "namespace": "http://registry.denic.de/domain/5.0",
            "min_length": 1,
            "max_length": 254,
            "pattern": r"[0-9a-zA-Z][0-9a-zA-Z\-]{0,62}\.[dD][eE]",
        },
    )
    contact: list[ContactType] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/domain/5.0",
            "max_occurs": 5,
        },
    )


@dataclass
class Info(InfoType):
    class Meta:
        name = "info"
        namespace = "http://registry.denic.de/domain/5.0"


@dataclass
class InfoDataType:
    class Meta:
        name = "infoDataType"

    handle: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/domain/5.0",
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
            "namespace": "http://registry.denic.de/domain/5.0",
            "required": True,
            "min_length": 1,
            "max_length": 254,
            "pattern": r"[0-9a-zA-Z][0-9a-zA-Z\-]{0,62}\.[dD][eE]",
        },
    )
    status: Optional[StatusType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/domain/5.0",
            "required": True,
        },
    )
    expire: Optional[XmlDateTime] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/domain/5.0",
        },
    )
    registry_lock: Optional[bool] = field(
        default=None,
        metadata={
            "name": "registryLock",
            "type": "Element",
            "namespace": "http://registry.denic.de/domain/5.0",
        },
    )
    auth_info: Optional[bool] = field(
        default=None,
        metadata={
            "name": "authInfo",
            "type": "Element",
            "namespace": "http://registry.denic.de/domain/5.0",
        },
    )
    auth_info1: Optional[XmlDateTime] = field(
        default=None,
        metadata={
            "name": "authInfo1",
            "type": "Element",
            "namespace": "http://registry.denic.de/domain/5.0",
        },
    )
    auth_info2: Optional[XmlDateTime] = field(
        default=None,
        metadata={
            "name": "authInfo2",
            "type": "Element",
            "namespace": "http://registry.denic.de/domain/5.0",
        },
    )
    contact: list[ContactInfoDataType] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/domain/5.0",
            "max_occurs": 16,
        },
    )
    dnsentry: list[Dnsentry] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/dnsentry/5.0",
            "max_occurs": 20,
        },
    )
    dispute_data: Optional[object] = field(
        default=None,
        metadata={
            "name": "disputeData",
            "type": "Element",
            "namespace": "http://registry.denic.de/domain/5.0",
        },
    )
    registration_date: Optional[str] = field(
        default=None,
        metadata={
            "name": "registrationDate",
            "type": "Element",
            "namespace": "http://registry.denic.de/domain/5.0",
        },
    )
    verification_deadline_before_dedelegation: Optional[XmlDateTime] = field(
        default=None,
        metadata={
            "name": "verificationDeadlineBeforeDedelegation",
            "type": "Element",
            "namespace": "http://registry.denic.de/domain/5.0",
        },
    )
    verification_deadline_before_deletion: Optional[XmlDateTime] = field(
        default=None,
        metadata={
            "name": "verificationDeadlineBeforeDeletion",
            "type": "Element",
            "namespace": "http://registry.denic.de/domain/5.0",
        },
    )
    changed: Optional[XmlDateTime] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/domain/5.0",
            "required": True,
        },
    )
    reg_acc: Optional[RegAccType] = field(
        default=None,
        metadata={
            "name": "regAcc",
            "type": "Element",
            "namespace": "http://registry.denic.de/domain/5.0",
        },
    )


@dataclass
class UpdateType:
    class Meta:
        name = "updateType"

    handle: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/domain/5.0",
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
            "namespace": "http://registry.denic.de/domain/5.0",
            "min_length": 1,
            "max_length": 254,
            "pattern": r"[0-9a-zA-Z][0-9a-zA-Z\-]{0,62}\.[dD][eE]",
        },
    )
    contact: list[ContactType] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/domain/5.0",
            "min_occurs": 1,
            "max_occurs": 7,
        },
    )
    dnsentry: list[Dnsentry] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/dnsentry/5.0",
            "min_occurs": 1,
            "max_occurs": 20,
        },
    )


@dataclass
class Chholder(UpdateType):
    class Meta:
        name = "chholder"
        namespace = "http://registry.denic.de/domain/5.0"


@dataclass
class ChprovType(UpdateType):
    class Meta:
        name = "chprovType"

    auth_info: Optional[str] = field(
        default=None,
        metadata={
            "name": "authInfo",
            "type": "Element",
            "namespace": "http://registry.denic.de/domain/5.0",
            "required": True,
            "pattern": r"[\p{IsBasicLatin}\p{IsLatin-1Supplement}\p{IsLatinExtended-A}]*",
        },
    )


@dataclass
class Create(CreateType):
    class Meta:
        name = "create"
        namespace = "http://registry.denic.de/domain/5.0"


@dataclass
class Delete(DeleteType):
    class Meta:
        name = "delete"
        namespace = "http://registry.denic.de/domain/5.0"


@dataclass
class InfoData(InfoDataType):
    class Meta:
        name = "infoData"
        namespace = "http://registry.denic.de/domain/5.0"


@dataclass
class Update(UpdateType):
    class Meta:
        name = "update"
        namespace = "http://registry.denic.de/domain/5.0"


@dataclass
class Chprov(ChprovType):
    class Meta:
        name = "chprov"
        namespace = "http://registry.denic.de/domain/5.0"
