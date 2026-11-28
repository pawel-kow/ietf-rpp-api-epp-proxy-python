"""The Release Process Object of the rri extension (docs/rri/rri-extension.md): a sponsor returns a domain name to the registry."""
from extensions.rri.core.model.release import Release
from extensions.rri.rpp.dto.rpp_release_process import RPPReleaseProcess
from rpp.mapping.shared.common import parse_rpp
from rpp.schema.validator import validate_request_schema, validate_schema


def rpp_to_keep_nameservers(rpp: dict, extensions: tuple[str, ...] = ()) -> bool | None:
    """Validates a create request and returns its Keep Name Servers, None when it has none."""
    validate_request_schema("releaseProcess.create", rpp, extensions)
    return parse_rpp(RPPReleaseProcess, rpp).keepNameservers


def model_to_rpp(release: Release, extensions: tuple[str, ...] = ()) -> dict:
    """The response of a create: the Keep Name Servers that applied."""
    process_dict = RPPReleaseProcess(keepNameservers=release.keep_nameservers).to_rpp()
    validate_schema("releaseProcess.read", process_dict, extensions)
    return process_dict
