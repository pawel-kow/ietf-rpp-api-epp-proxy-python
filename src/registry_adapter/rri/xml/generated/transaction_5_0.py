from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

__NAMESPACE__ = "http://registry.denic.de/transaction/5.0"


@dataclass
class DataType:
    class Meta:
        name = "dataType"

    other_element: list[object] = field(
        default_factory=list,
        metadata={
            "type": "Wildcard",
            "namespace": "##other",
        },
    )


class LevelType(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ResultType(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    EXCEPTION = "exception"


@dataclass
class MessageType:
    class Meta:
        name = "messageType"

    text: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/transaction/5.0",
            "required": True,
        },
    )
    argument: list[str] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/transaction/5.0",
        },
    )
    level: Optional[LevelType] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "required": True,
        },
    )
    code: Optional[int] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "required": True,
        },
    )


@dataclass
class Message(MessageType):
    class Meta:
        name = "message"
        namespace = "http://registry.denic.de/transaction/5.0"


@dataclass
class TransactionType:
    class Meta:
        name = "transactionType"

    stid: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/transaction/5.0",
            "min_length": 3,
            "max_length": 64,
        },
    )
    ctid: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/transaction/5.0",
            "min_length": 3,
            "max_length": 64,
        },
    )
    result: Optional[ResultType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/transaction/5.0",
            "required": True,
        },
    )
    message: list[MessageType] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/transaction/5.0",
        },
    )
    data: Optional[DataType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/transaction/5.0",
        },
    )


@dataclass
class Transaction(TransactionType):
    class Meta:
        name = "transaction"
        namespace = "http://registry.denic.de/transaction/5.0"
