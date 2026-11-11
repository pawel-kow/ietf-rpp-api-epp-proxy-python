from core.result.result_code import ResultCode
from core.capabilities.unsupported_feature import UnsupportedFeature


class PatchNotApplicable(UnsupportedFeature):
    """A well formed patch that does not fit the object: no element matches, or a match is ambiguous.

    json draft §5.2.2 requires an error and defines no code. EPP Data management policy violation fits (spec-issues.md).
    """

    code = ResultCode.DATA_MANAGEMENT_POLICY_VIOLATION
