from dataclasses import dataclass
from typing import List, Optional

from .ds_data import DsData
from .key_data import KeyData


@dataclass(kw_only=True)
class DnsSec:
    """The DNSSEC data of a domain. RFC 5910 takes either form, not both."""
    ds_data: Optional[List[DsData]] = None
    key_data: Optional[List[KeyData]] = None
