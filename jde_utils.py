"""Shared utilities for JDE MCP tools.

All Oracle SQL helpers, JDE Julian date conversion, schema resolution,
code translation, and result formatting live here so every tool module
can reuse them without duplication.
"""

import os
import re
from datetime import date, datetime, timedelta

from dotenv import load_dotenv

load_dotenv()

# ── Schema resolution (D2) ──────────────────────────────────────────────

_DEFAULT_SCHEMA = "PRODDTA"


def get_schema(override: str | None = None) -> str:
    """Return the JDE schema to use in SQL queries.

    Priority: explicit override > JDE_SCHEMA env var > default (PRODDTA).
    """
    if override:
        return override
    return os.getenv("JDE_SCHEMA", _DEFAULT_SCHEMA)


# ── JDE Julian date conversion (D4 / §8.1) ──────────────────────────────
#
# JDE stores dates as 6-digit integers in CYYDDD format:
#   C   = century flag (0 = 1900s, 1 = 2000s)
#   YY  = year within century
#   DDD = day of year (1–366)
# Example: 126001 = 2026-01-01


def gregorian_to_jde_julian(dt: date) -> int:
    """Convert a Python date to a JDE Julian integer (CYYDDD)."""
    c = 1 if dt.year >= 2000 else 0
    yy = dt.year % 100
    ddd = dt.timetuple().tm_yday
    return c * 100000 + yy * 1000 + ddd


