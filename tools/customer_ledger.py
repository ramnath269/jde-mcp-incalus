"""F03B11 Customer Ledger / AR invoice tools.

Provides aging analysis, outstanding balance, past-due invoices, document
type breakdown, invoice lookup, and date-range queries against the JDE
Customer Ledger (F03B11). Physical field prefix: RP (e.g. RPAN8, RPDOC).

Standard "open" filter: RPAG > 0 AND RPPOST = 'P' AND (RPVOD IS NULL OR RPVOD <> 'V').
Document types: RI = Invoice, RK = Credit Memo, RV = Receipt/Voucher,
                R5 = Deduction, RU = Chargeback.
"""

from jde import run_sql_query_with_validation
from jde_utils import (
    days_past_due_expr,
    escape_sql_string,
    format_result,
    format_single_result,
    get_schema,
    iso_to_jde_julian,
    julian_col_to_date,
    row_limit_clause,
    DOC_TYPE_LABELS,
)

# Standard filter for open, posted, non-voided items
_OPEN_FILTER = "RPAG > 0 AND RPPOST = 'P' AND (RPVOD IS NULL OR RPVOD <> 'V')"


async def jde_customer_aging_analysis(
    address_number: int,
    schema_override: str | None = None,
) -> dict:
    """Accounts Receivable aging analysis for a customer.

    Returns aging buckets (Current, 1–30 Days, 31–60 Days, 61–90 Days,
    90+ Days) with invoice count and total open/gross amounts per bucket.
    Uses the invoice due date to calculate days past due.

    Args:
        address_number: Customer Address Number (AN8).
        schema_override: Optional schema override.
    """
    schema = get_schema(schema_override)
    dpd = days_past_due_expr("RPDDJ")

    query = f"""
        SELECT
            CASE
                WHEN {dpd} <= 0  THEN 'Current'
                WHEN {dpd} <= 30 THEN '1-30 Days'
                WHEN {dpd} <= 60 THEN '31-60 Days'
                WHEN {dpd} <= 90 THEN '61-90 Days'
                ELSE '90+ Days'
            END AS AgingBucket,
            COUNT(*) AS InvoiceCount,
            SUM(RPAG) AS TotalOpenAmount,
            SUM(RPAAP) AS TotalGrossAmount
        FROM {schema}.F03B11
        WHERE RPAN8 = {address_number}
            AND {_OPEN_FILTER}
        GROUP BY
            CASE
                WHEN {dpd} <= 0  THEN 'Current'
                WHEN {dpd} <= 30 THEN '1-30 Days'
                WHEN {dpd} <= 60 THEN '31-60 Days'
                WHEN {dpd} <= 90 THEN '61-90 Days'
                ELSE '90+ Days'
            END
        ORDER BY MIN(RPDDJ) ASC
    """

    result = await run_sql_query_with_validation(query)
    return format_result(
        result,
        empty_message=f"No open invoices found for customer {address_number}.",
    )


async def jde_customer_outstanding_balance(
    address_number: int,
    schema_override: str | None = None,
) -> dict:
    """Total open A/R balance for a customer.

    Returns a single-row summary: open invoice count, total gross and open
    amounts, earliest and latest due dates, and currency code.

    Args:
        address_number: Customer Address Number (AN8).
        schema_override: Optional schema override.
    """
    schema = get_schema(schema_override)

    query = f"""
        SELECT RPAN8 AS AddressNumber, COUNT(*) AS OpenInvoiceCount,
               SUM(RPAAP) AS TotalGrossAmount, SUM(RPAG) AS TotalOpenAmount,
               MIN(RPDDJ) AS EarliestDueDate, MAX(RPDDJ) AS LatestDueDate,
               RPCRCD AS CurrencyCode
        FROM {schema}.F03B11
        WHERE RPAN8 = {address_number}
            AND {_OPEN_FILTER}
        GROUP BY RPAN8, RPCRCD
    """

    result = await run_sql_query_with_validation(query)
    return format_result(
        result,
        empty_message=f"No outstanding balance found for customer {address_number}.",
    )


async def jde_customer_past_due_invoices(
    address_numbers: list[int] | None = None,
    min_days_past_due: int = 1,
    max_rows: int = 100,
    schema_override: str | None = None,
) -> dict:
    """List past-due open invoices, with days past due.

    Returns only invoices whose due date is before today, sorted by most
    overdue first. Results include the AddressNumber column so invoices from
    multiple customers can be distinguished.

    If no address numbers are supplied, this runs across all customers rather
    than requiring a specific customer.

    Args:
        address_numbers: Optional list of Customer Address Numbers (AN8). Omit
            or pass an empty list to include all customers.
        min_days_past_due: Minimum days past due to include (default 1, i.e.
            any invoice past its due date). Use e.g. 30 for "more than 30 days".
        max_rows: Maximum number of invoices to return (default 100).
        schema_override: Optional schema override.
    """
    schema = get_schema(schema_override)
    dpd = days_past_due_expr("RPDDJ")
    due_date = julian_col_to_date("RPDDJ")
    inv_date = julian_col_to_date("RPDIVJ")

    # Only filter by customer when address numbers are supplied. Coerce to ints
    # to keep the IN-list injection-safe.
    if address_numbers:
        an8_list = ", ".join(str(int(an8)) for an8 in address_numbers)
        customer_filter = f"AND RPAN8 IN ({an8_list})"
    else:
        customer_filter = ""

    query = f"""
        SELECT RPAN8 AS AddressNumber, RPDOC AS DocumentNumber,
               RPDCT AS DocumentType, {inv_date} AS InvoiceDate,
               {due_date} AS DueDate, RPAAP AS GrossAmount,
               RPAG AS OpenAmount, RPCRCD AS CurrencyCode,
               {dpd} AS DaysPastDue
        FROM {schema}.F03B11
        WHERE {_OPEN_FILTER}
            {customer_filter}
            AND {dpd} >= {int(min_days_past_due)}
        ORDER BY {dpd} DESC, RPAN8
        {row_limit_clause(max_rows)}
    """

    result = await run_sql_query_with_validation(query, max_rows=max_rows)
    scope = (
        f"customers {', '.join(str(int(an8)) for an8 in address_numbers)}"
        if address_numbers
        else "any customer"
    )
    return format_result(
        result,
        empty_message=(
            f"No past-due invoices (>= {int(min_days_past_due)} days) "
            f"found for {scope}."
        ),
    )


