"""Cross-table orchestration tools.

Higher-value composite tools that call multiple single-table tools and
merge results into unified responses.
"""

from datetime import date, timedelta

from tools.address_book import (
    jde_address_book_lookup,
    jde_address_book_search_by_name,
)
from tools.customer_credit import jde_customer_credit_profile
from tools.customer_ledger import (
    jde_customer_aging_analysis,
    jde_customer_outstanding_balance,
)
from tools.receipts import jde_customer_payment_summary
from tools.sales_orders import jde_customer_sales_summary
from jde_utils import get_schema, gregorian_to_jde_julian


async def jde_resolve_customer_by_name(
    name_pattern: str,
    search_type: str = "C",
    max_rows: int = 10,
    schema_override: str | None = None,
) -> dict:
    """Resolve a customer name to address number(s).

    Many JDE tools require an Address Number (AN8) but users typically know
    the customer name. This tool searches the Address Book for matching
    customer names and returns candidate address numbers.

    Args:
        name_pattern: Full or partial customer name to search for.
        search_type: Address book search type code (default "C" = Customer).
        max_rows: Maximum number of candidates to return (default 10).
        schema_override: Optional schema override.

    Returns a list of matching customers with address numbers and names,
    which can then be used as input to other JDE tools.
    """
    from jde import run_sql_query_with_validation
    from jde_utils import escape_sql_string, row_limit_clause

    schema = get_schema(schema_override)
    safe_pattern = escape_sql_string(name_pattern)
    safe_type = escape_sql_string(search_type)

    query = (
        f"SELECT ABAN8 AS AddressNumber, ABALPH AS AlphaName, "
        f"ABAT1 AS SearchType, ABDC AS CompressedDescription "
        f"FROM {schema}.F0101 "
        f"WHERE ABALPH LIKE '%{safe_pattern}%' "
        f"AND ABAT1 = '{safe_type}' "
        f"ORDER BY ABALPH "
        f"{row_limit_clause(max_rows)}"
    )

    result = await run_sql_query_with_validation(query, max_rows=max_rows)

    rows = result.get("rows", [])
    if not rows:
        return {
            "message": (
                f"No customers found matching '{name_pattern}' "
                f"with search type '{search_type}'."
            ),
            "candidates": [],
            "candidate_count": 0,
        }

    return {
        "candidates": rows,
        "candidate_count": len(rows),
    }


async def jde_customer_360(
    address_number: int,
    company: str | None = None,
    schema_override: str | None = None,
) -> dict:
    """Consolidated 360-degree customer snapshot across all JDE modules.

    One call returns a complete customer profile by querying:
    - Address Book (F0101): identity & demographics
    - Customer Master (F03012): credit profile & hold status
    - Customer Ledger (F03B11): outstanding balance + aging buckets
    - Receipts (F03B14): payment summary
    - Sales Orders (F4211): trailing 12-month sales summary

    This is the flagship tool for a comprehensive customer handoff.

    Args:
        address_number: Customer Address Number (AN8).
        company: Optional company code for credit filtering.
        schema_override: Optional schema override.
    """
    # Trailing 12-month date range for sales
    today = date.today()
    twelve_months_ago = today - timedelta(days=365)
    sales_start = twelve_months_ago.strftime("%Y-%m-%d")
    sales_end = today.strftime("%Y-%m-%d")

    # Run all five queries (could be parallelised but kept sequential
    # for simplicity and to avoid overwhelming the JDE server)
    identity = await jde_address_book_lookup(
        address_number=address_number,
        fields="full",
        schema_override=schema_override,
    )

    credit = await jde_customer_credit_profile(
        address_number=address_number,
        company=company,
        fields="summary",
        schema_override=schema_override,
    )

    outstanding = await jde_customer_outstanding_balance(
        address_number=address_number,
        schema_override=schema_override,
    )

    aging = await jde_customer_aging_analysis(
        address_number=address_number,
        schema_override=schema_override,
    )

    payments = await jde_customer_payment_summary(
        address_number=address_number,
        schema_override=schema_override,
    )

    sales = await jde_customer_sales_summary(
        customer_number=address_number,
        start_date=sales_start,
        end_date=sales_end,
        schema_override=schema_override,
    )

    return {
        "customer": address_number,
        "identity": identity,
        "credit": credit,
        "receivables": {
            "outstanding_balance": outstanding,
            "aging_analysis": aging,
        },
        "payments": payments,
        "sales_trailing_12_months": sales,
    }
