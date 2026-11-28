from dataclasses import dataclass

from dataclasses_json import dataclass_json, Undefined

from rpp.dto.rpp_object import RPPObject, type_field


@dataclass_json(undefined=Undefined.RAISE)
@dataclass(kw_only=True)
class RPPAuthInfoIssueProcess(RPPObject):
    """The Authorisation Information Issue Process Object of the rri extension: it has no data element."""
    at_type: str = type_field("authInfoIssueProcess")
