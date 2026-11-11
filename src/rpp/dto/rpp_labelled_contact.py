from dataclasses import dataclass
from typing import Optional

from dataclasses_json import dataclass_json, Undefined

from rpp.dto.rpp_contact_reference import RPPContactReference
from rpp.dto.rpp_object import RPPObject


@dataclass_json(undefined=Undefined.RAISE)
@dataclass(kw_only=True)
class RPPLabelledContact(RPPObject):
    label: str
    object: RPPContactReference
