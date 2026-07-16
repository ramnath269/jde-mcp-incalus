"""F41021 Item Location tools.

Provides item availability, location/lot detail, branch and location rollups,
lot traceability, a negative-stock exception report, and item resolution
against the JDE Item Location File (F41021). Physical field prefix: LI
(e.g. LIITM, LIPQOH).

Key: (LIITM, LIMCU, LILOCN, LILOTN) — one row per item / branch / location / lot.

F41021 keys on the Short Item Number (LIITM), an 8-digit system-assigned
number. Humans know items by the 2nd Item Number ("SG1000") or description,
both of which live in F4101 — hence jde_item_resolve and the F4101 joins.

Quantity scale: the F41021 data dictionary declares Decimals = 0 for every
quantity column, so values are stored unscaled and are returned raw. This was
cross-checked against the F4111 cardex, which reconciles 1:1 with LIPQOH on the
large majority of rows. Availability arithmetic (on-hand less commitments) is
scale-invariant and stays correct even where a site configured display
decimals differently.

Dates are JDE Julian CYYDDD and are frequently 0 ("never received") here, so
conversion goes through _safe_julian rather than the bare julian_col_to_date
helper — TO_DATE raises on the 0 sentinel.
"""

from jde import run_sql_query_with_validation
from jde_utils import (
    escape_sql_string,
    format_result,
    get_schema,
    julian_col_to_date,
    row_limit_clause,
)


def _available(alias: str = "") -> str:
    """On-hand less every commitment bucket, optionally table-qualified."""
    p = f"{alias}." if alias else ""
    return f"({p}LIPQOH - {p}LIHCOM - {p}LIPCOM - {p}LIFCOM)"


def _safe_julian(col: str) -> str:
    """Julian-to-date conversion that tolerates the 0 ("unset") sentinel.

    F41021 leaves LILRCJ/LINCDJ at 0 when there is no date, and TO_DATE would
    raise on the resulting '1900000'. Yields NULL instead.
    """
    return f"CASE WHEN {col} > 0 THEN {julian_col_to_date(col)} END"


async def jde_item_availability(
    item_number: int,
    branch: str | None = None,
    schema_override: str | None = None,
) -> dict:
    """Net availability for an item, rolled up across locations.

    Returns on-hand, hard/soft/future commitments, quantity on purchase order,
    and computed available (on-hand less all commitments), as one row per
    branch. The headline "can I sell or consume this?" tool — start here, then
    drill in with jde_item_location_detail.

    Args:
        item_number: Short Item Number (LIITM). Use jde_item_resolve to
            translate a catalogue number like "SG1000" into this.
        branch: Optional Business Unit (LIMCU) filter, e.g. "20000".
        schema_override: Optional schema override.
    """
    schema = get_schema(schema_override)
    where = [f"LIITM = {int(item_number)}"]
    if branch:
        where.append(f"TRIM(LIMCU) = '{escape_sql_string(branch)}'")

    query = f"""
        SELECT TRIM(LIMCU) AS Branch,
               SUM(LIPQOH) AS QuantityOnHand,
               SUM(LIHCOM) AS HardCommitted,
               SUM(LIPCOM) AS SoftCommitted,
               SUM(LIFCOM) AS FutureCommitted,
               SUM(LIPREQ) AS QuantityOnPurchaseOrder,
               SUM({_available()}) AS QuantityAvailable,
               COUNT(*) AS LocationCount
        FROM {schema}.F41021
        WHERE {' AND '.join(where)}
        GROUP BY TRIM(LIMCU)
        ORDER BY QuantityOnHand DESC
    """

    result = await run_sql_query_with_validation(query)
    return format_result(
        result,
        empty_message=f"No inventory records found for item {item_number}.",
    )


