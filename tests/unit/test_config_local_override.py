import pytest

from settings.load_settings import load_settings


def load(tmp_path, monkeypatch, base, local=None, name="config.yaml"):
    (tmp_path / name).write_text(base)
    if local is not None:
        (tmp_path / name.replace(".yaml", ".local.yaml")).write_text(local)
    monkeypatch.setenv("RPP_CONFIG_FILE", str(tmp_path / name))
    return load_settings()


def test_without_a_local_file_the_base_file_is_used(tmp_path, monkeypatch):
    settings = load(tmp_path, monkeypatch, "rpp_epp_host: base.example\nrpp_epp_port: 743\n")

    assert settings.epp.rpp_epp_host == "base.example"
    assert settings.epp.rpp_epp_port == 743


def test_the_local_file_replaces_the_keys_it_has(tmp_path, monkeypatch):
    settings = load(tmp_path, monkeypatch, "rpp_epp_host: base.example\nrpp_epp_port: 743\n",
                    "rpp_epp_host: local.example\n")

    assert settings.epp.rpp_epp_host == "local.example"
    assert settings.epp.rpp_epp_port == 743


def test_the_local_file_replaces_a_mapping_whole(tmp_path, monkeypatch):
    settings = load(tmp_path, monkeypatch, "rpp_epp_host: h\nrpp_idn_lgr_tables:\n  latn-1.0: de\n  spa-1.0: es\n",
                    "rpp_idn_lgr_tables:\n  latn-1.0: xx\n")

    assert settings.epp.rpp_idn_lgr_tables == {"latn-1.0": "xx"}


def test_an_empty_local_file_changes_nothing(tmp_path, monkeypatch):
    settings = load(tmp_path, monkeypatch, "rpp_epp_host: base.example\n", "")

    assert settings.epp.rpp_epp_host == "base.example"


def test_the_local_file_sits_next_to_the_file_named_by_the_environment(tmp_path, monkeypatch):
    settings = load(tmp_path, monkeypatch, "rpp_epp_host: base.example\n", "rpp_epp_host: local.example\n",
                    name="other.yaml")

    assert settings.epp.rpp_epp_host == "local.example"


def test_the_profile_is_the_protocols_without_a_profile_of_the_server(tmp_path, monkeypatch):
    settings = load(tmp_path, monkeypatch, "rpp_backend: rri\n")

    generic, specific = settings.profile_layers
    assert generic["name"] == "RRI"
    assert specific == {}


def test_the_profile_of_the_server_extends_a_generic_one(tmp_path, monkeypatch):
    settings = load(tmp_path, monkeypatch,
                    "rpp_backend_profile:\n  extends: epp\n  contact:\n    fax:\n      supported: false\n")

    generic, specific = settings.profile_layers
    assert generic["name"] == "EPP"
    assert specific == {"contact": {"fax": {"supported": False}}}


def test_a_profile_extends_only_a_generic_one(tmp_path, monkeypatch):
    with pytest.raises(ValueError, match="extends one of epp, rri"):
        load(tmp_path, monkeypatch, "rpp_backend_profile:\n  extends: ../secrets\n")


def test_the_lgrs_come_from_the_config_of_the_protocol(tmp_path, monkeypatch):
    assert load(tmp_path, monkeypatch, "rpp_idn_lgr_tables:\n  latn-1.0: de\n").lgrs == ("latn-1.0",)
    assert load(tmp_path, monkeypatch, "rpp_backend: rri\nrpp_rri_lgr: latn-1.0\n").lgrs == ("latn-1.0",)
    assert load(tmp_path, monkeypatch, "rpp_backend: rri\n").lgrs == ()
