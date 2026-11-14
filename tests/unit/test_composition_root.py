import ssl
from types import SimpleNamespace

import main
from main import new_backend, new_epp_client, settings, tls_context, tls_context_from_config
from registry_adapter.common.transport.tcp_client import TCPClient
from registry_adapter.epp.gateways.epp_backend import EppBackend
from registry_adapter.rri.gateways.rri_backend import RriBackend
from settings.load_settings import load_settings
from tests.helper.test_environment import REPOSITORY

import pytest

# The tests of the EPP composition hold where the test environment composes the app for EPP.
epp_only = pytest.mark.skipif(settings.backend != "epp", reason="the app under test is not composed for EPP")


def test_default_factory_connects_to_the_configured_backend():
    client = new_epp_client("user", "pw")

    assert isinstance(client.client, TCPClient)
    assert client.client.server_address == settings.epp.rpp_epp_host
    assert client.client.server_port == settings.epp.rpp_epp_port


def test_default_factory_uses_the_request_credentials():
    client = new_epp_client("user", "pw")

    assert client.verify_credentials("user", "pw")


@epp_only
def test_the_backend_is_epp_over_the_default_client():
    backend = new_backend("user", "pw")

    assert isinstance(backend, EppBackend)
    assert backend.epp_client.client.server_address == settings.epp.rpp_epp_host
    assert backend.sponsor_id == "user"


def test_no_tls_context_when_tls_is_off():
    settings = SimpleNamespace(rpp_epp_use_tls=False, rpp_epp_tls_insecure_skip_verify=True)

    assert tls_context_from_config(settings) is None


def test_tls_context_verifies_unless_told_otherwise():
    settings = SimpleNamespace(rpp_epp_use_tls=True, rpp_epp_tls_insecure_skip_verify=False)

    assert tls_context_from_config(settings).verify_mode == ssl.CERT_REQUIRED


def test_tls_context_honours_the_opt_in():
    settings = SimpleNamespace(rpp_epp_use_tls=True, rpp_epp_tls_insecure_skip_verify=True)

    assert tls_context_from_config(settings).verify_mode == ssl.CERT_NONE


def test_skip_verify_warns(caplog):
    settings = SimpleNamespace(rpp_epp_use_tls=True, rpp_epp_tls_insecure_skip_verify=True)

    tls_context_from_config(settings)

    assert "rpp_epp_tls_insecure_skip_verify" in caplog.text


def test_default_factory_passes_the_tls_context_to_the_transport():
    client = new_epp_client("user", "pw")

    assert client.client.tls_context is tls_context


def test_tls_is_on_and_verified_when_the_config_is_silent(tmp_path, monkeypatch):
    config_file = tmp_path / "config.yaml"
    config_file.write_text("rpp_epp_host: example.org\n")
    monkeypatch.setenv("RPP_CONFIG_FILE", str(config_file))

    loaded = load_settings()

    assert loaded.epp.rpp_epp_use_tls is True
    assert loaded.epp.rpp_epp_tls_insecure_skip_verify is False


def test_the_composition_root_gives_discovery_the_configuration():
    assert settings.discovery.rpp_base_url
    assert settings.discovery.rpp_tlds
    assert settings.discovery.rpp_environment_name
    assert settings.discovery.rpp_environment_status


def test_the_composition_root_hands_the_configuration_to_the_app():
    assert main.app.app.config["RPP_DISCOVERY_SETTINGS"] is settings.discovery


@epp_only
def test_the_app_offers_the_configured_lgrs():
    assert main.app.app.config["RPP_BACKEND_PROFILE"].lgrs == tuple(sorted(settings.epp.rpp_idn_lgr_tables or {}))


@epp_only
def test_the_backend_maps_lgr_to_the_configured_idn_tables():
    tables = main.idn_tables

    for lgr, table in (settings.epp.rpp_idn_lgr_tables or {}).items():
        assert tables.table(lgr) == table
        assert tables.lgr(table) == lgr
    assert new_backend("user", "pw").profile.lgrs == tuple(sorted(settings.epp.rpp_idn_lgr_tables or {}))


def test_compose_builds_an_app_for_other_settings():
    rri = main.compose(load_settings(str(REPOSITORY / "config.rri-mtest.yaml")))

    assert rri.settings.backend == "rri"
    assert rri.app is not main.app
    assert rri.app.app.config["RPP_BACKEND_PROFILE"] is rri.profile
    assert isinstance(rri.new_backend("user", "pw"), RriBackend)
