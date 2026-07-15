"""F4211 Sales Order Detail tools.

Provides sales summary, line-level detail, period sales, top customers,
order count, backorder report, and order status tools against the JDE
Sales Order Detail (F4211). Physical field prefix: SD (e.g. SDDOCO, SDAN8).

Key: (SDDOCO, SDDCTO, SDKCOO, SDLNID).
Standard order filter: SDDCTO IN ('SO', 'S').
Dates are JDE Julian CYYDDD — conversion is mandatory.
Primary amount: SDAEXP (extended price). Primary qty: SDUORG (ordered qty).
"""

from datetime import date, timedelta

from jde import run_sql_query_with_validation
from jde_utils import (
    escape_sql_string,
    format_result,
    get_schema,
    gregorian_to_jde_julian,
    iso_to_jde_julian,
    julian_col_to_date,
    row_limit_clause,
)

# Standard sales order type filter
_ORDER_TYPE_FILTER = "SDDCTO IN ('SO', 'S')"


def _default_date_range() -> tuple[int, int]:
    """Return JDE Julian start/end for the last month (default period)."""
    today = date.today()
    end = today
    start = today - timedelta(days=30)
    return gregorian_to_jde_julian(start), gregorian_to_jde_julian(end)


async def jde_customer_sales_summary(
    customer_number: int,
    start_date: str | None = None,
    end_date: str | None = None,
    schema_override: str | None = None,
) -> dict:
    """Sales summary for a customer over a period.

    Returns total sales amount, total quantity, distinct order count,
    and line count. Defaults to the last 30 days if no dates are given.

    Args:
        customer_number: Customer Address Number (AN8).
        start_date: Start of period (ISO YYYY-MM-DD). Defaults to 30 days ago.
        end_date: End of period (ISO YYYY-MM-DD). Defaults to today.
        schema_override: Optional schema override.
    """
    schema = get_schema(schema_override)

    if start_date and end_date:
        start_j = iso_to_jde_julian(start_date)
        end_j = iso_to_jde_julian(end_date)
    else:
        start_j, end_j = _default_date_range()

    query = f"""
        SELECT SDAN8 AS Customer,
               SUM(SDAEXP) AS TotalAmount,
               SUM(SDUORG) AS TotalQuantity,
               COUNT(DISTINCT SDDOCO) AS OrderCount,
               COUNT(*) AS LineCount
        FROM {schema}.F4211
        WHERE SDAN8 = {customer_number}
            AND SDTRDJ BETWEEN {start_j} AND {end_j}
            AND {_ORDER_TYPE_FILTER}
        GROUP BY SDAN8
        ORDER BY TotalAmount DESC
    """

    result = await run_sql_query_with_validation(query)
    return format_result(
        result,
        empty_message=f"No sales found for customer {customer_number} in the specified period.",
    )


async def jde_customer_sales_detail(
    customer_number: int,
    start_date: str | None = None,
    end_date: str | None = None,
    max_rows: int = 100,
    schema_override: str | None = None,
) -> dict:
    """Line-level sales order detail for a customer over a period.

    Returns individual order lines with item, description, quantities,
    prices, amounts, order date, and status codes.

    Args:
        customer_number: Customer Address Number (AN8).
        start_date: Start of period (ISO YYYY-MM-DD). Defaults to 30 days ago.
        end_date: End of period (ISO YYYY-MM-DD). Defaults to today.
        max_rows: Maximum number of lines to return (default 100).
        schema_override: Optional schema override.
    """
    schema = get_schema(schema_override)
    order_date = julian_col_to_date("SDTRDJ")
    request_date = julian_col_to_date("SDDRQJ")

    if start_date and end_date:
        start_j = iso_to_jde_julian(start_date)
        end_j = iso_to_jde_julian(end_date)
    else:
        start_j, end_j = _default_date_range()

    query = f"""
        SELECT SDDOCO AS OrderNumber, SDDCTO AS OrderType,
               SDLNID AS LineNumber, SDITM AS ItemNumber,
               SDLITM AS SecondItemNumber, SDDSC1 AS Description,
               SDUORG AS OrderedQuantity, SDSOQS AS ShippedQuantity,
               SDUPRC AS UnitPrice, SDAEXP AS ExtendedAmount,
               {order_date} AS OrderDate, {request_date} AS RequestedDate,
               SDLTTR AS LastStatus, SDNXTR AS NextStatus
        FROM {schema}.F4211
        WHERE SDAN8 = {customer_number}
            AND SDTRDJ BETWEEN {start_j} AND {end_j}
            AND {_ORDER_TYPE_FILTER}
        ORDER BY SDTRDJ DESC, SDDOCO, SDLNID
        {row_limit_clause(max_rows)}
    """

    result = await run_sql_query_with_validation(query, max_rows=max_rows)
    return format_result(
        result,
        empty_message=f"No sales detail found for customer {customer_number} in the specified period.",
    )


