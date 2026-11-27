from dataclasses import dataclass
from typing import Optional

from core.model.shared.common import ProvisioningObject


@dataclass(kw_only=True)
class RequestContact(ProvisioningObject):
    """A contact that is only a URI template: where a domain's general requests or abuse reports go. It has no
    name, address or status; a template names the domain with `{Alabel}` or `{Ulabel}`, which the registry expands.
    """
    id: str
    uriTemplate: Optional[str] = None
