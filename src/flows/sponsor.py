from eppclient.eppclient import EPPClient
from models import ErrorResponse, OperationResponse, ResultCode


def require_sponsor(
    epp_client: EPPClient, sponsor_id: str | None, read: OperationResponse, client_transaction_id, object_name: str,
) -> ErrorResponse | None:
    """The refusal of an update that changes nothing, which sends no EPP command. Only the sponsor may update
    (data-objects §11.3.4, §12.3.4), and EPP would have said so. The login id is taken to be the `clID`, whatever its case."""
    if (sponsor_id or "").lower() == epp_client.username.lower():
        return None
    return ErrorResponse(
        code=ResultCode.AUTHORIZATION_ERROR,
        msg=f"Only the sponsoring client can update the {object_name}",
        server_transaction_id=read.server_transaction_id,
        client_transaction_id=client_transaction_id,
    )
