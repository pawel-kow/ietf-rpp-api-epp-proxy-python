"""The request contacts of a domain: the members the rri extension adds to it that each refer to a request contact
(`generalRequest` and `abuse`, docs/rri/rri-extension.md). They are not `contacts`: the model holds each as a contact
reference whose role is the member's name, so a backend writes them as it writes a role."""

from core.capabilities.not_supported_by_backend import NotSupportedByBackend
from core.model.domain.domains import Domain
from extensions.rri.core.ports.rri_gateways import EXTENSION_ID

TYPE = "requestContact"


class RequestContactMembers:
    """The mapper of the rri extension for the members of a domain name (`DOMAIN_MEMBERS`)."""
    extension_id = EXTENSION_ID
    members = ("generalRequest", "abuse")

    def to_model(self, present: dict) -> list[tuple[str, str]]:
        """The role and id of each request contact a request states (a member that is null states none)."""
        return [(role, present[role]["id"]) for role in self.members if present.get(role) is not None]

    def to_rpp(self, domain: Domain) -> dict:
        """The members of the request contacts a domain has: its contact references of these roles."""
        roles = {label: contact.id for contact in domain.contacts or [] for label in contact.types}
        return {role: {"@type": TYPE, "id": roles[role]} for role in self.members if role in roles}

    def check(self, rpp: dict) -> None:
        """The roles of the request contacts are members of their own, not labels of `contacts`: a label that names one is a
        contact label RRI cannot hold, whichever profile applies (core §Extensions and Profiles of a Request: what an extension
        defines is refused as it defines it, and not with 02308)."""
        for contact in rpp.get("contacts") or ():
            if isinstance(contact, dict) and contact.get("label") in self.members:
                raise NotSupportedByBackend(f"Contact label '{contact['label']}'")
