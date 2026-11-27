from dataclasses import dataclass, field
from typing import Optional

from core.model.contact.address import Address


@dataclass(kw_only=True)
class Organisation:
    """An organisation as a registry states it publicly (read only). A registry that holds no organisation objects, such as a
    registry of registrars, gives what it knows: the backend fills `status`, `roles` and `sponsor_id` with what that stands for.

    `parent` is the id of the organisation that holds this one, None when there is none. `phones` and `faxes` are in the dotted
    form (`+49.69272350`, `+1.7035555555x12`). `extensions` maps the id of an extension to a typed object of its own core.
    """
    id: str
    sponsor_id: str
    status: list[str]
    roles: dict[str, list[str]]
    up_date: Optional[str] = None
    parent: Optional[str] = None
    name: Optional[str] = None
    address: Optional[Address] = None
    phones: list[str] = field(default_factory=list)
    faxes: list[str] = field(default_factory=list)
    email: Optional[str] = None
    urls: list[str] = field(default_factory=list)
    extensions: dict[str, object] = field(default_factory=dict)
