"""The runner's selectors, test environments and pacing (docs/rri/refactoring.md §5.2, §5.3)."""
import base64
from dataclasses import replace

import pytest

from registry_adapter.epp.profile import EPP_PROFILE
from tests.helper import selectors
from tests.helper.pacer import Pacer
from tests.helper.selectors import Facts, SelectorError
from tests.helper.test_environment import (
    Credentials, EnvironmentError, environment_names, load, replace_values,
)

FACTS = Facts(EPP_PROFILE, {"tld": "example", "restore_within_run": True, "failed_logins_lock": False})

EPP_ENV = {"TEST_EPP_REGACC1": "foo", "TEST_EPP_REGACC1_PASSWORD": "bar", "TEST_EPP_REGACC1_PREFIX": "FO-",
           "TEST_EPP_REGACC2": "baz", "TEST_EPP_REGACC2_PASSWORD": "qux", "TEST_EPP_REGACC2_PREFIX": "BA-"}


@pytest.mark.parametrize("selector", [
    {"profile.host_objects": True},
    {"profile.contact_labels": {"contains": "admin"}},
    {"profile.max_registrants": {"min": 1}},
    {"profile.max_registrants": {"max": 1}},
    {"profile.max_registrants": {"not": 2}},
    {"env.tld": "example", "profile.supports_renew": True},
    [{"profile.host_objects": False}, {"env.restore_within_run": True}],
])
def test_selector_holds(selector):
    assert selectors.holds(selector, FACTS)


@pytest.mark.parametrize("selector", [
    {"profile.host_objects": False},
    {"profile.contact_labels": {"contains": "abuse"}},
    {"profile.max_registrants": {"min": 2}},
    {"env.tld": "de", "profile.supports_renew": True},
    [{"profile.host_objects": False}, {"env.tld": "de"}],
])
def test_selector_does_not_hold(selector):
    assert not selectors.holds(selector, FACTS)


def test_unmet_names_the_fact():
    assert selectors.unmet({"profile.host_objects": False}, FACTS) == ["profile.host_objects is True, not False"]


@pytest.mark.parametrize("selector", [{"profile.hostObjects": True}, {"env.nope": 1}, {"backend": "epp"}, {}, []])
def test_a_key_that_names_no_fact_is_an_error(selector):
    with pytest.raises(SelectorError):
        selectors.unmet(selector, FACTS)


def test_select_takes_the_first_entry_that_holds():
    value = {"select": [{"when": {"profile.host_objects": False}, "then": 1},
                        {"when": {"env.tld": "example"}, "then": {"x": {"select": [{"then": 2}]}}},
                        {"then": 3}]}
    assert selectors.resolve(value, FACTS) == {"x": 2}


def test_select_falls_back_to_the_default():
    assert selectors.resolve({"select": [{"when": {"env.tld": "de"}, "then": 1}, {"then": 3}]}, FACTS) == 3


@pytest.mark.parametrize("case", [
    {"when": {"env.nope": True}, "steps": []},
    {"steps": [{"when": {"profile.nope": 1}, "request": {}, "response": {}}]},
    {"steps": [{"when": {"env.tld": "x"}, "capture": {"id": "id"}, "request": {}, "response": {}}]},
    {"steps": [{"request": {}, "response": {"select": [{"when": {"env.tld": "x"}, "then": 1}]}}]},
    {"steps": [{"request": {}, "response": {"select": [{"then": 1}, {"when": {"env.tld": "x"}, "then": 2}]}}]},
    {"steps": [{"request": {}, "response": {"select": [{"when": {"env.nope": "x"}, "then": 1}, {"then": 2}]}}]},
])
def test_check_refuses_a_bad_case(case):
    with pytest.raises(SelectorError):
        selectors.check(case, FACTS)


def test_check_accepts_a_good_case():
    selectors.check({"when": {"env.tld": "example"}, "steps": [
        {"when": {"profile.host_objects": True}, "request": {}, "response": {}},
        {"request": {}, "capture": {"id": "id"},
         "response": {"select": [{"when": {"env.tld": "x"}, "then": 1}, {"then": 2}]}},
    ]}, FACTS)


def test_every_environment_descriptor_loads_and_names_a_profile():
    for name in environment_names():
        env = load(name, with_credentials=False)
        assert env.declared_profile().name


