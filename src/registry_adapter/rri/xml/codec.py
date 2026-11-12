"""Renders RRI requests and parses RRI replies (XML 5.0), with the hardened parser: no DTD, no entities."""
from lxml import etree
from xsdata.formats.dataclass.context import XmlContext
from xsdata.formats.dataclass.parsers import XmlParser
from xsdata.formats.dataclass.parsers.config import ParserConfig
from xsdata.formats.dataclass.serializers import XmlSerializer
from xsdata.formats.dataclass.serializers.config import SerializerConfig

# Every module whose elements a reply's `tr:data` may hold must be loaded, so the parser binds them to their classes.
from registry_adapter.rri.xml.generated import contact_5_0, domain_5_0, message_5_0, regacc_5_0  # noqa: F401
from registry_adapter.common.xmlsafe.xml_helper import hardened_parser
from registry_adapter.rri.xml.generated.global_5_0 import RegistryRequest, RegistryResponse

NS_MAP = {
    None: "http://registry.denic.de/global/5.0",
    "tr": "http://registry.denic.de/transaction/5.0",
    "contact": "http://registry.denic.de/contact/5.0",
    "domain": "http://registry.denic.de/domain/5.0",
    "dnsentry": "http://registry.denic.de/dnsentry/5.0",
    "msg": "http://registry.denic.de/msg/5.0",
    "regacc": "http://registry.denic.de/regacc/5.0",
    "verification": "http://registry.denic.de/verification/5.0",
    "xsi": "http://www.w3.org/2001/XMLSchema-instance",
}

_serializer = XmlSerializer(config=SerializerConfig(pretty_print=False))

_parser = XmlParser(context=XmlContext(), config=ParserConfig(fail_on_unknown_properties=False))


def rri_to_str(request: RegistryRequest) -> str:
    return _serializer.render(request, ns_map=NS_MAP)


def str_to_rri(reply: str) -> RegistryResponse:
    """Parses an RRI reply. A DOCTYPE, and with it every entity, is refused: no RRI message has one."""
    data = reply.encode("utf-8") if isinstance(reply, str) else reply
    tree = etree.fromstring(data, parser=hardened_parser(remove_comments=True)).getroottree()
    if tree.docinfo.doctype or tree.docinfo.internalDTD is not None or tree.docinfo.externalDTD is not None:
        raise ValueError("The RRI reply has a DOCTYPE")
    return _parser.parse(tree, RegistryResponse)
