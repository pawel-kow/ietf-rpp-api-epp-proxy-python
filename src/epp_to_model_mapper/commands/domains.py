import re

from xsdata.models.datatype import XmlDate

from models import Domain, DomainUpdate

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
from ..epp_model.sec_dns_1_1 import Create as SecdnsCreateType
from ..epp_model.sec_dns_1_1 import KeyDataType


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


def domain_create(domain: Domain, rpp_cl_trid: str) -> Epp:
    create = Create(name=domain.name.upper())

    if domain.processes and domain.processes.get("creation"):
        duration = domain.processes["creation"].duration
        match = re.match(r"P([0-9]+)([MY])", duration)
        if not match:
            raise ValueError(
                "Unsupported duration format. Only whole years (Y) or months (M) are allowed."
            )
        value, unit = match.groups()
        create.period = PeriodType(value=int(value), unit=PUnitType(unit.lower()))

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

    return Epp(
        command=CommandType(
            create=ReadWriteType(other_element=create),
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
                            value=contact.contact.id,
                            type_value=ContactAttrType(contact.type),
                        )
                    )
                else:
                    set_registrant = True
        if add.ns is not None and (add.ns.host_objs or add.ns.host_attrs):
            add_elem.ns = _ns_type(add.ns)
        if add_elem.contact or add_elem.ns:
            update.add = add_elem

    if remove is not None:
        rem_elem = AddRemType()
        if remove.ns is not None and (remove.ns.host_objs or remove.ns.host_attrs):
            if remove.ns.host_objs:
                rem_elem.ns = NsType(host_obj=[h.id for h in remove.ns.host_objs])
            else:
                rem_elem.ns = NsType(
                    host_attr=[HostAttrType(host_name=h.id) for h in remove.ns.host_attrs]
                )
        if remove.contacts is not None:
            for contact in remove.contacts:
                if contact.type != "registrant":
                    rem_elem.contact.append(
                        ContactType(
                            value=contact.contact.id,
                            type_value=ContactAttrType(contact.type),
                        )
                    )
                else:
                    set_registrant = True
        if rem_elem.contact or rem_elem.ns:
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
                        new_registrant = contact.contact.id
                        break
            chg.registrant = new_registrant
        if change is not None and change.authInfo is not None and change.authInfo.pw is not None:
            chg.auth_info = AuthInfoChgType(pw=PwAuthInfoType(value=change.authInfo.pw))
        update.chg = chg

    return Epp(
        command=CommandType(
            update=ReadWriteType(other_element=update),
            cl_trid=rpp_cl_trid,
        )
    )
