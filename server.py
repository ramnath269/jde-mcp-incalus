import logging
from mcp.server.fastmcp import FastMCP
from jde import (
    get_token,
    customer_ledger_inquiry,
    run_sql_query_with_validation,
)

logger = logging.getLogger(__name__)
from jde_utils import get_allowed_tables_description
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Mount, Route
from auth.routes.oauth_routes import (
    oauth_callback,
    oauth_login,
)
from starlette.middleware import Middleware
import uvicorn
from mcp.server.auth.settings import AuthSettings
from tools import (
    # F0101 — Address Book Master
    jde_address_book_lookup as _address_book_lookup,
    jde_address_book_search_by_name as _address_book_search_by_name,
    jde_address_book_by_search_type as _address_book_by_search_type,
    jde_address_book_by_category_code as _address_book_by_category_code,
    # F03012 — Customer Master / AR & Credit
    jde_customer_credit_profile as _customer_credit_profile,
    jde_customer_credit_hold_check as _customer_credit_hold_check,
    # F03B11 — Customer Ledger / AR Invoices
    jde_customer_aging_analysis as _customer_aging_analysis,
    jde_customer_outstanding_balance as _customer_outstanding_balance,
    jde_customer_past_due_invoices as _customer_past_due_invoices,
    jde_customer_documents_by_type as _customer_documents_by_type,
    jde_invoice_lookup as _invoice_lookup,
    jde_invoices_due_in_range as _invoices_due_in_range,
    # F03B14 — Receipts Detail / Cash Application
    jde_customer_receipts as _customer_receipts,
    jde_unapplied_cash as _unapplied_cash,
    jde_customer_payment_summary as _customer_payment_summary,
    jde_receipt_type_distribution as _receipt_type_distribution,
    jde_writeoffs_chargebacks_deductions as _writeoffs_chargebacks_deductions,
    jde_nsf_receipts as _nsf_receipts,
    jde_receipts_in_range as _receipts_in_range,
    # F4211 — Sales Order Detail
    jde_customer_sales_summary as _customer_sales_summary,
    jde_customer_sales_detail as _customer_sales_detail,
    jde_sales_by_period as _sales_by_period,
    jde_top_customers as _top_customers,
    jde_customer_order_count as _customer_order_count,
    jde_backorder_report as _backorder_report,
    jde_order_status as _order_status,
    # Cross-table orchestration
    jde_resolve_customer_by_name as _resolve_customer_by_name,
    jde_customer_360 as _customer_360,
    # F4311 — Purchase Order schema metadata
    list_po_tables as _list_po_tables,
    get_table_schema as _get_table_schema,
    get_column as _get_column,
    find_columns as _find_columns,
    list_decimal_columns as _list_decimal_columns,
    list_date_columns as _list_date_columns,
    build_select as _build_select,
    julian_to_date as _julian_to_date,
    date_to_julian as _date_to_julian,
)
from auth.dependencies import provider

auth_settings = AuthSettings(
    issuer_url="https://aoctest.webine3.com/aoc-mcp",
    resource_server_url="https://aoctest.webine3.com/aoc-mcp",
    required_scopes=["mcp"],
)

# token_verifier = ProviderTokenVerifier(provider)

logger.info(
    "Initializing FastMCP server",
    extra={"server_name": "JD Edwards MCP Incalus", "host": "0.0.0.0", "port": 8005},
)
mcp = FastMCP(
    "JD Edwards MCP Incalus",
    host="0.0.0.0",
    port=8005,
    auth_server_provider=provider,
    auth=auth_settings,
    mount_path="/",
    streamable_http_path="/"
)

# ── Existing tools (unchanged) ──────────────────────────────────────────

@mcp.tool()
async def jde_get_token() -> dict:
    """Authenticate with JD Edwards AIS and return a session token."""
    logger.info("Tool called: jde_get_token")
    result = await get_token()
    logger.debug("jde_get_token completed", extra={"result_keys": list(result.keys()) if isinstance(result, dict) else None})
    return result

@mcp.tool()
async def jde_customer_ledger_inquiry(address_number: str) -> dict:
    """
    Retrieve customer open invoice and payment details from JD Edwards.

    Takes a Customer Address Number and returns all open invoices with:
    InvoiceDate, GrossAmount, Open Amount, DueDate, CustomerNumber,
    OriginalDocument, OrigDocType, SalesOrderNumber, CatCd1, Reference,
    DaysPastDue, BusinessUnit, CustomerDesc, DocumentTypeSalesOrder,
    and CategoryCode1Desc.

    The tool automatically handles AIS authentication internally.
    """
    logger.info("Tool called: jde_customer_ledger_inquiry", extra={"address_number": address_number})
    result = await customer_ledger_inquiry(address_number)
    logger.debug("jde_customer_ledger_inquiry completed", extra={"address_number": address_number})
    return result

