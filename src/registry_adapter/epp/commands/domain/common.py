import base64
import logging
import re
from typing import Union

from core.model.domain.dns_sec import DnsSec
from core.model.domain.domain_idn import DomainIdn
from core.model.domain.domains import HostAttr, HostObj, NS
from core.model.domain.ds_data import DsData
from core.model.domain.key_data import KeyData
from core.result.error_response import ErrorResponse
from core.result.result_code import ResultCode
from registry_adapter.epp.commands.shared.epp_response import find_extension
from registry_adapter.epp.idn_tables import IdnTables
from registry_adapter.epp.session.epp_client import EPPClient
from registry_adapter.epp.xml.generated.domain_1_0 import HostAttrType, NsType, PeriodType, PUnitType
from registry_adapter.epp.xml.generated.epp_1_0 import Epp
from registry_adapter.epp.xml.generated.host_1_0 import AddrType, IpType
from registry_adapter.epp.xml.generated.idn_1_0 import Data as IdnData
from registry_adapter.epp.xml.generated.sec_dns_1_1 import InfData as SecDnsInfData

logger = logging.getLogger(__name__)


def ns_type(ns) -> NsType:
    """Build a domain nsType from an internal NS model (hostObj xor hostAttr)."""
    if ns.host_objs:
        return NsType(host_obj=[h.id for h in ns.host_objs])
    return NsType(
        host_attr=[
            HostAttrType(
                host_name=h.id,
                host_addr=[AddrType(value=ip, ip=IpType.V4) for ip in (h.ipv4 or [])]
                + [AddrType(value=ip, ip=IpType.V6) for ip in (h.ipv6 or [])],
            )
            for h in (ns.host_attrs or [])
        ]
    )


def period_of(duration: str) -> PeriodType:
    match = re.match(r"P([0-9]+)([MY])", duration)
    if not match:
        raise ValueError(
            "Unsupported duration format. Only whole years (Y) or months (M) are allowed."
        )
    value, unit = match.groups()
    return PeriodType(value=int(value), unit=PUnitType(unit.lower()))


def rgp_status_of(data) -> list[str]:
    """The RGP statuses of rgp:infData or rgp:upData (RFC 3915 §4.1.2, §4.2.5)."""
    return [status.s.value for status in data.rgp_status if status.s is not None] if data else []


def ns_from_epp(ns) -> Union[NS, None]:
    """Map an EPP domain nsType to the internal NS model."""
    if ns is None:
        return None
    if ns.host_obj:
        return NS(host_objs=[HostObj(id=h) for h in ns.host_obj], host_attrs=None)
    if ns.host_attr:
        host_attrs = [
            HostAttr(
                id=ha.host_name,
                ipv4=[a.value for a in ha.host_addr if a.ip and a.ip.value == "v4"] or None,
                ipv6=[a.value for a in ha.host_addr if a.ip and a.ip.value == "v6"] or None,
            )
            for ha in ns.host_attr
        ]
        return NS(host_objs=None, host_attrs=host_attrs)
    return None


def dns_sec_from_epp(epp: Epp) -> Union[DnsSec, None]:
    """The DNSSEC data of an Info response. A keyData inside a dsData is not kept (spec-issues.md)."""
    data = find_extension(epp, SecDnsInfData)
    if data is None or not (data.ds_data or data.key_data):
        return None
    return DnsSec(
        ds_data=[
            DsData(keyTag=ds.key_tag, algorithm=ds.alg, digestType=ds.digest_type, digest=ds.digest.hex().upper())
            for ds in data.ds_data
        ] or None,
        key_data=[
            KeyData(
                flags=key.flags,
                protocol=key.protocol,
                algorithm=key.alg,
                publicKey=base64.b64encode(key.pub_key).decode(),
            )
            for key in data.key_data
        ] or None,
    )


def idn_from_epp(epp: Epp, idn_tables: IdnTables) -> Union[DomainIdn, None]:
    """The IDN data of an Info response (draft-obispo-epp-idn-04). Without an LGR for its table there is none, as json
    §6.4 does not allow `uName` without `lgr`."""
    data = find_extension(epp, IdnData)
    if data is None:
        return None
    lgr = idn_tables.lgr(data.table)
    if lgr is None:
        logger.warning("No LGR is configured for the IDN table '%s', so uName and lgr are left out", data.table)
        return None
    return DomainIdn(lgr=lgr, uname=data.uname)


def missing_extension(epp_client: EPPClient, uri: str, feature: str, data, client_transaction_id) -> ErrorResponse | None:
    """The error for data that needs an extension the server does not offer, or None."""
    if not data or epp_client.supports_extension(uri):
        return None
    return ErrorResponse(
        code=ResultCode.UNIMPLEMENTED_EXTENSION,
        msg=f"{feature} needs {uri}, which the EPP server does not offer",
        server_transaction_id=None,
        client_transaction_id=client_transaction_id,
    )
