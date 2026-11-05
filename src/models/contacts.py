from dataclasses import dataclass, field
from typing import List, Optional, Dict
from .address import Address
from .common import ProvisioningObject
from .localized_postal_info import LocalizedPostalInfo
from .response import OperationResponse
from enum import Enum

class ContactType(Enum):
    UNDEFINED = "UNDEFINED"
    PERSON = "PERSON"
    ORG = "ORG"

@dataclass(kw_only=True)
class ContactMinimal():
    id: str;

@dataclass(kw_only=True)
class Contact(ProvisioningObject, ContactMinimal):
    id: str;
    type: ContactType = ContactType(ContactType.UNDEFINED);
    name: Optional[str] = None;
    organisationName: Optional[str] = None
    email: Optional[List[str]] = None;
    phone: Optional[List[str]] = None;
    fax: Optional[List[str]] = None;
    address: Optional[Address] = None;
    localizedPostalInfo: Optional[LocalizedPostalInfo] = None
    
    def __post_init__(self):
        localized = self.localizedPostalInfo
        if self.type == ContactType.ORG and not (self.organisationName or (localized and localized.organisationName)):
            raise ValueError("Organisation name is required for contact type ORG")
    
    def update(self, contact):
        super().update(contact)
        self.id = contact.id if contact.id else self.id
        self.type = contact.type
        self.name = contact.name if contact.name else self.name
        self.organisationName = contact.organisationName if contact.organisationName else self.organisationName
        self.email = contact.email if contact.email else self.email
        self.phone = contact.phone if contact.phone else self.phone
        self.fax = contact.fax if contact.fax else self.fax
        if contact.address:
            if not self.address:
                self.address = Address()
            self.address.update(contact.address)


@dataclass(kw_only=True)
class ErrorResponse(OperationResponse):
    pass

@dataclass(kw_only=True)
class ContactCreateResponse(OperationResponse):
    contact: Contact

@dataclass(kw_only=True)
class ContactInfoResponse(OperationResponse):
    contact: Contact

@dataclass(kw_only=True)
class ContactDeleteResponse(OperationResponse):
    pass
