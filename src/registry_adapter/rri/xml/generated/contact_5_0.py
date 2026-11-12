from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from xsdata.models.datatype import XmlDateTime

from registry_adapter.rri.xml.generated.verification_5_0 import (
    VerificationInformation,
)

__NAMESPACE__ = "http://registry.denic.de/contact/5.0"


@dataclass
class CheckInfoType:
    class Meta:
        name = "checkInfoType"

    handle: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/contact/5.0",
            "required": True,
            "max_length": 32,
            "pattern": r"[dD][eE][nN][iI][cC]\-[1-9][0-9]*\-[\-\.a-zA-Z0-9]+",
        },
    )


@dataclass
class Handle:
    class Meta:
        name = "handle"
        namespace = "http://registry.denic.de/contact/5.0"

    value: str = field(
        default="",
        metadata={
            "required": True,
            "max_length": 32,
            "pattern": r"[dD][eE][nN][iI][cC]\-[1-9][0-9]*\-[\-\.a-zA-Z0-9]+",
        },
    )


@dataclass
class NormalizedStringPrivacyType:
    class Meta:
        name = "normalizedStringPrivacyType"

    value: str = field(
        default="",
        metadata={
            "required": True,
        },
    )


class RoleType(Enum):
    HOLDER = "holder"
    GENERALREQUEST = "generalrequest"
    ABUSECONTACT = "abusecontact"


class StatusType(Enum):
    FREE = "free"
    EXIST = "exist"
    INVALID = "invalid"


@dataclass
class TokenPrivacyType:
    class Meta:
        name = "tokenPrivacyType"

    value: str = field(
        default="",
        metadata={
            "required": True,
        },
    )


@dataclass
class AddressType(NormalizedStringPrivacyType):
    class Meta:
        name = "addressType"


@dataclass
class Check(CheckInfoType):
    class Meta:
        name = "check"
        namespace = "http://registry.denic.de/contact/5.0"


@dataclass
class CheckDataType:
    class Meta:
        name = "checkDataType"

    handle: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/contact/5.0",
            "required": True,
            "max_length": 32,
            "pattern": r"[dD][eE][nN][iI][cC]\-[1-9][0-9]*\-[\-\.a-zA-Z0-9]+",
        },
    )
    status: Optional[StatusType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/contact/5.0",
            "required": True,
        },
    )


@dataclass
class CityType(NormalizedStringPrivacyType):
    class Meta:
        name = "cityType"


@dataclass
class CountryCodeType(TokenPrivacyType):
    class Meta:
        name = "countryCodeType"


@dataclass
class EmailType(TokenPrivacyType):
    class Meta:
        name = "emailType"


@dataclass
class Info(CheckInfoType):
    class Meta:
        name = "info"
        namespace = "http://registry.denic.de/contact/5.0"


@dataclass
class NameType(NormalizedStringPrivacyType):
    class Meta:
        name = "nameType"


@dataclass
class OrganisationType(NormalizedStringPrivacyType):
    class Meta:
        name = "organisationType"


@dataclass
class PhoneType(NormalizedStringPrivacyType):
    class Meta:
        name = "phoneType"


@dataclass
class PostalCodeType(TokenPrivacyType):
    class Meta:
        name = "postalCodeType"


@dataclass
class TypeType(TokenPrivacyType):
    class Meta:
        name = "typeType"


@dataclass
class UriTemplateType(NormalizedStringPrivacyType):
    class Meta:
        name = "uriTemplateType"


@dataclass
class CheckData(CheckDataType):
    class Meta:
        name = "checkData"
        namespace = "http://registry.denic.de/contact/5.0"


@dataclass
class NillablePostalType:
    class Meta:
        name = "nillablePostalType"

    address: list[AddressType] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/contact/5.0",
            "min_occurs": 1,
        },
    )
    postal_code: Optional[PostalCodeType] = field(
        default=None,
        metadata={
            "name": "postalCode",
            "type": "Element",
            "namespace": "http://registry.denic.de/contact/5.0",
            "required": True,
        },
    )
    city: Optional[CityType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/contact/5.0",
            "required": True,
        },
    )
    country_code: Optional[CountryCodeType] = field(
        default=None,
        metadata={
            "name": "countryCode",
            "type": "Element",
            "namespace": "http://registry.denic.de/contact/5.0",
            "required": True,
        },
    )


@dataclass
class PostalType:
    class Meta:
        name = "postalType"

    address: list[AddressType] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/contact/5.0",
            "min_occurs": 1,
        },
    )
    postal_code: Optional[PostalCodeType] = field(
        default=None,
        metadata={
            "name": "postalCode",
            "type": "Element",
            "namespace": "http://registry.denic.de/contact/5.0",
            "required": True,
        },
    )
    city: Optional[CityType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/contact/5.0",
            "required": True,
        },
    )
    country_code: Optional[CountryCodeType] = field(
        default=None,
        metadata={
            "name": "countryCode",
            "type": "Element",
            "namespace": "http://registry.denic.de/contact/5.0",
            "required": True,
        },
    )


@dataclass
class CreateType:
    class Meta:
        name = "createType"

    handle: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/contact/5.0",
            "required": True,
            "max_length": 32,
            "pattern": r"[dD][eE][nN][iI][cC]\-[1-9][0-9]*\-[\-\.a-zA-Z0-9]+",
        },
    )
    type_value: Optional[TypeType] = field(
        default=None,
        metadata={
            "name": "type",
            "type": "Element",
            "namespace": "http://registry.denic.de/contact/5.0",
            "required": True,
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
    postal: Optional[PostalType] = field(
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
    uri_template: Optional[UriTemplateType] = field(
        default=None,
        metadata={
            "name": "uri-template",
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


@dataclass
class InfoDataType:
    class Meta:
        name = "infoDataType"

    handle: Optional[Handle] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/contact/5.0",
            "required": True,
        },
    )
    type_value: Optional[TypeType] = field(
        default=None,
        metadata={
            "name": "type",
            "type": "Element",
            "namespace": "http://registry.denic.de/contact/5.0",
            "required": True,
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


@dataclass
class UpdateType:
    class Meta:
        name = "updateType"

    handle: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/contact/5.0",
            "required": True,
            "max_length": 32,
            "pattern": r"[dD][eE][nN][iI][cC]\-[1-9][0-9]*\-[\-\.a-zA-Z0-9]+",
        },
    )
    type_value: Optional[TypeType] = field(
        default=None,
        metadata={
            "name": "type",
            "type": "Element",
            "namespace": "http://registry.denic.de/contact/5.0",
            "required": True,
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
    postal: Optional[PostalType] = field(
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
    uri_template: Optional[UriTemplateType] = field(
        default=None,
        metadata={
            "name": "uri-template",
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


@dataclass
class Create(CreateType):
    class Meta:
        name = "create"
        namespace = "http://registry.denic.de/contact/5.0"


@dataclass
class InfoData(InfoDataType):
    class Meta:
        name = "infoData"
        namespace = "http://registry.denic.de/contact/5.0"


@dataclass
class Update(UpdateType):
    class Meta:
        name = "update"
        namespace = "http://registry.denic.de/contact/5.0"
