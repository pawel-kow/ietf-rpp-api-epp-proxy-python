from dataclasses import dataclass, field

from core.result.error_response import ErrorResponse
from core.result.operation_response import OperationResponse
from core.result.result_code import ResultCode
from core.ports import derived_update
from core.ports.replacement_steps import ReplacementSteps


@dataclass(kw_only=True)
class Read(OperationResponse):
    value: str = ""


def ok() -> dict:
    return dict(code=ResultCode.COMMAND_COMPLETED_SUCCESSFULLY, msg="ok", server_transaction_id="sv", client_transaction_id=None)


@dataclass
class Registry:
    """A registry with one object, `value`, updated by a delta `(old, new)`. Records every command."""
    value: str = "a"
    commands: list = field(default_factory=list)
    refusal: ErrorResponse | None = None

    def read(self, key):
        self.commands.append(("read", key))
        return Read(value=self.value, **ok())

    def update(self, delta, client_transaction_id=None):
        self.commands.append(("update", delta, client_transaction_id))
        self.value = delta[1]
        return OperationResponse(**ok())

    def steps(self) -> ReplacementSteps:
        return ReplacementSteps(
            read=self.read,
            object_of=lambda read: read.value,
            difference=lambda current, wanted: (current, wanted),
            changes_nothing=lambda delta: delta[0] == delta[1],
            update=self.update,
            refuse=lambda current, wanted: self.refusal,
        )


def test_the_object_is_read_then_the_difference_sent():
    registry = Registry()

    outcome = derived_update.replace(registry.steps(), "k", "b", "cl-1")

    assert registry.commands == [("read", "k"), ("update", ("a", "b"), "cl-1")]
    assert outcome.update == ("a", "b") and not outcome.unchanged


def test_a_read_the_caller_has_is_not_repeated():
    registry = Registry()

    derived_update.replace(registry.steps(), "k", "b", "cl-1", Read(value="a", **ok()))

    assert registry.commands == [("update", ("a", "b"), "cl-1")]


def test_nothing_is_sent_when_nothing_changes():
    registry = Registry()

    outcome = derived_update.replace(registry.steps(), "k", "a", "cl-1")

    assert registry.commands == [("read", "k")]
    assert outcome.unchanged and outcome.current.value == "a"


def test_a_refusal_sends_nothing():
    refusal = ErrorResponse(code=ResultCode.UNIMPLEMENTED_OPTION, msg="no", server_transaction_id=None, client_transaction_id=None)
    registry = Registry(refusal=refusal)

    assert derived_update.replace(registry.steps(), "k", "b", "cl-1") is refusal
    assert registry.commands == [("read", "k")]
