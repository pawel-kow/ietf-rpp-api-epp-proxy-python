class OneOf:
    """An expected value that any of `values` meets. A case gets one where it writes `{env:<path>}` as a whole value and
    the fact is a list, such as the statuses a domain may read with right after its create."""

    def __init__(self, values):
        self.values = tuple(values)

    def __eq__(self, other):
        return isinstance(other, OneOf) and self.values == other.values

    def __repr__(self):
        return f"one of {list(self.values)}"
