class IdnTables:
    """Maps an LGR name (json §6.4) to the IDN table id of the EPP IDN extension, and back.

    The map comes from configuration, LGR name to table id. It must be one to one, or a read could not name the LGR.
    """

    def __init__(self, lgr_tables: dict[str, str] | None = None):
        lgr_tables = lgr_tables or {}
        if not isinstance(lgr_tables, dict):
            raise ValueError("The LGR to IDN table map must be a mapping")
        for lgr, table in lgr_tables.items():
            if not (isinstance(lgr, str) and lgr and isinstance(table, str) and table):
                raise ValueError("Every LGR and IDN table in the map must be a non-empty string")
        tables = list(lgr_tables.values())
        if len(set(tables)) != len(tables):
            raise ValueError("An IDN table is mapped from more than one LGR")
        self._tables = dict(lgr_tables)
        self._lgrs = {table: lgr for lgr, table in lgr_tables.items()}

    def table(self, lgr: str) -> str:
        """The IDN table of an LGR. An LGR the registry has no table for is refused."""
        if lgr not in self._tables:
            raise ValueError(f"The LGR '{lgr}' is not offered")
        return self._tables[lgr]

    def lgrs(self) -> frozenset[str]:
        """The LGRs that have a table."""
        return frozenset(self._tables)

    def lgr(self, table: str) -> str | None:
        """The LGR of an IDN table, or None when no LGR is mapped to it."""
        return self._lgrs.get(table)
