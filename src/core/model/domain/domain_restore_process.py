from dataclasses import dataclass, field

PENDING_RESTORE = "pendingRestore"

PENDING_DELETE = "pendingDelete"


@dataclass(kw_only=True)
class DomainRestoreProcess:
    """The state of a restore: the RGP statuses of the domain (RFC 3915 §3.2), empty when it has none."""
    rgpStatus: list[str] = field(default_factory=list)

    def under_way(self) -> bool:
        """A restore was requested and has not completed: pendingRestore, or pendingDelete when it failed."""
        return PENDING_RESTORE in self.rgpStatus or PENDING_DELETE in self.rgpStatus
