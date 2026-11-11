from core.model.shared.client_statuses import is_client_label
from rpp.schema.validator import validate_schema

OK = "ok"


def _visible(status: dict) -> bool:
    """`ok` stays visible: the registry drops it by itself, and the draft replaces it in an example (json §5.3.1)."""
    return is_client_label(status["label"]) or status["label"] == OK


def without_server_statuses(document: dict) -> dict:
    """The object a patch applies to: it acts as if the object had no server statuses."""
    return {**document, "status": [status for status in document.get("status") or [] if _visible(status)]}


def with_server_statuses(patched: dict, current: dict, status_type: str) -> dict:
    """The object after a patch: the server statuses are back, and a patch that cleared the rest leaves `ok`.

    A client cannot name a server status, whether or not the object has it.
    """
    statuses = patched.get("status") or []
    visible_labels = {status["label"] for status in without_server_statuses(current)["status"]}
    for status in statuses:
        validate_schema(f"{status_type}.read", status)
        if not is_client_label(status["label"]) and status["label"] not in visible_labels:
            raise ValueError(f"Status '{status['label']}' can only be set by the server")
    server = [status for status in current.get("status") or [] if not _visible(status)]
    return {**patched, "status": statuses + server or [{"@type": status_type, "label": OK}]}
