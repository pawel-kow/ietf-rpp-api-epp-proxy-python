from dataclasses import dataclass, field
from typing import List, Optional, Dict
from .common import ProvisioningObject
from .response import OperationResponse
from enum import Enum

@dataclass(kw_only=True)
class Address:
    street: Optional[List[str]]
    city: Optional[str] = None
    stateProvince: Optional[str] = None
    postalCode: Optional[str] = None
    country: Optional[str] = None
    
    def update(self, address):
        self.street = address.street if address.street else self.street
        self.city = address.city if address.city else self.city
        self.stateProvince = address.stateProvince if address.stateProvince else self.stateProvince
        self.postalCode = address.postalCode if address.postalCode else self.postalCode
        self.country = address.country if address.country else self.country

class ContactType(Enum):
    UNDEFINED = "UNDEFINED"
    PERSON = "PERSON"
    ORG = "ORG"

@dataclass(kw_only=True)
class Contact(ProvisioningObject):
    id: str;
    type: ContactType = ContactType(ContactType.UNDEFINED);
    name: Optional[str] = None;
    organisationName: Optional[str] = None
    email: Optional[List[str]] = None;
    phone: Optional[List[str]] = None;
    fax: Optional[List[str]] = None;
    address: Optional[Address] = None;
    
    def __post_init__(self):
        if self.type == ContactType.ORG and not self.organisationName:
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
