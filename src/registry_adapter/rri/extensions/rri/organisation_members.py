import logging

from extensions.rri.core.model.registrar_request_templates import RegistrarRequestTemplates, RequestTemplate
from registry_adapter.rri.commands.shared.rri_time import utc_time
from registry_adapter.rri.xml.generated.contact_5_0 import RoleType

logger = logging.getLogger(__name__)


def _template(entry) -> RequestTemplate | None:
    """A `regacc:contact` as a template: one without a `contact:uri-template` is left out."""
    if entry is None or entry.uri_template is None or not entry.uri_template.value:
        if entry is not None:
            logger.warning("regacc INFO: a request template is left out, it has no uri-template")
        return None
    return RequestTemplate(uri_template=entry.uri_template.value, up_date=utc_time(entry.changed) if entry.changed else None)


def organisation_members(data) -> RegistrarRequestTemplates:
    """The request templates of a RegAcc, from the `contact` entries of its regacc INFO by role."""
    by_role = {}
    for entry in data.contact:
        by_role.setdefault(entry.role, entry)
    return RegistrarRequestTemplates(general_request=_template(by_role.get(RoleType.GENERALREQUEST)),
                                     abuse=_template(by_role.get(RoleType.ABUSECONTACT)))


ORGANISATION_MEMBERS = organisation_members
