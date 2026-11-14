"""The runner's selectors, test environments and pacing (docs/rri/refactoring.md §5.2, §5.3)."""
import base64
import pytest

from tests.helper.profiles import EPP_PROFILE
from tests.helper import durations, selectors
from tests.helper.one_of import OneOf
from tests.helper.pacer import Pacer
from tests.helper.recursive_compare_existing import recusive_compare_existing
from tests.helper.selectors import Facts, SelectorError
from tests.helper.test_environment import (
    Credentials, EnvironmentError, environment_names, load, replace_fact, replace_values,
)

FACTS = Facts(EPP_PROFILE, {"tld": "example", "domainName": {"processes": {"restore": {"within_run": True}}}})

EPP_ENV = {"TEST_EPP_REGACC1": "foo", "TEST_EPP_REGACC1_PASSWORD": "bar", "TEST_EPP_REGACC1_PREFIX": "FO-",
           "TEST_EPP_REGACC2": "baz", "TEST_EPP_REGACC2_PASSWORD": "qux", "TEST_EPP_REGACC2_PREFIX": "BA-"}


@pytest.mark.parametrize("selector", [
    {"profile.objects": {"contains": "host"}},
    {"profile.domainName.contacts.labels": {"contains": "admin"}},
    {"profile.domainName.registrant.max_count": {"min": 1}},
    {"profile.domainName.registrant.max_count": {"max": 1}},
    {"profile.domainName.registrant.max_count": {"not": 2}},
    {"env.tld": "example", "profile.domainName.processes.renew.supported": True},
    [{"profile.objects": {"not": {"contains": "host"}}}, {"env.domainName.processes.restore.within_run": True}],
])
def test_selector_holds(selector):
    assert selectors.holds(selector, FACTS)


@pytest.mark.parametrize("selector", [
    {"profile.objects": {"not": {"contains": "host"}}},
    {"profile.domainName.contacts.labels": {"contains": "abuse"}},
    {"profile.domainName.registrant.max_count": {"min": 2}},
    {"env.tld": "de", "profile.domainName.processes.renew.supported": True},
    [{"profile.objects": {"not": {"contains": "host"}}}, {"env.tld": "de"}],
])
def test_selector_does_not_hold(selector):
    assert not selectors.holds(selector, FACTS)


def test_unmet_names_the_fact():
    assert selectors.unmet({"profile.contact.fax.supported": False}, FACTS) == [
        "profile.contact.fax.supported is True, not False"]


@pytest.mark.parametrize("selector", [
    {"profile.hostObjects": True}, {"env.nope": 1}, {"backend": "epp"}, {}, [],
    {"profile.contact.fax": True}, {"env.domainName.processes": True}, {"env.tld.x": 1},
])
def test_a_key_that_names_no_fact_is_an_error(selector):
    with pytest.raises(SelectorError):
        selectors.unmet(selector, FACTS)


def test_select_takes_the_first_entry_that_holds():
    value = {"select": [{"when": {"profile.objects": {"not": {"contains": "host"}}}, "then": 1},
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
        {"when": {"profile.objects": {"contains": "host"}}, "request": {}, "response": {}},
        {"request": {}, "capture": {"id": "id"},
         "response": {"select": [{"when": {"env.tld": "x"}, "then": 1}, {"then": 2}]}},
    ]}, FACTS)


def test_every_environment_has_the_profile_tld_and_lgrs_of_its_config():
    for name in environment_names():
        env = load(name, with_credentials=False)
        assert env.profile.name
        assert env.facts["tld"] and env.facts["environment_name"]
        assert env.profile.lgrs == ("latn-1.0",)


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
    assert credentials.header("{auth:unknown_user}") == "Basic " + base64.b64encode(b"ghost:nope").decode()
    assert credentials.header("application/rpp+json") == "application/rpp+json"
    assert "bar" not in repr(load("epp-docker", environ=EPP_ENV))


def test_no_case_logs_in_to_a_test_account_with_a_wrong_password():
    credentials = Credentials(load("epp-docker", environ=EPP_ENV))
    with pytest.raises(EnvironmentError, match="Malformed"):
        credentials.header("{auth:a:wrong_password}")


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


