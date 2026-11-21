"""Includes of the integration case files (tests/helper/includes.py, #218)."""
import json

import pytest

from tests.helper.includes import IncludeError, expand

STEP = {"comment": "c", "request": {"method": "GET", "url": "/x/{param:name}"}, "response": {"status": 200}}


@pytest.fixture
def includes(tmp_path):
    def write(name, steps, parameters=None):
        definition = {"comment": "c", "steps": steps}
        if parameters is not None:
            definition["parameters"] = parameters
        (tmp_path / f"{name}.json").write_text(json.dumps(definition))
    write.dir = tmp_path
    return write


def test_an_include_becomes_a_block_of_its_steps_with_the_parameters(includes):
    includes("get", [STEP], {"name": {"comment": "c"}})

    case = expand({"steps": [{"comment": "uses", "include": "get", "with": {"name": "n1"}}]}, includes.dir)

    assert case["steps"] == [{"comment": "uses", "block": [{**STEP, "request": {**STEP["request"], "url": "/x/n1"}}],
                              "origin": "get"}]


def test_a_parameter_alone_in_a_string_takes_any_json_value(includes):
    includes("post", [{"request": {"body_json": "{param:body}"}, "response": {"status": "{param:status}"}}],
             {"body": {}, "status": {}})

    block = expand({"steps": [{"include": "post", "with": {"body": {"a": [1]}, "status": 201}}]}, includes.dir)

    assert block["steps"][0]["block"] == [{"request": {"body_json": {"a": [1]}}, "response": {"status": 201}}]


def test_a_parameter_with_a_default_may_be_left_out(includes):
    includes("get", [STEP], {"name": {"default": "d"}})

    case = expand({"steps": [{"include": "get"}]}, includes.dir)

    assert case["steps"][0]["block"][0]["request"]["url"] == "/x/d"


def test_a_default_may_use_the_other_parameters_also_their_defaults(includes):
    includes("post", [{"request": {"body_json": "{param:body}"}}],
             {"name": {}, "id": {"default": "{param:name}-1"}, "body": {"default": {"id": "{param:id}", "n": "{param:name}"}}})

    default = expand({"steps": [{"include": "post", "with": {"name": "n"}}]}, includes.dir)
    given = expand({"steps": [{"include": "post", "with": {"name": "n", "id": "x"}}]}, includes.dir)

    assert default["steps"][0]["block"][0]["request"]["body_json"] == {"id": "n-1", "n": "n"}
    assert given["steps"][0]["block"][0]["request"]["body_json"] == {"id": "x", "n": "n"}


def test_a_default_that_uses_itself_fails(includes):
    includes("post", [{"request": {"body_json": "{param:a}"}}], {"a": {"default": {"x": "{param:b}"}},
                                                                    "b": {"default": {"y": "{param:a}"}}})

    with pytest.raises(IncludeError, match="uses itself"):
        expand({"steps": [{"include": "post"}]}, includes.dir)


def test_other_placeholders_are_kept_for_the_run(includes):
    includes("get", [STEP], {"name": {}})

    case = expand({"steps": [{"include": "get", "with": {"name": "{random_name}.{tld}"}}]}, includes.dir)

    assert case["steps"][0]["block"][0]["request"]["url"] == "/x/{random_name}.{tld}"


def test_the_when_of_the_include_is_on_the_block(includes):
    includes("get", [STEP], {"name": {}})

    case = expand({"setup": [{"include": "get", "with": {"name": "n"}, "when": {"env.tld": "de"}}]}, includes.dir)

    assert case["setup"][0]["when"] == {"env.tld": "de"}


def test_includes_are_expanded_in_every_phase_and_in_loops(includes):
    includes("get", [STEP], {"name": {}})
    use = {"include": "get", "with": {"name": "n"}}

    case = expand({"setup": [use], "steps": [{"loop": [use]}], "teardown": [use]}, includes.dir)

    assert case["setup"][0]["origin"] == case["steps"][0]["loop"][0]["origin"] == case["teardown"][0]["origin"] == "get"


def test_an_include_may_use_an_include_with_its_own_parameters(includes):
    includes("get", [STEP], {"name": {}})
    includes("outer", [{"include": "get", "with": {"name": "{param:who}-x"}}], {"who": {}})

    case = expand({"steps": [{"include": "outer", "with": {"who": "w"}}]}, includes.dir)

    inner = case["steps"][0]["block"][0]
    assert inner["origin"] == "get" and inner["block"][0]["request"]["url"] == "/x/w-x"


@pytest.mark.parametrize("use, message", [
    ({"include": "nope"}, "unknown include 'nope'"),
    ({"include": "get"}, "include 'get': parameter name is missing"),
    ({"include": "get", "with": {"name": "n", "nmae": "x"}}, "include 'get': unknown parameter nmae"),
    ({"include": "undeclared"}, "include 'undeclared': parameter name is not declared"),
    ({"include": "loop_a"}, "include 'loop_a' includes itself: loop_a > loop_b > loop_a"),
    ({"include": "get", "with": {"name": "n"}, "capture": {}}, "include 'get': unknown keys ['capture']"),
])
def test_a_bad_include_names_the_include_and_the_parameter(includes, use, message):
    includes("get", [STEP], {"name": {}})
    includes("undeclared", [STEP])
    includes("loop_a", [{"include": "loop_b"}])
    includes("loop_b", [{"include": "loop_a"}])

    with pytest.raises(IncludeError) as raised:
        expand({"steps": [use]}, includes.dir)

    assert message in str(raised.value)
