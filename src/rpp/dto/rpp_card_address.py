from dataclasses import dataclass
from typing import List, Optional

from dataclasses_json import dataclass_json, Undefined

from rpp.dto.rpp_card_address_component import RPPCardAddressComponent
from rpp.dto.rpp_object import optional_type_field, RPPObject


@dataclass_json(undefined=Undefined.RAISE)
@dataclass(kw_only=True)
class RPPCardAddress(RPPObject):
    at_type: Optional[str] = optional_type_field()
    components: List[RPPCardAddressComponent]
    countryCode: str
