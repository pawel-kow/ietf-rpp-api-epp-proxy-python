from enum import Enum


class RegistryChangeKind(Enum):
    """What the registry did to an object, with the identifier of the message type that reports it."""
    DOMAIN_UPDATED = "domainUpdateMessage"
    CONTACT_UPDATED = "contactUpdateMessage"
    DOMAIN_DELETED = "domainDeletionMessage"
