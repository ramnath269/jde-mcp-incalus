"""JDE Purchase Order schema-metadata tools (F4311 and siblings).

A **metadata-only** module: it never touches a database. It serves exact
column metadata for JDE purchase-order tables so a calling agent looks a field
up instead of inventing one, and knows the implied scale before it does
arithmetic. Live data comes from the separate JDE data tools
(``jde_run_sql_query`` and friends). The intended pairing is:
**resolve the column here → run the query there.**

Tables are discovered by globbing ``data/*.json`` (override the directory with
``JDE_SCHEMA_DIR``). No table name is hardcoded — dropping ``F4301.json`` in
lights it up with zero code change.

Three data-contract rules this module exists to enforce (see the module spec):
  * Implied decimals — a ``Decimals > 0`` column may be stored *unscaled*
    (12.3456 as ``123456``). We expose the divisor and say, out loud, that it
    must be verified against a known order before anyone trusts a SUM.
  * Julian dates — every ``Date`` column is 6-digit ``CYYDDD``; never compare
    to an ISO string.
  * Blank padding — ``String``/``Character`` columns are space-padded, so any
    emitted SQL wraps character comparisons in ``RTRIM()``.
"""

from __future__ import annotations

import glob
import json
import os
from pathlib import Path

from jde_utils import iso_to_jde_julian, jde_julian_to_gregorian

# ── Data loading (glob discovery, JDE_SCHEMA_DIR override) ───────────────

_DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# The verify-before-you-trust message. Deliberately does NOT assert the value
# is scaled — this server does not know the platform, and a confident wrong
# answer about scale is exactly the failure mode it exists to prevent.
_SCALING_WARNING = (
    "Decimals shown are the data-dictionary scale. In many JDE installs the "
    "physical column stores the value UNSCALED (e.g. a unit cost of 12.3456 "
    "sits in a (15,4) column as 123456). Divide by "
    "'divide_by_to_get_display_value' ONLY after verifying the scaling against "
    "one known order — do not trust a SUM until you have confirmed it."
)

_JULIAN_FORMAT = (
    "JDE dates are 6-digit Julian CYYDDD: C = centuries since 1900, YY = "
    "2-digit year, DDD = day-of-year (1-366). Never compare a Julian column to "
    "an ISO date string. Example: 2026-07-14 = 126195 (C=1, YY=26, DDD=195)."
)


def _data_dir() -> Path:
    override = os.getenv("JDE_SCHEMA_DIR")
    return Path(override) if override else _DEFAULT_DATA_DIR


# table (upper) -> full table document
_TABLES: dict[str, dict] = {}
# table (upper) -> {"by_field": {...}, "by_item": {...}}
_INDEX: dict[str, dict[str, dict]] = {}


def _load() -> None:
    """(Re)load every ``data/*.json`` into the module-level registry."""
    _TABLES.clear()
    _INDEX.clear()
    for path in sorted(glob.glob(str(_data_dir() / "*.json"))):
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
        name = doc["table"].upper()
        _TABLES[name] = doc
        by_field = {c["field"].upper(): c for c in doc["columns"]}
        by_item = {c["data_item"].upper(): c for c in doc["columns"]}
        _INDEX[name] = {"by_field": by_field, "by_item": by_item}


_load()


# ── Internal resolution helpers ─────────────────────────────────────────


def _known_tables() -> list[str]:
    return sorted(_TABLES)


def _require_table(table: str) -> dict:
    """Return the table doc or raise a ValueError listing loaded tables."""
    doc = _TABLES.get(table.strip().upper())
    if doc is None:
        available = ", ".join(_known_tables()) or "(none loaded)"
        raise ValueError(
            f"Unknown table '{table}'. Loaded tables: {available}."
        )
    return doc


def _resolve_in_table(table_name: str, field: str) -> dict | None:
    """Resolve a field within one table, accepting prefixed or data-item form."""
    up = field.strip().upper()
    idx = _INDEX[table_name]
    return idx["by_field"].get(up) or idx["by_item"].get(up)


def _column_view(col: dict) -> dict:
    """A compact column projection (no glossary) for list-style responses."""
    return {
        "field": col["field"],
        "data_item": col["data_item"],
        "description": col["description"],
        "data_type": col["data_type"],
        "length": col["length"],
        "decimals": col["decimals"],
    }


# ── Julian / date conversion helpers ────────────────────────────────────


