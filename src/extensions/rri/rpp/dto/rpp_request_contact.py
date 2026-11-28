from dataclasses import dataclass
from typing import Optional

from dataclasses_json import dataclass_json, Undefined

from rpp.dto.rpp_object import RPPObject, type_field
from rpp.dto.rpp_prov_metadata import RPPProvMetadata


@dataclass_json(undefined=Undefined.RAISE)
@dataclass(kw_only=True)
class RPPRequestContact(RPPObject):
    """The request contact of the rri extension (docs/rri/rri-extension.md), an object of the extension's own."""
    at_type: str = type_field("requestContact")
    id: str
    provMetadata: Optional[RPPProvMetadata] = None
    uriTemplate: str
