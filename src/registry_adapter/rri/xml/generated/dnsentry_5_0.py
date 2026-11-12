from dataclasses import dataclass, field
from typing import Optional

__NAMESPACE__ = "http://registry.denic.de/dnsentry/5.0"


@dataclass
class DnsentryBaseType:
    class Meta:
        name = "dnsentryBaseType"

    owner: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/dnsentry/5.0",
            "required": True,
            "min_length": 1,
            "max_length": 254,
            "pattern": r"([*a-zA-Z0-9\-]+\.)+[*a-zA-Z0-9\-]*|(\.)",
        },
    )


@dataclass
class A(DnsentryBaseType):
    rdata: Optional["A.Rdata"] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/dnsentry/5.0",
            "required": True,
        },
    )

    @dataclass
    class Rdata:
        address: Optional[str] = field(
            default=None,
            metadata={
                "type": "Element",
                "namespace": "http://registry.denic.de/dnsentry/5.0",
                "required": True,
                "min_length": 3,
                "max_length": 39,
            },
        )


@dataclass
class Aaaa(DnsentryBaseType):
    class Meta:
        name = "AAAA"

    rdata: Optional["Aaaa.Rdata"] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/dnsentry/5.0",
            "required": True,
        },
    )

    @dataclass
    class Rdata:
        address: Optional[str] = field(
            default=None,
            metadata={
                "type": "Element",
                "namespace": "http://registry.denic.de/dnsentry/5.0",
                "required": True,
                "min_length": 3,
                "max_length": 39,
            },
        )


@dataclass
class Dnskey(DnsentryBaseType):
    class Meta:
        name = "DNSKEY"

    rdata: Optional["Dnskey.Rdata"] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/dnsentry/5.0",
            "required": True,
        },
    )

    @dataclass
    class Rdata:
        flags: Optional[int] = field(
            default=None,
            metadata={
                "type": "Element",
                "namespace": "http://registry.denic.de/dnsentry/5.0",
                "required": True,
            },
        )
        protocol: Optional[int] = field(
            default=None,
            metadata={
                "type": "Element",
                "namespace": "http://registry.denic.de/dnsentry/5.0",
                "required": True,
            },
        )
        algorithm: Optional[int] = field(
            default=None,
            metadata={
                "type": "Element",
                "namespace": "http://registry.denic.de/dnsentry/5.0",
                "required": True,
            },
        )
        public_key: Optional[bytes] = field(
            default=None,
            metadata={
                "name": "publicKey",
                "type": "Element",
                "namespace": "http://registry.denic.de/dnsentry/5.0",
                "required": True,
                "format": "base64",
            },
        )


@dataclass
class Mx(DnsentryBaseType):
    class Meta:
        name = "MX"

    rdata: Optional["Mx.Rdata"] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/dnsentry/5.0",
            "required": True,
        },
    )

    @dataclass
    class Rdata:
        preference: Optional[int] = field(
            default=None,
            metadata={
                "type": "Element",
                "namespace": "http://registry.denic.de/dnsentry/5.0",
                "required": True,
                "min_inclusive": 0,
                "max_inclusive": 999,
            },
        )
        exchange: Optional[str] = field(
            default=None,
            metadata={
                "type": "Element",
                "namespace": "http://registry.denic.de/dnsentry/5.0",
                "required": True,
                "min_length": 1,
                "max_length": 254,
                "pattern": r"([*a-zA-Z0-9\-]+\.)+[*a-zA-Z0-9\-]*|(\.)",
            },
        )


@dataclass
class Ns(DnsentryBaseType):
    class Meta:
        name = "NS"

    rdata: Optional["Ns.Rdata"] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/dnsentry/5.0",
            "required": True,
        },
    )

    @dataclass
    class Rdata:
        nameserver: Optional[str] = field(
            default=None,
            metadata={
                "type": "Element",
                "namespace": "http://registry.denic.de/dnsentry/5.0",
                "required": True,
                "min_length": 1,
                "max_length": 254,
                "pattern": r"([*a-zA-Z0-9\-]+\.)+[*a-zA-Z0-9\-]*|(\.)",
            },
        )
        address: list[str] = field(
            default_factory=list,
            metadata={
                "type": "Element",
                "namespace": "http://registry.denic.de/dnsentry/5.0",
                "min_length": 3,
                "max_length": 39,
            },
        )
        address_v6: list[str] = field(
            default_factory=list,
            metadata={
                "name": "addressV6",
                "type": "Element",
                "namespace": "http://registry.denic.de/dnsentry/5.0",
                "min_length": 3,
                "max_length": 39,
            },
        )


@dataclass
class Dnsentry(DnsentryBaseType):
    class Meta:
        name = "dnsentry"
        namespace = "http://registry.denic.de/dnsentry/5.0"
