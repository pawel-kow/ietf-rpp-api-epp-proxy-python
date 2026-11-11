from dataclasses import dataclass
from typing import List, Optional

from dataclasses_json import Undefined, dataclass_json

from rpp.dto.rpp_object import RPPObject, optional_type_field
from rpp.dto.rpp_card_address_component import RPPCardAddressComponent


@dataclass_json(undefined=Undefined.RAISE)
@dataclass(kw_only=True)
class RPPCardAddress(RPPObject):
    at_type: Optional[str] = optional_type_field()
    components: List[RPPCardAddressComponent]
    countryCode: str
