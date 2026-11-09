from dataclasses import dataclass
from typing import Optional

from models import Contact, OperationResponse


@dataclass(kw_only=True)
class ContactMutationResult:
    """A mutation the registry applied. `contact` is None when it could not be read back."""
    mutation: OperationResponse
    contact: Optional[Contact] = None
