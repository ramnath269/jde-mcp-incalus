"""F03012 Customer Master / AR & Credit tools.

Provides credit profile and credit-hold check tools against the JDE
Customer Master (F03012). Physical field prefix: AI (e.g. AIAN8, AICO).
Composite key: (AIAN8, AICO).
"""

from jde import run_sql_query_with_validation
from jde_utils import (
    escape_sql_string,
    format_result,
    format_single_result,
    get_schema,
    _translate_credit_hold,
)


async def jde_customer_credit_profile(
    address_number: int,
    company: str | None = None,
    fields: str = "summary",
    schema_override: str | None = None,
) -> dict:
    """Retrieve the credit profile for a customer from JDE.

    Returns credit limit, open amount, balance, credit-hold status, payment
    terms, and DSO. If no company is specified, returns all companies
    (lines of business) for that customer.

    Args:
        address_number: Customer Address Number (AN8).
        company: Optional company code to filter to one line of business.
        fields: Level of detail — "summary" (default) or "full".
        schema_override: Optional schema override.
    """
    schema = get_schema(schema_override)

    if fields == "full":
        columns = (
            "AIAN8 AS AddressNumber, AICO AS Company, "
            "AIAMCR AS CreditLimit, AIOPY AS OpenAmount, "
            "AIOYTD AS OpenAmountYTD, AISBAL AS BalanceForward, "
            "AICRCD AS CurrencyCode, AIHDAR AS CreditHoldFlag, "
            "AIACL AS CreditLineStatus, AIPOPN AS PriorOpenAmount, "
            "AIMAXO AS MaximumOpenOrder, AIMINO AS MinimumOpenOrder, "
            "AITRAR AS PaymentTermsCode, AIDSO AS DaysSalesOutstanding, "
            "AICMGR AS CreditManager, AICLMG AS CollectionManager, "
            "AIHOLD AS HoldCode, AIARC AS AutoReceiptCode, "
            "AISTMT AS StatementCode, AIUPMJ AS DateUpdated, "
            "AIUSER AS UserID"
        )
    else:
        columns = (
            "AIAN8 AS AddressNumber, AICO AS Company, "
            "AIAMCR AS CreditLimit, AIOPY AS OpenAmount, "
            "AIOYTD AS OpenAmountYTD, AISBAL AS BalanceForward, "
            "AICRCD AS CurrencyCode, AIHDAR AS CreditHoldFlag"
        )

    company_filter = ""
    if company:
        safe_co = escape_sql_string(company)
        company_filter = f" AND AICO = '{safe_co}'"

    query = (
        f"SELECT {columns} "
        f"FROM {schema}.F03012 "
        f"WHERE AIAN8 = {address_number}{company_filter}"
    )

    result = await run_sql_query_with_validation(query)

    # If filtering by company, expect a single result
    if company:
        return format_single_result(
            result,
            empty_message=(
                f"No credit profile found for customer {address_number} "
                f"in company '{company}'."
            ),
        )
    return format_result(
        result,
        empty_message=f"No credit profile found for customer {address_number}.",
    )


async def jde_customer_credit_hold_check(
    address_number: int,
    company: str | None = None,
    schema_override: str | None = None,
) -> dict:
    """Quick check whether a customer is on credit hold in JDE.

    Returns the credit-hold flag and hold code for the customer.
    Translates the flag to plain language ("On credit hold" / "No hold").

    Args:
        address_number: Customer Address Number (AN8).
        company: Optional company code to narrow the check.
        schema_override: Optional schema override.
    """
    schema = get_schema(schema_override)

    company_filter = ""
    if company:
        safe_co = escape_sql_string(company)
        company_filter = f" AND AICO = '{safe_co}'"

    query = (
        f"SELECT AIAN8 AS AddressNumber, AICO AS Company, "
        f"AIHDAR AS CreditHoldFlag, AIHOLD AS HoldCode "
        f"FROM {schema}.F03012 "
        f"WHERE AIAN8 = {address_number}{company_filter}"
    )

    result = await run_sql_query_with_validation(query)
    formatted = format_result(
        result,
        empty_message=f"No credit record found for customer {address_number}.",
    )

    # Translate flags to human-readable in each row
    if "data" in formatted and formatted["data"]:
        for row in formatted["data"]:
            flag = row.get("CreditHoldFlag") or row.get("CREDITHOLDFLG")
            row["CreditHoldStatus"] = _translate_credit_hold(flag)

    return formatted