async def jde_sales_by_period(
    start_date: str,
    end_date: str,
    customer_number: int | None = None,
    max_rows: int = 100,
    schema_override: str | None = None,
) -> dict:
    """All-customer sales within a date range, optionally filtered by customer.

    Returns per-customer totals: amount, quantity, order count, and line count.

    Args:
        start_date: Start of period (ISO YYYY-MM-DD).
        end_date: End of period (ISO YYYY-MM-DD).
        customer_number: Optional customer filter (AN8).
        max_rows: Maximum number of rows to return (default 100).
        schema_override: Optional schema override.
    """
    schema = get_schema(schema_override)
    start_j = iso_to_jde_julian(start_date)
    end_j = iso_to_jde_julian(end_date)

    customer_filter = ""
    if customer_number is not None:
        customer_filter = f" AND SDAN8 = {customer_number}"

    query = f"""
        SELECT SDAN8 AS Customer,
               SUM(SDAEXP) AS TotalAmount,
               SUM(SDUORG) AS TotalQuantity,
               COUNT(DISTINCT SDDOCO) AS OrderCount,
               COUNT(*) AS LineCount
        FROM {schema}.F4211
        WHERE SDTRDJ BETWEEN {start_j} AND {end_j}
            AND {_ORDER_TYPE_FILTER}{customer_filter}
        GROUP BY SDAN8
        ORDER BY TotalAmount DESC
        {row_limit_clause(max_rows)}
    """

    result = await run_sql_query_with_validation(query, max_rows=max_rows)
    return format_result(
        result,
        empty_message=f"No sales found between {start_date} and {end_date}.",
    )


async def jde_top_customers(
    start_date: str | None = None,
    end_date: str | None = None,
    top_n: int = 10,
    schema_override: str | None = None,
) -> dict:
    """Ranked top-N customers by total sales amount over a period.

    Args:
        start_date: Start of period (ISO YYYY-MM-DD). Defaults to 30 days ago.
        end_date: End of period (ISO YYYY-MM-DD). Defaults to today.
        top_n: Number of top customers to return (default 10).
        schema_override: Optional schema override.
    """
    schema = get_schema(schema_override)

    if start_date and end_date:
        start_j = iso_to_jde_julian(start_date)
        end_j = iso_to_jde_julian(end_date)
    else:
        start_j, end_j = _default_date_range()

    query = f"""
        SELECT SDAN8 AS Customer,
               SUM(SDAEXP) AS TotalAmount,
               SUM(SDUORG) AS TotalQuantity,
               COUNT(DISTINCT SDDOCO) AS OrderCount,
               COUNT(*) AS LineCount
        FROM {schema}.F4211
        WHERE SDTRDJ BETWEEN {start_j} AND {end_j}
            AND {_ORDER_TYPE_FILTER}
        GROUP BY SDAN8
        ORDER BY TotalAmount DESC
        {row_limit_clause(top_n)}
    """

    result = await run_sql_query_with_validation(query, max_rows=top_n)
    return format_result(
        result,
        empty_message="No sales found in the specified period.",
    )


