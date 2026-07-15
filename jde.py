import json
import os

import httpx
from dotenv import load_dotenv

from jde_utils import (
    days_past_due_expr,
    format_result,
    get_schema,
    julian_col_to_date,
    validate_allowed_tables,
    validate_select_only,
)

load_dotenv()

BASE_URL = os.getenv("JDE_BASE_URL")
USERNAME = os.getenv("JDE_USERNAME")
PASSWORD = os.getenv("JDE_PASSWORD")
ENVIRONMENT = os.getenv("JDE_ENVIRONMENT")


async def get_token() -> dict:
    """Authenticate with JD Edwards AIS and return a session token."""

    url = f"{BASE_URL}/jderest/tokenrequest"

    payload = {
        "username": USERNAME,
        "password": PASSWORD,
        "environment": ENVIRONMENT,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(url, json=payload)

    response.raise_for_status()

    return response.json()


async def customer_ledger_inquiry(
    address_number: str,
    schema_override: str | None = None,
) -> dict:
    """
    Retrieve a customer's open invoices from the JDE Customer Ledger (F03B11).

    Runs a read-only SQL query (via ``run_sql_query_with_validation``, the
    shared RunSQL orchestration) joining F03B11 to the Address Book (F0101)
    for the customer name. Returns every open item (open amount <> 0, not
    fully paid) for the given AddressNumber, with readable invoice/due dates
    and computed days-past-due, ordered by due date.

    NOTE: this was previously served by the ORCH_55_CustomerLedgerInquiry
    orchestration, which is not published/shared on the JDV920 server. It is
    now built from SQL so it runs against the same shared orchestration as the
    other tools.

    Fields returned: CustomerNumber, CustomerDesc, Document, DocType,
    OriginalDocument, OrigDocType, SalesOrderNumber, SalesOrderType,
    InvoiceDate, DueDate, GrossAmount, OpenAmount, DaysPastDue, BusinessUnit,
    Reference, PayStatus, Company.
    """

    # Validate the address number is numeric before interpolating into SQL.
    try:
        addr = int(str(address_number).strip())
    except (ValueError, TypeError):
        return {
            "error": (
                f"Invalid address number '{address_number}'. "
                "Expected a numeric AddressNumber."
            ),
            "rows": [],
            "row_count": 0,
        }

    schema = get_schema(schema_override)
    inv_date = julian_col_to_date("b.RPDIVJ")
    due_date = julian_col_to_date("b.RPDDJ")
    days_past = days_past_due_expr("b.RPDDJ")

    query = (
        "SELECT "
        "b.RPAN8 AS CustomerNumber, a.ABALPH AS CustomerDesc, "
        "b.RPDOC AS Document, b.RPDCT AS DocType, "
        "b.RPODOC AS OriginalDocument, b.RPODCT AS OrigDocType, "
        "b.RPDOCO AS SalesOrderNumber, b.RPDCTO AS SalesOrderType, "
        f"TO_CHAR({inv_date}, 'YYYY-MM-DD') AS InvoiceDate, "
        f"TO_CHAR({due_date}, 'YYYY-MM-DD') AS DueDate, "
        "b.RPAG AS GrossAmount, b.RPAAP AS OpenAmount, "
        f"{days_past} AS DaysPastDue, "
        "TRIM(b.RPMCU) AS BusinessUnit, TRIM(b.RPVR01) AS Reference, "
        "b.RPPST AS PayStatus, b.RPCO AS Company "
        f"FROM {schema}.F03B11 b "
        f"LEFT JOIN {schema}.F0101 a ON a.ABAN8 = b.RPAN8 "
        f"WHERE b.RPAN8 = {addr} AND b.RPAAP <> 0 AND b.RPPST <> 'P' "
        f"ORDER BY {due_date} ASC"
    )

    result = await run_sql_query_with_validation(query)
    return format_result(
        result,
        empty_message=f"No open invoices found for customer {addr}.",
    )


async def run_sql_query_with_validation(
    query: str,
    max_rows: int | None = None,
    query_timeout: str | None = None,
) -> dict:
    """Execute a read-only SQL query via the shared SQL orchestration.

    The query is first checked by ``validate_select_only`` and
    ``validate_allowed_tables`` (single read-only SELECT against allowlisted
    tables), then sent to the orchestration named by ``JDE_SQL_ORCHESTRATION``
    (default ``ORC_2607030001CUST``). Credentials are read from environment
    variables (no separate token call required).

    Args:
        query: A SQL SELECT statement to execute. Example::

            SELECT AIAN8 AS AddressNumber, AICO AS Company, AIOPY AS OpenAmount
            FROM PRODDTA.F03012
            WHERE AIOPY > 1000
            ORDER BY AIOPY DESC

        max_rows: Optional maximum number of rows to return.
        query_timeout: Optional timeout string for the query execution.

    Returns:
        A dict with the following shape::

            {
                "rows": [ ... ],      # parsed list of row dicts
                "row_count": <int>,   # number of rows returned
                "raw": { ... }        # full original orchestrator response
            }

        If the query fails validation, returns::

            { "error": "<reason>", "rows": [], "row_count": 0 }
    """

    # ── SQL safety guard ──
    error = validate_select_only(query)
    if error:
        return {"error": error, "rows": [], "row_count": 0}

    # ── Table allowlist guard ──
    error = validate_allowed_tables(query)
    if error:
        return {"error": error, "rows": [], "row_count": 0}

    # ── Build payload ──
    # NOTE: ORCH_55_RunSQL is not published/shared on the JDV920 server; the
    # SQL-passthrough orchestration that IS shared to this user is
    # ORC_2607030001CUST (accepts username/password/environment/Query and
    # returns rows under ConnectorRequest1.rows). Override with
    # JDE_SQL_ORCHESTRATION if a differently-named orchestration is published.
    orchestration = os.getenv("JDE_SQL_ORCHESTRATION", "ORC_2607030001CUST")
    url = f"{BASE_URL}/jderest/orchestrator/{orchestration}"

    payload: dict = {
        "username": USERNAME,
        "password": PASSWORD,
        "environment": ENVIRONMENT,
        "Query": query,
    }

    if max_rows is not None:
        payload["maxRows"] = max_rows
    if query_timeout is not None:
        payload["queryTimeout"] = query_timeout

    # ── Call the orchestrator ──
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )

        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        # Server returned a non-2xx status (e.g. 500).
        body = None
        try:
            body = exc.response.json()
        except Exception:
            body = exc.response.text
        return {
            "error": f"JDE server returned {exc.response.status_code}: {exc.response.reason_phrase}",
            "server_response": body,
            "rows": [],
            "row_count": 0,
        }
    except httpx.HTTPError as exc:
        # Connection / timeout errors.
        return {
            "error": f"HTTP request failed: {exc}",
            "rows": [],
            "row_count": 0,
        }

    raw = response.json()

    # ── Parse the (potentially double-encoded) row data ──
    #
    # The orchestrator may return rows in different shapes:
    #   • returnMap.rows  — a JSON-encoded string (Groovy JsonOutput.toJson)
    #   • ConnectorRequest1.rows — a plain list of dicts
    # We try known locations first, then fall back to scanning top-level keys.
    rows: list = []
    try:
        rows_field = None

        # 1. Try returnMap.rows (may be double-encoded).
        return_map = raw.get("returnMap")
        if return_map is not None:
            if isinstance(return_map, str):
                return_map = json.loads(return_map)
            if isinstance(return_map, dict):
                rows_field = return_map.get("rows")

        # 2. Try ConnectorRequest1.rows (plain list).
        if rows_field is None:
            connector = raw.get("ConnectorRequest1")
            if isinstance(connector, dict):
                rows_field = connector.get("rows")

        # 3. Fallback: scan all top-level values for a dict with a "rows" key.
        if rows_field is None:
            for value in raw.values():
                if isinstance(value, dict) and "rows" in value:
                    rows_field = value["rows"]
                    break

        # Parse rows_field into a list.
        if isinstance(rows_field, str):
            rows = json.loads(rows_field)
        elif isinstance(rows_field, list):
            rows = rows_field
    except (json.JSONDecodeError, TypeError, AttributeError):
        # If anything goes wrong during parsing, return the raw response
        # so the caller can still inspect it.
        return {"rows": [], "row_count": 0, "raw": raw}

    return {"rows": rows, "row_count": len(rows), "raw": raw}