def julian_to_date(cyyddd: int) -> str:
    """Convert a JDE Julian integer (CYYDDD) to an ISO ``YYYY-MM-DD`` string."""
    return jde_julian_to_gregorian(int(cyyddd)).isoformat()


def date_to_julian(iso_date: str) -> int:
    """Convert an ISO ``YYYY-MM-DD`` string to a JDE Julian integer (CYYDDD)."""
    return iso_to_jde_julian(iso_date)


# ── Tool 1: list_po_tables ──────────────────────────────────────────────


def list_po_tables() -> list[dict]:
    """List every loaded JDE purchase-order table with its high-level shape.

    Start here when you do not yet know which table holds the field you need.
    Each entry gives the table name, what it stores, its column prefix, how
    many columns it has, and the composite unique key for a row.
    """
    out = []
    for name in _known_tables():
        doc = _TABLES[name]
        out.append(
            {
                "table": doc["table"],
                "description": doc["description"],
                "prefix": doc["prefix"],
                "column_count": doc["column_count"],
                "unique_key": doc["unique_key"],
            }
        )
    return out


# ── Tool 2: get_table_schema ────────────────────────────────────────────


def get_table_schema(table: str, include_glossary: bool = False) -> dict:
    """Return the full column list and keys for one table.

    Use this to see every column of a table at once — field name, data item,
    description, data type, length, and decimals. Glossary text is large and
    omitted unless ``include_glossary=True``. Raises ``ValueError`` (listing the
    tables that ARE loaded) for an unknown table.

    Args:
        table: Table name, e.g. "F4311".
        include_glossary: Include per-column glossary text when True.
    """
    doc = _require_table(table)
    columns = []
    for col in doc["columns"]:
        view = _column_view(col)
        if include_glossary:
            view["glossary"] = col.get("glossary", "")
        columns.append(view)
    return {
        "table": doc["table"],
        "description": doc["description"],
        "prefix": doc["prefix"],
        "unique_key": doc["unique_key"],
        "surrogate_key": doc["surrogate_key"],
        "column_count": doc["column_count"],
        "columns": columns,
    }


# ── Tool 3: get_column ──────────────────────────────────────────────────


def get_column(field: str, table: str = "") -> dict:
    """Return one column in full, including glossary and which table it is in.

    Accepts either the physical name (``PDUORG``) or the JDE data item
    (``UORG``). With ``table`` empty, searches every loaded table and reports
    the one that matched. Raises ``ValueError`` (pointing you at
    ``find_columns``) when the field is unknown.

    Args:
        field: Column name, prefixed or data-item form.
        table: Optional table to restrict the search to.
    """
    if table:
        doc = _require_table(table)
        col = _resolve_in_table(doc["table"].upper(), field)
        if col is None:
            raise ValueError(
                f"Unknown column '{field}' in {doc['table']}. "
                f"Try find_columns('{field}') to search by keyword."
            )
        return {"table": doc["table"], **col}

    for name in _known_tables():
        col = _resolve_in_table(name, field)
        if col is not None:
            return {"table": _TABLES[name]["table"], **col}

    raise ValueError(
        f"Unknown column '{field}' in any loaded table. "
        f"Try find_columns('{field}') to search by keyword."
    )


# ── Tool 4: find_columns ────────────────────────────────────────────────


def find_columns(query: str, table: str = "F4311", limit: int = 25) -> list[dict]:
    """Keyword-search a table's columns by field name and description.

    This is how you get from a concept ("open", "quantity", "promised date",
    "supplier") to a real column name. Every whitespace-separated token in
    ``query`` must appear (case-insensitively) somewhere in the field name,
    data item, or description. Returns up to ``limit`` matches. Raises
    ``ValueError`` for an unknown table.

    Args:
        query: One or more keywords.
        table: Table to search (default "F4311").
        limit: Maximum matches to return (default 25).
    """
    doc = _require_table(table)
    tokens = [t for t in query.lower().split() if t]
    matches = []
    for col in doc["columns"]:
        haystack = (
            f"{col['field']} {col['data_item']} {col['description']}".lower()
        )
        if all(tok in haystack for tok in tokens):
            view = _column_view(col)
            view["table"] = doc["table"]
            matches.append(view)
            if len(matches) >= limit:
                break
    return matches


# ── Tool 5: list_decimal_columns ────────────────────────────────────────


