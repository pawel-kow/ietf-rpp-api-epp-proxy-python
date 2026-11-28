from enum import Enum


class RriMessageKind(Enum):
    """The notifications of the registry that the extension has a message type for (the RRI `msgType` they are read as)."""
    EXPIRE_WARNING = "expireWarning"
    EXPIRE = "expire"
    AUTH_INFO_EXPIRE = "authInfoExpire"
    AUTH_INFO2_NOTIFY = "authInfo2Notify"
    AUTH_INFO2_DELETE = "authInfo2Delete"
    DOMAIN_TRANSIT = "domainTransit"
    DOMAIN_STATUS_UPDATE = "domainStatusUpdate"
    CONTACT_VERIFICATION_REQUIRED = "contactVerificationRequired"

    @property
    def identifier(self) -> str:
        """The identifier of the message type (docs/rri/rri-extension.md, Message Types) that the notification is read as, which a
        Query's `type` names."""
        return IDENTIFIERS[self]


IDENTIFIERS = {
    RriMessageKind.EXPIRE_WARNING: "domainExpiryWarningMessage",
    RriMessageKind.EXPIRE: "domainExpiryMessage",
    RriMessageKind.AUTH_INFO_EXPIRE: "authInfoExpiryMessage",
    RriMessageKind.AUTH_INFO2_NOTIFY: "authInfoIssueMessage",
    RriMessageKind.AUTH_INFO2_DELETE: "authInfoWithdrawalMessage",
    RriMessageKind.DOMAIN_TRANSIT: "domainReleaseMessage",
    RriMessageKind.DOMAIN_STATUS_UPDATE: "domainStatusMessage",
    RriMessageKind.CONTACT_VERIFICATION_REQUIRED: "contactVerificationMessage",
}
