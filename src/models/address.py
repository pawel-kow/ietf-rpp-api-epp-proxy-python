from dataclasses import dataclass
from typing import List, Optional


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
