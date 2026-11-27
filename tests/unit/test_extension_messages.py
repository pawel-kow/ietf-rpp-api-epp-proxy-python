"""`rpp:messages`: the message types an extension defines (json has no extension point for the `data` union of a message)."""
import pytest

from rpp.schema.effective_schema import compose
from rpp.schema.extension_registration import check_names
from rpp.schema.extensions import EXTENSIONS, _from_schema

NOTE = {"type": "object", "properties": {"@type": {"const": "noteMessage"}, "text": {"type": "string"}},
        "required": ["@type", "text"]}


def schema(extension_id="x.messages", messages=None, defs=None):
    return {"$id": "https://x.example/m.json", "rpp:extension": {"id": extension_id, "name": "x", "version": "1.0"},
            "rpp:extends": {}, "rpp:messages": messages if messages is not None else {"noteMessage": "#/$defs/ext.x.noteMessage.read"},
            "$defs": defs if defs is not None else {"ext.x.noteMessage.read": NOTE}}


def test_the_message_types_of_an_extension_are_read_from_its_schema():
    assert _from_schema(schema()).messages == {"noteMessage": "ext.x.noteMessage.read"}


def test_a_target_the_extension_does_not_define_is_refused():
    with pytest.raises(ValueError, match="maps the message type noteMessage to ext.x.other.read, which it does not define"):
        check_names(schema(messages={"noteMessage": "#/$defs/ext.x.other.read"}))


def test_the_identifier_of_a_base_message_type_is_refused():
    with pytest.raises(ValueError, match="maps serviceNoticeMessage, a message type of the base schema"):
        check_names(schema(messages={"serviceNoticeMessage": "#/$defs/ext.x.noteMessage.read"}))


def test_the_identifier_of_another_extensions_message_type_is_refused():
    EXTENSIONS["x.first"] = _from_schema(schema("x.first"))
    try:
        with pytest.raises(ValueError, match="maps noteMessage, which the extension x.first maps"):
            check_names(schema("x.second"))
    finally:
        del EXTENSIONS["x.first"]


@pytest.mark.parametrize("message", ["message.read", "message.create"])
def test_the_effective_schema_adds_a_branch_for_each_message_type(message):
    extension = _from_schema(schema())

    branches = compose([extension], (), False)[message]["properties"]["data"]["oneOf"]

    assert {"$ref": "#/$defs/ext.x.noteMessage.read"} in branches
    assert {"$ref": "#/$defs/serviceNoticeMessage.read"} in branches


def test_without_the_extension_the_data_of_a_message_has_the_branches_of_the_base_only():
    branches = compose([], (), False)["message.read"]["properties"]["data"]["oneOf"]

    assert {"$ref": "#/$defs/ext.x.noteMessage.read"} not in branches and len(branches) == 6
