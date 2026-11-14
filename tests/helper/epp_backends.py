from registry_adapter.epp.gateways.epp_backend import EppBackend
from tests.helper.epp_ns_map import EPP_NS_MAP
from tests.helper.profiles import EPP_PROFILE


def epp_backends(client_factory, idn_tables=None):
    """A factory of backends over the EPP clients `client_factory` makes, so a test still sees those clients. The
    profile is EPP's, with the LGRs of `idn_tables`."""
    profile = EPP_PROFILE.with_changes({"lgrs": list(idn_tables.lgrs())}) if idn_tables else EPP_PROFILE
    return lambda username, password: EppBackend(client_factory(username, password), EPP_NS_MAP, profile, idn_tables)
