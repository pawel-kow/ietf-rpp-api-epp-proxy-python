from dataclasses import dataclass, field
from typing import List, Optional, Dict
from enum import Enum

@dataclass
class Process:
    pass

@dataclass(kw_only=True)
class ProvisioningObject:
    crDate: Optional[str] = None
    exDate: Optional[str] = None
    upDate: Optional[str] = None
    trDate: Optional[str] = None
    clID: Optional[str] = None
    crID: Optional[str] = None
    
    def update(self, obj):
        self.crDate = obj.crDate if obj.crDate else self.crDate
        self.exDate = obj.exDate if obj.exDate else self.exDate
        self.upDate = obj.upDate if obj.upDate else self.upDate
        self.trDate = obj.trDate if obj.trDate else self.trDate
        self.clID = obj.clID if obj.clID else self.clID
        self.crID = obj.crID if obj.crID else self.crID