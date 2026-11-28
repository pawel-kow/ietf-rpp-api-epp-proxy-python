"""The request contact model ↔ RRI XML: a contact of type REQUEST, which holds a handle and a URI template only."""
from extensions.rri.core.model.request_contact import RequestContact
from registry_adapter.rri.commands.contact.common import REQUEST, changed_of, regacc_of
from registry_adapter.rri.xml.generated import contact_5_0 as rri


def fields_of(contact: RequestContact) -> dict:
    """The fields of CREATE and UPDATE."""
    return dict(
        handle=contact.id,
        type_value=rri.TypeType(value=REQUEST),
        uri_template=rri.UriTemplateType(value=contact.uriTemplate) if contact.uriTemplate is not None else None,
    )


def request_contact_from_rri(data: rri.InfoData) -> RequestContact:
    handle = data.handle.value
    return RequestContact(
        id=handle,
        uriTemplate=data.uri_template.value if data.uri_template is not None else None,
        clID=regacc_of(handle),
        upDate=changed_of(data),
    )