def jde_julian_to_gregorian(j: int) -> date:
    """Convert a JDE Julian integer (CYYDDD) to a Python date."""
    c = j // 100000
    yy = (j // 1000) % 100
    ddd = j % 1000
    year = 1900 + c * 100 + yy
    return date(year, 1, 1) + timedelta(days=ddd - 1)


def parse_iso_date(iso_str: str) -> date:
    """Parse an ISO YYYY-MM-DD string to a Python date.

    Raises ValueError with a clear message on bad input.
    """
    try:
        return datetime.strptime(iso_str.strip(), "%Y-%m-%d").date()
    except (ValueError, AttributeError) as exc:
        raise ValueError(
            f"Invalid date '{iso_str}'. Expected ISO format YYYY-MM-DD "
            f"(e.g. '2025-06-15')."
        ) from exc


def iso_to_jde_julian(iso_str: str) -> int:
    """Convert an ISO date string directly to a JDE Julian integer."""
    return gregorian_to_jde_julian(parse_iso_date(iso_str))


# ── Oracle SQL fragment builders (D1 / §8.2 / §8.3) ─────────────────────


def julian_col_to_date(col: str) -> str:
    """Return an Oracle SQL expression that converts a Julian column to a DATE.

    Example: julian_col_to_date("RPDDJ")
      → "TO_DATE(TO_CHAR(1900000 + RPDDJ), 'YYYYDDD')"
    """
    return f"TO_DATE(TO_CHAR(1900000 + {col}), 'YYYYDDD')"


def days_past_due_expr(col: str) -> str:
    """Return an Oracle SQL expression for days past due (positive = overdue).

    Example: days_past_due_expr("RPDDJ")
      → "TRUNC(SYSDATE) - TO_DATE(TO_CHAR(1900000 + RPDDJ), 'YYYYDDD')"
    """
    return f"TRUNC(SYSDATE) - {julian_col_to_date(col)}"


def row_limit_clause(n: int) -> str:
    """Return an Oracle FETCH FIRST clause for row limiting."""
    return f"FETCH FIRST {int(n)} ROWS ONLY"


# ── Input sanitisation ───────────────────────────────────────────────────


def escape_sql_string(s: str) -> str:
    """Escape a string value for safe interpolation into an Oracle SQL literal.

    Doubles single quotes and strips any leading/trailing whitespace.
    """
    return s.strip().replace("'", "''")


# Valid category codes for F0101 (AC01–AC30)
_VALID_CATEGORY_CODES = {f"AC{i:02d}" for i in range(1, 31)}


def validate_category_code(code: str) -> str:
    """Validate and return the JDE column name for a category code.

    Args:
        code: e.g. "AC01", "AC15", "AC30"

    Returns:
        The F0101 physical column name, e.g. "ABAC01".

    Raises:
        ValueError: if the code is not in the AC01–AC30 range.
    """
    upper = code.strip().upper()
    if upper not in _VALID_CATEGORY_CODES:
        raise ValueError(
            f"Invalid category code '{code}'. "
            f"Must be AC01 through AC30."
        )
    return f"AB{upper}"


# Valid receipt types for F03B14
VALID_RECEIPT_TYPES = {"U", "A", "C", "D", "N", "V"}

# Valid adjustment types for writeoffs/chargebacks/deductions
VALID_ADJUSTMENT_TYPES = {"writeoff", "chargeback", "deduction", "all"}


# ── Code-to-label translation dictionaries (§12) ────────────────────────

DOC_TYPE_LABELS = {
    "RI": "Standard Invoice",
    "RK": "Credit Memo",
    "RV": "Receipt Voucher",
    "R5": "Deduction",
    "RU": "Chargeback",
}

RECEIPT_TYPE_LABELS = {
    "U": "Unapplied Cash",
    "A": "Applied",
    "C": "Chargeback",
    "D": "Deduction",
    "N": "NSF (Non-Sufficient Funds)",
    "V": "Void",
}

SEARCH_TYPE_LABELS = {
    "C": "Customer",
    "S": "Supplier",
    "V": "Employee",
    "E": "Employee",
    "X": "Employee (Former)",
    "N": "Address",
}

ORDER_STATUS_LABELS = {
    "520": "Shipped",
    "540": "Confirmed",
    "560": "In Warehouse",
    "580": "Picked",
    "600": "Other/Pending",
    "999": "Closed/Complete",
}


# ── Result formatting (§12) ─────────────────────────────────────────────


def _translate_code(value, lookup: dict) -> str:
    """Translate a raw code to a friendly label, or return as-is."""
    if value is None:
        return ""
    key = str(value).strip()
    return lookup.get(key, key)


def _format_money(amount, currency: str | None = None) -> str:
    """Format a monetary value with thousands separators and 2 decimals."""
    if amount is None:
        return "0.00"
    try:
        formatted = f"{float(amount):,.2f}"
    except (ValueError, TypeError):
        return str(amount)
    if currency:
        return f"{currency.strip()} {formatted}"
    return formatted


def _translate_credit_hold(flag) -> str:
    """Translate AIHDAR flag to human-readable text."""
    if flag is None:
        return "No hold"
    return "On credit hold" if str(flag).strip().upper() == "Y" else "No hold"


def format_result(
    result: dict,
    *,
    empty_message: str = "No records found for the given criteria.",
) -> dict:
    """Normalise executor output into a clean tool response.

    - If the executor returned an error, pass it through.
    - If rows are empty, return a clear message (not an error).
    - Otherwise return the data rows and count.
    """
    if "error" in result:
        return result

    rows = result.get("rows", [])
    if not rows:
        return {"message": empty_message, "data": [], "record_count": 0}

    return {"data": rows, "record_count": len(rows)}


def format_single_result(
    result: dict,
    *,
    empty_message: str = "No record found for the given criteria.",
) -> dict:
    """Like format_result but expects exactly one row (lookup tools)."""
    if "error" in result:
        return result

    rows = result.get("rows", [])
    if not rows:
        return {"message": empty_message, "data": None}

    return {"data": rows[0]}


# ── SQL safety validation ───────────────────────────────────────────────
#
# Guards for the free-form SQL passthrough (``run_sql_query_with_validation``):
# only single, read-only SELECT statements against an allowlisted set of JDE
# physical tables are permitted.

# Keywords that indicate a non-read-only statement.
_FORBIDDEN_KEYWORDS = [
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE",
    "TRUNCATE", "MERGE", "GRANT", "REVOKE", "EXEC", "EXECUTE",
    "CALL", "INTO",
]

# Pre-compiled pattern: whole-word match for any forbidden keyword.
_FORBIDDEN_RE = re.compile(
    r"\b(?:" + "|".join(_FORBIDDEN_KEYWORDS) + r")\b",
    re.IGNORECASE,
)

# Only these JDE physical tables may be queried by free-form SQL. Add entries
# here to widen access — the docstring for the SQL tool is generated from this
# dict automatically, so no second place needs updating.
# Names are compared case-insensitively, without schema.
_ALLOWED_TABLES = {
    "F4211":  "Sales Order Detail",
    "F03B11": "Customer Ledger (A/R)",
    "F03B14": "Receipts Detail",
    "F0101":  "Address Book",
    "F03012": "Customer Master",
    "F4311":  "Purchase Order Detail",
    "F43121": "Purchase Order Receiver",
    "F4101":  "Item Master",
    "F41021": "Item Location File",
    #  "F9210" : "Data Dictionary",
}


def get_allowed_tables_description() -> str:
    """Return a human-readable comma-separated list of allowed tables.

    Example output:
        "F0101 (Address Book), F03012 (Customer Master), ..."
    """
    return ", ".join(
        f"{tbl} ({desc})" for tbl, desc in sorted(_ALLOWED_TABLES.items())
    )


# Table references following FROM or JOIN, optionally schema-qualified
# (e.g. PRODDTA.F03B11 or just F03B11). Captures schema (group 1) and an
# optional table part (group 2) when the reference is qualified.
_TABLE_REF_RE = re.compile(
    r"\b(?:FROM|JOIN)\s+([A-Za-z_$#][\w$#]*)(?:\.([A-Za-z_$#][\w$#]*))?",
    re.IGNORECASE,
)

# CTE names introduced by `WITH name AS (` / `, name AS (` — these are valid
# FROM targets even though they are not physical tables.
_CTE_NAME_RE = re.compile(
    r"(?:\bWITH|,)\s+([A-Za-z_$#][\w$#]*)\s+AS\s*\(",
    re.IGNORECASE,
)


def validate_allowed_tables(query: str) -> str | None:
    """Reject queries that reference any table outside ``_ALLOWED_TABLES``.

    Returns ``None`` if every FROM/JOIN target is either an allowed physical
    table or a CTE defined within the same query; otherwise an error string.
    """
    cte_names = {m.group(1).upper() for m in _CTE_NAME_RE.finditer(query)}

    for schema_part, table_part in _TABLE_REF_RE.findall(query):
        # When qualified (schema.table), the table is the second group;
        # when bare, the first group is the identifier itself.
        name = (table_part or schema_part).upper()
        if name in cte_names or name in _ALLOWED_TABLES:
            continue
        return (
            f"table '{name}' is not allowed — permitted tables: "
            + ", ".join(sorted(_ALLOWED_TABLES))
        )

    return None


def validate_select_only(query: str) -> str | None:
    """Validate that *query* is a single, read-only SELECT statement.

    Returns ``None`` if the query is acceptable, or an error-message string
    explaining why it was rejected.
    """

    stripped = query.strip()

    if not stripped:
        return "query is empty"

    # Strip a single optional trailing semicolon.
    if stripped.endswith(";"):
        stripped = stripped[:-1].rstrip()

    if not stripped:
        return "query is empty after removing trailing semicolon"

    # Reject multiple statements (any remaining semicolons).
    if ";" in stripped:
        return "multiple statements not allowed"

    # The top-level statement must be a SELECT (allow leading CTEs).
    upper = stripped.upper()
    if not (upper.startswith("SELECT") or upper.startswith("WITH")):
        return "query must begin with SELECT (or WITH ... SELECT for CTEs)"

    # Reject forbidden keywords (whole-word match).
    match = _FORBIDDEN_RE.search(stripped)
    if match:
        return f"forbidden keyword '{match.group()}' detected — only read-only SELECT queries are allowed"

    return None
