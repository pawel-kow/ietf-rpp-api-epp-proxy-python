from dataclasses import dataclass
from typing import Optional


@dataclass(kw_only=True)
class RequestTemplate:
    """A URI Template a registrar states for requests about its domain names, with the date of its last change (UTC)."""
    uri_template: str
    up_date: Optional[str] = None


@dataclass(kw_only=True)
class RegistrarRequestTemplates:
    """What the rri extension adds to the organisation of a registrar: its General Request and Abuse templates."""
    general_request: Optional[RequestTemplate] = None
    abuse: Optional[RequestTemplate] = None
