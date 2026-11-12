from dataclasses import dataclass, field
from typing import Optional

from xsdata.models.datatype import XmlDateTime

from registry_adapter.rri.xml.generated.contact_5_0 import (
    EmailType as Contact50EmailType,
)
from registry_adapter.rri.xml.generated.contact_5_0 import (
    NameType as Contact50NameType,
)
from registry_adapter.rri.xml.generated.contact_5_0 import (
    NillablePostalType,
    OrganisationType,
    RoleType,
    TypeType,
    UriTemplateType,
)
from registry_adapter.rri.xml.generated.contact_5_0 import (
    PhoneType as Contact50PhoneType,
)
from registry_adapter.rri.xml.generated.verification_5_0 import (
    VerificationInformation,
)

__NAMESPACE__ = "http://registry.denic.de/regacc/5.0"


@dataclass
class InfoType:
    class Meta:
        name = "infoType"

    handle: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/regacc/5.0",
            "required": True,
            "max_length": 32,
            "pattern": r"[dD][eE][nN][iI][cC]\-[1-9][0-9]*",
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
class CityType(NormalizedStringPrivacyType):
    class Meta:
        name = "cityType"


@dataclass
class ContactInfoDataType:
    class Meta:
        name = "contactInfoDataType"

    type_value: Optional[TypeType] = field(
        default=None,
        metadata={
            "name": "type",
            "type": "Element",
            "namespace": "http://registry.denic.de/contact/5.0",
        },
    )
    name: Optional[Contact50NameType] = field(
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
    email: list[Contact50EmailType] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/contact/5.0",
        },
    )
    phone: Optional[Contact50PhoneType] = field(
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
class CountryCodeType(TokenPrivacyType):
    class Meta:
        name = "countryCodeType"


@dataclass
class EmailType(TokenPrivacyType):
    class Meta:
        name = "emailType"


@dataclass
class Info(InfoType):
    class Meta:
        name = "info"
        namespace = "http://registry.denic.de/regacc/5.0"


@dataclass
class NameType(NormalizedStringPrivacyType):
    class Meta:
        name = "nameType"


@dataclass
class PhoneType(TokenPrivacyType):
    class Meta:
        name = "phoneType"


@dataclass
class PostalCodeType(TokenPrivacyType):
    class Meta:
        name = "postalCodeType"


@dataclass
class UrlType(NormalizedStringPrivacyType):
    class Meta:
        name = "urlType"


@dataclass
class PostalType:
    class Meta:
        name = "postalType"

    address: list[AddressType] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/regacc/5.0",
            "min_occurs": 1,
        },
    )
    postal_code: Optional[PostalCodeType] = field(
        default=None,
        metadata={
            "name": "postalCode",
            "type": "Element",
            "namespace": "http://registry.denic.de/regacc/5.0",
            "required": True,
        },
    )
    city: Optional[CityType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/regacc/5.0",
            "required": True,
        },
    )
    country_code: Optional[CountryCodeType] = field(
        default=None,
        metadata={
            "name": "countryCode",
            "type": "Element",
            "namespace": "http://registry.denic.de/regacc/5.0",
            "required": True,
        },
    )


@dataclass
class InfoDataType:
    class Meta:
        name = "infoDataType"

    handle: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/regacc/5.0",
            "required": True,
            "max_length": 32,
            "pattern": r"[dD][eE][nN][iI][cC]\-[1-9][0-9]*",
        },
    )
    name: Optional[NameType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/regacc/5.0",
            "required": True,
        },
    )
    postal: Optional[PostalType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/regacc/5.0",
            "required": True,
        },
    )
    phone: list[PhoneType] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/regacc/5.0",
        },
    )
    fax: list[PhoneType] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/regacc/5.0",
        },
    )
    email: Optional[EmailType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/regacc/5.0",
            "required": True,
        },
    )
    url: list[UrlType] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/regacc/5.0",
        },
    )
    memberacc: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/regacc/5.0",
            "required": True,
            "max_length": 32,
            "pattern": r"[dD][eE][nN][iI][cC]\-[1-9][0-9]*",
        },
    )
    contact: list[ContactInfoDataType] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/regacc/5.0",
            "max_occurs": 2,
        },
    )
    changed: Optional[XmlDateTime] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/regacc/5.0",
            "required": True,
        },
    )


@dataclass
class InfoData(InfoDataType):
    class Meta:
        name = "infoData"
        namespace = "http://registry.denic.de/regacc/5.0"