async def jde_item_location_detail(
    item_number: int,
    branch: str | None = None,
    include_zero: bool = False,
    max_rows: int = 100,
    schema_override: str | None = None,
) -> dict:
    """Every stocking location for an item — one row per location/lot.

    Returns branch, location, lot, lot status, on-hand, commitments, available,
    and last receipt date. A blank location or lot means the branch primary
    location, which is the common case in this data.

    Args:
        item_number: Short Item Number (LIITM).
        branch: Optional Business Unit (LIMCU) filter.
        include_zero: Include locations with zero on-hand (default False).
        max_rows: Maximum rows to return (default 100).
        schema_override: Optional schema override.
    """
    schema = get_schema(schema_override)
    where = [f"LIITM = {int(item_number)}"]
    if branch:
        where.append(f"TRIM(LIMCU) = '{escape_sql_string(branch)}'")
    if not include_zero:
        where.append("LIPQOH <> 0")

    query = f"""
        SELECT TRIM(LIMCU) AS Branch, TRIM(LILOCN) AS Location,
               TRIM(LILOTN) AS Lot, TRIM(LILOTS) AS LotStatus,
               TRIM(LIPBIN) AS PrimaryLocationFlag,
               LIPQOH AS QuantityOnHand, LIHCOM AS HardCommitted,
               LIPCOM AS SoftCommitted, LIPREQ AS QuantityOnPurchaseOrder,
               {_available()} AS QuantityAvailable,
               {_safe_julian('LILRCJ')} AS LastReceiptDate
        FROM {schema}.F41021
        WHERE {' AND '.join(where)}
        ORDER BY LIPQOH DESC
        {row_limit_clause(max_rows)}
    """

    result = await run_sql_query_with_validation(query, max_rows=max_rows)
    return format_result(
        result,
        empty_message=f"No stocking locations found for item {item_number}.",
    )


async def jde_item_stock_by_branch(
    item_number: int,
    min_on_hand: int | None = None,
    max_rows: int = 50,
    schema_override: str | None = None,
) -> dict:
    """Where an item is stocked, ranked by on-hand quantity.

    Aggregates F41021 to one row per branch and reports available alongside
    on-hand. Answers "which plant can fill this order?" — the sourcing and
    stock-transfer question.

    Args:
        item_number: Short Item Number (LIITM).
        min_on_hand: Optional floor on on-hand; omit to include every branch.
        max_rows: Maximum branches to return (default 50).
        schema_override: Optional schema override.
    """
    schema = get_schema(schema_override)
    having = ""
    if min_on_hand is not None:
        having = f"HAVING SUM(LIPQOH) >= {int(min_on_hand)}"

    query = f"""
        SELECT TRIM(LIMCU) AS Branch,
               SUM(LIPQOH) AS QuantityOnHand,
               SUM({_available()}) AS QuantityAvailable,
               COUNT(*) AS LocationCount,
               {_safe_julian('MAX(LILRCJ)')} AS LastReceiptDate
        FROM {schema}.F41021
        WHERE LIITM = {int(item_number)}
        GROUP BY TRIM(LIMCU)
        {having}
        ORDER BY QuantityOnHand DESC
        {row_limit_clause(max_rows)}
    """

    result = await run_sql_query_with_validation(query, max_rows=max_rows)
    return format_result(
        result,
        empty_message=f"Item {item_number} is not stocked at any branch.",
    )


async def jde_branch_inventory_summary(
    branch: str,
    max_rows: int = 100,
    schema_override: str | None = None,
) -> dict:
    """Inventory carried by one branch, ranked by on-hand.

    One row per item, joined to F4101 for the catalogue number and
    description. Answers "what is sitting in plant 20000?".

    Args:
        branch: Business Unit (LIMCU), e.g. "20000".
        max_rows: Maximum items to return (default 100).
        schema_override: Optional schema override.
    """
    schema = get_schema(schema_override)

    query = f"""
        SELECT l.LIITM AS ItemNumberShort,
               TRIM(i.IMLITM) AS ItemNumber2nd,
               TRIM(i.IMDSC1) AS Description,
               SUM(l.LIPQOH) AS QuantityOnHand,
               SUM({_available('l')}) AS QuantityAvailable,
               COUNT(*) AS LocationCount
        FROM {schema}.F41021 l
        LEFT JOIN {schema}.F4101 i ON i.IMITM = l.LIITM
        WHERE TRIM(l.LIMCU) = '{escape_sql_string(branch)}'
            AND l.LIPQOH <> 0
        GROUP BY l.LIITM, TRIM(i.IMLITM), TRIM(i.IMDSC1)
        ORDER BY QuantityOnHand DESC
        {row_limit_clause(max_rows)}
    """

    result = await run_sql_query_with_validation(query, max_rows=max_rows)
    return format_result(
        result,
        empty_message=f"No stocked items found at branch '{branch}'.",
    )


