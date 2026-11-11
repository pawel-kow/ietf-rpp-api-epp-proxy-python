from .unsupported_rpp_feature import UnsupportedRppFeature


class NotSupportedByBackend(UnsupportedRppFeature):
    """The backend has no place for the input, neither in its core nor in an extension the proxy knows of.

    The mapper names the `feature`, and `detail` the backend, which the mapper need not know.
    """

    def __init__(self, feature: str):
        super().__init__(feature)
        self.feature = feature

    def detail(self, backend_name: str) -> str:
        return f"{self.feature} cannot be expressed in {backend_name}"
