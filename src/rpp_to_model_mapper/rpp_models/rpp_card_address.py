from dataclasses import dataclass
from typing import List, Optional

from dataclasses_json import Undefined, dataclass_json

from .rpp_object import RPPObject
from .rpp_card_address_component import RPPCardAddressComponent


@dataclass_json(undefined=Undefined.RAISE)
@dataclass(kw_only=True)
class RPPCardAddress(RPPObject):
    full: Optional[str] = None
    countryCode: Optional[str] = None
    components: Optional[List[RPPCardAddressComponent]] = None
