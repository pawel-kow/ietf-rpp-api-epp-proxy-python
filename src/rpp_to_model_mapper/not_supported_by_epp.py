from .unsupported_rpp_feature import UnsupportedRppFeature


class NotSupportedByEpp(UnsupportedRppFeature):
    """EPP has no place for the input, neither in its core nor in an extension the proxy knows of."""

    def __init__(self, feature: str):
        super().__init__(f"{feature} cannot be expressed in EPP")
