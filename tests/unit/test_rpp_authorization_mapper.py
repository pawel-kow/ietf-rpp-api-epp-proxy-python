import pytest

from core.capabilities.not_supported_by_backend import NotSupportedByBackend
from core.model.shared.common import AuthInfo
from rpp.mapping.shared import rpp_authorization

SECRET = "TXkgU2VjcmV0IFRva2Vu"  # "My Secret Token", core §6.1


def test_no_header_is_no_auth_info():
    assert rpp_authorization.rpp_to_model(None) is None


def test_value_is_base64_decoded():
    assert rpp_authorization.rpp_to_model(f"authinfo value={SECRET}") == AuthInfo(pw="My Secret Token")


def test_value_keeps_base64_padding():
    assert rpp_authorization.rpp_to_model("authinfo value=MmZvb0JBUg==").pw == "2fooBAR"


def test_roid_is_kept():
    auth_info = rpp_authorization.rpp_to_model(f"authinfo value={SECRET}, roid=REG-123")
    assert auth_info == AuthInfo(pw="My Secret Token", roid="REG-123")


def test_other_method_cannot_reach_epp():
    with pytest.raises(NotSupportedByBackend, match="'bearer'"):
        rpp_authorization.rpp_to_model(f"bearer value={SECRET}")


@pytest.mark.parametrize("header", [
    "authinfo",
    "authinfo roid=REG-123",
    "authinfo value=",
    "authinfo value=%%%",
    "authinfo value=/w==",  # not UTF-8
    f"authinfo value={SECRET}, value={SECRET}",
    f"authinfo value={SECRET}, other=1",
    f"authinfo value={SECRET}, roid",
])
def test_malformed_header_is_rejected(header):
    with pytest.raises(ValueError):
        rpp_authorization.rpp_to_model(header)


def test_rejection_does_not_repeat_the_value():
    with pytest.raises(ValueError) as rejection:
        rpp_authorization.rpp_to_model("authinfo value=s3cr3t%")
    assert "s3cr3t" not in str(rejection.value)
