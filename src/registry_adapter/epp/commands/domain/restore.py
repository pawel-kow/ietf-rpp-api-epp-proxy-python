from typing import Union

from xsdata.models.datatype import XmlDateTime

from core.model.domain.domain_restore import DomainRestore
from core.model.domain.domain_restore_process import DomainRestoreProcess
from core.model.domain.restore_report import RestoreReport
from core.result.error_response import ErrorResponse
from core.result.operation_response import OperationResponse
from core.result.result_code import ResultCode
from registry_adapter.epp.commands.domain.common import missing_extension, rgp_status_of
from registry_adapter.epp.commands.shared.epp_core import get_epp_error_response
from registry_adapter.epp.commands.shared.epp_response import cl_trid, find_extension, parse_epp_response_header
from registry_adapter.epp.session.epp_client import EPPClient, RGP_EXTENSION
from registry_adapter.epp.xml.codec import epp_to_str, str_to_epp
from registry_adapter.epp.xml.generated.domain_1_0 import ChgType, Update
from registry_adapter.epp.xml.generated.epp_1_0 import CommandType, Epp, ExtAnyType, ReadWriteType
from registry_adapter.epp.xml.generated.rgp_1_0 import (
    MixedType, ReportTextType, ReportType, RestoreType, RgpOpType, UpData as RgpUpData, Update as RgpUpdate,
)


def _rgp_report(report: RestoreReport) -> ReportType:
    return ReportType(
        pre_data=MixedType(content=[report.preData]),
        post_data=MixedType(content=[report.postData]),
        del_time=XmlDateTime.from_string(report.deleteTime),
        res_time=XmlDateTime.from_string(report.restoreTime),
        res_reason=ReportTextType(content=[report.restoreReason]),
        statement=[ReportTextType(content=[statement]) for statement in report.statements],
        other=MixedType(content=[report.other]) if report.other is not None else None,
    )


def domain_restore(restore: DomainRestore, rpp_cl_trid: str) -> Epp:
    """RFC 3915 §4.2.5: a domain update with an empty chg, carrying the request or the report."""
    if restore.report is None:
        rgp_restore = RestoreType(op=RgpOpType.REQUEST)
    else:
        rgp_restore = RestoreType(op=RgpOpType.REPORT, report=_rgp_report(restore.report))
    return Epp(
        command=CommandType(
            update=ReadWriteType(other_element=Update(name=restore.name.upper(), chg=ChgType())),
            extension=ExtAnyType(other_element=[RgpUpdate(restore=rgp_restore)]),
            cl_trid=rpp_cl_trid,
        )
    )


def restore_domain_xml(restore: DomainRestore, client_request_id=None, *, ns_map: dict[str, str]) -> str:
    return epp_to_str(domain_restore(restore, cl_trid(client_request_id)), ns_map)


def parse_domain_restore_response(xml_string: str, restore: DomainRestore, client_transaction_id: str | None) -> OperationResponse[DomainRestoreProcess]:
    """Parses the reply to a restore. Without rgp:upData, an accepted request (RFC 3915 §3.2) and a pending report
    leave the domain in pendingRestore, and a completed report restores it."""
    epp = str_to_epp(xml_string)
    header = parse_epp_response_header(epp)
    if client_transaction_id is None:
        header["client_transaction_id"] = None
    up_data = find_extension(epp, RgpUpData)
    if up_data is not None:
        rgp_status = rgp_status_of(up_data)
    elif restore.report is None or header["code"] == ResultCode.COMMAND_COMPLETED_ACTION_PENDING:
        rgp_status = ["pendingRestore"]
    else:
        rgp_status = []
    return OperationResponse(payload=DomainRestoreProcess(rgpStatus=rgp_status), **header)


def epp_domains_Restore(epp_client: EPPClient, restore: DomainRestore, client_transaction_id=None, *, ns_map: dict[str, str]) -> Union[OperationResponse[DomainRestoreProcess], ErrorResponse]:
    """
    Requests the restore of a deleted domain, or sends its report (RFC 3915).
    Args:
        epp_client (EPPClient): The EPP client instance.
        restore (DomainRestore): The request, or the report.
        client_transaction_id (str): The client transaction ID for the request.
    Returns:
        OperationResponse[DomainRestoreProcess]: The RGP state of the domain after the command.
    """
    missing = missing_extension(epp_client, RGP_EXTENSION, "A restore", True, client_transaction_id)
    if missing:
        return missing
    eppxml = restore_domain_xml(restore, client_request_id=client_transaction_id, ns_map=ns_map)
    success, code, response = epp_client.send_and_get_response(eppxml)

    if success == True:
        return parse_domain_restore_response(response, restore, client_transaction_id=client_transaction_id)
    else:
        return get_epp_error_response(response, client_transaction_id=client_transaction_id)
