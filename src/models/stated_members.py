from dataclasses import replace


def stated(wanted, current):
    """The replacement with every member stated: a member it leaves `unchanged` takes the stored value, so that it
    compares equal and nothing is sent for it."""
    if not wanted.unchanged:
        return wanted
    return replace(wanted, **{member: getattr(current, member) for member in wanted.unchanged}, unchanged=frozenset())
