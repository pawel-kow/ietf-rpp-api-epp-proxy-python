"""The Authorisation Information Issue Process Object of the rri extension (docs/rri/rri-extension.md)."""
from extensions.rri.rpp.dto.rpp_auth_info_issue_process import RPPAuthInfoIssueProcess
from rpp.schema.validator import validate_request_schema, validate_schema


def check_request(rpp: dict, extensions: tuple[str, ...] = ()) -> None:
    """Validates a create request, which holds nothing but its type."""
    validate_request_schema("authInfoIssueProcess.create", rpp, extensions)


def model_to_rpp(extensions: tuple[str, ...] = ()) -> dict:
    """The response of a create: the process, which has no data element."""
    process_dict = RPPAuthInfoIssueProcess().to_rpp()
    validate_schema("authInfoIssueProcess.read", process_dict, extensions)
    return process_dict
