from connexion.validators import JSONResponseBodyValidator


class RppResponseBodyValidator(JSONResponseBodyValidator):
    """Validates a response body, which RPP allows to be absent (delete has output cardinality 0-1)."""

    def _validate(self, body):
        if body is not None:
            super()._validate(body)