async def jde_location_contents(
    branch: str,
    location: str | None = None,
    max_rows: int = 100,
    schema_override: str | None = None,
) -> dict:
    """Contents of a physical location — every item in one bin or aisle.

    The warehouse-operations inverse of jde_item_location_detail: that asks
    "where is my item?", this asks "what is in this location?". Omit location
    to list every location in the branch.

    Args:
        branch: Business Unit (LIMCU).
        location: Optional Location (LILOCN). Omit for all locations; note a
            blank location in JDE means the branch primary location.
        max_rows: Maximum rows to return (default 100).
        schema_override: Optional schema override.
    """
    schema = get_schema(schema_override)
    where = [
        f"TRIM(l.LIMCU) = '{escape_sql_string(branch)}'",
        "l.LIPQOH <> 0",
    ]
    if location:
        where.append(f"TRIM(l.LILOCN) = '{escape_sql_string(location)}'")

    query = f"""
        SELECT TRIM(l.LILOCN) AS Location, TRIM(l.LILOTN) AS Lot,
               l.LIITM AS ItemNumberShort, TRIM(i.IMLITM) AS ItemNumber2nd,
               TRIM(i.IMDSC1) AS Description,
               l.LIPQOH AS QuantityOnHand,
               {_available('l')} AS QuantityAvailable,
               {_safe_julian('l.LILRCJ')} AS LastReceiptDate
        FROM {schema}.F41021 l
        LEFT JOIN {schema}.F4101 i ON i.IMITM = l.LIITM
        WHERE {' AND '.join(where)}
        ORDER BY l.LILOCN, l.LIPQOH DESC
        {row_limit_clause(max_rows)}
    """

    result = await run_sql_query_with_validation(query, max_rows=max_rows)
    return format_result(
        result,
        empty_message=f"No stock found at branch '{branch}'"
                      + (f", location '{location}'." if location else "."),
    )


async def jde_lot_inventory(
    lot_number: str | None = None,
    item_number: int | None = None,
    max_rows: int = 100,
    schema_override: str | None = None,
) -> dict:
    """Lot-level inventory for traceability and recall.

    Returns on-hand by lot with lot status (LILOTS) and last receipt date.
    At least one of lot_number/item_number is required.

    Lot status follows UDC 41/L: blank means the lot is approved, any other
    code means it is on hold. Only a small minority of rows in this data carry
    a status, so treat a blank as "no hold recorded" rather than as positive
    confirmation that the lot was reviewed.

    Args:
        lot_number: Lot/Serial Number (LILOTN).
        item_number: Short Item Number (LIITM).
        max_rows: Maximum rows to return (default 100).
        schema_override: Optional schema override.
    """
    if not lot_number and item_number is None:
        return {"error": "provide at least one of lot_number or item_number"}

    schema = get_schema(schema_override)
    # TRIM of an all-blank NCHAR yields NULL in Oracle, which filters the
    # non-lot-controlled rows without an NCHAR/CHAR literal comparison.
    where = ["TRIM(l.LILOTN) IS NOT NULL"]
    if lot_number:
        where.append(f"TRIM(l.LILOTN) = '{escape_sql_string(lot_number)}'")
    if item_number is not None:
        where.append(f"l.LIITM = {int(item_number)}")

    query = f"""
        SELECT TRIM(l.LILOTN) AS Lot, TRIM(l.LILOTS) AS LotStatus,
               l.LIITM AS ItemNumberShort, TRIM(i.IMLITM) AS ItemNumber2nd,
               TRIM(i.IMDSC1) AS Description,
               TRIM(l.LIMCU) AS Branch, TRIM(l.LILOCN) AS Location,
               l.LIPQOH AS QuantityOnHand,
               {_available('l')} AS QuantityAvailable,
               {_safe_julian('l.LILRCJ')} AS LastReceiptDate
        FROM {schema}.F41021 l
        LEFT JOIN {schema}.F4101 i ON i.IMITM = l.LIITM
        WHERE {' AND '.join(where)}
        ORDER BY l.LILOTN, l.LIPQOH DESC
        {row_limit_clause(max_rows)}
    """

    result = await run_sql_query_with_validation(query, max_rows=max_rows)
    return format_result(
        result, empty_message="No lot-controlled inventory found."
    )


