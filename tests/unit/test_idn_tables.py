import pytest

from rpp.mapping.domain.idn_tables import IdnTables

TABLES = IdnTables({"latn-1.0": "de", "spa-1.0": "es"})


def test_an_lgr_maps_to_its_table():
    assert TABLES.table("latn-1.0") == "de"


def test_a_table_maps_back_to_its_lgr():
    assert TABLES.lgr("es") == "spa-1.0"


def test_an_unknown_lgr_is_refused():
    with pytest.raises(ValueError):
        TABLES.table("cyrl-1.0")


def test_an_unknown_table_has_no_lgr():
    assert TABLES.lgr("ru") is None


@pytest.mark.parametrize("lgr_tables", [None, {}])
def test_without_a_map_every_lgr_is_refused_and_no_table_has_one(lgr_tables):
    tables = IdnTables(lgr_tables)

    with pytest.raises(ValueError):
        tables.table("latn-1.0")
    assert tables.lgr("de") is None


@pytest.mark.parametrize("lgr_tables", [
    {"latn-1.0": "de", "deu-1.0": "de"},  # not one to one: a read could not tell the LGR
    {"latn-1.0": ""},
    {"": "de"},
    {"latn-1.0": 1},
    ["latn-1.0"],
])
def test_a_map_that_cannot_go_both_ways_is_refused(lgr_tables):
    with pytest.raises(ValueError):
        IdnTables(lgr_tables)
