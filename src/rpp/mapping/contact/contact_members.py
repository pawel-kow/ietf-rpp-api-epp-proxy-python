"""The members extensions add to a contact (`CONTACT_MEMBERS`), which map to and from what the core model of a contact holds
(`Contact.extensions` and `ContactReplacement.extensions`, a typed object per extension id). An extension registers its mapper in
its `register` function.

A mapper's `to_model` gives `{extension_id: object}`, which the mappers' results are joined from. A full update states every member,
so a mapper is asked with the members the request has, none if it omits them: the object is then the member's empty value, and
the backend removes what it held. Under a preset without the extension the mapper is not asked, and the replacement has no entry
for the extension, which the backend reads as "keep what is stored" (spec-issues.md, "Full update of a member an extension adds")."""
from rpp.mapping.shared.member_mappers import MemberMappers


def _joined(results: list[dict]) -> dict:
    return {extension_id: value for result in results for extension_id, value in result.items()}


CONTACT_MEMBERS = MemberMappers(merge=_joined)
