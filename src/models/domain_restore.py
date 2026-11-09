from dataclasses import dataclass
from typing import Optional

from .restore_report import RestoreReport


@dataclass(kw_only=True)
class DomainRestore:
    """A restore of a deleted domain (RFC 3915): a request without a report, else the report."""
    name: str
    report: Optional[RestoreReport] = None
