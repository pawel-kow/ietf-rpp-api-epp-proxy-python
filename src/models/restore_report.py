from dataclasses import dataclass, field
from typing import Optional


@dataclass(kw_only=True)
class RestoreReport:
    """The restore report of the Redemption Grace Period (RFC 3915 §4.2.5). Times are RFC 3339 date-times."""
    preData: str
    postData: str
    deleteTime: str
    restoreTime: str
    restoreReason: str
    statements: list[str] = field(default_factory=list)
    other: Optional[str] = None
