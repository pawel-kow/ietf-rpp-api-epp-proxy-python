from xsdata.models.datatype import XmlDate

from ..epp_model.domain_1_0 import (
    AddRemType,
    AuthInfoChgType,
    AuthInfoType,
    Check,
    ChgType,
    ContactAttrType,
    ContactType,
    Create,
    Delete,
    HostsType,
    Info,
    InfoNameType,
    NsType,
    PeriodType,
    PUnitType,
    Renew,
    StatusType,
    Transfer,
    Update,
)
from ..epp_model.epp_1_0 import (
    CommandType,
    Epp,
    ExtAnyType,
    ReadWriteType,
    TransferOpType,
    TransferType,
)
from ..epp_model.eppcom_1_0 import PwAuthInfoType
from ..epp_model.sec_dns_1_1 import Create as SecdnsCreateType
from ..epp_model.sec_dns_1_1 import KeyDataType

def domain_check(domainname: str, rpp_cl_trid: str) -> Epp:
    epp_request = Epp(
        command=CommandType(
            check=ReadWriteType(other_element=Check(name=[domainname])),
            cl_trid=rpp_cl_trid,
        )
    )

    return epp_request
