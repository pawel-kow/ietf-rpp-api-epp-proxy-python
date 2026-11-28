from rpp.dto.rpp_patch_operation import RPPPatchOperation
from rpp.schema.validator import refuse_removal_by_profile


def refuse_removals_by_profile(schema_name: str, operations: list[RPPPatchOperation], extensions: tuple[str, ...] = ()) -> None:
    """A patch applied to the object read for it checks the object it results in, which carries no sign of a member the patch
    removed that the update definition requires. The removal of a whole member that an applicable profile lists in an
    unconditional `required` of `schema_name` is refused with that profile, as for the native patch of an extension
    (spec-issues.md, two-step validation of a patch)."""
    for operation in operations:
        member = operation.path.removeprefix("/")
        if operation.op == "remove" and operation.match is None and member and "/" not in member:
            refuse_removal_by_profile(schema_name, member, extensions)
