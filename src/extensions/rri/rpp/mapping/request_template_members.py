"""The request templates of a registrar: the members the rri extension adds to an organisation (`generalRequestTemplate` and
`abuseTemplate`, docs/rri/rri-extension.md). They are read only, and not references to request contacts: a registrar's template has no
handle."""
from core.model.organisation.organisation import Organisation
from extensions.rri.core.model.registrar_request_templates import RegistrarRequestTemplates, RequestTemplate
from extensions.rri.core.ports.rri_gateways import EXTENSION_ID

TYPE = "requestTemplate"


def _template(template: RequestTemplate) -> dict:
    rpp = {"@type": TYPE, "uriTemplate": template.uri_template}
    if template.up_date:
        rpp["upDate"] = template.up_date
    return rpp


class RequestTemplateMembers:
    """The mapper of the rri extension for the members of an organisation (`ORGANISATION_MEMBERS`)."""
    extension_id = EXTENSION_ID
    members = ("generalRequestTemplate", "abuseTemplate")

    def to_rpp(self, organisation: Organisation) -> dict:
        """The templates of the organisation, those it has."""
        held = organisation.extensions.get(EXTENSION_ID)
        if not isinstance(held, RegistrarRequestTemplates):
            return {}
        templates = {"generalRequestTemplate": held.general_request, "abuseTemplate": held.abuse}
        return {member: _template(template) for member, template in templates.items() if template is not None}