# Build the SQL tool description dynamically so it always reflects _ALLOWED_TABLES.
_SQL_TOOL_DOC = f"""\
Execute a read-only SQL query against the JD Edwards database.

Runs any SELECT query via the RunSQLQueryWithValidation orchestrator
on the test server. DML / DDL statements are rejected before reaching
the server, and queries may only reference an allowlisted set of tables:
{get_allowed_tables_description()}.
Any query touching another table is rejected.

Args:
    query: A SQL SELECT statement. Example:
        SELECT AIAN8 AS AddressNumber, AICO AS Company, AIOPY AS OpenAmount
        FROM PRODDTA.F03012
        WHERE AIOPY > 1000
        ORDER BY AIOPY DESC
    max_rows: Optional cap on the number of rows returned.
    query_timeout: Optional timeout for query execution.

Returns a dict with keys: rows, row_count, and raw.
If the query fails validation, returns an error dict instead.
"""


@mcp.tool(description=_SQL_TOOL_DOC)
async def jde_run_sql_query(
    query: str,
    max_rows: int | None = None,
    query_timeout: str | None = None,
) -> dict:
    logger.info("Tool called: jde_run_sql_query", extra={"query": query[:100], "max_rows": max_rows, "query_timeout": query_timeout})
    result = await run_sql_query_with_validation(query, max_rows, query_timeout)
    logger.debug("jde_run_sql_query completed", extra={"row_count": result.get("row_count") if isinstance(result, dict) else None})
    return result


# ── F0101 — Address Book Master (4 tools) ───────────────────────────────

@mcp.tool()
async def jde_address_book_lookup(
    address_number: int,
    fields: str = "summary",
    schema_override: str | None = None,
) -> dict:
    """Look up the profile for a JDE address number.

    Table: F0101 — Address Book Master.

    Returns name, search type, business unit, tax IDs, and more.
    Use fields='full' for the complete profile including DUNS, stock
    ticker, employee count, and growth rate.

    Args:
        address_number: The JDE Address Number (AN8) to look up.
        fields: Detail level — "summary" (default) or "full".
        schema_override: Optional schema name override.
    """
    logger.info("Tool called: jde_address_book_lookup", extra={"address_number": address_number, "fields": fields})
    result = await _address_book_lookup(address_number, fields, schema_override)
    logger.debug("jde_address_book_lookup completed", extra={"address_number": address_number})
    return result

@mcp.tool()
async def jde_address_book_search_by_name(
    name_pattern: str,
    max_rows: int = 100,
    schema_override: str | None = None,
) -> dict:
    """Search the JDE Address Book by name (partial match).

    Table: F0101 — Address Book Master.

    Finds address entries whose name contains the search pattern.
    Returns address number, name, search type, and description.

    Args:
        name_pattern: Full or partial name to search for.
        max_rows: Maximum results to return (default 100).
        schema_override: Optional schema name override.
    """
    logger.info("Tool called: jde_address_book_search_by_name", extra={"name_pattern": name_pattern, "max_rows": max_rows})
    result = await _address_book_search_by_name(name_pattern, max_rows, schema_override)
    logger.debug("jde_address_book_search_by_name completed", extra={"name_pattern": name_pattern})
    return result

@mcp.tool()
async def jde_address_book_by_search_type(
    search_type: str,
    max_rows: int = 100,
    schema_override: str | None = None,
) -> dict:
    """List addresses by type from the JDE Address Book.

    Table: F0101 — Address Book Master.

    Common types: C = Customer, S = Supplier, V = Employee, E = Employee.

    Args:
        search_type: Single-character type code (e.g. "C" for Customer).
        max_rows: Maximum results to return (default 100).
        schema_override: Optional schema name override.
    """
    logger.info("Tool called: jde_address_book_by_search_type", extra={"search_type": search_type, "max_rows": max_rows})
    result = await _address_book_by_search_type(search_type, max_rows, schema_override)
    logger.debug("jde_address_book_by_search_type completed", extra={"search_type": search_type})
    return result

@mcp.tool()
async def jde_address_book_by_category_code(
    category_code: str,
    value: str,
    max_rows: int = 100,
    schema_override: str | None = None,
) -> dict:
    """Filter the JDE Address Book by a category code (AC01–AC30).

    Table: F0101 — Address Book Master.

    Args:
        category_code: Category code to filter (e.g. "AC01", "AC15").
        value: The value to match for that category code.
        max_rows: Maximum results to return (default 100).
        schema_override: Optional schema name override.
    """
    logger.info("Tool called: jde_address_book_by_category_code", extra={"category_code": category_code, "value": value, "max_rows": max_rows})
    result = await _address_book_by_category_code(category_code, value, max_rows, schema_override)
    logger.debug("jde_address_book_by_category_code completed", extra={"category_code": category_code, "value": value})
    return result


