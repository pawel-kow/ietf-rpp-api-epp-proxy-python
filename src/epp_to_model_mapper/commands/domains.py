import base64
import re

from xsdata.models.datatype import XmlDate

from models import AuthInfo, DnsSec, Domain, DomainRenew, DomainTransfer, DomainUpdate

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
    HostAttrType,
    HostsType,
    Info,
    InfoNameType,
    NsType,
    PeriodType,
    PUnitType,
    Renew,
    StatusType,
    StatusValueType,
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
from ..epp_model.host_1_0 import AddrType, IpType
from ..epp_model.idn_1_0 import Data as IdnData
from ..epp_model.sec_dns_1_1 import Create as SecdnsCreateType
from ..epp_model.sec_dns_1_1 import DsDataType, DsOrKeyType, KeyDataType, RemType as SecdnsRemType
from ..epp_model.sec_dns_1_1 import Update as SecdnsUpdateType


def _ns_type(ns) -> NsType:
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


def _period(duration: str) -> PeriodType:
    match = re.match(r"P([0-9]+)([MY])", duration)
    if not match:
        raise ValueError(
            "Unsupported duration format. Only whole years (Y) or months (M) are allowed."
        )
    value, unit = match.groups()
    return PeriodType(value=int(value), unit=PUnitType(unit.lower()))


def _sec_dns_create(dns_sec: DnsSec) -> SecdnsCreateType:
    return SecdnsCreateType(
        ds_data=[
            DsDataType(key_tag=ds.keyTag, alg=ds.algorithm, digest_type=ds.digestType, digest=bytes.fromhex(ds.digest))
            for ds in dns_sec.ds_data or []
        ],
        key_data=[
            KeyDataType(flags=key.flags, protocol=key.protocol, alg=key.algorithm, pub_key=base64.b64decode(key.publicKey))
            for key in dns_sec.key_data or []
        ],
    )


def _ds_data(dns_sec: DnsSec) -> list[DsDataType]:
    return [
        DsDataType(key_tag=ds.keyTag, alg=ds.algorithm, digest_type=ds.digestType, digest=bytes.fromhex(ds.digest))
        for ds in dns_sec.ds_data or []
    ]


def _key_data(dns_sec: DnsSec) -> list[KeyDataType]:
    return [
        KeyDataType(flags=key.flags, protocol=key.protocol, alg=key.algorithm, pub_key=base64.b64decode(key.publicKey))
        for key in dns_sec.key_data or []
    ]


def _sec_dns_update(add: DnsSec | None, remove: DnsSec | None) -> SecdnsUpdateType | None:
    if not (add or remove):
        return None
    return SecdnsUpdateType(
        add=DsOrKeyType(ds_data=_ds_data(add), key_data=_key_data(add)) if add else None,
        rem=SecdnsRemType(ds_data=_ds_data(remove), key_data=_key_data(remove)) if remove else None,
    )


def _status_types(labels: list[str] | None, reasons: dict[str, str] | None = None) -> list[StatusType]:
    return [StatusType(s=StatusValueType(label), value=(reasons or {}).get(label, "")) for label in labels or []]


def domain_check(domainname: str, rpp_cl_trid: str) -> Epp:
    epp_request = Epp(
        command=CommandType(
            check=ReadWriteType(other_element=Check(name=[domainname])),
            cl_trid=rpp_cl_trid,
        )
    )

    return epp_request


def domain_info(domainname: str, rpp_cl_trid: str) -> Epp:
    return Epp(
        command=CommandType(
            info=ReadWriteType(other_element=Info(name=InfoNameType(value=domainname))),
            cl_trid=rpp_cl_trid,
        )
    )


def domain_delete(domainname: str, rpp_cl_trid: str) -> Epp:
    return Epp(
        command=CommandType(
            delete=ReadWriteType(other_element=Delete(name=domainname)),
            cl_trid=rpp_cl_trid,
        )
    )


def _transfer_auth_info(auth_info: AuthInfo) -> AuthInfoType:
    return AuthInfoType(pw=PwAuthInfoType(value=auth_info.pw, roid=auth_info.roid))


def domain_transfer(transfer: DomainTransfer, rpp_cl_trid: str) -> Epp:
    return Epp(
        command=CommandType(
            transfer=TransferType(
                op=TransferOpType(transfer.operation.value),
                other_element=Transfer(
                    name=transfer.name,
                    period=_period(transfer.duration) if transfer.duration else None,
                    auth_info=_transfer_auth_info(transfer.authInfo) if transfer.authInfo else None,
                ),
            ),
            cl_trid=rpp_cl_trid,
        )
    )


