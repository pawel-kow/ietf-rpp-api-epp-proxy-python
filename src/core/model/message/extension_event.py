from dataclasses import dataclass


@dataclass(kw_only=True)
class ExtensionEvent:
    """What a queued message reports that an extension defines the message type of: the id of the RPP extension, and the
    typed object of that extension's own core (which the extension's message mapper renders, and nothing else reads)."""
    extension_id: str
    event: object
