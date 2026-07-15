"""F0101 Address Book Master tools.

Provides lookup and search tools against the JDE Address Book (F0101).
Physical field prefix: AB (e.g. ABAN8, ABALPH).
"""

from jde import run_sql_query_with_validation
from jde_utils import (
    escape_sql_string,
    format_result,
    format_single_result,
    get_schema,
    row_limit_clause,
    validate_category_code,
    SEARCH_TYPE_LABELS,
    _translate_code,
)


async def jde_address_book_lookup(
    address_number: int,
    fields: str = "summary",
    schema_override: str | None = None,
) -> dict:
    """Look up a full or summary profile for one address number in the
    JDE Address Book.

    Args:
        address_number: The JDE Address Number (AN8) to look up.
        fields: Level of detail — "summary" (default) or "full".
        schema_override: Optional schema override (default from config).

    Returns a profile with name, search type, business unit, tax IDs, etc.
    """
    schema = get_schema(schema_override)

    if fields == "full":
        columns = (
            "ABAN8 AS AddressNumber, ABALPH AS AlphaName, "
            "ABAT1 AS SearchType, ABMCU AS BusinessUnit, "
            "ABTAX AS TaxID, ABLNGP AS LanguageCode, "
            "ABALKY AS LongAddressNumber, ABDC AS CompressedDescription, "
            "ABTX2 AS TaxID2, ABSIC AS IndustryClassCode, "
            "ABTAXC AS TaxExemptCertificate, ABDUNS AS DUNSNumber, "
            "ABTICKER AS StockTickerSymbol, ABEXCHG AS StockExchange, "
            "ABNOE AS NumberOfEmployees, ABGROWTHR AS GrowthRate, "
            "ABACTIN AS ActiveInactive, ABUPMJ AS DateUpdated, "
            "ABUSER AS UserID"
        )
    else:
        columns = (
            "ABAN8 AS AddressNumber, ABALPH AS AlphaName, "
            "ABAT1 AS SearchType, ABMCU AS BusinessUnit, "
            "ABTAX AS TaxID, ABLNGP AS LanguageCode"
        )

    query = (
        f"SELECT {columns} "
        f"FROM {schema}.F0101 "
        f"WHERE ABAN8 = {address_number}"
    )

    result = await run_sql_query_with_validation(query)
    return format_single_result(
        result,
        empty_message=f"No address book entry found for address number {address_number}.",
    )


async def jde_address_book_search_by_name(
    name_pattern: str,
    max_rows: int = 100,
    schema_override: str | None = None,
) -> dict:
    """Search the JDE Address Book by name (partial match).

    Args:
        name_pattern: Full or partial name to search for. Automatically
            wrapped in wildcards for a LIKE match.
        max_rows: Maximum number of results to return (default 100).
        schema_override: Optional schema override.

    Returns a list of matching addresses with number, name, search type,
    and compressed description.
    """
    schema = get_schema(schema_override)
    safe_pattern = escape_sql_string(name_pattern)

    query = (
        f"SELECT ABAN8 AS AddressNumber, ABALPH AS AlphaName, "
        f"ABAT1 AS SearchType, ABDC AS CompressedDescription "
        f"FROM {schema}.F0101 "
        f"WHERE ABALPH LIKE '%{safe_pattern}%' "
        f"ORDER BY ABALPH "
        f"{row_limit_clause(max_rows)}"
    )

    result = await run_sql_query_with_validation(query, max_rows=max_rows)
    return format_result(
        result,
        empty_message=f"No address book entries found matching '{name_pattern}'.",
    )


async def jde_address_book_by_search_type(
    search_type: str,
    max_rows: int = 100,
    schema_override: str | None = None,
) -> dict:
    """List addresses of a given type from the JDE Address Book.

    Common search types: C = Customer, S = Supplier, V/E = Employee.

    Args:
        search_type: Single-character search type code (e.g. "C", "S", "V").
        max_rows: Maximum number of results to return (default 100).
        schema_override: Optional schema override.

    Returns a list of addresses filtered by search type.
    """
    schema = get_schema(schema_override)
    safe_type = escape_sql_string(search_type)

    query = (
        f"SELECT ABAN8 AS AddressNumber, ABALPH AS AlphaName, "
        f"ABMCU AS BusinessUnit, ABAT1 AS SearchType "
        f"FROM {schema}.F0101 "
        f"WHERE ABAT1 = '{safe_type}' "
        f"ORDER BY ABALPH "
        f"{row_limit_clause(max_rows)}"
    )

    label = _translate_code(search_type, SEARCH_TYPE_LABELS)
    result = await run_sql_query_with_validation(query, max_rows=max_rows)
    return format_result(
        result,
        empty_message=f"No address book entries found for search type '{search_type}' ({label}).",
    )


async def jde_address_book_by_category_code(
    category_code: str,
    value: str,
    max_rows: int = 100,
    schema_override: str | None = None,
) -> dict:
    """Filter the JDE Address Book by a category code (AC01–AC30).

    Args:
        category_code: The category code to filter on (e.g. "AC01", "AC15").
        value: The value to match for that category code.
        max_rows: Maximum number of results to return (default 100).
        schema_override: Optional schema override.

    Returns a list of addresses matching the specified category code value.
    """
    schema = get_schema(schema_override)

    # Validates code is AC01–AC30 and returns the physical column name (ABAC01, etc.)
    column_name = validate_category_code(category_code)
    safe_value = escape_sql_string(value)

    query = (
        f"SELECT ABAN8 AS AddressNumber, ABALPH AS AlphaName, "
        f"ABMCU AS BusinessUnit, ABAT1 AS SearchType, "
        f"{column_name} AS CategoryCodeValue "
        f"FROM {schema}.F0101 "
        f"WHERE {column_name} = '{safe_value}' "
        f"ORDER BY ABALPH "
        f"{row_limit_clause(max_rows)}"
    )

    result = await run_sql_query_with_validation(query, max_rows=max_rows)
    return format_result(
        result,
        empty_message=f"No address book entries found for {category_code} = '{value}'.",
    )
