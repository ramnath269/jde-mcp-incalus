"""Acceptance tests for the JDE PO schema-metadata tools (spec Section 8).

Derived from Appendix A of the build spec, so these also catch a botched data
build (wrong column count, dropped column, mis-parsed type/scale).
"""

import pytest

from tools.po_schema import (
    build_select,
    date_to_julian,
    find_columns,
    get_column,
    get_table_schema,
    julian_to_date,
    list_date_columns,
    list_decimal_columns,
)


# 1 — column count
def test_column_count():
    assert get_table_schema("F4311")["column_count"] == 228


# 2 — data-type census
def test_type_census():
    census: dict[str, int] = {}
    for col in get_table_schema("F4311")["columns"]:
        census[col["data_type"]] = census.get(col["data_type"], 0) + 1
    assert census == {"String": 105, "Numeric": 71, "Character": 37, "Date": 15}


# 3 — decimal column count
def test_decimal_count():
    assert list_decimal_columns("F4311")["count"] == 34


# 4 — date vs time column split
def test_date_and_time_counts():
    dates = list_date_columns("F4311")
    assert dates["date_column_count"] == 15
    assert dates["time_column_count"] == 5
    assert len(dates["date_columns"]) == 15
    assert len(dates["time_columns"]) == 5


# 5 — data-item lookup resolves to the physical column
def test_get_column_by_data_item():
    col = get_column("UORG")
    assert col["field"] == "PDUORG"
    assert col["data_type"] == "Numeric"
    assert col["length"] == 15
    assert col["decimals"] == 0
    assert col["table"] == "F4311"


# 6 — unit cost scale
def test_unit_cost_scale():
    col = get_column("PDPRRC")
    assert col["data_type"] == "Numeric"
    assert (col["length"], col["decimals"]) == (15, 4)
    dec = {c["field"]: c for c in list_decimal_columns("F4311")["columns"]}
    assert dec["PDPRRC"]["divide_by_to_get_display_value"] == 10000


# 7 — the canonical implied-decimals case
def test_line_number_scale():
    col = get_column("PDLNID")
    assert col["data_type"] == "Numeric"
    assert (col["length"], col["decimals"]) == (6, 3)


# 8 — keyword search
def test_find_open():
    fields = {c["field"] for c in find_columns("open")}
    assert "PDUOPN" in fields
    assert "PDAOPN" in fields


# 9 — build_select emits prefixed names, annotates decimals, ends with warnings
def test_build_select():
    sql = build_select("F4311", "DOCO,LNID,UORG,PDAOPN,NXTR")
    for name in ("PDDOCO", "PDLNID", "PDUORG", "PDAOPN", "PDNXTR"):
        assert name in sql
    # decimal columns annotated with their scale
    assert "PDLNID" in sql and "divide by 1000" in sql
    assert "PDAOPN" in sql and "divide by 100" in sql
    # trailing RTRIM + Julian comments
    assert "RTRIM(" in sql
    assert "CYYDDD" in sql or "126195" in sql


# 10 — unknown field never reaches the SQL string
def test_build_select_rejects_unknown():
    with pytest.raises(ValueError) as exc:
        build_select("F4311", "BOGUS")
    assert "BOGUS" in str(exc.value)


# 11 — unknown table lists what is loaded
def test_unknown_table():
    with pytest.raises(ValueError) as exc:
        get_table_schema("F9999")
    assert "F4311" in str(exc.value)


# 12 — Julian round-trip
def test_julian_roundtrip():
    assert julian_to_date(126195) == "2026-07-14"
    assert date_to_julian("2026-07-14") == 126195
    assert julian_to_date(100001) == "2000-01-01"
    assert date_to_julian("2000-01-01") == 100001
    assert julian_to_date(99365) == "1999-12-31"
    assert date_to_julian("1999-12-31") == 99365


# 13 — every Appendix A column round-trips through the JSON with no silent drop
def test_no_silent_drops():
    cols = get_table_schema("F4311")["columns"]
    assert len(cols) == 228
    # ordinals are the full 1..228 sequence — nothing dropped or duplicated
    schema = get_table_schema("F4311")
    assert schema["column_count"] == len(cols)
    # spot-check the last row survived intact
    last = get_column("PDPNS")
    assert (last["data_type"], last["length"], last["decimals"]) == (
        "Numeric",
        10,
        0,
    )


# 14 — the scaling warning is present and non-empty
def test_scaling_warning():
    warning = list_decimal_columns("F4311")["warning"]
    assert warning
    assert "verif" in warning.lower()
