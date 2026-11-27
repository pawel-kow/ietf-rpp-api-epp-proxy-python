"""The request contacts of a domain: the members the rri extension adds to it that each refer to a request contact
(`generalRequest` and `abuse`, docs/rri/rri-extension.md). They are not `contacts`: the model holds each as a contact
reference whose role is the member's name, so a backend writes them as it writes a role."""

from extensions.rri.core.ports.rri_gateways import EXTENSION_ID

TYPE = "requestContact"


class RequestContactMembers:
    """The mapper of the rri extension for the members of a domain name (`DOMAIN_MEMBERS`)."""
    extension_id = EXTENSION_ID
    members = ("generalRequest", "abuse")

    def to_model(self, present: dict) -> list[tuple[str, str]]:
        """The role and id of each request contact a request states."""
        return [(role, present[role]["id"]) for role in self.members if present.get(role)]

    def to_rpp(self, roles: dict[str, str]) -> dict:
        """The members of the request contacts a domain has, by role."""
        return {role: {"@type": TYPE, "id": roles[role]} for role in self.members if role in roles}
