"""F03B14 Receipts Detail / cash application tools.

Provides receipt listing, unapplied cash, payment summary, receipt type
distribution, adjustments (write-offs/chargebacks/deductions), NSF
receipts, and date-range queries against the JDE Receipts Detail (F03B14).
Physical field prefix: RZ (e.g. RZAN8, RZCKNU).

Receipt types (RZTYIN): U = Unapplied, A = Applied, C = Chargeback,
                        D = Deduction, N = NSF, V = Void.
"""

from jde import run_sql_query_with_validation
from jde_utils import (
    escape_sql_string,
    format_result,
    get_schema,
    iso_to_jde_julian,
    julian_col_to_date,
    row_limit_clause,
    VALID_RECEIPT_TYPES,
    VALID_ADJUSTMENT_TYPES,
    RECEIPT_TYPE_LABELS,
)


async def jde_customer_receipts(
    address_number: int,
    receipt_type: str | None = None,
    max_rows: int = 100,
    schema_override: str | None = None,
) -> dict:
    """Posted receipts for a customer, with optional receipt type filter.

    Receipt types: U = Unapplied Cash, A = Applied, C = Chargeback,
    D = Deduction, N = NSF, V = Void.

    Args:
        address_number: Customer Address Number (AN8).
        receipt_type: Optional receipt type filter (U/A/C/D/N/V).
        max_rows: Maximum number of receipts to return (default 100).
        schema_override: Optional schema override.
    """
    schema = get_schema(schema_override)
    gl_date = julian_col_to_date("RZDGJ")
    rcpt_date = julian_col_to_date("RZADGJ")

    type_filter = ""
    if receipt_type:
        rt = receipt_type.strip().upper()
        if rt not in VALID_RECEIPT_TYPES:
            return {
                "error": (
                    f"Invalid receipt type '{receipt_type}'. "
                    f"Valid types: {', '.join(sorted(VALID_RECEIPT_TYPES))}."
                ),
                "data": [],
                "record_count": 0,
            }
        type_filter = f" AND RZTYIN = '{rt}'"

    query = f"""
        SELECT RZAN8 AS CustomerNumber, RZCKNU AS ReceiptNumber,
               RZPYID AS PaymentID, RZDCT AS DocumentType,
               RZDOC AS DocumentNumber, RZPAAP AS PaymentAmount,
               RZADSA AS DiscountTaken, RZCRCD AS CurrencyCode,
               {gl_date} AS GLDate, RZTYIN AS ReceiptType,
               RZPOST AS PostedCode, {rcpt_date} AS ActualReceiptDate
        FROM {schema}.F03B14
        WHERE RZAN8 = {address_number}{type_filter}
            AND RZPOST = 'P'
        ORDER BY RZDGJ DESC
        {row_limit_clause(max_rows)}
    """

    result = await run_sql_query_with_validation(query, max_rows=max_rows)
    return format_result(
        result,
        empty_message=f"No posted receipts found for customer {address_number}.",
    )


async def jde_unapplied_cash(
    address_number: int,
    max_rows: int = 100,
    schema_override: str | None = None,
) -> dict:
    """Open unapplied cash receipts for a customer.

    Returns receipts with type 'U' (Unapplied) that have not been fully
    applied or voided.

    Args:
        address_number: Customer Address Number (AN8).
        max_rows: Maximum number of receipts to return (default 100).
        schema_override: Optional schema override.
    """
    schema = get_schema(schema_override)
    gl_date = julian_col_to_date("RZDGJ")
    rcpt_date = julian_col_to_date("RZADGJ")

    query = f"""
        SELECT RZAN8 AS CustomerNumber, RZCKNU AS ReceiptNumber,
               RZPYID AS PaymentID, RZDOC AS DocumentNumber,
               RZPAAP AS PaymentAmount, RZADSA AS DiscountTaken,
               RZCRCD AS CurrencyCode, {gl_date} AS GLDate,
               {rcpt_date} AS ActualReceiptDate
        FROM {schema}.F03B14
        WHERE RZAN8 = {address_number}
            AND RZTYIN = 'U'
            AND RZPOST IN (' ', 'A')
        ORDER BY RZDGJ DESC
        {row_limit_clause(max_rows)}
    """

    result = await run_sql_query_with_validation(query, max_rows=max_rows)
    return format_result(
        result,
        empty_message=f"No unapplied cash found for customer {address_number}.",
    )