# ── F03012 — Customer Master / AR & Credit (2 tools) ────────────────────

@mcp.tool()
async def jde_customer_credit_profile(
    address_number: int,
    company: str | None = None,
    fields: str = "summary",
    schema_override: str | None = None,
) -> dict:
    """Credit profile for a JDE customer: credit limit, open amount,
    balance, credit-hold status, and payment terms.

    Table: F03012 — Customer Master.

    If no company is specified, returns all lines of business for the customer.
    Use fields='full' for DSO, credit/collection manager, and more.

    Args:
        address_number: Customer Address Number (AN8).
        company: Optional company code for one line of business.
        fields: Detail level — "summary" (default) or "full".
        schema_override: Optional schema name override.
    """
    logger.info("Tool called: jde_customer_credit_profile", extra={"address_number": address_number, "company": company, "fields": fields})
    result = await _customer_credit_profile(address_number, company, fields, schema_override)
    logger.debug("jde_customer_credit_profile completed", extra={"address_number": address_number})
    return result

@mcp.tool()
async def jde_customer_credit_hold_check(
    address_number: int,
    company: str | None = None,
    schema_override: str | None = None,
) -> dict:
    """Quick check whether a JDE customer is on credit hold.

    Table: F03012 — Customer Master.

    Returns the credit-hold flag and hold code with a human-readable
    status ("On credit hold" or "No hold").

    Args:
        address_number: Customer Address Number (AN8).
        company: Optional company code.
        schema_override: Optional schema name override.
    """
    logger.info("Tool called: jde_customer_credit_hold_check", extra={"address_number": address_number, "company": company})
    result = await _customer_credit_hold_check(address_number, company, schema_override)
    logger.debug("jde_customer_credit_hold_check completed", extra={"address_number": address_number})
    return result


# ── F03B11 — Customer Ledger / AR Invoices (6 tools) ────────────────────

@mcp.tool()
async def jde_customer_aging_analysis(
    address_number: int,
    schema_override: str | None = None,
) -> dict:
    """Accounts Receivable aging analysis for a JDE customer.

    Table: F03B11 — Customer Ledger.

    Groups open invoices into aging buckets (Current, 1–30 Days,
    31–60 Days, 61–90 Days, 90+ Days) by due date with counts and amounts.

    Args:
        address_number: Customer Address Number (AN8).
        schema_override: Optional schema name override.
    """
    logger.info("Tool called: jde_customer_aging_analysis", extra={"address_number": address_number})
    result = await _customer_aging_analysis(address_number, schema_override)
    logger.debug("jde_customer_aging_analysis completed", extra={"address_number": address_number})
    return result

@mcp.tool()
async def jde_customer_outstanding_balance(
    address_number: int,
    schema_override: str | None = None,
) -> dict:
    """Total open A/R balance for a JDE customer.

    Table: F03B11 — Customer Ledger.

    Returns open invoice count, total gross and open amounts, earliest and
    latest due dates, and currency code — all in one summary row.

    Args:
        address_number: Customer Address Number (AN8).
        schema_override: Optional schema name override.
    """
    logger.info("Tool called: jde_customer_outstanding_balance", extra={"address_number": address_number})
    result = await _customer_outstanding_balance(address_number, schema_override)
    logger.debug("jde_customer_outstanding_balance completed", extra={"address_number": address_number})
    return result

@mcp.tool()
async def jde_customer_past_due_invoices(
    address_numbers: list[int] | None = None,
    min_days_past_due: int = 1,
    max_rows: int = 100,
    schema_override: str | None = None,
) -> dict:
    """Past-due open invoices with days past due.

    Table: F03B11 — Customer Ledger.

    Returns only invoices whose due date has passed, sorted by most
    overdue first. Results include the AddressNumber column so invoices
    from multiple customers can be distinguished. If no address numbers are
    supplied, runs across all customers rather than requiring one.

    Args:
        address_numbers: Optional list of Customer Address Numbers (AN8). Omit
            or pass an empty list to include all customers.
        min_days_past_due: Minimum days past due to include (default 1). Use
            e.g. 30 for "more than 30 days past due".
        max_rows: Maximum invoices to return (default 100).
        schema_override: Optional schema name override.
    """
    logger.info("Tool called: jde_customer_past_due_invoices", extra={
        "address_numbers_count": len(address_numbers) if address_numbers else 0,
        "min_days_past_due": min_days_past_due,
        "max_rows": max_rows,
    })
    result = await _customer_past_due_invoices(
        address_numbers, min_days_past_due, max_rows, schema_override
    )
    logger.debug("jde_customer_past_due_invoices completed")
    return result

