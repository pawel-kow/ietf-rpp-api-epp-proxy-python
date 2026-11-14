from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class RppExtension:
    """An RPP extension (json §7) as its schema file states it: what discovery says of it (json §6.2.12), and the
    sub-schemas it adds to the base objects it extends.

    `extends` maps the name of a base definition (`domainTransferProcess.create`) to the name of the extension's
    definition composed with it. `defs` are the extension's definitions; they refer to the base definitions by their
    names in the bundle (`#/$defs/contact.reference`), so they are added to it.
    """
    id: str
    name: str
    version: str
    url: str
    extends: dict
    defs: dict
