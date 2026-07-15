---
table: F4311
description: Purchase Order Detail File - one row per purchase order line
prefix: PD
system: 43 - Procurement
unique_key: PDKCOO,PDDOCO,PDDCTO,PDSFXO,PDLNID
surrogate_key: PDUKID
time_columns: PDTDAY,PDDRQT,PDRSHT,PDCHT,PDCHRT
---
| # | Field | Description | Data Type | Length | Decimals |
|---|-------|-------------|-----------|--------|----------|
| 1 | `PDKCOO` | Order Company (Order Number) | String | 5 | 0 |
| 2 | `PDDOCO` | Document (Order No Invoice etc.) | Numeric | 8 | 0 |
| 3 | `PDDCTO` | Order Type | String | 2 | 0 |
| 4 | `PDSFXO` | Order Suffix | String | 3 | 0 |
| 5 | `PDLNID` | Line Number | Numeric | 6 | 3 |
| 6 | `PDMCU` | Business Unit | String | 12 | 0 |
| 7 | `PDCO` | Company | String | 5 | 0 |
| 8 | `PDOKCO` | Document Company (Original Order) | String | 5 | 0 |
| 9 | `PDOORN` | Original Order Number | String | 8 | 0 |
| 10 | `PDOCTO` | Original Order Type | String | 2 | 0 |
| 11 | `PDOGNO` | Original Line Number | Numeric | 7 | 3 |
| 12 | `PDRKCO` | Company - Key (Related Order) | String | 5 | 0 |
| 13 | `PDRORN` | Related PO/SO/WO Number | String | 8 | 0 |
| 14 | `PDRCTO` | Related PO/SO/WO Order Type | String | 2 | 0 |
| 15 | `PDRLLN` | Related PO/SO Line Number | Numeric | 7 | 3 |
| 16 | `PDDMCT` | Agreement Number - Distribution | String | 12 | 0 |
| 17 | `PDDMCS` | Agreement Supplement - Distribution | Numeric | 3 | 0 |
| 18 | `PDBALU` | Contract Balances Updated Y/N | Character | 1 | 0 |
| 19 | `PDAN8` | Address Number | Numeric | 8 | 0 |
| 20 | `PDSHAN` | Address Number - Ship To | Numeric | 8 | 0 |
| 21 | `PDDRQJ` | Date - Requested | Date | 6 | 0 |
| 22 | `PDTRDJ` | Date - Order/Transaction | Date | 6 | 0 |
| 23 | `PDPDDJ` | Date - Scheduled Pick | Date | 6 | 0 |
| 24 | `PDOPDJ` | Date - Original Promised Delivery | Date | 6 | 0 |
| 25 | `PDADDJ` | Date - Actual Ship Date | Date | 6 | 0 |
| 26 | `PDCNDJ` | Date - Cancel | Date | 6 | 0 |
| 27 | `PDPEFJ` | Date - Price Effective Date | Date | 6 | 0 |
| 28 | `PDPPDJ` | Date - Promised Shipment | Date | 6 | 0 |
| 29 | `PDPSDJ` | Date - Future Date 2 | Date | 6 | 0 |
| 30 | `PDDSVJ` | Date - Service/Tax | Date | 6 | 0 |
| 31 | `PDDGL` | Date - For G/L (and Voucher) | Date | 6 | 0 |
| 32 | `PDPN` | Period Number - General Ledger | Numeric | 2 | 0 |
| 33 | `PDVR01` | Reference | String | 25 | 0 |
| 34 | `PDVR02` | Reference 2 | String | 25 | 0 |
| 35 | `PDITM` | Item Number - Short | Numeric | 8 | 0 |
| 36 | `PDLITM` | 2nd Item Number | String | 25 | 0 |
| 37 | `PDAITM` | 3rd Item Number | String | 25 | 0 |
| 38 | `PDLOCN` | Location | String | 20 | 0 |
| 39 | `PDLOTN` | Lot/Serial Number | String | 30 | 0 |
| 40 | `PDFRGD` | From Grade | String | 3 | 0 |
| 41 | `PDTHGD` | Thru Grade | String | 3 | 0 |
| 42 | `PDFRMP` | From Potency | Numeric | 7 | 3 |
| 43 | `PDTHRP` | Thru Potency | Numeric | 7 | 3 |
| 44 | `PDDSC1` | Description | String | 30 | 0 |
| 45 | `PDDSC2` | Description - Line 2 | String | 30 | 0 |
| 46 | `PDLNTY` | Line Type | String | 2 | 0 |
| 47 | `PDNXTR` | Status Code - Next | String | 3 | 0 |
| 48 | `PDLTTR` | Status Code - Last | String | 3 | 0 |
| 49 | `PDRLIT` | Item Number - Related (Kit) | String | 8 | 0 |
| 50 | `PDPDS1` | Reporting Code 1 - Sales | String | 3 | 0 |
| 51 | `PDPDS2` | Reporting Code 2 - Sales | String | 3 | 0 |
| 52 | `PDPDS3` | Reporting Code 3 - Sales | String | 3 | 0 |
| 53 | `PDPDS4` | Reporting Code 4 - Sales | String | 3 | 0 |
| 54 | `PDPDS5` | Reporting Code 5 - Sales | String | 3 | 0 |
| 55 | `PDPDP1` | Reporting Code 1 - Purchasing | String | 3 | 0 |
| 56 | `PDPDP2` | Reporting Code 2 - Purchasing | String | 3 | 0 |
| 57 | `PDPDP3` | Reporting Code 3 - Purchasing | String | 3 | 0 |
| 58 | `PDPDP4` | Reporting Code 4 - Purchasing | String | 3 | 0 |
| 59 | `PDPDP5` | Reporting Code 5 - Purchasing | String | 3 | 0 |
| 60 | `PDUOM` | Unit of Measure as Input | String | 2 | 0 |
| 61 | `PDUORG` | Units - Order/Transaction Quantity | Numeric | 15 | 0 |
| 62 | `PDUCHG` | Units - On Hold | Numeric | 15 | 0 |
| 63 | `PDUOPN` | Units - Open | Numeric | 15 | 0 |
| 64 | `PDUREC` | Units - Received | Numeric | 15 | 0 |
| 65 | `PDCREC` | Units - Cumulative Received | Numeric | 15 | 0 |
| 66 | `PDURLV` | Units - Relieved | Numeric | 15 | 0 |
| 67 | `PDOTQY` | Other Quantity (1/2) | Character | 1 | 0 |
| 68 | `PDPRRC` | Amount - Unit Cost | Numeric | 15 | 4 |
| 69 | `PDAEXP` | Amount - Extended Price | Numeric | 15 | 2 |
| 70 | `PDACHG` | Amount - On Hold | Numeric | 15 | 2 |
| 71 | `PDAOPN` | Amount - Open | Numeric | 15 | 2 |
| 72 | `PDAREC` | Amount - Received | Numeric | 15 | 2 |
| 73 | `PDARLV` | Amount - Relieved | Numeric | 15 | 2 |
| 74 | `PDFTN1` | Amount - Tax Commitment | Numeric | 15 | 2 |
| 75 | `PDTRLV` | Amount - Tax Relieved | Numeric | 15 | 2 |
| 76 | `PDPROV` | Price Override Code | Character | 1 | 0 |
| 77 | `PDAMC3` | Unit Cost - Purchasing | Numeric | 15 | 4 |
| 78 | `PDECST` | Amount - Extended Cost | Numeric | 15 | 2 |
| 79 | `PDCSTO` | Cost Override Code | Character | 1 | 0 |
| 80 | `PDCSMP` | Costing Method - Purchasing | Character | 1 | 0 |
| 81 | `PDINMG` | Print Message | String | 10 | 0 |
| 82 | `PDASN` | Price and Adjustment Schedule | String | 8 | 0 |
| 83 | `PDPRGR` | Item Price Group | String | 8 | 0 |
| 84 | `PDCLVL` | Pricing Category Level | String | 3 | 0 |
| 85 | `PDCATN` | Catalog | String | 8 | 0 |
| 86 | `PDDSPR` | Discount Factor | Numeric | 7 | 4 |
| 87 | `PDPTC` | Payment Terms Code | String | 3 | 0 |
| 88 | `PDTX` | Purchasing Taxable (Y/N) | Character | 1 | 0 |
| 89 | `PDEXR1` | Tax Expl Code 1 | String | 2 | 0 |
| 90 | `PDTXA1` | Tax Rate/Area | String | 10 | 0 |
| 91 | `PDATXT` | Associated Text | Character | 1 | 0 |
| 92 | `PDCNID` | Container I.D. | String | 20 | 0 |
| 93 | `PDCDCD` | Commodity Code | String | 15 | 0 |
| 94 | `PDNTR` | Nature of Transaction | String | 2 | 0 |
| 95 | `PDFRTH` | Freight Handling Code | String | 3 | 0 |
| 96 | `PDFRTC` | Freight Calculated (Y/N) | Character | 1 | 0 |
| 97 | `PDZON` | Zone Number | String | 3 | 0 |
| 98 | `PDFRAT` | Rate Code - Frieght/Misc | String | 10 | 0 |
| 99 | `PDRATT` | Rate Type - Freight/Misc | Character | 1 | 0 |
| 100 | `PDANBY` | Buyer Number | Numeric | 8 | 0 |
| 101 | `PDANCR` | Carrier Number | Numeric | 8 | 0 |
| 102 | `PDMOT` | Mode of Transport | String | 3 | 0 |
| 103 | `PDCOT` | Conditions of Transport | String | 3 | 0 |
| 104 | `PDSHCM` | Shipping Commodity Class | String | 3 | 0 |
| 105 | `PDSHCN` | Shipping Conditions Code | String | 3 | 0 |
| 106 | `PDUOM1` | Unit of Measure - Primary | String | 2 | 0 |
| 107 | `PDPQOR` | Units - Primary Quantity Ordered | Numeric | 15 | 0 |
| 108 | `PDUOM2` | Unit of Measure - Secondary | String | 2 | 0 |
| 109 | `PDSQOR` | Units - Secondary Quantity Ordered | Numeric | 15 | 0 |
| 110 | `PDUOM3` | Unit of Measure - Purchasing | String | 2 | 0 |
| 111 | `PDITWT` | Unit Weight | Numeric | 15 | 4 |
| 112 | `PDWTUM` | Weight Unit of Measure | String | 2 | 0 |
| 113 | `PDITVL` | Unit Volume | Numeric | 15 | 4 |
| 114 | `PDVLUM` | Volume Unit of Measure | String | 2 | 0 |
| 115 | `PDGLC` | G/L Offset | String | 4 | 0 |
| 116 | `PDCTRY` | Century | Numeric | 2 | 0 |
| 117 | `PDFY` | Fiscal Year | Numeric | 2 | 0 |
| 118 | `PDSTTS` | Line Status | String | 2 | 0 |
| 119 | `PDRCD` | Reason Code | String | 3 | 0 |
| 120 | `PDFUF1` | AIA Document Flag | Character | 1 | 0 |
| 121 | `PDFUF2` | Post Quantities | Character | 1 | 0 |
| 122 | `PDGRWT` | Gross Weight | Numeric | 15 | 4 |
| 123 | `PDGWUM` | Gross Weight Unit of Measure | String | 2 | 0 |
| 124 | `PDLT` | Ledger Types | String | 2 | 0 |
| 125 | `PDANI` | Account Number - Input (Mode Unknown) | String | 29 | 0 |
| 126 | `PDAID` | Account ID | String | 8 | 0 |
| 127 | `PDOMCU` | Project Business Unit | String | 12 | 0 |
| 128 | `PDOBJ` | Object Account | String | 6 | 0 |
| 129 | `PDSUB` | Subsidiary | String | 8 | 0 |
| 130 | `PDSBLT` | Subledger Type | Character | 1 | 0 |
| 131 | `PDSBL` | Subledger - G/L | String | 8 | 0 |
| 132 | `PDASID` | Serial Number | String | 25 | 0 |
| 133 | `PDCCMP` | Cost Component Number | Numeric | 3 | 0 |
| 134 | `PDTAG` | Tag - Reference | String | 8 | 0 |
| 135 | `PDWR01` | Categories - Work Order 01 | String | 4 | 0 |
| 136 | `PDPL` | Plan Number | String | 4 | 0 |
| 137 | `PDELEV` | Elevation | String | 3 | 0 |
| 138 | `PDR001` | Category Code - G/L1 | String | 3 | 0 |
| 139 | `PDRTNR` | Retainage Rule | String | 3 | 0 |
| 140 | `PDLCOD` | Code - Location Tax Status | String | 2 | 0 |
| 141 | `PDPURG` | Purge Code | Character | 1 | 0 |
| 142 | `PDPROM` | Processing Mode | Character | 1 | 0 |
| 143 | `PDFNLP` | Closed Item - As Of Processing | Character | 1 | 0 |
| 144 | `PDAVCH` | Code - Evaluated Receipt Settlement | Character | 1 | 0 |
| 145 | `PDPRPY` | Pre-Payment (Y/N) | Character | 1 | 0 |
| 146 | `PDUNCD` | Work Order Freeze Code | Character | 1 | 0 |
| 147 | `PDMATY` | Type - Match Type | Character | 1 | 0 |
| 148 | `PDRTGC` | Routing Process (Y/N) | Character | 1 | 0 |
| 149 | `PDRCPF` | Leadtime Recalculated (Y/N) | Character | 1 | 0 |
| 150 | `PDPS01` | Transfer/Direct Ship Flag | Character | 1 | 0 |
| 151 | `PDPS02` | Purchase Order Status 02 | Character | 1 | 0 |
| 152 | `PDPS03` | Purchase Order Status 03 | Character | 1 | 0 |
| 153 | `PDPS04` | Purchase Order Status 04 | Character | 1 | 0 |
| 154 | `PDPS05` | Purchase Order Status 05 | Character | 1 | 0 |
| 155 | `PDPS06` | Purchase Order Status 06 | Character | 1 | 0 |
| 156 | `PDPS07` | Purchase Order Status 07 | Character | 1 | 0 |
| 157 | `PDPS08` | Purchase Order Status 08 | Character | 1 | 0 |
| 158 | `PDPS09` | Purchase Order Status 09 | Character | 1 | 0 |
| 159 | `PDPS10` | Purchase Order Status 10 | Character | 1 | 0 |
| 160 | `PDCRMD` | Send Method | Character | 1 | 0 |
| 161 | `PDARTG` | Code - Approval Routing | String | 12 | 0 |
| 162 | `PDCORD` | Change Order Number | Numeric | 3 | 0 |
| 163 | `PDCHDT` | Change Order Type | String | 2 | 0 |
| 164 | `PDDOCC` | Document (Change Order #) | Numeric | 8 | 0 |
| 165 | `PDCHLN` | Change Order Line Number | Numeric | 7 | 3 |
| 166 | `PDCRCD` | Currency Code - From | String | 3 | 0 |
| 167 | `PDCRR` | Currency Conversion Rate - Spot Rate | Numeric | 15 | 0 |
| 168 | `PDFRRC` | Amount - Foreign Unit Price | Numeric | 15 | 4 |
| 169 | `PDFEA` | Amount - Foreign Extended Price | Numeric | 15 | 2 |
| 170 | `PDFUC` | Amount - Foreign Unit Cost | Numeric | 15 | 4 |
| 171 | `PDFEC` | Amount - Foreign Extended Cost | Numeric | 15 | 2 |
| 172 | `PDFCHG` | Amount - Foreign Changed Amount | Numeric | 15 | 2 |
| 173 | `PDFAP` | Amount - Foreign Open | Numeric | 15 | 2 |
| 174 | `PDFREC` | Amount - Received Foreign | Numeric | 15 | 2 |
| 175 | `PDURCD` | User Reserved Code | String | 2 | 0 |
| 176 | `PDURDT` | User Reserved Date | Date | 6 | 0 |
| 177 | `PDURAT` | User Reserved Amount | Numeric | 15 | 2 |
| 178 | `PDURAB` | User Reserved Number | Numeric | 8 | 0 |
| 179 | `PDURRF` | User Reserved Reference | String | 15 | 0 |
| 180 | `PDTORG` | Transaction Originator | String | 10 | 0 |
| 181 | `PDUSER` | User ID | String | 10 | 0 |
| 182 | `PDPID` | Program ID | String | 10 | 0 |
| 183 | `PDJOBN` | Work Station ID | String | 10 | 0 |
| 184 | `PDUPMJ` | Date - Updated | Date | 6 | 0 |
| 185 | `PDTDAY` | Time of Day | Numeric | 6 | 0 |
| 186 | `PDVR05` | Outside Reference 2 | String | 25 | 0 |
| 187 | `PDVR04` | Outside Reference 1 | String | 25 | 0 |
| 188 | `PDSHPN` | Shipment Number | Numeric | 8 | 0 |
| 189 | `PDRSHT` | Requested Ship Time | Numeric | 6 | 0 |
| 190 | `PDPRJM` | Project Number | Numeric | 8 | 0 |
| 191 | `PDOSFX` | Document Pay Item - Original | String | 3 | 0 |
| 192 | `PDMERL` | Item Revision Level | String | 3 | 0 |
| 193 | `PDMCLN` | Matrix Control Line Number | Numeric | 6 | 3 |
| 194 | `PDMACT` | Multiple Accounts | Character | 1 | 0 |
| 195 | `PDKTLN` | Kit Master Line Number | Numeric | 6 | 3 |
| 196 | `PDFTRL` | Amount - Foreign Tax Relieved | Numeric | 15 | 2 |
| 197 | `PDDUAL` | Dual Unit Of Measure Item | Character | 1 | 0 |
| 198 | `PDDRQT` | Requested Delivery Time | Numeric | 6 | 0 |
| 199 | `PDDLEJ` | Lot Effectivity Date | Date | 6 | 0 |
| 200 | `PDCTAM` | Amount - Foreign Tax | Numeric | 15 | 2 |
| 201 | `PDCPNT` | Component Line Number | Numeric | 4 | 1 |
| 202 | `PDCHT` | Change Order Time of Day | Numeric | 7 | 0 |
| 203 | `PDCHRT` | Time - Scheduled Required (HH/MM/SS) | Numeric | 6 | 0 |
| 204 | `PDCHRS` | Shift Code - Scheduled Required | Character | 1 | 0 |
| 205 | `PDCHMJ` | Change Order Date - Updated | Date | 6 | 0 |
| 206 | `PDBCRC` | Currency Code - Base | String | 3 | 0 |
| 207 | `PDVR03` | Reference | String | 25 | 0 |
| 208 | `PDLDNM` | Load Number | Numeric | 8 | 0 |
| 209 | `PDMKFR` | Address Number - Mark-for | Numeric | 8 | 0 |
| 210 | `PDPMTN` | Promotion ID | String | 12 | 0 |
| 211 | `PDUKID` | Unique Key ID (Internal) | Numeric | 15 | 0 |
| 212 | `PDUNSPSC` | UNSPSC Commodity Code | String | 8 | 0 |
| 213 | `PDCMDCDE` | Commodity Code | String | 15 | 0 |
| 214 | `PDRSFX` | Related Order Suffix | String | 3 | 0 |
| 215 | `PDWVID` | Vessel ID | Numeric | 8 | 0 |
| 216 | `PDCNTRTID` | Contract ID | Numeric | 8 | 0 |
| 217 | `PDCNTRTDID` | Contract Detail ID | Numeric | 15 | 0 |
| 218 | `PDMOADJ` | Manual Override Adjustment Flag | Character | 1 | 0 |
| 219 | `PDPODC01` | Purchase Line Code 01 | String | 3 | 0 |
| 220 | `PDPODC02` | Purchase Line Code 02 | String | 3 | 0 |
| 221 | `PDPODC03` | Purchase Line Code 03 | String | 10 | 0 |
| 222 | `PDPODC04` | Purchase Line Code 04 | String | 10 | 0 |
| 223 | `PDJBCD` | Job Type (Craft) Code | String | 6 | 0 |
| 224 | `PDSRQTY` | Service Quantity | Numeric | 15 | 4 |
| 225 | `PDSRUOM` | Service Unit of Measure | String | 2 | 0 |
| 226 | `PDCFGFL` | Created By Configurator Flag | Character | 1 | 0 |
| 227 | `PDPMPN` | Production Number | String | 30 | 0 |
| 228 | `PDPNS` | Production Number Short | Numeric | 10 | 0 |