@mcp.tool()
async def jde_customer_documents_by_type(
    address_number: int,
    schema_override: str | None = None,
) -> dict:
    """Document type breakdown for a JDE customer's open A/R items.

    Table: F03B11 — Customer Ledger.

    Groups open items by type (Invoice, Credit Memo, Chargeback, etc.)
    with counts and amounts per type.

    Args:
        address_number: Customer Address Number (AN8).
        schema_override: Optional schema name override.
    """
    logger.info("Tool called: jde_customer_documents_by_type", extra={"address_number": address_number})
    result = await _customer_documents_by_type(address_number, schema_override)
    logger.debug("jde_customer_documents_by_type completed", extra={"address_number": address_number})
    return result

@mcp.tool()
async def jde_invoice_lookup(
    document_number: int,
    document_type: str,
    document_company: str,
    schema_override: str | None = None,
) -> dict:
    """Look up a specific invoice or document in JDE by its composite key.

    Table: F03B11 — Customer Ledger.

    Returns full detail including pay items, dates, amounts, and status.

    Args:
        document_number: Document number (DOC).
        document_type: Document type code (e.g. "RI" for Standard Invoice).
        document_company: Document company key (KCO).
        schema_override: Optional schema name override.
    """
    logger.info("Tool called: jde_invoice_lookup", extra={
        "document_number": document_number,
        "document_type": document_type,
        "document_company": document_company,
    })
    result = await _invoice_lookup(document_number, document_type, document_company, schema_override)
    logger.debug("jde_invoice_lookup completed", extra={"document_number": document_number})
    return result

@mcp.tool()
async def jde_invoices_due_in_range(
    address_number: int,
    start_date: str,
    end_date: str,
    max_rows: int = 100,
    schema_override: str | None = None,
) -> dict:
    """Open invoices due within a date range for a JDE customer.

    Table: F03B11 — Customer Ledger.

    Args:
        address_number: Customer Address Number (AN8).
        start_date: Range start (ISO YYYY-MM-DD).
        end_date: Range end (ISO YYYY-MM-DD).
        max_rows: Maximum invoices to return (default 100).
        schema_override: Optional schema name override.
    """
    logger.info("Tool called: jde_invoices_due_in_range", extra={
        "address_number": address_number,
        "start_date": start_date,
        "end_date": end_date,
        "max_rows": max_rows,
    })
    result = await _invoices_due_in_range(address_number, start_date, end_date, max_rows, schema_override)
    logger.debug("jde_invoices_due_in_range completed", extra={"address_number": address_number})
    return result


# ── F03B14 — Receipts Detail / Cash Application (7 tools) ──────────────

@mcp.tool()
async def jde_customer_receipts(
    address_number: int,
    receipt_type: str | None = None,
    max_rows: int = 100,
    schema_override: str | None = None,
) -> dict:
    """Posted receipts for a JDE customer, with optional type filter.

    Table: F03B14 — Receipts Detail.

    Receipt types: U = Unapplied Cash, A = Applied, C = Chargeback,
    D = Deduction, N = NSF, V = Void.

    Args:
        address_number: Customer Address Number (AN8).
        receipt_type: Optional receipt type filter (U/A/C/D/N/V).
        max_rows: Maximum receipts to return (default 100).
        schema_override: Optional schema name override.
    """
    logger.info("Tool called: jde_customer_receipts", extra={
        "address_number": address_number,
        "receipt_type": receipt_type,
        "max_rows": max_rows,
    })
    result = await _customer_receipts(address_number, receipt_type, max_rows, schema_override)
    logger.debug("jde_customer_receipts completed", extra={"address_number": address_number})
    return result

@mcp.tool()
async def jde_unapplied_cash(
    address_number: int,
    max_rows: int = 100,
    schema_override: str | None = None,
) -> dict:
    """Open unapplied cash receipts for a JDE customer.

    Table: F03B14 — Receipts Detail.

    Returns receipts that have been received but not yet applied
    to specific invoices.

    Args:
        address_number: Customer Address Number (AN8).
        max_rows: Maximum receipts to return (default 100).
        schema_override: Optional schema name override.
    """
    logger.info("Tool called: jde_unapplied_cash", extra={"address_number": address_number, "max_rows": max_rows})
    result = await _unapplied_cash(address_number, max_rows, schema_override)
    logger.debug("jde_unapplied_cash completed", extra={"address_number": address_number})
    return result

@mcp.tool()
async def jde_customer_payment_summary(
    address_number: int,
    schema_override: str | None = None,
) -> dict:
    """Payment summary totals for a JDE customer.

    Table: F03B14 — Receipts Detail.

    Returns aggregate totals: receipt count, total payments, discounts,
    write-offs, chargebacks, deductions, and the date range covered.

    Args:
        address_number: Customer Address Number (AN8).
        schema_override: Optional schema name override.
    """
    logger.info("Tool called: jde_customer_payment_summary", extra={"address_number": address_number})
    result = await _customer_payment_summary(address_number, schema_override)
    logger.debug("jde_customer_payment_summary completed", extra={"address_number": address_number})
    return result

