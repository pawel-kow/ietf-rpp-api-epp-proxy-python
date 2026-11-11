from dataclasses import dataclass
from typing import Optional

from core.model.contact.contact_update_change import ContactUpdateChange
from core.model.contact.contact_update_changes import ContactUpdateChanges


@dataclass(kw_only=True)
class ContactUpdate:
    id: str
    add: Optional[ContactUpdateChanges] = None
    remove: Optional[ContactUpdateChanges] = None
    change: Optional[ContactUpdateChange] = None