def test_a_list_fact_as_a_whole_value_is_one_of_its_entries():
    env = load("epp-docker", environ=EPP_ENV)
    env.facts["domainName"]["processes"]["create"]["success_status"] = ["pendingCreate", "inactive"]

    assert replace_fact("{env:domainName.processes.create.success_status}", env) == OneOf(["pendingCreate", "inactive"])
    assert replace_fact("{env:domainName.authInfo.min_length}", env) == "{env:domainName.authInfo.min_length}"
    assert replace_values("at least {env:domainName.authInfo.min_length}", env, "r") == "at least 6"
    with pytest.raises(EnvironmentError, match="whole value"):
        replace_values("is {env:domainName.processes.create.success_status}", env, "r")
    with pytest.raises(EnvironmentError, match="no such fact"):
        replace_fact("{env:domainName.processes}", env)


def test_one_of_takes_any_of_its_entries_case_blind():
    expected = [{"@type": "domainStatus", "label": OneOf(["pendingCreate", "inactive"])}]

    recusive_compare_existing("c", "$", [{"@type": "domainStatus", "label": "pendingcreate"}], expected, False)
    recusive_compare_existing("c", "$", [{"@type": "domainStatus", "label": "inactive", "due": "x"}], expected, False)
    with pytest.raises(AssertionError, match="does not match"):
        recusive_compare_existing("c", "$", [{"@type": "domainStatus", "label": "ok"}], expected, False)


@pytest.mark.parametrize("duration, expected", [
    ("PT2M", 120), ("PT1M30S", 90), ("P1D", 86400), ("P1DT14H", 136800), ("P1W", 604800), ("PT0S", 0),
])
def test_iso_durations_are_seconds(duration, expected):
    assert durations.seconds(duration) == expected


@pytest.mark.parametrize("duration", ["P", "PT", "P1M", "P1Y", "PT1.5M", "2M", "P1DT", None])
def test_a_duration_without_a_fixed_length_is_refused(duration):
    with pytest.raises(ValueError):
        durations.seconds(duration)


def test_the_run_waits_ten_minutes_and_ten_percent_unless_told_otherwise():
    assert durations.max_wait({}) == 600
    assert durations.buffer_percent({}) == 10
    assert durations.max_wait({"RPP_TEST_MAX_WAIT": "P2D"}) == 172800
    assert durations.buffer_percent({"RPP_TEST_WAIT_BUFFER": "25"}) == 25


PERIODS = {"domainName": {"processes": {"create": {"add_grace_period": "PT2M"},
                                        "delete": {"redemption_period": "P1DT14H"},
                                        "transfer": {"pending_period": None}}}}


def test_a_wait_holds_within_the_longest_wait_of_the_run():
    run = Facts(EPP_PROFILE, PERIODS, max_wait=600, buffer_percent=10)

    assert selectors.holds({"wait.domainName.processes.create.add_grace_period": True}, run)
    assert run.wait_seconds("domainName.processes.create.add_grace_period") == 132
    assert selectors.unmet({"wait.domainName.processes.delete.redemption_period": True}, run) == [
        "wait.domainName.processes.delete.redemption_period needs 150480 s, the run waits at most 600 s "
        "(RPP_TEST_MAX_WAIT)"]
    assert selectors.holds({"wait.domainName.processes.delete.redemption_period": True},
                           Facts(EPP_PROFILE, PERIODS, max_wait=None))


def test_a_case_does_not_run_where_the_server_lacks_the_transition_it_waits_for():
    run = Facts(EPP_PROFILE, PERIODS, max_wait=600)

    assert selectors.unmet({"wait.domainName.processes.transfer.pending_period": True}, run) == [
        "wait.domainName.processes.transfer.pending_period: the server has no such transition"]


@pytest.mark.parametrize("case", [
    {"steps": [{"wait": "domainName.processes.create.add_grace_period", "request": {}, "response": {}}]},
    {"when": {"wait.domainName.processes.create.add_grace_period": True},
     "steps": [{"wait": "domainName.processes.delete.redemption_period", "request": {}, "response": {}}]},
    {"steps": [{"delay_seconds": 125, "request": {}, "response": {}}]},
    {"when": {"wait.domainName.processes.create.add_grace_period": False}, "steps": []},
    {"when": {"wait.domainName.nope": True}, "steps": []},
])
def test_a_case_names_the_waits_it_relies_on(case):
    with pytest.raises(SelectorError):
        selectors.check(case, Facts(EPP_PROFILE, PERIODS))


def test_a_case_that_selects_its_waits_is_accepted():
    selectors.check({"when": {"wait.domainName.processes.create.add_grace_period": True,
                              "wait.domainName.processes.delete.redemption_period": True},
                     "steps": [{"wait": ["domainName.processes.create.add_grace_period",
                                         "domainName.processes.delete.redemption_period"],
                                "request": {}, "response": {}}]}, Facts(EPP_PROFILE, PERIODS))
