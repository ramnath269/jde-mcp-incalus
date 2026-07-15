#!/usr/bin/env python3
"""Regenerate ``data/*.json`` from JDE data-dictionary exports.

Each export lives in ``scripts/exports/<TABLE>_export.md`` and has two parts:

  1. A YAML-ish frontmatter block (between ``---`` fences) carrying the
     table-level metadata that the column grid does not contain — description,
     prefix, unique/surrogate keys, and the curated ``time_columns`` list.
  2. A markdown table with the columns: ``# | Field | Description |
     Data Type | Length | Decimals`` (physical order preserved).

Column glossary text is optional. If ``scripts/exports/<TABLE>_glossary.md``
exists, lines of the form ``FIELD: text`` are merged in by field name; any
column without an entry keeps ``glossary == ""`` (never invented).

Adding a new table is data-only: drop ``F4301_export.md`` in and re-run — no
change to this script or the server.

Usage:
    python scripts/build_data.py            # build every export
    python scripts/build_data.py F4311      # build one table
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_EXPORTS_DIR = _ROOT / "scripts" / "exports"
_DATA_DIR = _ROOT / "data"

# Frontmatter keys parsed as comma-separated lists rather than scalars.
_LIST_KEYS = {"unique_key", "time_columns"}


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Split leading ``---`` frontmatter from the body. Returns (meta, body)."""
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.DOTALL)
    if not m:
        raise ValueError("export is missing a '---' frontmatter block")
    meta: dict = {}
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        key, value = key.strip(), value.strip()
        if key in _LIST_KEYS:
            meta[key] = [v.strip() for v in value.split(",") if v.strip()]
        else:
            meta[key] = value
    return meta, m.group(2)


def _parse_columns(body: str, prefix: str) -> list[dict]:
    """Parse the markdown grid into ordered column dicts."""
    columns: list[dict] = []
    for line in body.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) != 6:
            continue
        ordinal_raw = cells[0]
        if not ordinal_raw.isdigit():
            # Header row ("#") and separator row ("---") land here.
            continue
        field = cells[1].strip("`").strip()
        data_item = field[len(prefix):] if field.startswith(prefix) else field
        columns.append(
            {
                "ordinal": int(ordinal_raw),
                "field": field,
                "data_item": data_item,
                "description": cells[2],
                "data_type": cells[3],
                "length": int(cells[4]),
                "decimals": int(cells[5]),
                "glossary": "",
            }
        )
    return columns


def _merge_glossary(table: str, columns: list[dict]) -> None:
    """Merge ``<TABLE>_glossary.md`` (``FIELD: text`` lines) if present."""
    gloss_path = _EXPORTS_DIR / f"{table}_glossary.md"
    if not gloss_path.exists():
        return
    entries: dict[str, str] = {}
    for line in gloss_path.read_text(encoding="utf-8").splitlines():
        if ":" not in line:
            continue
        field, _, text = line.partition(":")
        field, text = field.strip().strip("`"), text.strip()
        if field:
            entries[field.upper()] = text
    for col in columns:
        if col["field"].upper() in entries:
            col["glossary"] = entries[col["field"].upper()]


def build_one(export_path: Path) -> Path:
    """Build a single ``data/<TABLE>.json`` from an export file."""
    meta, body = _parse_frontmatter(export_path.read_text(encoding="utf-8"))
    prefix = meta.get("prefix", "")
    columns = _parse_columns(body, prefix)
    table = meta["table"]
    _merge_glossary(table, columns)

    doc = {
        "table": table,
        "description": meta.get("description", ""),
        "prefix": prefix,
        "system": meta.get("system", ""),
        "unique_key": meta.get("unique_key", []),
        "surrogate_key": meta.get("surrogate_key", ""),
        "time_columns": meta.get("time_columns", []),
        "column_count": len(columns),
        "columns": columns,
    }

    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    out = _DATA_DIR / f"{table}.json"
    out.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

    # Census — printed so a botched transcription is obvious at build time.
    census: dict[str, int] = {}
    for col in columns:
        census[col["data_type"]] = census.get(col["data_type"], 0) + 1
    decimals = sum(1 for c in columns if c["decimals"] > 0)
    print(
        f"{table}: {len(columns)} columns  "
        f"{dict(sorted(census.items()))}  decimals>0={decimals}  "
        f"time={len(doc['time_columns'])}"
    )
    return out


def main(argv: list[str]) -> int:
    if not _EXPORTS_DIR.exists():
        print(f"no exports directory at {_EXPORTS_DIR}", file=sys.stderr)
        return 1

    wanted = {a.upper() for a in argv}
    exports = sorted(_EXPORTS_DIR.glob("*_export.md"))
    if not exports:
        print(f"no *_export.md files in {_EXPORTS_DIR}", file=sys.stderr)
        return 1

    built = 0
    for path in exports:
        table = path.name.replace("_export.md", "")
        if wanted and table.upper() not in wanted:
            continue
        build_one(path)
        built += 1

    if not built:
        print("nothing matched", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
