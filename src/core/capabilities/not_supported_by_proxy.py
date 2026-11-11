from core.result.result_code import ResultCode
from core.capabilities.unsupported_feature import UnsupportedFeature


class NotSupportedByProxy(UnsupportedFeature):
    """EPP can hold the input, through an extension if one is named, but the proxy does not map it."""

    def __init__(self, feature: str, extension: str | None = None):
        if extension is None:
            super().__init__(f"{feature} can be expressed in EPP, but not by this proxy")
        else:
            super().__init__(f"{feature} needs {extension}, which this proxy does not implement")
            self.code = ResultCode.UNIMPLEMENTED_EXTENSION
