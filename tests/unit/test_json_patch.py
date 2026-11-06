import pytest

from rpp_to_model_mapper import PatchNotApplicable, json_patch
from rpp_to_model_mapper.rpp_models import RPPPatchOperation

DOCUMENT = {
    "name": "foo.example",
    "nameservers": [{"hostName": "ns1.foo.example"}, {"hostName": "ns2.foo.example"}],
    "contacts": [
        {"label": "tech", "object": {"id": "REG-200"}},
        {"label": "tech", "object": {"id": "REG-300"}},
        {"label": "admin", "object": {"id": "REG-100"}},
    ],
    "registrant": {"id": "REG-1"},
}
ARRAYS = ("/nameservers", "/contacts", "/status")


def patch(*operations, document=DOCUMENT):
    return json_patch.apply(document, [RPPPatchOperation.from_dict(operation) for operation in operations], ARRAYS)


def op(name, path, **members):
    return {"op": name, "path": path, **members}


def test_the_document_is_not_changed():
    patch(op("remove", "/nameservers"))

    assert "nameservers" in DOCUMENT


def test_replace_whole_array():
    assert patch(op("replace", "/nameservers", value=[]))["nameservers"] == []


def test_remove_whole_array():
    assert "nameservers" not in patch(op("remove", "/nameservers"))


def test_add_appends():
    result = patch(op("add", "/nameservers", value={"hostName": "ns3.foo.example"}))

    assert result["nameservers"][-1] == {"hostName": "ns3.foo.example"}


def test_add_to_an_absent_array_creates_it():
    assert patch(op("add", "/status", value={"label": "clientHold"}))["status"] == [{"label": "clientHold"}]


def test_remove_by_partial_match_removes_all_matches():
    result = patch(op("remove", "/contacts", match={"label": "tech"}))

    assert [c["object"]["id"] for c in result["contacts"]] == ["REG-100"]


def test_match_reaches_the_nested_object_of_the_example():
    result = patch(op("remove", "/contacts", match={"label": "tech", "object": {"id": "REG-200"}}))

    assert len(result["contacts"]) == 2


def test_replace_with_one_match():
    result = patch(op("replace", "/nameservers", match={"hostName": "ns1.foo.example"}, value={"hostName": "ns9.foo.example"}))

    assert result["nameservers"][0] == {"hostName": "ns9.foo.example"}


def test_replace_with_several_matches_is_ambiguous():
    with pytest.raises(PatchNotApplicable, match="Operation 1.*ambiguous"):
        patch(op("replace", "/contacts", match={"label": "tech"}, value={"label": "tech", "object": {"id": "X"}}))


@pytest.mark.parametrize("name", ["remove", "replace"])
def test_no_matching_element_fails(name):
    with pytest.raises(PatchNotApplicable, match="no element matches"):
        patch(op(name, "/nameservers", match={"hostName": "other"}, value={"hostName": "x"}))


def test_a_failure_names_the_operation():
    with pytest.raises(PatchNotApplicable, match="Operation 2"):
        patch(op("replace", "/nameservers", value=[]), op("remove", "/nameservers", match={"hostName": "a"}))


def test_primitive_lists_match_in_any_order():
    document = {"items": [{"tld": ["example", "org"]}, {"tld": ["example"]}]}

    result = json_patch.apply(
        document, [RPPPatchOperation.from_dict(op("remove", "/items", match={"tld": ["org", "example"]}))], ("/items",),
    )

    assert result["items"] == [{"tld": ["example"]}]


def test_operations_apply_in_order():
    result = patch(op("replace", "/nameservers", value=[]), op("add", "/nameservers", value={"hostName": "a"}))

    assert result["nameservers"] == [{"hostName": "a"}]


def test_object_property_is_set_and_removed():
    assert patch(op("replace", "/registrant", value={"id": "REG-2"}))["registrant"] == {"id": "REG-2"}
    assert "registrant" not in patch(op("remove", "/registrant"))


def test_ignored_path_is_left_to_the_caller():
    result = json_patch.apply(DOCUMENT, [RPPPatchOperation.from_dict(op("remove", "/authInfo"))], ARRAYS, "/authInfo")

    assert result == DOCUMENT


@pytest.mark.parametrize("operation", [
    op("move", "/registrant", value={}),
    op("add", "/nameservers", match={"hostName": "a"}, value={}),
    op("replace", "/nameservers/0/hostName", value="x"),
    op("replace", "/missing/child", value="x"),
    op("replace", "/registrant", match={"id": "x"}, value={}),
    op("replace", "/nameservers", value={"hostName": "not a list"}),
    op("replace", "/registrant"),
    op("remove", "/nameservers", match={"hostName": None}),
    op("remove", "/", ),
])
def test_invalid_operations(operation):
    with pytest.raises(ValueError):
        patch(operation)


def test_removing_an_absent_property_fails():
    with pytest.raises(PatchNotApplicable):
        patch(op("remove", "/expiryDate"))
