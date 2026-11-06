from models import ResultCode
from .unsupported_rpp_feature import UnsupportedRppFeature


class PatchNotApplicable(UnsupportedRppFeature):
    """A well formed patch that does not fit the object: no element matches, or a match is ambiguous.

    json draft §5.2.2 requires an error and defines no code. EPP Data management policy violation fits (spec-issues.md).
    """

    code = ResultCode.DATA_MANAGEMENT_POLICY_VIOLATION
