from xsdata.formats.dataclass.parsers import XmlParser
from xsdata.formats.dataclass.context import XmlContext
from xsdata.formats.dataclass.serializers import XmlSerializer
from xsdata.formats.dataclass.serializers.config import SerializerConfig
from xsdata.formats.dataclass.parsers.config import ParserConfig
from ..epp_model.epp_1_0 import Epp
from config import config
import logging

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
    return parser.from_string(epp_response, Epp)
