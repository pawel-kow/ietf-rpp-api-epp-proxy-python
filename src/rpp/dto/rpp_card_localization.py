from dataclasses import dataclass
from typing import Dict, Optional

from dataclasses_json import Undefined, dataclass_json

from rpp.dto.rpp_card_address import RPPCardAddress
from rpp.dto.rpp_card_email import RPPCardEmail
from rpp.dto.rpp_card_name import RPPCardName
from rpp.dto.rpp_card_organization import RPPCardOrganization
from rpp.dto.rpp_object import RPPObject


@dataclass_json(undefined=Undefined.RAISE)
@dataclass(kw_only=True)
class RPPCardLocalization(RPPObject):
    name: Optional[RPPCardName] = None
    organizations: Optional[Dict[str, RPPCardOrganization]] = None
    addresses: Optional[Dict[str, RPPCardAddress]] = None
    emails: Optional[Dict[str, RPPCardEmail]] = None
