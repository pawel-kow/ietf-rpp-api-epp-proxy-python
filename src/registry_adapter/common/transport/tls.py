import ssl


def new_tls_context(insecure_skip_verify: bool) -> ssl.SSLContext:
    """
    Builds the client TLS context for the connection to the registry server.

    Args:
        insecure_skip_verify (bool): Accept any certificate for any name. The
            registrars' credentials cross this connection, so this is for test
            backends only.
    """
    context = ssl.create_default_context()
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    if insecure_skip_verify:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    return context
