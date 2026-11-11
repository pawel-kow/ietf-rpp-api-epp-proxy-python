from connexion.validators import JSONRequestBodyValidator


class RppRequestBodyValidator(JSONRequestBodyValidator):
    """Validates a request body, which an operation may declare optional (a transfer reject)."""

    def _validate(self, body):
        if body is not None or self._required:
            return super()._validate(body)