async def jde_customer_order_count(
    customer_number: int,
    start_date: str | None = None,
    end_date: str | None = None,
    schema_override: str | None = None,
) -> dict:
    """Distinct order count for a customer over a period.

    Args:
        customer_number: Customer Address Number (AN8).
        start_date: Start of period (ISO YYYY-MM-DD). Defaults to 30 days ago.
        end_date: End of period (ISO YYYY-MM-DD). Defaults to today.
        schema_override: Optional schema override.
    """
    schema = get_schema(schema_override)

    if start_date and end_date:
        start_j = iso_to_jde_julian(start_date)
        end_j = iso_to_jde_julian(end_date)
    else:
        start_j, end_j = _default_date_range()

    query = f"""
        SELECT SDAN8 AS Customer,
               COUNT(DISTINCT SDDOCO) AS OrderCount
        FROM {schema}.F4211
        WHERE SDAN8 = {customer_number}
            AND SDTRDJ BETWEEN {start_j} AND {end_j}
            AND {_ORDER_TYPE_FILTER}
        GROUP BY SDAN8
    """

    result = await run_sql_query_with_validation(query)
    return format_result(
        result,
        empty_message=f"No orders found for customer {customer_number} in the specified period.",
    )


async def jde_backorder_report(
    customer_number: int,
    max_rows: int = 100,
    schema_override: str | None = None,
) -> dict:
    """Backordered lines for a customer.

    Returns sales order lines where the backorder quantity is greater
    than zero, sorted by requested date and order number.

    Args:
        customer_number: Customer Address Number (AN8).
        max_rows: Maximum number of lines to return (default 100).
        schema_override: Optional schema override.
    """
    schema = get_schema(schema_override)
    order_date = julian_col_to_date("SDTRDJ")
    request_date = julian_col_to_date("SDDRQJ")

    query = f"""
        SELECT SDDOCO AS OrderNumber, SDDCTO AS OrderType,
               SDLNID AS LineNumber, SDITM AS ItemNumber,
               SDLITM AS SecondItemNumber, SDDSC1 AS Description,
               SDUORG AS OrderedQuantity, SDSOQS AS ShippedQuantity,
               SDSOBK AS BackorderQuantity, SDUOPN AS OpenQuantity,
               SDAEXP AS ExtendedAmount,
               {order_date} AS OrderDate, {request_date} AS RequestedDate,
               SDLTTR AS LastStatus, SDNXTR AS NextStatus
        FROM {schema}.F4211
        WHERE SDAN8 = {customer_number}
            AND SDSOBK > 0
            AND {_ORDER_TYPE_FILTER}
        ORDER BY SDDRQJ, SDDOCO
        {row_limit_clause(max_rows)}
    """

    result = await run_sql_query_with_validation(query, max_rows=max_rows)
    return format_result(
        result,
        empty_message=f"No backordered items found for customer {customer_number}.",
    )


async def jde_order_status(
    order_number: int,
    order_type: str,
    order_company: str,
    schema_override: str | None = None,
) -> dict:
    """Line-level status for a specific sales order.

    Returns each line of the order with item details, quantities
    (ordered, shipped, backordered, open), and status codes.

    Args:
        order_number: Order number (DOCO).
        order_type: Order type code (e.g. "SO").
        order_company: Order company key (KCOO).
        schema_override: Optional schema override.
    """
    schema = get_schema(schema_override)
    safe_type = escape_sql_string(order_type)
    safe_co = escape_sql_string(order_company)

    query = f"""
        SELECT SDDOCO AS OrderNumber, SDDCTO AS OrderType,
               SDLNID AS LineNumber, SDITM AS ItemNumber,
               SDLITM AS SecondItemNumber, SDDSC1 AS Description,
               SDUORG AS OrderedQuantity, SDSOQS AS ShippedQuantity,
               SDSOBK AS BackorderQuantity, SDUOPN AS OpenQuantity,
               SDLTTR AS LastStatus, SDNXTR AS NextStatus
        FROM {schema}.F4211
        WHERE SDDOCO = {order_number}
            AND SDDCTO = '{safe_type}'
            AND SDKCOO = '{safe_co}'
        ORDER BY SDLNID
    """

    result = await run_sql_query_with_validation(query)
    return format_result(
        result,
        empty_message=(
            f"No order found for number {order_number}, "
            f"type '{order_type}', company '{order_company}'."
        ),
    )