def test_a_missing_variable_is_named_and_refused():
    with pytest.raises(EnvironmentError, match="TEST_EPP_REGACC2_PASSWORD"):
        load("epp-docker", environ={k: v for k, v in EPP_ENV.items() if k != "TEST_EPP_REGACC2_PASSWORD"})


def test_values_of_the_epp_environment():
    env = load("epp-docker", environ=EPP_ENV)
    assert replace_values("{handle:a:ud1} {handle:b:x} {regacc:a} d.{tld}", env, "r") == "FO-rud1 BA-rx foo d.example"


def test_credentials_are_put_into_the_header_only():
    credentials = Credentials(load("epp-docker", environ=EPP_ENV))
    assert credentials.header("{auth:a}") == "Basic " + base64.b64encode(b"foo:bar").decode()
    assert credentials.header("{auth:b}") == "Basic " + base64.b64encode(b"baz:qux").decode()
    assert credentials.header("{auth:a:wrong_password}") == "Basic " + base64.b64encode(b"foo:cat").decode()
    assert credentials.header("{auth:unknown_user}") == "Basic " + base64.b64encode(b"ghost:nope").decode()
    assert credentials.header("application/rpp+json") == "application/rpp+json"
    assert "bar" not in repr(load("epp-docker", environ=EPP_ENV))


def test_wrong_credentials_are_refused_where_failed_logins_lock():
    env = load("epp-docker", environ=EPP_ENV)
    credentials = Credentials(replace(env, facts={**env.facts, "failed_logins_lock": True}))
    # an environment that locks never gets these forms, whatever its descriptor says
    for value in ("{auth:a:wrong_password}", "{auth:unknown_user}"):
        with pytest.raises(EnvironmentError, match="lock"):
            credentials.header(value)


def test_rri_values_come_from_the_variables_and_the_login():
    environ = {"TEST_RRI_REGACC1": "DENIC-99995-RRI", "TEST_RRI_REGACC1_PASSWORD": "pw",
               "TEST_RRI_REGACC1_PREFIX": "DENIC-99995-T-", "TEST_RRI_REGACC2_PREFIX": "DENIC-99996-T-",
               "TEST_RRI_REGACC1_GEN_REQ": "DENIC-99995-GR", "TEST_RRI_REGACC1_ABUSE": "DENIC-99995-AB",
               "TEST_RRI_REGACC2": "DENIC-99996-RRI", "TEST_RRI_REGACC2_PASSWORD": "pw",
               "TEST_RRI_REGACC2_GEN_REQ": "DENIC-99996-GR", "TEST_RRI_REGACC2_ABUSE": "DENIC-99996-AB"}
    if "rri-mtest" not in environment_names():
        pytest.skip("no RRI environment yet")
    env = load("rri-mtest", environ=environ)
    assert replace_values("{handle:a:x} {regacc:b} {gen_req:a} {abuse:b} {tld}", env, "r") == \
        "DENIC-99995-T-rx DENIC-99996 DENIC-99995-GR DENIC-99996-AB de"


def test_pacer_spaces_the_requests_of_each_registrar():
    now = [0.0]
    waits = []

    def sleep(seconds):
        waits.append(seconds)
        now[0] += seconds

    pacer = Pacer(30, 2, lambda value: value or None, clock=lambda: now[0], sleep=sleep)
    for slot in ("a", "a", "b", "a"):
        pacer.wait({"Authorization": slot})
    pacer.wait({})
    assert waits == [4.0, 4.0]


def test_an_omitting_select_leaves_the_member_or_element_out():
    value = {"a": 1, "b": {"select": [{"when": {"env.tld": "example"}, "omit": True}, {"then": 2}]},
             "c": [1, {"select": [{"when": {"env.tld": "example"}, "omit": True}, {"then": 2}]}]}
    assert selectors.resolve(value, FACTS) == {"a": 1, "c": [1]}
    assert selectors.resolve({"b": {"select": [{"when": {"env.tld": "de"}, "omit": True}, {"then": 2}]}}, FACTS) == {"b": 2}


def test_check_accepts_omit_and_refuses_both():
    selectors.check({"steps": [{"request": {"x": {"select": [{"when": {"env.tld": "x"}, "omit": True}, {"then": 1}]}},
                                "response": {}}]}, FACTS)
    with pytest.raises(SelectorError):
        selectors.check({"steps": [{"request": {"x": {"select": [{"omit": True, "then": 1}]}}, "response": {}}]}, FACTS)
