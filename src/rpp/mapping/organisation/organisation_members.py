"""The members extensions add to an organisation (`ORGANISATION_MEMBERS`), which map from what the core model of an organisation
holds (`Organisation.extensions`, a typed object per extension id). An extension registers its mapper in its `register` function.

An organisation is read only, so the members are too: a mapper has `to_rpp` only. A definition without the member (every create and
update definition) refuses it as undeclared before a mapper would be asked, so `to_model` is never called."""
from rpp.mapping.shared.member_mappers import MemberMappers


def _no_members(results: list) -> None:
    return None


ORGANISATION_MEMBERS = MemberMappers(merge=_no_members)
