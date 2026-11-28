"""The Verification Process Object of the rri extension (docs/rri/rri-extension.md), model to RPP: a process is only read."""
from extensions.rri.core.model.verification_process import VerificationProcess
from extensions.rri.rpp.dto.rpp_holder_verification import RPPHolderVerification
from extensions.rri.rpp.dto.rpp_verification_process import RPPVerificationProcess
from extensions.rri.rpp.mapping import verification_information
from rpp.dto.rpp_contact_reference import RPPContactReference
from rpp.schema.validator import validate_schema


def model_to_rpp(process: VerificationProcess, extensions: tuple[str, ...] = ()) -> dict:
    """Converts the process to its read representation. A holder without a handle has no `holder`."""
    rpp = RPPVerificationProcess(
        holdDeadline=process.hold_deadline,
        deletionDeadline=process.deletion_deadline,
        holders=[RPPHolderVerification(
            holder=RPPContactReference(id=holder.handle) if holder.handle else None,
            verifications=[verification_information.model_to_dto(record) for record in holder.verifications] or None)
            for holder in process.holders],
    ).to_rpp()
    validate_schema("verificationProcess.read", rpp, extensions)
    return rpp