@mcp.tool()
async def jde_receipt_type_distribution(
    address_number: int,
    schema_override: str | None = None,
) -> dict:
    """Receipt type distribution for a JDE customer.

    Table: F03B14 — Receipts Detail.

    Breaks down posted receipts by type (Applied, Unapplied, Chargeback,
    Deduction, NSF, Void) with counts and amounts — useful for pie charts.

    Args:
        address_number: Customer Address Number (AN8).
        schema_override: Optional schema name override.
    """
    logger.info("Tool called: jde_receipt_type_distribution", extra={"address_number": address_number})
    result = await _receipt_type_distribution(address_number, schema_override)
    logger.debug("jde_receipt_type_distribution completed", extra={"address_number": address_number})
    return result

@mcp.tool()
async def jde_writeoffs_chargebacks_deductions(
    address_number: int,
    adjustment_type: str = "all",
    max_rows: int = 100,
    schema_override: str | None = None,
) -> dict:
    """Adjustment detail for a JDE customer: write-offs, chargebacks,
    and/or deductions with reason codes.

    Table: F03B14 — Receipts Detail.

    Args:
        address_number: Customer Address Number (AN8).
        adjustment_type: Filter — "writeoff", "chargeback", "deduction",
            or "all" (default).
        max_rows: Maximum results to return (default 100).
        schema_override: Optional schema name override.
    """
    logger.info("Tool called: jde_writeoffs_chargebacks_deductions", extra={
        "address_number": address_number,
        "adjustment_type": adjustment_type,
        "max_rows": max_rows,
    })
    result = await _writeoffs_chargebacks_deductions(address_number, adjustment_type, max_rows, schema_override)
    logger.debug("jde_writeoffs_chargebacks_deductions completed", extra={"address_number": address_number})
    return result

@mcp.tool()
async def jde_nsf_receipts(
    address_number: int,
    schema_override: str | None = None,
) -> dict:
    """Non-sufficient-funds (NSF) receipts for a JDE customer.

    Table: F03B14 — Receipts Detail.

    Returns receipts flagged as NSF with payment amount, void date,
    and reason code.

    Args:
        address_number: Customer Address Number (AN8).
        schema_override: Optional schema name override.
    """
    logger.info("Tool called: jde_nsf_receipts", extra={"address_number": address_number})
    result = await _nsf_receipts(address_number, schema_override)
    logger.debug("jde_nsf_receipts completed", extra={"address_number": address_number})
    return result

@mcp.tool()
async def jde_receipts_in_range(
    address_number: int,
    start_date: str,
    end_date: str,
    max_rows: int = 100,
    schema_override: str | None = None,
) -> dict:
    """Posted receipts within a G/L date window for a JDE customer.

    Table: F03B14 — Receipts Detail.

    Args:
        address_number: Customer Address Number (AN8).
        start_date: Range start (ISO YYYY-MM-DD).
        end_date: Range end (ISO YYYY-MM-DD).
        max_rows: Maximum receipts to return (default 100).
        schema_override: Optional schema name override.
    """
    logger.info("Tool called: jde_receipts_in_range", extra={
        "address_number": address_number,
        "start_date": start_date,
        "end_date": end_date,
        "max_rows": max_rows,
    })
    result = await _receipts_in_range(address_number, start_date, end_date, max_rows, schema_override)
    logger.debug("jde_receipts_in_range completed", extra={"address_number": address_number})
    return result


# ── F4211 — Sales Order Detail (7 tools) ────────────────────────────────

@mcp.tool()
async def jde_customer_sales_summary(
    customer_number: int,
    start_date: str | None = None,
    end_date: str | None = None,
    schema_override: str | None = None,
) -> dict:
    """Sales summary for a JDE customer over a period.

    Table: F4211 — Sales Order Detail.

    Returns total amount, quantity, order count, and line count.
    Defaults to the last 30 days if no dates are given.

    Args:
        customer_number: Customer Address Number (AN8).
        start_date: Period start (ISO YYYY-MM-DD, default: 30 days ago).
        end_date: Period end (ISO YYYY-MM-DD, default: today).
        schema_override: Optional schema name override.
    """
    logger.info("Tool called: jde_customer_sales_summary", extra={
        "customer_number": customer_number,
        "start_date": start_date,
        "end_date": end_date,
    })
    result = await _customer_sales_summary(customer_number, start_date, end_date, schema_override)
    logger.debug("jde_customer_sales_summary completed", extra={"customer_number": customer_number})
    return result

