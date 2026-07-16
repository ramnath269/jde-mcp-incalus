---
table: F41021
description: Item Location File - one row per item / branch / location / lot
prefix: LI
system: 41 - Inventory Management
unique_key: LIITM,LIMCU,LILOCN,LILOTN
surrogate_key:
time_columns: LITDAY
---
| # | Field | Description | Data Type | Length | Decimals |
|---|-------|-------------|-----------|--------|----------|
| 1 | `LIITM` | Item Number - Short | Numeric | 8 | 0 |
| 2 | `LIMCU` | Business Unit | String | 12 | 0 |
| 3 | `LILOCN` | Location | String | 20 | 0 |
| 4 | `LILOTN` | Lot/Serial Number | String | 30 | 0 |
| 5 | `LIPBIN` | Primary Location (P/S) | Character | 1 | 0 |
| 6 | `LIGLPT` | Category - G/L | String | 4 | 0 |
| 7 | `LILOTS` | Lot Status Code | Character | 1 | 0 |
| 8 | `LILRCJ` | Date - Last Receipt (Julian) | Date | 6 | 0 |
| 9 | `LIPQOH` | Quantity on Hand - Primary units | Numeric | 15 | 0 |
| 10 | `LIPBCK` | Quantity on Backorder | Numeric | 15 | 0 |
| 11 | `LIPREQ` | Quantity on Purchase Order-primary units | Numeric | 15 | 0 |
| 12 | `LIQWBO` | Quantity on Work Order Receipt | Numeric | 15 | 0 |
| 13 | `LIOT1P` | Quantity 1 - Other primary units | Numeric | 15 | 0 |
| 14 | `LIOT2P` | Quantity 2 - Other primary units | Numeric | 15 | 0 |
| 15 | `LIOT1A` | Quantity - Other Purchasing 1 | Numeric | 15 | 0 |
| 16 | `LIHCOM` | Quantity - Hard Committed | Numeric | 15 | 0 |
| 17 | `LIPCOM` | Quantity Soft Committed | Numeric | 15 | 0 |
| 18 | `LIFCOM` | Quantity on Future Commit | Numeric | 15 | 0 |
| 19 | `LIFUN1` | Quantity - Work Order Soft Commit | Numeric | 15 | 0 |
| 20 | `LIQOWO` | Quantity - Work Order Hard Commit | Numeric | 15 | 0 |
| 21 | `LIQTTR` | Units - In Transit - Primary units | Numeric | 15 | 0 |
| 22 | `LIQTIN` | Units - In Inspection - Primary units | Numeric | 15 | 0 |
| 23 | `LIQONL` | Quantity - On Loan to Manufacturing | Numeric | 15 | 0 |
| 24 | `LIQTRI` | Quantity Inbound - Warehouse | Numeric | 15 | 0 |
| 25 | `LIQTRO` | Quantity Outbound - Warehouse | Numeric | 15 | 0 |
| 26 | `LINCDJ` | Date - Next Count (Julian) | Date | 6 | 0 |
| 27 | `LIQTY1` | Future Use Quantity | Numeric | 15 | 0 |
| 28 | `LIQTY2` | Future Use Quantity 2 | Numeric | 15 | 0 |
| 29 | `LIURAB` | User Reserved Number | Numeric | 8 | 0 |
| 30 | `LIURRF` | User Reserved Reference | String | 15 | 0 |
| 31 | `LIURAT` | User Reserved Amount | Numeric | 15 | 2 |
| 32 | `LIURCD` | User Reserved Code | String | 2 | 0 |
| 33 | `LIJOBN` | Work Station ID | String | 10 | 0 |
| 34 | `LIPID` | Program ID | String | 10 | 0 |
| 35 | `LIUPMJ` | Date - Updated | Date | 6 | 0 |
| 36 | `LIUSER` | User ID | String | 10 | 0 |
| 37 | `LITDAY` | Time of Day | Numeric | 6 | 0 |
| 38 | `LIURDT` | User Reserved Date | Date | 6 | 0 |
| 39 | `LIQTO1` | Units - In Operation 1 - Primary units | Numeric | 15 | 0 |
| 40 | `LIQTO2` | Units - In Operation 2 - Primary units | Numeric | 15 | 0 |
| 41 | `LIHCMS` | Secondary Quantity Hard Committed | Numeric | 15 | 0 |
| 42 | `LIPJCM` | Project Hard Committed Quantity in Prima | Numeric | 15 | 0 |
| 43 | `LIPJDM` | Project Hard Committed Quantity in Secon | Numeric | 15 | 0 |
| 44 | `LISCMS` | Secondary Quantity Soft Committed | Numeric | 15 | 0 |
| 45 | `LISIBW` | Secondary Quantity Inbound - Warehouse | Numeric | 15 | 0 |
| 46 | `LISOBW` | Secondary Quantity Outbound - Warehouse | Numeric | 15 | 0 |
| 47 | `LISQOH` | Quantity on Hand - in Secondary units | Numeric | 15 | 0 |
| 48 | `LISQWO` | Secondary Quantity on Work Order Receipt | Numeric | 15 | 0 |
| 49 | `LISREQ` | Quantity on Purchase Order - Secondary | Numeric | 15 | 0 |
| 50 | `LISWHC` | Secondary Quantity WO Hard Commit | Numeric | 15 | 0 |
| 51 | `LISWSC` | SecondaryQuantity W.O. Soft Commit | Numeric | 15 | 0 |
| 52 | `LICHDF` | Critical Hold Flag | Character | 1 | 0 |
| 53 | `LIWPDF` | Work Flow Pending Flag | Character | 1 | 0 |
| 54 | `LICFGSID` | Unique Configuration ID | String | 32 | 0 |
