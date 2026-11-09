from xsdata.formats.dataclass.parsers import XmlParser
from xsdata.formats.dataclass.context import XmlContext
from xsdata.formats.dataclass.serializers import XmlSerializer
from xsdata.formats.dataclass.serializers.config import SerializerConfig
from xsdata.formats.dataclass.parsers.config import ParserConfig
from ..epp_model.epp_1_0 import Epp
from config import config
import logging

from lxml import etree

from helpers.xml_helper import hardened_parser

logger = logging.getLogger('uvicorn.error')

serializer_config = SerializerConfig(
    pretty_print=True,
)
serializer = XmlSerializer(config=serializer_config)
parser_config = ParserConfig()
parser_context = XmlContext()
parser = XmlParser(context=parser_context, config=parser_config)

def epp_to_str(epp_request: Epp) -> str:
    return serializer.render(epp_request, ns_map=config.rpp_epp_ns_map)

def str_to_epp(epp_response: str) -> Epp:
    """Parses an EPP reply. A DOCTYPE, and with it every entity, is refused: no EPP message has one."""
    data = epp_response.encode("utf-8") if isinstance(epp_response, str) else epp_response
    tree = etree.fromstring(data, parser=hardened_parser(remove_comments=True)).getroottree()
    if tree.docinfo.doctype or tree.docinfo.internalDTD is not None or tree.docinfo.externalDTD is not None:
        raise ValueError("The EPP reply has a DOCTYPE")
    return parser.parse(tree, Epp)