@mcp.tool()
async def jde_customer_sales_detail(
    customer_number: int,
    start_date: str | None = None,
    end_date: str | None = None,
    max_rows: int = 100,
    schema_override: str | None = None,
) -> dict:
    """Line-level sales order detail for a JDE customer.

    Table: F4211 — Sales Order Detail.

    Returns individual order lines with item, description, quantities,
    unit price, extended amount, dates, and status codes.

    Args:
        customer_number: Customer Address Number (AN8).
        start_date: Period start (ISO YYYY-MM-DD, default: 30 days ago).
        end_date: Period end (ISO YYYY-MM-DD, default: today).
        max_rows: Maximum lines to return (default 100).
        schema_override: Optional schema name override.
    """
    logger.info("Tool called: jde_customer_sales_detail", extra={
        "customer_number": customer_number,
        "start_date": start_date,
        "end_date": end_date,
        "max_rows": max_rows,
    })
    result = await _customer_sales_detail(customer_number, start_date, end_date, max_rows, schema_override)
    logger.debug("jde_customer_sales_detail completed", extra={"customer_number": customer_number})
    return result

@mcp.tool()
async def jde_sales_by_period(
    start_date: str,
    end_date: str,
    customer_number: int | None = None,
    max_rows: int = 100,
    schema_override: str | None = None,
) -> dict:
    """Sales totals by customer within a date range.

    Table: F4211 — Sales Order Detail.

    Returns per-customer totals: amount, quantity, order count, and
    line count. Optionally filter to a single customer.

    Args:
        start_date: Period start (ISO YYYY-MM-DD).
        end_date: Period end (ISO YYYY-MM-DD).
        customer_number: Optional customer filter (AN8).
        max_rows: Maximum rows to return (default 100).
        schema_override: Optional schema name override.
    """
    logger.info("Tool called: jde_sales_by_period", extra={
        "start_date": start_date,
        "end_date": end_date,
        "customer_number": customer_number,
        "max_rows": max_rows,
    })
    result = await _sales_by_period(start_date, end_date, customer_number, max_rows, schema_override)
    logger.debug("jde_sales_by_period completed")
    return result

@mcp.tool()
async def jde_top_customers(
    start_date: str | None = None,
    end_date: str | None = None,
    top_n: int = 10,
    schema_override: str | None = None,
) -> dict:
    """Top-N customers ranked by sales amount over a period.

    Table: F4211 — Sales Order Detail.

    Args:
        start_date: Period start (ISO YYYY-MM-DD, default: 30 days ago).
        end_date: Period end (ISO YYYY-MM-DD, default: today).
        top_n: Number of top customers to return (default 10).
        schema_override: Optional schema name override.
    """
    logger.info("Tool called: jde_top_customers", extra={"start_date": start_date, "end_date": end_date, "top_n": top_n})
    result = await _top_customers(start_date, end_date, top_n, schema_override)
    logger.debug("jde_top_customers completed")
    return result

@mcp.tool()
async def jde_customer_order_count(
    customer_number: int,
    start_date: str | None = None,
    end_date: str | None = None,
    schema_override: str | None = None,
) -> dict:
    """Distinct order count for a JDE customer over a period.

    Table: F4211 — Sales Order Detail.

    Args:
        customer_number: Customer Address Number (AN8).
        start_date: Period start (ISO YYYY-MM-DD, default: 30 days ago).
        end_date: Period end (ISO YYYY-MM-DD, default: today).
        schema_override: Optional schema name override.
    """
    logger.info("Tool called: jde_customer_order_count", extra={
        "customer_number": customer_number,
        "start_date": start_date,
        "end_date": end_date,
    })
    result = await _customer_order_count(customer_number, start_date, end_date, schema_override)
    logger.debug("jde_customer_order_count completed", extra={"customer_number": customer_number})
    return result

@mcp.tool()
async def jde_backorder_report(
    customer_number: int,
    max_rows: int = 100,
    schema_override: str | None = None,
) -> dict:
    """Backordered lines for a JDE customer.

    Table: F4211 — Sales Order Detail.

    Returns sales order lines with backorder quantity greater than zero,
    sorted by requested date and order number.

    Args:
        customer_number: Customer Address Number (AN8).
        max_rows: Maximum lines to return (default 100).
        schema_override: Optional schema name override.
    """
    logger.info("Tool called: jde_backorder_report", extra={"customer_number": customer_number, "max_rows": max_rows})
    result = await _backorder_report(customer_number, max_rows, schema_override)
    logger.debug("jde_backorder_report completed", extra={"customer_number": customer_number})
    return result