async def jde_customer_payment_summary(
    address_number: int,
    schema_override: str | None = None,
) -> dict:
    """Payment summary totals for a customer.

    Returns aggregate totals: receipt count, payment amount, discounts
    taken, write-offs, chargebacks, deductions, and date range of
    posted receipts.

    Args:
        address_number: Customer Address Number (AN8).
        schema_override: Optional schema override.
    """
    schema = get_schema(schema_override)

    query = f"""
        SELECT RZAN8 AS CustomerNumber,
               COUNT(DISTINCT RZCKNU) AS ReceiptCount,
               COUNT(*) AS LineCount,
               SUM(RZPAAP) AS TotalPaymentAmount,
               SUM(RZADSA) AS TotalDiscountTaken,
               SUM(RZAAAJ) AS TotalWriteOffAmount,
               SUM(RZECBA) AS TotalChargebackAmount,
               SUM(RZDDA) AS TotalDeductionAmount,
               MIN(RZDGJ) AS EarliestGLDate,
               MAX(RZDGJ) AS LatestGLDate,
               RZCRCD AS CurrencyCode
        FROM {schema}.F03B14
        WHERE RZAN8 = {address_number}
            AND RZPOST = 'P'
        GROUP BY RZAN8, RZCRCD
    """

    result = await run_sql_query_with_validation(query)
    return format_result(
        result,
        empty_message=f"No payment history found for customer {address_number}.",
    )


async def jde_receipt_type_distribution(
    address_number: int,
    schema_override: str | None = None,
) -> dict:
    """Receipt type distribution for a customer (pie-chart data).

    Groups posted receipts by type (Unapplied, Applied, Chargeback,
    Deduction, NSF, Void) with counts and total amounts.

    Args:
        address_number: Customer Address Number (AN8).
        schema_override: Optional schema override.
    """
    schema = get_schema(schema_override)

    query = f"""
        SELECT RZTYIN AS ReceiptType,
               COUNT(DISTINCT RZCKNU) AS ReceiptCount,
               COUNT(*) AS LineCount,
               SUM(RZPAAP) AS TotalPaymentAmount
        FROM {schema}.F03B14
        WHERE RZAN8 = {address_number}
            AND RZPOST = 'P'
        GROUP BY RZTYIN
        ORDER BY SUM(RZPAAP) DESC
    """

    result = await run_sql_query_with_validation(query)
    return format_result(
        result,
        empty_message=f"No receipts found for customer {address_number}.",
    )


async def jde_writeoffs_chargebacks_deductions(
    address_number: int,
    adjustment_type: str = "all",
    max_rows: int = 100,
    schema_override: str | None = None,
) -> dict:
    """Adjustment detail for a customer: write-offs, chargebacks, and/or
    deductions with reason codes.

    Args:
        address_number: Customer Address Number (AN8).
        adjustment_type: Filter type — "writeoff", "chargeback",
            "deduction", or "all" (default).
        max_rows: Maximum number of results to return (default 100).
        schema_override: Optional schema override.
    """
    schema = get_schema(schema_override)
    adj = adjustment_type.strip().lower()

    if adj not in VALID_ADJUSTMENT_TYPES:
        return {
            "error": (
                f"Invalid adjustment type '{adjustment_type}'. "
                f"Valid types: {', '.join(sorted(VALID_ADJUSTMENT_TYPES))}."
            ),
            "data": [],
            "record_count": 0,
        }

    gl_date = julian_col_to_date("RZDGJ")

    # Build columns and filter based on adjustment type
    base_cols = (
        f"RZAN8 AS CustomerNumber, RZCKNU AS ReceiptNumber, "
        f"RZDOC AS DocumentNumber, RZDCT AS DocumentType, "
        f"RZCRCD AS CurrencyCode, {gl_date} AS GLDate"
    )

    if adj == "writeoff":
        columns = f"{base_cols}, RZAAAJ AS WriteOffAmount, RZRSCO AS WriteOffReasonCode"
        adj_filter = " AND RZAAAJ <> 0"
    elif adj == "chargeback":
        columns = f"{base_cols}, RZECBA AS ChargebackAmount, RZECBR AS ChargebackReasonCode"
        adj_filter = " AND RZECBA <> 0"
    elif adj == "deduction":
        columns = f"{base_cols}, RZDDA AS DeductionAmount, RZDDEX AS DeductionExplanation"
        adj_filter = " AND RZDDA <> 0"
    else:  # "all"
        columns = (
            f"{base_cols}, RZAAAJ AS WriteOffAmount, RZRSCO AS WriteOffReasonCode, "
            f"RZECBA AS ChargebackAmount, RZECBR AS ChargebackReasonCode, "
            f"RZDDA AS DeductionAmount, RZDDEX AS DeductionExplanation"
        )
        adj_filter = " AND (RZAAAJ <> 0 OR RZECBA <> 0 OR RZDDA <> 0)"

    query = f"""
        SELECT {columns}
        FROM {schema}.F03B14
        WHERE RZAN8 = {address_number}
            AND RZPOST = 'P'{adj_filter}
        ORDER BY RZDGJ DESC
        {row_limit_clause(max_rows)}
    """

    result = await run_sql_query_with_validation(query, max_rows=max_rows)
    return format_result(
        result,
        empty_message=(
            f"No {adj} adjustments found for customer {address_number}."
            if adj != "all"
            else f"No adjustments (write-offs, chargebacks, deductions) found for customer {address_number}."
        ),
    )


