from core.model.host.host import Host
from core.model.host.host_update import HostUpdate
from core.model.host.host_update_changes import HostUpdateChanges

from registry_adapter.epp.xml.generated.epp_1_0 import CommandType, Epp, ReadWriteType
from registry_adapter.epp.xml.generated.host_1_0 import (
    AddRemType, AddrType, Check, ChgType, Create, Delete, Info, IpType, StatusType, StatusValueType, Update,
)


def _addresses(ipv4: list[str] | None, ipv6: list[str] | None) -> list[AddrType]:
    return [AddrType(value=ip, ip=IpType.V4) for ip in ipv4 or []] + [
        AddrType(value=ip, ip=IpType.V6) for ip in ipv6 or []
    ]


def _add_rem(changes: HostUpdateChanges | None) -> AddRemType | None:
    if not changes:
        return None
    return AddRemType(
        addr=_addresses(changes.ipv4, changes.ipv6),
        status=[
            StatusType(s=StatusValueType(label), value=changes.status_reasons.get(label, ""))
            for label in changes.status
        ],
    )


def host_check(host_name: str, rpp_cl_trid: str) -> Epp:
    return Epp(command=CommandType(check=ReadWriteType(other_element=Check(name=[host_name])), cl_trid=rpp_cl_trid))


def host_info(host_name: str, rpp_cl_trid: str) -> Epp:
    return Epp(command=CommandType(info=ReadWriteType(other_element=Info(name=host_name)), cl_trid=rpp_cl_trid))


def host_delete(host_name: str, rpp_cl_trid: str) -> Epp:
    return Epp(command=CommandType(delete=ReadWriteType(other_element=Delete(name=host_name)), cl_trid=rpp_cl_trid))


def host_create(host: Host, rpp_cl_trid: str) -> Epp:
    create = Create(name=host.name, addr=_addresses(host.ipv4, host.ipv6))
    return Epp(command=CommandType(create=ReadWriteType(other_element=create), cl_trid=rpp_cl_trid))


def host_update(host_update_model: HostUpdate, rpp_cl_trid: str) -> Epp:
    update = Update(
        name=host_update_model.name,
        add=_add_rem(host_update_model.add),
        rem=_add_rem(host_update_model.remove),
        chg=ChgType(name=host_update_model.new_name) if host_update_model.new_name else None,
    )
    return Epp(command=CommandType(update=ReadWriteType(other_element=update), cl_trid=rpp_cl_trid))
