from lxml import etree

def decode_xml(response):
    parser = etree.XMLParser(recover=True)
    # Convert response to bytes using UTF-8 encoding if it's not already bytes
    response_bytes = response.encode('utf-8') if isinstance(response, str) else response
    root = etree.fromstring(response_bytes, parser=parser)
    return root
