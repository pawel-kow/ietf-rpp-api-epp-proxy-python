from dataclasses import dataclass
from typing import Optional

from dataclasses_json import Undefined, dataclass_json

from .rpp_object import RPPObject
from .rpp_contact_reference import RPPContactReference


@dataclass_json(undefined=Undefined.RAISE)
@dataclass(kw_only=True)
class RPPLabelledContact(RPPObject):
    label: str
    object: RPPContactReference
