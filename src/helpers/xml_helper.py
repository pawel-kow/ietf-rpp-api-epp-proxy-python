from lxml import etree


def hardened_parser(**options):
    """A parser that reads no external entities, loads no DTD and opens no network connection.

    EPP replies come from another party, and an entity must not turn a file of this host into content.
    """
    return etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False, **options)


def decode_xml(response):
    # Convert response to bytes using UTF-8 encoding if it's not already bytes
    response_bytes = response.encode('utf-8') if isinstance(response, str) else response
    root = etree.fromstring(response_bytes, parser=hardened_parser(recover=True))
    return root