def domain_renew(renew: DomainRenew, rpp_cl_trid: str) -> Epp:
    return Epp(
        command=CommandType(
            renew=ReadWriteType(
                other_element=Renew(
                    name=renew.name,
                    cur_exp_date=XmlDate.from_string(renew.curExpDate),
                    period=_period(renew.duration) if renew.duration else None,
                ),
            ),
            cl_trid=rpp_cl_trid,
        )
    )


def domain_create(domain: Domain, rpp_cl_trid: str) -> Epp:
    create = Create(name=domain.name.upper())

    if domain.processes and domain.processes.get("creation"):
        create.period = _period(domain.processes["creation"].duration)

    if domain.ns and (domain.ns.host_objs or domain.ns.host_attrs):
        create.ns = _ns_type(domain.ns)

    if domain.contacts:
        registrant_generated = False
        for contact in domain.contacts:
            if "registrant" in contact.types:
                if registrant_generated:
                    raise ValueError("Only one registrant is allowed in EPP")
                create.registrant = contact.id.upper()
                registrant_generated = True
            for t in contact.types:
                if t != "registrant":
                    create.contact.append(
                        ContactType(value=contact.id.upper(), type_value=ContactAttrType(t))
                    )

    if domain.authInfo and domain.authInfo.pw:
        create.auth_info = AuthInfoType(pw=PwAuthInfoType(value=domain.authInfo.pw))

    extensions = []
    if domain.dnsSEC:
        extensions.append(_sec_dns_create(domain.dnsSEC))
    if domain.idn:
        extensions.append(IdnData(table=domain.idn.table, uname=domain.idn.uname))

    return Epp(
        command=CommandType(
            create=ReadWriteType(other_element=create),
            extension=ExtAnyType(other_element=extensions) if extensions else None,
            cl_trid=rpp_cl_trid,
        )
    )


def domain_update(domain_update: DomainUpdate, rpp_cl_trid: str) -> Epp:
    update = Update(name=domain_update.name.upper())

    set_registrant = False
    add = domain_update.add
    remove = domain_update.remove

    if add is not None:
        add_elem = AddRemType()
        if add.contacts is not None:
            for contact in add.contacts:
                if contact.type != "registrant":
                    add_elem.contact.append(
                        ContactType(
                            value=contact.contact.id.upper(),
                            type_value=ContactAttrType(contact.type),
                        )
                    )
                else:
                    set_registrant = True
        if add.ns is not None and (add.ns.host_objs or add.ns.host_attrs):
            add_elem.ns = _ns_type(add.ns)
        add_elem.status = _status_types(add.status, add.status_reasons)
        if add_elem.contact or add_elem.ns or add_elem.status:
            update.add = add_elem

    if remove is not None:
        rem_elem = AddRemType()
        if remove.ns is not None and (remove.ns.host_objs or remove.ns.host_attrs):
            rem_elem.ns = _ns_type(remove.ns)
        if remove.contacts is not None:
            for contact in remove.contacts:
                if contact.type != "registrant":
                    rem_elem.contact.append(
                        ContactType(
                            value=contact.contact.id.upper(),
                            type_value=ContactAttrType(contact.type),
                        )
                    )
                else:
                    set_registrant = True
        rem_elem.status = _status_types(remove.status)
        if rem_elem.contact or rem_elem.ns or rem_elem.status:
            update.rem = rem_elem

    change = domain_update.change
    if change is not None or set_registrant:
        chg = ChgType()
        if set_registrant:
            # EPP registrant change is a replacement: empty string clears it.
            new_registrant = ""
            if add is not None and add.contacts is not None:
                for contact in add.contacts:
                    if contact.type == "registrant":
                        new_registrant = contact.contact.id.upper()
                        break
            chg.registrant = new_registrant
        if change is not None and change.authInfo is not None and change.authInfo.pw is not None:
            chg.auth_info = AuthInfoChgType(pw=PwAuthInfoType(value=change.authInfo.pw))
        elif change is not None and change.clear_auth_info:
            chg.auth_info = AuthInfoChgType(null="")
        update.chg = chg

    sec_dns = _sec_dns_update(add.dnsSEC if add else None, remove.dnsSEC if remove else None)
    return Epp(
        command=CommandType(
            update=ReadWriteType(other_element=update),
            extension=ExtAnyType(other_element=[sec_dns]) if sec_dns else None,
            cl_trid=rpp_cl_trid,
        )
    )
