from dataclasses import dataclass
from typing import Optional

from core.model.contact.contacts import Contact
from core.result.operation_response import OperationResponse


@dataclass(kw_only=True)
class ContactMutationResult:
    """A mutation the registry applied. `contact` is None when it could not be read back."""
    mutation: OperationResponse
    contact: Optional[Contact] = None
