"""JDE MCP tool modules — one per JD Edwards table/functional area.

Re-exports all tool functions for convenient importing in server.py.
"""

# F0101 — Address Book Master (4 tools)
from tools.address_book import (
    jde_address_book_lookup,
    jde_address_book_search_by_name,
    jde_address_book_by_search_type,
    jde_address_book_by_category_code,
)

# F03012 — Customer Master / AR & Credit (2 tools)
from tools.customer_credit import (
    jde_customer_credit_profile,
    jde_customer_credit_hold_check,
)

# F03B11 — Customer Ledger / AR Invoices (6 tools)
from tools.customer_ledger import (
    jde_customer_aging_analysis,
    jde_customer_outstanding_balance,
    jde_customer_past_due_invoices,
    jde_customer_documents_by_type,
    jde_invoice_lookup,
    jde_invoices_due_in_range,
)

# F03B14 — Receipts Detail / Cash Application (7 tools)
from tools.receipts import (
    jde_customer_receipts,
    jde_unapplied_cash,
    jde_customer_payment_summary,
    jde_receipt_type_distribution,
    jde_writeoffs_chargebacks_deductions,
    jde_nsf_receipts,
    jde_receipts_in_range,
)

# F4211 — Sales Order Detail (7 tools)
from tools.sales_orders import (
    jde_customer_sales_summary,
    jde_customer_sales_detail,
    jde_sales_by_period,
    jde_top_customers,
    jde_customer_order_count,
    jde_backorder_report,
    jde_order_status,
)

# F41021 — Item Location / Inventory (8 tools)
from tools.item_location import (
    jde_item_availability,
    jde_item_location_detail,
    jde_item_stock_by_branch,
    jde_branch_inventory_summary,
    jde_location_contents,
    jde_lot_inventory,
    jde_negative_stock,
    jde_item_resolve,
)

# Cross-table orchestration (2 tools)
from tools.orchestration import (
    jde_resolve_customer_by_name,
    jde_customer_360,
)

# F4311 — Purchase Order schema metadata (7 tools + 2 helpers)
from tools.po_schema import (
    list_po_tables,
    get_table_schema,
    get_column,
    find_columns,
    list_decimal_columns,
    list_date_columns,
    build_select,
    julian_to_date,
    date_to_julian,
)
