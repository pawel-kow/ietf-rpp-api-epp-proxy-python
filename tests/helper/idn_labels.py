import re

IDN_PLACEHOLDER = re.compile(r"\{(alabel|ulabel):([^}]+)\}")


def u_label(text: str, seed: str) -> str:
    """A U-label made unique by the seed of the test session."""
    return f"{text}-{seed}".lower()


def a_label(text: str, seed: str) -> str:
    """The A-label of `u_label` (RFC 3492 punycode with the ACE prefix)."""
    return "xn--" + u_label(text, seed).encode("punycode").decode("ascii")


def replace_idn_placeholders(value: str, seed: str) -> str:
    """Replaces `{ulabel:TEXT}` by a U-label and `{alabel:TEXT}` by its A-label, both from TEXT and the seed."""
    def replace(match):
        return (a_label if match.group(1) == "alabel" else u_label)(match.group(2), seed)

    return IDN_PLACEHOLDER.sub(replace, value)
