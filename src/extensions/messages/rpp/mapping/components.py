"""The Component Objects of the messages extension (docs/extensions/messages-extension.md) as the members of a message type
of a dependent extension: an Object Reference Object or a Dated Object Reference Object, and a Registry Notice Object."""
from extensions.messages.core.model.object_reference import ObjectReference
from extensions.messages.core.model.registry_notice import RegistryNotice


def reference(reference: ObjectReference) -> dict:
    """An Object Reference Object, a Dated Object Reference Object where the reference has a date."""
    if reference.date is None:
        return {"@type": "objectReference", "objectType": reference.object_type, "objectId": reference.object_id}
    return {"@type": "datedObjectReference", "objectType": reference.object_type, "objectId": reference.object_id,
            "date": reference.date}


def notice(notice: RegistryNotice) -> dict:
    rpp = {"@type": "registryNotice", "code": notice.code, "text": notice.text}
    if notice.arguments:
        rpp["arguments"] = list(notice.arguments)
    return rpp


def subject(reference: ObjectReference) -> dict:
    """The Object Type and the Object Identifier of the Base Message Object."""
    return {"objectType": reference.object_type, "objectId": reference.object_id}