async def jde_nsf_receipts(
    address_number: int,
    schema_override: str | None = None,
) -> dict:
    """Non-sufficient-funds (NSF) receipts for a customer.

    Returns receipts flagged as NSF, with payment amount, void date,
    and reason code.

    Args:
        address_number: Customer Address Number (AN8).
        schema_override: Optional schema override.
    """
    schema = get_schema(schema_override)
    gl_date = julian_col_to_date("RZDGJ")
    void_date = julian_col_to_date("RZVDGJ")

    query = f"""
        SELECT RZAN8 AS CustomerNumber, RZCKNU AS ReceiptNumber,
               RZDOC AS DocumentNumber, RZPAAP AS PaymentAmount,
               RZCRCD AS CurrencyCode, {gl_date} AS GLDate,
               {void_date} AS VoidDate, RZVRE AS VoidReasonCode
        FROM {schema}.F03B14
        WHERE RZAN8 = {address_number}
            AND RZNFVD = 'N'
        ORDER BY RZVDGJ DESC
    """

    result = await run_sql_query_with_validation(query)
    return format_result(
        result,
        empty_message=f"No NSF receipts found for customer {address_number}.",
    )


async def jde_receipts_in_range(
    address_number: int,
    start_date: str,
    end_date: str,
    max_rows: int = 100,
    schema_override: str | None = None,
) -> dict:
    """Posted receipts within a G/L date window for a customer.

    Args:
        address_number: Customer Address Number (AN8).
        start_date: Start of the date range (ISO YYYY-MM-DD).
        end_date: End of the date range (ISO YYYY-MM-DD).
        max_rows: Maximum number of receipts to return (default 100).
        schema_override: Optional schema override.
    """
    schema = get_schema(schema_override)
    start_j = iso_to_jde_julian(start_date)
    end_j = iso_to_jde_julian(end_date)
    gl_date = julian_col_to_date("RZDGJ")
    rcpt_date = julian_col_to_date("RZADGJ")

    query = f"""
        SELECT RZAN8 AS CustomerNumber, RZCKNU AS ReceiptNumber,
               RZPYID AS PaymentID, RZDOC AS DocumentNumber,
               RZDCT AS DocumentType, RZPAAP AS PaymentAmount,
               RZADSA AS DiscountTaken, RZCRCD AS CurrencyCode,
               {gl_date} AS GLDate, RZTYIN AS ReceiptType,
               {rcpt_date} AS ActualReceiptDate
        FROM {schema}.F03B14
        WHERE RZAN8 = {address_number}
            AND RZDGJ BETWEEN {start_j} AND {end_j}
            AND RZPOST = 'P'
        ORDER BY RZDGJ DESC
        {row_limit_clause(max_rows)}
    """

    result = await run_sql_query_with_validation(query, max_rows=max_rows)
    return format_result(
        result,
        empty_message=(
            f"No posted receipts found for customer {address_number} "
            f"between {start_date} and {end_date}."
        ),
    )