async def jde_customer_documents_by_type(
    address_number: int,
    schema_override: str | None = None,
) -> dict:
    """Document type breakdown for a customer's open A/R items.

    Groups open invoices by document type (e.g. Standard Invoice, Credit
    Memo, Chargeback) with counts and amounts per type.

    Args:
        address_number: Customer Address Number (AN8).
        schema_override: Optional schema override.
    """
    schema = get_schema(schema_override)

    query = f"""
        SELECT RPDCT AS DocumentType, COUNT(*) AS DocumentCount,
               SUM(RPAAP) AS TotalGrossAmount, SUM(RPAG) AS TotalOpenAmount
        FROM {schema}.F03B11
        WHERE RPAN8 = {address_number}
            AND {_OPEN_FILTER}
        GROUP BY RPDCT
        ORDER BY SUM(RPAG) DESC
    """

    result = await run_sql_query_with_validation(query)
    return format_result(
        result,
        empty_message=f"No documents found for customer {address_number}.",
    )


async def jde_invoice_lookup(
    document_number: int,
    document_type: str,
    document_company: str,
    schema_override: str | None = None,
) -> dict:
    """Look up a specific invoice/document in JDE by its composite key.

    Returns full pay-item detail for the specified document.

    Args:
        document_number: Document number (DOC).
        document_type: Document type code (e.g. "RI" for Standard Invoice).
        document_company: Document company key (KCO).
        schema_override: Optional schema override.
    """
    schema = get_schema(schema_override)
    safe_dct = escape_sql_string(document_type)
    safe_kco = escape_sql_string(document_company)
    due_date = julian_col_to_date("RPDDJ")
    inv_date = julian_col_to_date("RPDIVJ")
    gl_date = julian_col_to_date("RPDGJ")

    query = f"""
        SELECT RPAN8 AS AddressNumber, RPDOC AS DocumentNumber,
               RPDCT AS DocumentType, RPKCO AS DocumentCompany,
               RPSFX AS PayItem, RPCO AS Company,
               {inv_date} AS InvoiceDate, {due_date} AS DueDate,
               {gl_date} AS GLDate,
               RPAAP AS GrossAmount, RPAG AS OpenAmount,
               RPCRCD AS CurrencyCode, RPPOST AS PostedCode,
               RPVOD AS VoidFlag, RPPYID AS PaymentID,
               RPICU AS BatchNumber
        FROM {schema}.F03B11
        WHERE RPDOC = {document_number}
            AND RPDCT = '{safe_dct}'
            AND RPKCO = '{safe_kco}'
        ORDER BY RPSFX
    """

    result = await run_sql_query_with_validation(query)
    return format_result(
        result,
        empty_message=(
            f"No document found for number {document_number}, "
            f"type '{document_type}', company '{document_company}'."
        ),
    )


async def jde_invoices_due_in_range(
    address_number: int,
    start_date: str,
    end_date: str,
    max_rows: int = 100,
    schema_override: str | None = None,
) -> dict:
    """Open invoices with due dates within a specified date range.

    Args:
        address_number: Customer Address Number (AN8).
        start_date: Start of the date range (ISO YYYY-MM-DD).
        end_date: End of the date range (ISO YYYY-MM-DD).
        max_rows: Maximum number of invoices to return (default 100).
        schema_override: Optional schema override.
    """
    schema = get_schema(schema_override)
    start_j = iso_to_jde_julian(start_date)
    end_j = iso_to_jde_julian(end_date)
    due_date = julian_col_to_date("RPDDJ")
    inv_date = julian_col_to_date("RPDIVJ")

    query = f"""
        SELECT RPAN8 AS AddressNumber, RPDOC AS DocumentNumber,
               RPDCT AS DocumentType, {inv_date} AS InvoiceDate,
               {due_date} AS DueDate,
               RPAAP AS GrossAmount, RPAG AS OpenAmount,
               RPCRCD AS CurrencyCode
        FROM {schema}.F03B11
        WHERE RPAN8 = {address_number}
            AND {_OPEN_FILTER}
            AND RPDDJ BETWEEN {start_j} AND {end_j}
        ORDER BY RPDDJ
        {row_limit_clause(max_rows)}
    """

    result = await run_sql_query_with_validation(query, max_rows=max_rows)
    return format_result(
        result,
        empty_message=(
            f"No open invoices found for customer {address_number} "
            f"due between {start_date} and {end_date}."
        ),
    )
