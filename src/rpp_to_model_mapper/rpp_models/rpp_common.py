from dataclasses import dataclass, field
from dataclasses_json import dataclass_json
from typing import List, Optional, Dict

    
@dataclass_json
@dataclass(kw_only=True)
class RPPProvisioningObject:
    crDate: Optional[str] = None
    exDate: Optional[str] = None
    upDate: Optional[str] = None
    trDate: Optional[str] = None
    clID: Optional[str] = None
    crID: Optional[str] = None
