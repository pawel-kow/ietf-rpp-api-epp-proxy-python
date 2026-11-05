from dataclasses import dataclass
from typing import Any, Dict, Optional

from dataclasses_json import Undefined, dataclass_json

from .rpp_object import RPPObject, type_field
from .rpp_card_address import RPPCardAddress
from .rpp_card_email import RPPCardEmail
from .rpp_card_localization import RPPCardLocalization
from .rpp_card_name import RPPCardName
from .rpp_card_organization import RPPCardOrganization
from .rpp_card_phone import RPPCardPhone


@dataclass_json(undefined=Undefined.RAISE)
@dataclass(kw_only=True)
class RPPCard(RPPObject):
    at_type: str = type_field("Card")
    version: str = "2.0"
    kind: Optional[str] = None
    language: Optional[str] = None
    name: Optional[RPPCardName] = None
    organizations: Optional[Dict[str, RPPCardOrganization]] = None
    addresses: Optional[Dict[str, RPPCardAddress]] = None
    phones: Optional[Dict[str, RPPCardPhone]] = None
    emails: Optional[Dict[str, RPPCardEmail]] = None
    links: Optional[Dict[str, Any]] = None
    localizations: Optional[Dict[str, RPPCardLocalization]] = None
