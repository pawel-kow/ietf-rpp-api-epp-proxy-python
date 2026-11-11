from core.result.result_code import ResultCode
from core.capabilities.unsupported_feature import UnsupportedFeature


class NotSupportedByProxy(UnsupportedFeature):
    """The backend can hold the input, through an extension if one is named, but the proxy does not map it.

    The mapper names the `feature`, and `detail` the backend, which the mapper need not know.
    """

    def __init__(self, feature: str, extension: str | None = None):
        super().__init__(feature)
        self.feature = feature
        self.extension = extension
        if extension is not None:
            self.code = ResultCode.UNIMPLEMENTED_EXTENSION

    def detail(self, backend_name: str) -> str:
        if self.extension is None:
            return f"{self.feature} can be expressed in {backend_name}, but not by this proxy"
        return f"{self.feature} needs {self.extension}, which this proxy does not implement"