@mcp.tool()
async def jde_order_status(
    order_number: int,
    order_type: str,
    order_company: str,
    schema_override: str | None = None,
) -> dict:
    """Line-level status for a specific JDE sales order.

    Table: F4211 — Sales Order Detail.

    Returns each line with item details, quantities (ordered, shipped,
    backordered, open), and status codes.

    Args:
        order_number: Order number (DOCO).
        order_type: Order type code (e.g. "SO").
        order_company: Order company key (KCOO).
        schema_override: Optional schema name override.
    """
    logger.info("Tool called: jde_order_status", extra={
        "order_number": order_number,
        "order_type": order_type,
        "order_company": order_company,
    })
    result = await _order_status(order_number, order_type, order_company, schema_override)
    logger.debug("jde_order_status completed", extra={"order_number": order_number})
    return result


# ── Cross-table orchestration (2 tools) ─────────────────────────────────

@mcp.tool()
async def jde_resolve_customer_by_name(
    name_pattern: str,
    search_type: str = "C",
    max_rows: int = 10,
    schema_override: str | None = None,
) -> dict:
    """Resolve a customer name to JDE address number(s).

    Table: F0101 — Address Book Master.

    Most JDE tools require an Address Number (AN8) but users know the
    customer name. This tool searches by name and returns matching
    candidates with their address numbers.

    Args:
        name_pattern: Full or partial customer name to search.
        search_type: Address type code (default "C" = Customer).
        max_rows: Maximum candidates to return (default 10).
        schema_override: Optional schema name override.
    """
    logger.info("Tool called: jde_resolve_customer_by_name", extra={
        "name_pattern": name_pattern,
        "search_type": search_type,
        "max_rows": max_rows,
    })
    result = await _resolve_customer_by_name(name_pattern, search_type, max_rows, schema_override)
    logger.debug("jde_resolve_customer_by_name completed", extra={"name_pattern": name_pattern})
    return result

@mcp.tool()
async def jde_customer_360(
    address_number: int,
    company: str | None = None,
    schema_override: str | None = None,
) -> dict:
    """Complete 360-degree customer snapshot from JDE.

    Tables: F0101, F03012, F03B11, F03B14, F4211 (cross-table).

    One call returns a consolidated view across all modules:
    identity (Address Book), credit profile (Customer Master),
    outstanding A/R balance and aging (Customer Ledger),
    payment history (Receipts), and trailing 12-month sales (Sales Orders).

    Args:
        address_number: Customer Address Number (AN8).
        company: Optional company code for credit filtering.
        schema_override: Optional schema name override.
    """
    logger.info("Tool called: jde_customer_360", extra={"address_number": address_number, "company": company})
    result = await _customer_360(address_number, company, schema_override)
    logger.debug("jde_customer_360 completed", extra={"address_number": address_number})
    return result


# ── F4311 — Purchase Order schema metadata (7 tools + 2 helpers) ─────────
#
# Metadata-only: these tools never touch the database. They serve exact JDE
# column metadata (type, length, implied decimals, Julian-date format) so an
# agent resolves a real column here, then runs the query with the live JDE data
# tools. Column data is loaded from data/*.json (override with JDE_SCHEMA_DIR).

@mcp.tool()
def jde_po_list_tables() -> list[dict]:
    """List loaded JDE purchase-order tables (name, description, prefix, key).

    The entry point when you do not yet know which JDE table holds a field.
    Metadata only — pair with the live JDE data tools to actually query rows.
    """
    logger.info("Tool called: jde_po_list_tables")
    result = _list_po_tables()
    logger.debug("jde_po_list_tables completed", extra={"table_count": len(result)})
    return result

@mcp.tool()
def jde_po_get_table_schema(table: str, include_glossary: bool = False) -> dict:
    """Full column list + keys for a JDE PO table (e.g. F4311).

    Returns every column's field, data item, description, data type, length,
    and decimals. Glossary text is omitted unless include_glossary=True.
    Unknown table raises an error listing the tables that are loaded.

    Args:
        table: Table name, e.g. "F4311".
        include_glossary: Include per-column glossary text when True.
    """
    logger.info("Tool called: jde_po_get_table_schema", extra={"table": table, "include_glossary": include_glossary})
    result = _get_table_schema(table, include_glossary)
    logger.debug("jde_po_get_table_schema completed", extra={"table": table})
    return result

@mcp.tool()
def jde_po_get_column(field: str, table: str = "") -> dict:
    """Look up one JDE column in full — accepts PDUORG or UORG form.

    Returns type, length, implied decimals, glossary, and which table matched.
    With table empty, searches every loaded table. Unknown field raises an
    error suggesting jde_po_find_columns. Use this before writing SQL so you
    never guess a column name or its scale.

    Args:
        field: Column name, prefixed (PDUORG) or data-item (UORG) form.
        table: Optional table to restrict the search to.
    """
    logger.info("Tool called: jde_po_get_column", extra={"field": field, "table": table})
    result = _get_column(field, table)
    logger.debug("jde_po_get_column completed", extra={"field": field})
    return result

