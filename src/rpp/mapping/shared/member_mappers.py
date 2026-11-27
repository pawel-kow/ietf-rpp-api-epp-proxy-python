from typing import Callable, Protocol

from rpp.schema.extensions import added_members


class MemberMapper(Protocol):
    """What an extension that adds members to a base object gives the mappers of that object: how its JSON members become
    what the core model of the object takes in and holds, and back. Nothing of the JSON goes beyond the mapper.

    `members` are the names of the JSON members the extension adds to the object, whichever definition (create, update, read, a
    process request) adds them: which member a definition has is the extension's schema's (`added_members`)."""
    extension_id: str
    members: tuple[str, ...]

    def to_model(self, present: dict) -> object:
        """What the members of a request (`present` holds those of `self.members` the request has) stand for in the model."""

    def to_rpp(self, held) -> dict:
        """The members of a read, from what the model of the object holds."""

    def check(self, rpp: dict) -> None:
        """Optional. What RPP or the extension states of the request in prose and the schema cannot express, refused as the
        extension defines it (not as a broken constraint of a profile, core §Extensions and Profiles of a Request): it runs
        after step 1 of the validation and before step 2."""


class MemberMappers:
    """The mappers of the extensions that add members to one kind of object (the domain name, and with it the request of its
    transfer). Each extension adds its mapper when it registers, once (a second registration of the same id is no change, as
    for the schemas of the extensions), and the mappers of an object use those of the extensions of the request's preset
    only: a member of another extension is undeclared, which the schema already refused (400)."""

    def __init__(self, merge: Callable[[list], object]):
        """`merge(results)` joins what the mappers of a request made (`to_model` of each) into what the model of the object takes."""
        self._merge = merge
        self._by_id: dict[str, MemberMapper] = {}

    def add(self, mapper: MemberMapper) -> None:
        self._by_id.setdefault(mapper.extension_id, mapper)

    def of(self, extensions) -> list[MemberMapper]:
        return [mapper for extension_id, mapper in self._by_id.items() if extension_id in extensions]

    @staticmethod
    def _added(mapper: MemberMapper, schema: str) -> tuple[str, ...]:
        added = added_members(schema, (mapper.extension_id,))
        return tuple(name for name in mapper.members if name in added)

    def members(self, schema: str, extensions) -> tuple[str, ...]:
        """The members the mappers of these extensions handle on a definition."""
        return tuple(name for mapper in self.of(extensions) for name in self._added(mapper, schema))

    def check(self, rpp: dict, extensions) -> None:
        """The checks of the mappers of these extensions on a request (or the object a patch results in)."""
        for mapper in self.of(extensions):
            check = getattr(mapper, "check", None)
            if check is not None:
                check(rpp)

    def split(self, rpp: dict, schema: str, extensions):
        """The representation without the members the mappers handle on a definition, and what they make of those it has."""
        rest = dict(rpp)
        results = []
        for mapper in self.of(extensions):
            names = self._added(mapper, schema)
            present = {name: rest[name] for name in names if rest.get(name)}
            rest = {name: value for name, value in rest.items() if name not in names}
            if present:
                results.append(mapper.to_model(present))
        return rest, self._merge(results)

    def to_rpp(self, held, schema: str, extensions) -> dict:
        """The members of a read of the extensions' mappers, as far as the definition has them."""
        rpp: dict = {}
        for mapper in self.of(extensions):
            names = self._added(mapper, schema)
            rpp.update({name: value for name, value in mapper.to_rpp(held).items() if name in names})
        return rpp
