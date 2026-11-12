"""The test environment: one backend server the integration suite runs against (docs/rri/refactoring.md §5.3).

It is chosen with `RPP_TEST_ENV` (default `epp-docker`) and described in `tests/integration/environments/<name>.yaml`.
Credentials are not in the descriptor: it names the variables that hold them, which come from the process
environment or from `.env` in the repository root.
"""
import base64
import importlib
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

REPOSITORY = Path(__file__).resolve().parents[2]
ENVIRONMENTS = REPOSITORY / "tests" / "integration" / "environments"
DEFAULT_ENVIRONMENT = "epp-docker"


class EnvironmentError(Exception):
    """The environment descriptor is wrong or a variable it names is missing. Never holds a credential."""


@dataclass(frozen=True)
class Registrar:
    """One slot the cases name (`a`, `b`), with its credentials and the handles it uses."""
    slot: str
    user: str
    password: str = field(repr=False)
    regacc: str
    handle_prefix: str
    gen_req: str | None = None
    abuse: str | None = None

    def basic(self, password: str | None = None) -> str:
        token = f"{self.user}:{self.password if password is None else password}".encode()
        return "Basic " + base64.b64encode(token).decode("ascii")


@dataclass(frozen=True)
class TestEnvironment:
    name: str
    config: str
    profile: str
    max_workers: int
    rpp_requests_per_minute: int | None
    registrars: dict[str, Registrar]
    facts: dict
    wrong_password: str | None = field(default=None, repr=False)
    unknown_user: tuple[str, str] | None = field(default=None, repr=False)

    def declared_profile(self):
        """The `BackendProfile` the descriptor names, for selectors evaluated outside the app under test."""
        module, _, name = self.profile.partition(":")
        return getattr(importlib.import_module(module), name)


def environment_names() -> list[str]:
    return sorted(p.stem for p in ENVIRONMENTS.glob("*.yaml"))


def selected_name() -> str:
    return os.getenv("RPP_TEST_ENV", DEFAULT_ENVIRONMENT)


def _descriptor(name: str) -> dict:
    path = ENVIRONMENTS / f"{name}.yaml"
    if not path.exists():
        raise EnvironmentError(f"No test environment {name!r}: known are {', '.join(environment_names())}")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def config_file(name: str) -> str:
    """The `RPP_CONFIG_FILE` of the app under test, relative to the repository root."""
    return str(REPOSITORY / _descriptor(name)["config"])


REGACC_FORMS = {
    "user": lambda user: user,
    # An RRI login is a DENIC handle, which starts with the RegAccId of its RegAcc (refactoring.md §3.2, P1).
    "login_prefix": lambda user: "-".join(user.split("-")[:2]).upper(),
}


def load(name: str, environ=None, with_credentials: bool = True) -> TestEnvironment:
    """Reads the descriptor and, unless `with_credentials` is false, the variables it names. A missing variable is an
    error that names it, so no case logs in with an empty one."""
    data = _descriptor(name)
    environ = os.environ if environ is None else environ
    regacc_of = REGACC_FORMS[data.get("regacc", "user")]
    missing = []

    def variable(var):
        if var is None:
            return None
        if not with_credentials:
            return f"<{var}>"
        value = environ.get(var)
        if not value:
            missing.append(var)
        return value

    registrars = {}
    for slot, spec in data["registrars"].items():
        user = variable(spec["user"])
        password = variable(spec["password"])
        regacc = regacc_of(user) if user else ""
        # The prefix the backend requires of the handles of this registrar, which differs between accounts.
        prefix = variable(spec["prefix"])
        registrars[slot] = Registrar(
            slot=slot, user=user or "", password=password or "", regacc=regacc, handle_prefix=prefix or "",
            gen_req=variable(spec.get("gen_req")), abuse=variable(spec.get("abuse")))
    if missing:
        raise EnvironmentError(f"Test environment {name!r} needs {', '.join(missing)} in .env or the environment")
    unknown = data.get("unknown_user")
    return TestEnvironment(
        name=name, config=data["config"], profile=data["profile"], max_workers=int(data.get("max_workers", 8)),
        rpp_requests_per_minute=data.get("rpp_requests_per_minute"), registrars=registrars,
        facts=dict(data.get("facts") or {}), wrong_password=data.get("wrong_password"),
        unknown_user=(unknown["user"], unknown["password"]) if unknown else None)


VALUE_PLACEHOLDER = re.compile(r"\{(handle|regacc|gen_req|abuse):([a-z])(?::([^{}]*))?\}")
TLD_PLACEHOLDER = "{tld}"


def replace_values(value: str, env: TestEnvironment, random_id: str) -> str:
    """Replaces `{handle:a:SUFFIX}`, `{regacc:a}`, `{gen_req:a}`, `{abuse:a}` and `{tld}`. None of them is a secret."""
    def replace(match):
        kind, slot, suffix = match.groups()
        registrar = env.registrars.get(slot)
        if registrar is None:
            raise EnvironmentError(f"{match.group(0)}: no registrar {slot!r} in {env.name}")
        if kind == "handle":
            return f"{registrar.handle_prefix}{random_id}{suffix or ''}"
        if kind == "regacc":
            return registrar.regacc
        result = getattr(registrar, kind)
        if result is None:
            raise EnvironmentError(f"{match.group(0)}: {env.name} has no {kind} handle for registrar {slot!r}")
        return result

    return VALUE_PLACEHOLDER.sub(replace, value).replace(TLD_PLACEHOLDER, str(env.facts.get("tld", "")))


AUTH_PLACEHOLDER = re.compile(r"\{auth:([a-z_]+)(?::([a-z_]+))?\}")


class Credentials:
    """Puts the credentials into a request header when the request is sent, never into the case."""

    def __init__(self, env: TestEnvironment):
        self.env = env

    def slot(self, value: str) -> str | None:
        """The registrar slot a header value names, for pacing."""
        match = AUTH_PLACEHOLDER.fullmatch(value)
        return match.group(1) if match and match.group(1) in self.env.registrars else None

    def header(self, value: str) -> str:
        match = AUTH_PLACEHOLDER.fullmatch(value)
        if match is None:
            if "{auth:" in value:
                raise EnvironmentError("Malformed credential placeholder in a header")
            return value
        who, form = match.groups()
        if self.env.facts.get("failed_logins_lock") and (who == "unknown_user" or form == "wrong_password"):
            raise EnvironmentError(f"{self.env.name} takes no wrong credentials: failed logins lock the login")
        if who == "unknown_user":
            if self.env.unknown_user is None:
                raise EnvironmentError(f"{self.env.name} has no unknown user form")
            user, password = self.env.unknown_user
            return "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode("ascii")
        registrar = self.env.registrars.get(who)
        if registrar is None:
            raise EnvironmentError(f"{{auth:{who}}}: no registrar {who!r} in {self.env.name}")
        if form is None:
            return registrar.basic()
        if form == "wrong_password":
            if self.env.wrong_password is None:
                raise EnvironmentError(f"{self.env.name} has no wrong password form")
            return registrar.basic(self.env.wrong_password)
        raise EnvironmentError(f"{{auth:{who}:{form}}}: unknown form {form!r}")

    def headers(self, headers: dict) -> dict:
        return {k: self.header(v) if isinstance(v, str) else v for k, v in headers.items()}
