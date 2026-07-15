# JDE Purchase Order Schema MCP Tools

A **metadata-only** set of MCP tools that serve exact column information for JDE
purchase-order tables (starting with **F4311**, all 228 columns). They exist to
stop an agent from guessing: the real column name (`PDDOCO`, not `ORDER_NO`),
the Julian date format (`126195`, not `'2026-07-14'`), and the implied decimal
scale (a `(15,4)` unit cost may be stored as `123456`, not `12.3456`).

These tools **never connect to a database**. Live data comes from the separate
JDE data tools (`jde_run_sql_query`, `jde_open_purchase_orders`, …). The
pairing: **resolve the column here → run the query there.**

## Two ways it is served

1. **Inside the main server** (`server.py`, streamable HTTP) — registered as
   `jde_po_*` tools alongside every other JDE tool. If that server is already
   wired into your client, the schema tools appear automatically.
2. **Standalone stdio server** (`jde_po_schema_server.py`) — a local,
   database-free process for clients that launch tools by command. This is what
   `mcp_config.json` / `.mcp.json` point at.

## Tools

| Tool (main server) | Standalone name | Purpose |
|--------------------|-----------------|---------|
| `jde_po_list_tables` | `list_po_tables` | List loaded tables — the entry point. |
| `jde_po_get_table_schema` | `get_table_schema` | Every column of a table (glossary optional). |
| `jde_po_get_column` | `get_column` | One column in full; accepts `PDUORG` or `UORG`. |
| `jde_po_find_columns` | `find_columns` | Keyword search: "open", "promised date". |
| `jde_po_list_decimal_columns` | `list_decimal_columns` | The 34 scaled columns + divisor + verify warning. |
| `jde_po_list_date_columns` | `list_date_columns` | 15 Julian date + 5 HHMMSS time columns. |
| `jde_po_build_select` | `build_select` | Validated `SELECT` skeleton; unknown field → error, no SQL. |
| `jde_po_julian_to_date` | `julian_to_date` | `126195` → `2026-07-14`. |
| `jde_po_date_to_julian` | `date_to_julian` | `2026-07-14` → `126195`. |

## The three data-contract rules

- **Implied decimals** — `list_decimal_columns` gives `divide_by_to_get_display_value`
  and a warning that the scaling must be **verified against one known order**
  before you trust a SUM. The server does not assert the value is scaled; it
  does not know your platform.
- **Julian dates** — every `Date` column is 6-digit `CYYDDD`. Never compare to
  an ISO string. Use the two conversion tools.
- **Blank padding** — `String`/`Character` columns are space-padded, so
  `build_select` emits a trailing note to wrap comparisons in `RTRIM()`.

## Configuration

### Antigravity — `~/.gemini/config/mcp_config.json`
(per-project override: `.agents/mcp_config.json`; reach it in the IDE via the
agent panel → **… → MCP Servers → Manage MCP Servers → View raw config**).
Antigravity uses `serverUrl` for remote servers (not `url`). See
[`mcp_config.json`](mcp_config.json) — fill in absolute paths. Add a sibling
`"headers": { "Authorization": "Bearer <TOKEN>" }` if the JDE endpoints need auth.

### Claude Code — `.mcp.json` (project root)
See [`.mcp.json`](.mcp.json).

## Adding a table

Table discovery is by globbing `data/*.json` — **no table name is hardcoded**.
To add F4301 (PO header) or F43121 (PO receiver):

1. Drop `scripts/exports/F4301_export.md` in — a `---` frontmatter block
   (`table`, `description`, `prefix`, `unique_key`, `surrogate_key`,
   `time_columns`) followed by the data-dictionary column grid.
2. Run `python scripts/build_data.py` (or `... F4301` for just that one). It
   writes `data/F4301.json` and prints a census so a botched transcription is
   obvious.
3. The new table lights up with zero code change. `JDE_SCHEMA_DIR` overrides the
   data directory.

Per-column glossary text is optional: add `scripts/exports/F4301_glossary.md`
with `FIELD: text` lines and `build_data.py` merges it by field name. Columns
without an entry keep `glossary: ""` (never invented).

## Tests

```
python -m pytest tests/test_po_schema.py -q
```

The 14 acceptance tests are derived from the F4311 data dictionary, so they also
catch a bad data build (wrong column count, dropped column, mis-parsed scale).