@mcp.tool()
def jde_po_find_columns(
    query: str, table: str = "F4311", limit: int = 25
) -> list[dict]:
    """Keyword-search JDE PO columns by name/description ("open", "supplier").

    How you get from a concept to a real column name. Every whitespace token in
    query must appear in the field name, data item, or description.

    Args:
        query: One or more keywords.
        table: Table to search (default "F4311").
        limit: Maximum matches to return (default 25).
    """
    logger.info("Tool called: jde_po_find_columns", extra={"query": query, "table": table, "limit": limit})
    result = _find_columns(query, table, limit)
    logger.debug("jde_po_find_columns completed", extra={"match_count": len(result)})
    return result

@mcp.tool()
def jde_po_list_decimal_columns(table: str = "F4311") -> dict:
    """List JDE columns with implied decimals + the divisor to display them.

    Each entry carries divide_by_to_get_display_value = 10 ** decimals, plus a
    warning that the scaling MUST be verified against a known order before you
    trust a SUM — the value may be stored unscaled. Read this before doing
    arithmetic on any cost/amount/quantity column.

    Args:
        table: Table to inspect (default "F4311").
    """
    logger.info("Tool called: jde_po_list_decimal_columns", extra={"table": table})
    result = _list_decimal_columns(table)
    logger.debug("jde_po_list_decimal_columns completed", extra={"table": table})
    return result

@mcp.tool()
def jde_po_list_date_columns(table: str = "F4311") -> dict:
    """List JDE Julian date columns + HHMMSS time columns, with the format.

    Date columns are 6-digit Julian CYYDDD — never compare them to an ISO
    string. Includes the format explanation and a worked example. Time columns
    are a curated HHMMSS list (they cannot be inferred from column shape).

    Args:
        table: Table to inspect (default "F4311").
    """
    logger.info("Tool called: jde_po_list_date_columns", extra={"table": table})
    result = _list_date_columns(table)
    logger.debug("jde_po_list_date_columns completed", extra={"table": table})
    return result

@mcp.tool()
def jde_po_build_select(
    table: str = "F4311", fields: str = "", schema: str = "PRODDTA"
) -> str:
    """Build a validated SELECT skeleton for a JDE PO table.

    Every name in fields (comma-separated, PDUORG or UORG form) is validated
    against the real columns; an unknown one raises an error and NO SQL is
    emitted. Decimal columns are annotated with their implied scale; trailing
    comments carry the RTRIM (blank-padding) and Julian-date warnings. Empty
    fields defaults to the unique key. Prefer naming columns over SELECT *.

    Args:
        table: Table to select from (default "F4311").
        fields: Comma-separated column names; empty = the unique key.
        schema: Schema/owner to qualify the table with (default "PRODDTA").
    """
    logger.info("Tool called: jde_po_build_select", extra={"table": table, "fields": fields, "schema": schema})
    result = _build_select(table, fields, schema)
    logger.debug("jde_po_build_select completed", extra={"table": table, "fields": fields})
    return result

@mcp.tool()
def jde_po_julian_to_date(cyyddd: int) -> str:
    """Convert a JDE Julian integer (CYYDDD) to ISO YYYY-MM-DD.

    Example: 126195 -> "2026-07-14". Use when reading a JDE date column value.

    Args:
        cyyddd: JDE Julian date integer, e.g. 126195.
    """
    logger.info("Tool called: jde_po_julian_to_date", extra={"cyyddd": cyyddd})
    result = _julian_to_date(cyyddd)
    logger.debug("jde_po_julian_to_date completed", extra={"cyyddd": cyyddd, "result": result})
    return result

@mcp.tool()
def jde_po_date_to_julian(iso_date: str) -> int:
    """Convert an ISO YYYY-MM-DD date to a JDE Julian integer (CYYDDD).

    Example: "2026-07-14" -> 126195. Use to build a WHERE clause against a JDE
    Julian date column (never compare the column to an ISO string).

    Args:
        iso_date: ISO date string, e.g. "2026-07-14".
    """
    logger.info("Tool called: jde_po_date_to_julian", extra={"iso_date": iso_date})
    result = _date_to_julian(iso_date)
    logger.debug("jde_po_date_to_julian completed", extra={"iso_date": iso_date, "result": result})
    return result


# if __name__ == "__main__":
#     mcp.run(transport="streamable-http")
mcp_app=mcp.streamable_http_app()
app = Starlette(
    routes=[
        Route("/oauth/login", oauth_login, methods=["POST"]),
        Route("/oauth/callback", oauth_callback, methods=["GET"]),
        Mount("/", app=mcp_app),
    ],
    lifespan=mcp_app.router.lifespan_context,
    middleware=[
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Change to your React origin in production
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    ],
)

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8005,
    )