def list_decimal_columns(table: str = "F4311") -> dict:
    """List the columns with implied decimals, each with its display divisor.

    Returns every column where ``decimals > 0`` plus
    ``divide_by_to_get_display_value = 10 ** decimals``, and a ``warning`` that
    the scaling must be verified against a known order before it is trusted.
    Raises ``ValueError`` for an unknown table.

    Args:
        table: Table to inspect (default "F4311").
    """
    doc = _require_table(table)
    columns = []
    for col in doc["columns"]:
        if col["decimals"] > 0:
            view = _column_view(col)
            view["divide_by_to_get_display_value"] = 10 ** col["decimals"]
            columns.append(view)
    return {
        "table": doc["table"],
        "count": len(columns),
        "warning": _SCALING_WARNING,
        "columns": columns,
    }


# ── Tool 6: list_date_columns ───────────────────────────────────────────


def list_date_columns(table: str = "F4311") -> dict:
    """List the Julian date columns and the companion HHMMSS time columns.

    Date columns hold 6-digit Julian ``CYYDDD``; time columns are numeric
    ``HHMMSS`` and are a curated list (they cannot be inferred from shape — a
    line-number column is also numeric length 6). Includes the format
    explanation and a worked example so a caller never compares a Julian value
    to an ISO string. Raises ``ValueError`` for an unknown table.

    Args:
        table: Table to inspect (default "F4311").
    """
    doc = _require_table(table)
    date_cols = [
        _column_view(c) for c in doc["columns"] if c["data_type"] == "Date"
    ]
    time_names = {n.upper() for n in doc.get("time_columns", [])}
    time_cols = [
        _column_view(c)
        for c in doc["columns"]
        if c["field"].upper() in time_names
    ]
    return {
        "table": doc["table"],
        "julian_format": _JULIAN_FORMAT,
        "example": "126195 -> 2026-07-14 ; 2026-07-14 -> 126195",
        "date_column_count": len(date_cols),
        "time_column_count": len(time_cols),
        "date_columns": date_cols,
        "time_columns": time_cols,
    }


# ── Tool 7: build_select ────────────────────────────────────────────────


def build_select(
    table: str = "F4311", fields: str = "", schema: str = "PRODDTA"
) -> str:
    """Build a validated ``SELECT`` skeleton for a purchase-order table.

    Every name in ``fields`` (comma-separated, prefixed or data-item form) is
    validated against the real columns; an unknown one raises ``ValueError``
    naming the offender and pointing at ``find_columns`` — it never reaches the
    SQL string. Emitted columns use their physical (prefixed) names; decimal
    columns are annotated with their implied scale. Empty ``fields`` defaults to
    the table's unique key. Trailing comments carry the RTRIM (blank-padding)
    and Julian-date warnings.

    Args:
        table: Table to select from (default "F4311").
        fields: Comma-separated column names; empty = the unique key.
        schema: Schema/owner to qualify the table with (default "PRODDTA").
    """
    doc = _require_table(table)
    table_name = doc["table"]

    requested = [f.strip() for f in fields.split(",") if f.strip()]
    if not requested:
        requested = list(doc["unique_key"])

    resolved: list[dict] = []
    for name in requested:
        col = _resolve_in_table(table_name.upper(), name)
        if col is None:
            raise ValueError(
                f"Unknown column '{name}' in {table_name}. "
                f"Try find_columns('{name}') to find the right column; "
                f"no SQL was generated."
            )
        resolved.append(col)

    lines = []
    for i, col in enumerate(resolved):
        comma = "," if i < len(resolved) - 1 else ""
        if col["decimals"] > 0:
            divisor = 10 ** col["decimals"]
            note = (
                f"  -- {col['data_type']}({col['length']},{col['decimals']}): "
                f"implied {col['decimals']} decimals — divide by {divisor} to "
                f"display (verify vs a known order)"
            )
        else:
            note = ""
        lines.append(f"    {col['field']}{comma}{note}")

    select_body = "\n".join(lines)
    return (
        "SELECT\n"
        f"{select_body}\n"
        f"FROM {schema}.{table_name}\n"
        "-- Blank padding: wrap CHAR/STRING comparisons in RTRIM(), "
        "e.g. RTRIM(PDDCTO) = 'OP' (columns are space-padded to full length).\n"
        "-- Julian dates: Date columns are 6-digit CYYDDD "
        "(e.g. 2026-07-14 = 126195); never compare to an ISO string."
    )
