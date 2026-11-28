from dataclasses import dataclass, field


@dataclass(frozen=True, kw_only=True)
class RppExtension:
    """An RPP extension (json §7) as its schema file states it: what discovery says of it (json §6.2.12), and the
    sub-schemas it adds to the base objects it extends.

    `extends` maps the name of a base definition (`domainTransferProcess.create`) to the name of the extension's
    definition composed with it. `defs` are the extension's definitions; they refer to the base definitions by their
    names in the bundle (`#/$defs/contact.reference`), so they are added to it. `objects` are the data objects the
    extension defines (the "new objects" of its overview), whose definitions are `defs` named `ext.<x>.<object>.<op>`.
    `owners` names, for a base definition that another extension defines (`planet.create`), the `$id` of that extension's
    schema: the extension adds members to an object of the owner, so a preset that holds it holds the owner too.
    """
    id: str
    name: str
    version: str
    url: str
    extends: dict
    defs: dict
    objects: tuple = ()
    owners: dict = field(default_factory=dict)
    # identifier of each message type (`rpp:messages`) -> its definition in `defs`; the effective schema adds a branch for each
    # to the `data` union of `message.read` and `message.create`
    messages: dict = field(default_factory=dict)
