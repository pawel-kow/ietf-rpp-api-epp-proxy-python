import logging
import ssl

logger = logging.getLogger(__name__)


def new_tls_context(insecure_skip_verify: bool) -> ssl.SSLContext:
    """
    Builds the client TLS context for the connection to the EPP server.

    Args:
        insecure_skip_verify (bool): Accept any certificate for any name. The
            registrars' credentials cross this connection, so this is for test
            backends only.
    """
    context = ssl.create_default_context()
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    if insecure_skip_verify:
        logger.warning("rpp_epp_tls_insecure_skip_verify is on: "
                       "the EPP server's certificate is not verified")
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    return context
