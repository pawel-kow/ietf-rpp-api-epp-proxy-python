"""What a registry backend can hold, which the RPP mappers, the flows and discovery check, and the test selectors read.

The profile is a tree, `<object>.<field>.<leaf>` and `<object>.processes.<process>.<leaf>`, objects and fields by
their RPP names. It is built from layers, merged in order: the generic profile of a protocol, then what one server
differs in (`profiles/` and `rpp_backend_profile` of the config, see settings). A leaf means the same under every
object: `min_count` and `max_count` how many a field holds, `<what>_supported` whether the backend has it,
`removable` whether an update can clear the field, `changeable` whether it can change it.
"""

# Every leaf of a profile and its type: a list is a tuple of strings. A profile has every leaf and no other.
LEAVES: dict[str, type] = {
    "name": str,                                         # names the backend in a refusal (`… cannot be expressed in`)
    "objects": tuple,                                    # the data objects discovery states; hosts are objects if there
    "profiles": tuple,                                   # the RPP profiles discovery states
    "extensions": tuple,                                 # the RPP extensions (ids) offered, which discovery states
    "lgrs": tuple,                                       # the LGRs offered for IDNs, from the config, none without IDN
    "domainName.registrant.min_count": int,              # left to the registry to refuse; the test selectors read it
    "domainName.registrant.max_count": int,              # further registrants are contacts labelled `registrant`
    "domainName.contacts.labels": tuple,                 # the contact roles besides the registrant
    "domainName.status.client_supported": bool,          # whether a client sets statuses
    "domainName.authInfo.read_supported": bool,          # whether a read can show the authInfo
    "domainName.period.supported": bool,                 # whether a domain is registered for a period, with expiry
    "domainName.dns.min_count": int,                     # DNS records (name servers included) from the create on;
                                                         # left to the registry to refuse, read by the test selectors
    "domainName.dns.record_types": tuple,                # the record types held at the apex; glue is always held
    "domainName.metadata": tuple,                        # provisioning metadata a read shows besides the sponsor
    "domainName.processes.renew.supported": bool,
    "domainName.processes.transfer.operations": tuple,   # request, query, cancel, approve, reject
    "domainName.processes.restore.report_supported": bool,
    "contact.name.changeable": bool,                     # left to the registry to refuse; the test selectors read it
    "contact.name.removable": bool,                      # whether the protocol can clear it at all
    "contact.email.removable": bool,                     # whether the protocol can clear it at all
    "contact.phone.min_count": int,                      # voice numbers; left to the registry to refuse
    "contact.phone.max_count": int,
    "contact.fax.supported": bool,
    "contact.region.supported": bool,
    "contact.localization.supported": bool,              # a localized form besides the international one
    "contact.kind.supported": bool,                      # held, so an individual can name an organisation; otherwise
                                                         # the kind follows from the organisation
    "contact.org.person_name_supported": bool,           # the contact of an organisation holds a person's name too
    "contact.authInfo.supported": bool,
    "contact.status.client_supported": bool,
    "contact.metadata": tuple,
    "contact.processes.delete.supported": bool,          # the test selectors read it
    "contact.processes.transfer.operations": tuple,
}


def _merged(base: dict, layer: dict) -> dict:
    """`layer` over `base`: maps merge, a list or a value replaces."""
    merged = dict(base)
    for key, value in layer.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merged(merged[key], value)
        else:
            merged[key] = value
    return merged


def _leaves(tree: dict, prefix: str = "") -> dict:
    leaves = {}
    for key, value in tree.items():
        if isinstance(value, dict):
            leaves.update(_leaves(value, f"{prefix}{key}."))
        else:
            leaves[f"{prefix}{key}"] = value
    return leaves


def _checked(value, kind: type, path: str):
    if kind is tuple:
        if not isinstance(value, (list, tuple)) or not all(isinstance(item, str) for item in value):
            raise ValueError(f"backend profile: {path} must be a list of strings")
        return tuple(value)
    if not isinstance(value, kind) or (kind is int and isinstance(value, bool)):
        raise ValueError(f"backend profile: {path} must be of type {kind.__name__}")
    return value


def _frozen(leaves: dict) -> dict:
    tree: dict = {}
    for path, value in leaves.items():
        *parents, leaf = path.split(".")
        node = tree
        for parent in parents:
            node = node.setdefault(parent, {})
        node[leaf] = value
    return tree


class BackendProfile:
    """A node of the profile tree: an attribute is a leaf, or the node of a field, object or process
    (`profile.contact.fax.supported`). Static per backend; build the root with `from_layers`."""

    def __init__(self, tree: dict, path: str = ""):
        self._tree = tree
        self._path = path

    @classmethod
    def from_layers(cls, *layers: dict) -> "BackendProfile":
        """The profile of the layers merged in order. A leaf missing, unknown or of the wrong type is a
        `ValueError`, so a wrong profile file stops the app."""
        tree: dict = {}
        for layer in layers:
            tree = _merged(tree, layer or {})
        leaves = _leaves(tree)
        unknown = sorted(set(leaves) - set(LEAVES))
        missing = sorted(set(LEAVES) - set(leaves))
        if unknown or missing:
            raise ValueError(
                f"backend profile: unknown {', '.join(unknown) or 'none'}; missing {', '.join(missing) or 'none'}")
        return cls(_frozen({path: _checked(leaves[path], kind, path) for path, kind in LEAVES.items()}))

    def with_changes(self, changes: dict) -> "BackendProfile":
        """This profile with `changes` merged over it, as another layer."""
        return BackendProfile.from_layers(self._tree, changes)

    def fact(self, path: str):
        """The leaf at a dotted path. A path that names no leaf is a `KeyError`."""
        node = self._tree
        for key in path.split("."):
            if not isinstance(node, dict) or key not in node:
                raise KeyError(path)
            node = node[key]
        if isinstance(node, dict):
            raise KeyError(path)
        return node

    def __getattr__(self, name: str):
        if name.startswith("_"):
            raise AttributeError(name)
        if name not in self._tree:
            raise AttributeError(f"the backend profile has no {self._path}{name}")
        value = self._tree[name]
        return BackendProfile(value, f"{self._path}{name}.") if isinstance(value, dict) else value

    def __eq__(self, other) -> bool:
        return isinstance(other, BackendProfile) and (self._tree, self._path) == (other._tree, other._path)

    __hash__ = None

    def __repr__(self) -> str:
        return f"BackendProfile({self._path or 'root'}: {self._tree!r})"
