"""The members extensions add to a domain name (`DOMAIN_MEMBERS`), which map to and from what the core model of a domain holds.
An extension registers its mapper in its `register` function. The request of a domain's transfer converts its domain data as
a create does, so its members are these too.

The model of a domain holds a contact as a reference with a role, so a mapper's `to_model` gives the references
(`(role, contact id)`) the members stand for, and `to_rpp` takes the contact ids by role."""
from rpp.mapping.shared.member_mappers import MemberMappers

ContactRoles = list[tuple[str, str]]


def _joined(results: list[ContactRoles]) -> ContactRoles:
    return [role for roles in results for role in roles]


DOMAIN_MEMBERS = MemberMappers(merge=_joined)
