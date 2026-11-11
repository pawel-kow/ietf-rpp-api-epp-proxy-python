from dataclasses import dataclass
from typing import List, Optional

from dataclasses_json import Undefined, dataclass_json

from rpp.dto.rpp_object import RPPObject, type_field
from rpp.dto.rpp_domain_create_process import RPPDomainCreateProcess


@dataclass_json(undefined=Undefined.RAISE)
@dataclass(kw_only=True)
class RPPProcesses(RPPObject):
    at_type: str = type_field("processes")
    createProcess: Optional[List[RPPDomainCreateProcess]] = None
