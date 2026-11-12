from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from registry_adapter.rri.xml.generated.contact_5_0 import (
    Check as ContactCheck,
)
from registry_adapter.rri.xml.generated.contact_5_0 import (
    Create as ContactCreate,
)
from registry_adapter.rri.xml.generated.contact_5_0 import (
    Info as ContactInfo,
)
from registry_adapter.rri.xml.generated.contact_5_0 import (
    Update as ContactUpdate,
)
from registry_adapter.rri.xml.generated.domain_5_0 import (
    Check as DomainCheck,
)
from registry_adapter.rri.xml.generated.domain_5_0 import (
    Chholder,
    Chprov,
    CreateAuthInfo1,
    CreateAuthInfo2,
    DeleteAuthInfo1,
    Restore,
    Transit,
)
from registry_adapter.rri.xml.generated.domain_5_0 import (
    Create as DomainCreate,
)
from registry_adapter.rri.xml.generated.domain_5_0 import (
    Delete as DomainDelete,
)
from registry_adapter.rri.xml.generated.domain_5_0 import (
    Info as DomainInfo,
)
from registry_adapter.rri.xml.generated.domain_5_0 import (
    Update as DomainUpdate,
)
from registry_adapter.rri.xml.generated.message_5_0 import (
    Delete as MessageDelete,
)
from registry_adapter.rri.xml.generated.message_5_0 import (
    QueueRead,
)
from registry_adapter.rri.xml.generated.regacc_5_0 import Info as RegaccInfo
from registry_adapter.rri.xml.generated.transaction_5_0 import Transaction

__NAMESPACE__ = "http://registry.denic.de/global/5.0"


@dataclass
class LoginType:
    class Meta:
        name = "loginType"

    user: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/global/5.0",
            "required": True,
        },
    )
    password: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/global/5.0",
            "required": True,
        },
    )


class LogoutType(Enum):
    VALUE = ""


@dataclass
class RequestType:
    class Meta:
        name = "requestType"

    login: Optional[LoginType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/global/5.0",
        },
    )
    logout: Optional[LogoutType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/global/5.0",
        },
    )
    create: Optional[ContactCreate] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/contact/5.0",
        },
    )
    update: Optional[ContactUpdate] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/contact/5.0",
        },
    )
    check: Optional[ContactCheck] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/contact/5.0",
        },
    )
    info: Optional[ContactInfo] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/contact/5.0",
        },
    )
    registry_denic_de_domain_5_0_create: Optional[DomainCreate] = field(
        default=None,
        metadata={
            "name": "create",
            "type": "Element",
            "namespace": "http://registry.denic.de/domain/5.0",
        },
    )
    registry_denic_de_domain_5_0_update: Optional[DomainUpdate] = field(
        default=None,
        metadata={
            "name": "update",
            "type": "Element",
            "namespace": "http://registry.denic.de/domain/5.0",
        },
    )
    chholder: Optional[Chholder] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/domain/5.0",
        },
    )
    delete: Optional[DomainDelete] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/domain/5.0",
        },
    )
    restore: Optional[Restore] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/domain/5.0",
        },
    )
    registry_denic_de_domain_5_0_check: Optional[DomainCheck] = field(
        default=None,
        metadata={
            "name": "check",
            "type": "Element",
            "namespace": "http://registry.denic.de/domain/5.0",
        },
    )
    info_1: Optional[DomainInfo] = field(
        default=None,
        metadata={
            "name": "info",
            "type": "Element",
            "namespace": "http://registry.denic.de/domain/5.0",
        },
    )
    chprov: Optional[Chprov] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/domain/5.0",
        },
    )
    transit: Optional[Transit] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/domain/5.0",
        },
    )
    create_auth_info1: Optional[CreateAuthInfo1] = field(
        default=None,
        metadata={
            "name": "createAuthInfo1",
            "type": "Element",
            "namespace": "http://registry.denic.de/domain/5.0",
        },
    )
    delete_auth_info1: Optional[DeleteAuthInfo1] = field(
        default=None,
        metadata={
            "name": "deleteAuthInfo1",
            "type": "Element",
            "namespace": "http://registry.denic.de/domain/5.0",
        },
    )
    create_auth_info2: Optional[CreateAuthInfo2] = field(
        default=None,
        metadata={
            "name": "createAuthInfo2",
            "type": "Element",
            "namespace": "http://registry.denic.de/domain/5.0",
        },
    )
    queue_read: Optional[QueueRead] = field(
        default=None,
        metadata={
            "name": "queue-read",
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
        },
    )
    registry_denic_de_msg_5_0_delete: Optional[MessageDelete] = field(
        default=None,
        metadata={
            "name": "delete",
            "type": "Element",
            "namespace": "http://registry.denic.de/msg/5.0",
        },
    )
    info_2: Optional[RegaccInfo] = field(
        default=None,
        metadata={
            "name": "info",
            "type": "Element",
            "namespace": "http://registry.denic.de/regacc/5.0",
        },
    )
    ctid: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/global/5.0",
            "min_length": 3,
            "max_length": 64,
        },
    )


@dataclass
class ResponseType:
    class Meta:
        name = "responseType"

    transaction: Optional[Transaction] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/transaction/5.0",
            "required": True,
        },
    )


@dataclass
class RegistryRequest(RequestType):
    class Meta:
        name = "registry-request"
        namespace = "http://registry.denic.de/global/5.0"


@dataclass
class RegistryResponse(ResponseType):
    class Meta:
        name = "registry-response"
        namespace = "http://registry.denic.de/global/5.0"
