#!/usr/bin/env python3
"""Standalone stdio MCP server for the JDE PO schema-metadata tools.

The same tools are also registered inside the main ``server.py`` (streamable
HTTP). This entrypoint exposes them over **stdio** so they can be run as a
local, database-free process from an MCP client config (see ``mcp_config.json``
/ ``.mcp.json``). It never connects to a database — it only serves column
metadata loaded from ``data/*.json`` (override with ``JDE_SCHEMA_DIR``).

Run:  python3 jde_po_schema_server.py
"""

from mcp.server.fastmcp import FastMCP

from tools.po_schema import (
    build_select,
    date_to_julian,
    find_columns,
    get_column,
    get_table_schema,
    julian_to_date,
    list_date_columns,
    list_decimal_columns,
    list_po_tables,
)

mcp = FastMCP("jde-po-schema")

# Register the 7 tools + 2 conversion helpers. Docstrings on the underlying
# functions describe when to reach for each tool — that text is what a calling
# model sees.
mcp.tool()(list_po_tables)
mcp.tool()(get_table_schema)
mcp.tool()(get_column)
mcp.tool()(find_columns)
mcp.tool()(list_decimal_columns)
mcp.tool()(list_date_columns)
mcp.tool()(build_select)
mcp.tool()(julian_to_date)
mcp.tool()(date_to_julian)


if __name__ == "__main__":
    mcp.run(transport="stdio")
