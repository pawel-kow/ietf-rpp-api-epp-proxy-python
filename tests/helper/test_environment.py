"""The test environment: one backend server the integration suite runs against (docs/rri/refactoring.md §5.3).

It is chosen with `RPP_TEST_ENV` (default `epp-docker`) and described in `tests/integration/environments/<name>.yaml`.
Credentials are not in the descriptor: it names the variables that hold them, which come from the process
environment or from `.env` in the repository root. The backend profile, the TLD, the LGRs and the environment name
are not in it either: they come from the config of the app under test, which the descriptor names.
"""
import base64
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from core.capabilities.backend_profile import BackendProfile
from settings.load_settings import load_settings
from tests.helper.one_of import OneOf
from tests.helper.selectors import env_fact

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

    def basic(self) -> str:
        token = f"{self.user}:{self.password}".encode()
        return "Basic " + base64.b64encode(token).decode("ascii")


@dataclass(frozen=True)
class TestEnvironment:
    name: str
    config: str
    max_workers: int
    rpp_requests_per_minute: int | None
    registrars: dict[str, Registrar]
    facts: dict
    profile: BackendProfile
    unknown_user: tuple[str, str] | None = field(default=None, repr=False)


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
    settings = load_settings(str(REPOSITORY / data["config"]))
    # What the config states, which the cases read as facts too: `{tld}` and `{env:environment_name}`.
    facts = {**(data.get("facts") or {}), "tld": (settings.discovery.rpp_tlds or [""])[0],
             "environment_name": settings.discovery.rpp_environment_name}
    return TestEnvironment(
        name=name, config=data["config"], max_workers=int(data.get("max_workers", 8)),
        rpp_requests_per_minute=data.get("rpp_requests_per_minute"), registrars=registrars, facts=facts,
        profile=BackendProfile.from_layers(*settings.profile_layers, {"lgrs": list(settings.lgrs)}),
        unknown_user=(unknown["user"], unknown["password"]) if unknown else None)


VALUE_PLACEHOLDER = re.compile(r"\{(handle|regacc|gen_req|abuse):([a-z])(?::([^{}]*))?\}")
TLD_PLACEHOLDER = "{tld}"
FACT_PLACEHOLDER = re.compile(r"\{env:([A-Za-z_.]+)\}")


def replace_values(value: str, env: TestEnvironment, random_id: str) -> str:
    """Replaces `{handle:a:SUFFIX}`, `{regacc:a}`, `{gen_req:a}`, `{abuse:a}`, `{tld}` and `{env:<path>}` (a fact of
    the environment that is not a list, see `replace_fact`). None of them is a secret."""
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

    def fact(match):
        value = _fact(match, env)
        if isinstance(value, list):
            raise EnvironmentError(f"{match.group(0)}: a list fact is a whole value, not part of a string")
        return str(value)

    value = VALUE_PLACEHOLDER.sub(replace, value).replace(TLD_PLACEHOLDER, str(env.facts.get("tld", "")))
    return FACT_PLACEHOLDER.sub(fact, value)


def _fact(match, env: TestEnvironment):
    try:
        return env_fact(env.facts, match.group(1))
    except KeyError:
        raise EnvironmentError(f"{match.group(0)}: {env.name} has no such fact") from None


def replace_fact(value: str, env: TestEnvironment):
    """A value that is `{env:<path>}` alone and names a list fact is `OneOf` its entries, which the response
    comparison takes any of; any other value is returned as it is, for `replace_values`."""
    match = FACT_PLACEHOLDER.fullmatch(value)
    if match is None:
        return value
    fact = _fact(match, env)
    return OneOf(fact) if isinstance(fact, list) else value


AUTH_PLACEHOLDER = re.compile(r"\{auth:([a-z_]+)\}")


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
        who = match.group(1)
        if who == "unknown_user":
            if self.env.unknown_user is None:
                raise EnvironmentError(f"{self.env.name} has no unknown user")
            user, password = self.env.unknown_user
            return "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode("ascii")
        registrar = self.env.registrars.get(who)
        if registrar is None:
            raise EnvironmentError(f"{{auth:{who}}}: no registrar {who!r} in {self.env.name}")
        return registrar.basic()

    def headers(self, headers: dict) -> dict:
        return {k: self.header(v) if isinstance(v, str) else v for k, v in headers.items()}
