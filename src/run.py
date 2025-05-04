from app import app
from connexion.resolver import RelativeResolver
from connexion.lifecycle import ConnexionResponse, ConnexionRequest
from connexion.problem import problem
from connexion.exceptions import ProblemException

def handle_rpp_error(request: ConnexionRequest, exc: Exception) -> ConnexionResponse:
    if isinstance(exc, ProblemException):
        exc.headers = exc.headers or {}
        exc.headers.update({
            "RPP-clTRID": request.headers.get("RPP-clTRID")
        } if "RPP-clTRID" in request.headers else {})
        return problem(
            title=exc.title,
            detail=exc.detail,
            status=exc.status,
            type=exc.type,
            instance=exc.instance,
            headers=exc.headers,
            ext=exc.ext
        )
    return problem(
        title="Internal Server Error",
        detail=f"An unexpected error occurred: {str(exc)}",
        status=500,
        headers={
            "RPP-clTRID": request.headers.get("RPP-clTRID", "")
        } if request.headers.get("RPP-clTRID", "") else None,
    )

app.add_api("openapi.yaml", resolver=RelativeResolver('controller'), resolver_error=501)
app.add_error_handler(ProblemException, handle_rpp_error)
