"""#128: the core and the HTTP side of the RPP adapter do not name the backend's protocol. Only the RPP terms that
contain it are allowed: the EPP Compatibility Profile and the EPP-derived result codes (core §12.4, §18)."""
import re
from pathlib import Path

import pytest

SRC = Path(__file__).parents[2] / "src"

RPP_TERMS = re.compile(r"EPP Compatibility Profile|EPP-derived|of an EPP code")


@pytest.mark.parametrize("package", ["core", "rpp/http", "rpp/handlers"])
def test_the_package_does_not_name_epp(package):
    named = [
        f"{path.relative_to(SRC)}:{number}"
        for path in (SRC / package).rglob("*.py")
        for number, line in enumerate(path.read_text().splitlines(), 1)
        if re.search(r"\bEPP\b", RPP_TERMS.sub("", line))
    ]

    assert named == []
