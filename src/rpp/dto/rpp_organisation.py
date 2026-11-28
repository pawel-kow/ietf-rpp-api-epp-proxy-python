from dataclasses import dataclass
from typing import Dict, List, Optional

from dataclasses_json import dataclass_json, Undefined

from rpp.dto.rpp_card import RPPCard
from rpp.dto.rpp_object import RPPObject, type_field
from rpp.dto.rpp_prov_metadata import RPPProvMetadata
from rpp.dto.rpp_status import RPPStatus


@dataclass_json(undefined=Undefined.RAISE)
@dataclass(kw_only=True)
class RPPOrganisationReference(RPPObject):
    at_type: str = type_field("organisation")
    id: str


@dataclass_json(undefined=Undefined.RAISE)
@dataclass(kw_only=True)
class RPPOrganisationRole(RPPObject):
    at_type: str = type_field("organisationRole")
    roleId: Optional[str] = None
    status: Optional[List[RPPStatus]] = None


@dataclass_json(undefined=Undefined.RAISE)
@dataclass(kw_only=True)
class RPPOrganisation(RPPObject):
    at_type: str = type_field("organisation")
    id: str
    provMetadata: RPPProvMetadata
    status: List[RPPStatus]
    roles: Dict[str, RPPOrganisationRole]
    parent: Optional[RPPOrganisationReference] = None
    contactInfo: Optional[RPPCard] = None