async def jde_negative_stock(
    branch: str | None = None,
    max_rows: int = 100,
    schema_override: str | None = None,
) -> dict:
    """Locations with negative on-hand — a data-integrity exception report.

    Negative on-hand usually means issues posted ahead of their receipts, or a
    mis-sequenced adjustment. Ranked most-negative first.

    Args:
        branch: Optional Business Unit (LIMCU) filter.
        max_rows: Maximum rows to return (default 100).
        schema_override: Optional schema override.
    """
    schema = get_schema(schema_override)
    where = ["l.LIPQOH < 0"]
    if branch:
        where.append(f"TRIM(l.LIMCU) = '{escape_sql_string(branch)}'")

    query = f"""
        SELECT TRIM(l.LIMCU) AS Branch, TRIM(l.LILOCN) AS Location,
               TRIM(l.LILOTN) AS Lot, l.LIITM AS ItemNumberShort,
               TRIM(i.IMLITM) AS ItemNumber2nd, TRIM(i.IMDSC1) AS Description,
               l.LIPQOH AS QuantityOnHand,
               {_safe_julian('l.LILRCJ')} AS LastReceiptDate,
               {_safe_julian('l.LIUPMJ')} AS LastUpdated
        FROM {schema}.F41021 l
        LEFT JOIN {schema}.F4101 i ON i.IMITM = l.LIITM
        WHERE {' AND '.join(where)}
        ORDER BY l.LIPQOH ASC
        {row_limit_clause(max_rows)}
    """

    result = await run_sql_query_with_validation(query, max_rows=max_rows)
    return format_result(
        result, empty_message="No negative on-hand balances found."
    )


async def jde_item_resolve(
    search_text: str,
    max_rows: int = 25,
    schema_override: str | None = None,
) -> dict:
    """Translate a catalogue item number or description to LIITM.

    F41021 keys on the Short Item Number (LIITM, e.g. 741343), but people know
    items as "SG1000" or "1000# FINE". Searches F4101 on the 2nd item number
    (IMLITM) and description (IMDSC1), case-insensitively. Call this first when
    a request names an item in words — every other tool here needs LIITM.

    Args:
        search_text: Catalogue number or description fragment.
        max_rows: Maximum matches to return (default 25).
        schema_override: Optional schema override.
    """
    schema = get_schema(schema_override)
    safe = escape_sql_string(search_text).upper()

    query = f"""
        SELECT IMITM AS ItemNumberShort, TRIM(IMLITM) AS ItemNumber2nd,
               TRIM(IMDSC1) AS Description, TRIM(IMSRTX) AS SearchText
        FROM {schema}.F4101
        WHERE UPPER(TRIM(IMLITM)) LIKE '%{safe}%'
            OR UPPER(TRIM(IMDSC1)) LIKE '%{safe}%'
        ORDER BY IMITM
        {row_limit_clause(max_rows)}
    """

    result = await run_sql_query_with_validation(query, max_rows=max_rows)
    return format_result(
        result, empty_message=f"No items matched '{search_text}'."
    )
