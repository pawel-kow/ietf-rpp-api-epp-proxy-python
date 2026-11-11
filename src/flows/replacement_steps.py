from dataclasses import dataclass
from typing import Any, Callable, Optional

from models import ErrorResponse


@dataclass(frozen=True, kw_only=True)
class ReplacementSteps:
    """How one kind of object is replaced through EPP, which has no full update.

    `read(epp_client, key)` and `update(epp_client, delta, client_transaction_id=...)` run the EPP commands, and
    `object_of` takes the object from a read. `prepare(wanted, current)` puts the wanted state in the terms of the
    stored one, `refuse(current, wanted)` says what EPP cannot do, and `difference` and `changes_nothing` are the
    model's.
    """
    read: Callable
    object_of: Callable[[Any], Any]
    difference: Callable[[Any, Any], Any]
    changes_nothing: Callable[[Any], bool]
    update: Callable
    prepare: Callable[[Any, Any], Any] = lambda wanted, current: wanted
    refuse: Callable[[Any, Any], Optional[ErrorResponse]] = lambda current, wanted: None
