"""Tests for the F41021 Item Location tools and data build.

The schema assertions are derived from the F41021 data-dictionary export, so
they also catch a botched data build (wrong column count, dropped column,
mis-parsed type/scale). The SQL assertions run offline against a stubbed
executor — no database required.
"""

import asyncio

import pytest

from jde_utils import _ALLOWED_TABLES, validate_allowed_tables
from tools import item_location
from tools.item_location import (
    _available,
    _safe_julian,
    jde_branch_inventory_summary,
    jde_item_availability,
    jde_item_location_detail,
    jde_item_resolve,
    jde_lot_inventory,
    jde_negative_stock,
)
from tools.po_schema import get_table_schema, list_date_columns


# ── data build ──────────────────────────────────────────────────────────

def test_column_count():
    assert get_table_schema("F41021")["column_count"] == 54


def test_type_census():
    census: dict[str, int] = {}
    for col in get_table_schema("F41021")["columns"]:
        census[col["data_type"]] = census.get(col["data_type"], 0) + 1
    assert census == {"Numeric": 36, "String": 10, "Character": 4, "Date": 4}


def test_key_and_prefix():
    doc = get_table_schema("F41021")
    assert doc["prefix"] == "LI"
    assert doc["unique_key"] == ["LIITM", "LIMCU", "LILOCN", "LILOTN"]


def test_date_columns():
    names = [c["field"] for c in list_date_columns("F41021")["date_columns"]]
    assert names == ["LILRCJ", "LINCDJ", "LIUPMJ", "LIURDT"]


def test_only_user_reserved_amount_is_scaled():
    """The DD declares every quantity column as Decimals = 0 (unscaled).

    LIURAT is the single scaled column. If this ever fails, the quantity
    docstrings in tools/item_location.py are wrong and must be revisited.
    """
    scaled = [
        (c["field"], c["decimals"])
        for c in get_table_schema("F41021")["columns"]
        if c["decimals"] > 0
    ]
    assert scaled == [("LIURAT", 2)]


def test_glossary_never_invented():
    """LIQONL has no glossary text in the DD export; it must stay empty."""
    doc = get_table_schema("F41021", include_glossary=True)
    cols = {c["field"]: c for c in doc["columns"]}
    assert cols["LIQONL"]["glossary"] == ""
    assert cols["LIPQOH"]["glossary"].startswith("The number of units")


# ── allowlist ───────────────────────────────────────────────────────────

def test_f41021_and_f4101_are_allowlisted():
    assert validate_allowed_tables("SELECT * FROM TESTDTA.F41021") is None
    assert validate_allowed_tables("SELECT * FROM TESTDTA.F4101") is None


def test_allowlist_keys_are_clean():
    """A stray space in a key silently disables the entry (it is compared
    against a regex-captured identifier, which never has one)."""
    for key in _ALLOWED_TABLES:
        assert key == key.strip(), f"allowlist key {key!r} has whitespace"


# ── SQL expression helpers ──────────────────────────────────────────────

def test_available_expression():
    assert _available() == "(LIPQOH - LIHCOM - LIPCOM - LIFCOM)"
    assert _available("l") == "(l.LIPQOH - l.LIHCOM - l.LIPCOM - l.LIFCOM)"


def test_safe_julian_guards_the_zero_sentinel():
    """LILRCJ is 0 on most rows; TO_DATE would raise on '1900000'."""
    expr = _safe_julian("LILRCJ")
    assert expr.startswith("CASE WHEN LILRCJ > 0 THEN")
    assert "1900000 + LILRCJ" in expr


# ── query construction (offline, stubbed executor) ──────────────────────

@pytest.fixture
def captured(monkeypatch):
    """Capture the SQL a tool builds without touching the database.

    Returns a callable that runs a tool coroutine and yields its SQL, so the
    tests stay synchronous — the suite has no pytest-asyncio dependency.
    """
    seen: dict[str, str] = {}

    async def fake(query, max_rows=None, query_timeout=None):
        seen["query"] = query
        return {"rows": []}

    monkeypatch.setattr(item_location, "run_sql_query_with_validation", fake)

    def run(coro) -> str:
        asyncio.run(coro)
        return seen["query"]

    return run


def test_availability_filters_by_item_and_branch(captured):
    q = captured(jde_item_availability(741343, branch="20000"))
    assert "LIITM = 741343" in q
    assert "TRIM(LIMCU) = '20000'" in q
    assert "FROM TESTDTA.F41021" in q


def test_location_detail_excludes_zero_by_default(captured):
    assert "LIPQOH <> 0" in captured(jde_item_location_detail(741343))
    assert "LIPQOH <> 0" not in captured(
        jde_item_location_detail(741343, include_zero=True)
    )


def test_string_literals_are_escaped(captured):
    """A quote in user input must be doubled, not break out of the literal."""
    q = captured(jde_branch_inventory_summary("20000' OR '1'='1"))
    assert "TRIM(l.LIMCU) = '20000'' OR ''1''=''1'" in q


def test_item_resolve_search_is_case_insensitive(captured):
    q = captured(jde_item_resolve("crude"))
    assert "UPPER(TRIM(IMLITM)) LIKE '%CRUDE%'" in q
    assert "UPPER(TRIM(IMDSC1)) LIKE '%CRUDE%'" in q


def test_negative_stock_selects_only_negatives(captured):
    assert "l.LIPQOH < 0" in captured(jde_negative_stock())


def test_lot_inventory_requires_an_argument():
    assert "error" in asyncio.run(jde_lot_inventory())


def test_lot_inventory_filters_blank_lots(captured):
    """TRIM of an all-blank NCHAR is NULL in Oracle — this filters the
    non-lot-controlled rows without an NCHAR/CHAR literal comparison, which
    would raise ORA-12704."""
    q = captured(jde_lot_inventory(item_number=741298))
    assert "TRIM(l.LILOTN) IS NOT NULL" in q
    assert "!= ''" not in q and "<> ''" not in q
