CLIENT_STATUS_PREFIX = "client"


def is_client_label(label) -> bool:
    """A status the client sets and clears, as opposed to the server's."""
    return isinstance(label, str) and label.startswith(CLIENT_STATUS_PREFIX)


def client_statuses(status: list[str] | None, reasons: dict[str, str] | None) -> dict[str, str | None]:
    """The client statuses with their reasons, a missing or empty reason as None."""
    return {label: ((reasons or {}).get(label) or None) for label in status or [] if is_client_label(label)}


def status_changes(before: dict[str, str | None], after: dict[str, str | None]) -> tuple[list[str], list[str]]:
    """The labels to add and to remove. A status is compared by label, and one whose reason changed is removed and
    added again, as EPP cannot change a reason."""
    new_reason = {label for label in before.keys() & after.keys() if before[label] != after[label]}
    return sorted(after.keys() - before.keys() | new_reason), sorted(before.keys() - after.keys() | new_reason)
