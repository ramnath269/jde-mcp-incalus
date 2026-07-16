LIITM: An inventory item number. The system provides three separate item numbers plus an extensive cross-reference capability to other item numbers (see data item XRT) to accommodate substitute item numbers, replacements, bar codes, customer numbers, supplier numbers, and so forth. The item numbers are as follows: o Item Number (short) - An eight-digit, computer-assigned item number o 2nd Item Number - The 25-digit, free-form, user defined alphanumeric item number o 3rd Item Number - Another 25-digit, free-form, user defined alphanumeric item number
LIMCU: An alphanumeric code that identifies a separate entity within a business for which you want to track costs. For example, a business unit might be a warehouse location, job, project, work center, branch, or plant. You can assign a business unit to a document, entity, or person for purposes of responsibility reporting. For example, the system provides reports of open accounts payable and accounts receivable by business unit to track equipment by responsible department. Business unit security might prevent you from viewing information about business units for which you have no authority.
LILOCN: The storage location from which goods will be moved.
LILOTN: A number that identifies a lot or a serial number. A lot is a group of items with similar characteristics.
LIPBIN: A code that indicates whether this is the primary or secondary location for this item within this stocking location. Valid values are: P Primary storage location S Secondary storage location Note: You can only have one storage area marked as primary within each branch or warehouse. In some cases, the system uses the primary storage area as the default.
LIGLPT: A user defined code (41/9) that identifies the G/L offset that system uses when it searches for the account to which it posts the transaction. If you do not want to specify a class code, you can enter **** (four asterisks) in this field. You can use automatic accounting instructions (AAIs) to predefine classes of automatic offset accounts for the Inventory Management, Procurement, and Sales Order Management systems. You might assign G/L class codes as follows: IN20 Direct Ship Orders IN60 Transfer Orders IN80 Stock Sales The system can generate accounting entries based upon a single transaction. For example, a single sale of a stock item can trigger the generation of accounting entries similar to the following: Sales-Stock (Debit) xxxxx.xx A/R Stock Sales (Credit) xxxxx.xx Posting Category: IN80 Stock Inventory (Debit) xxxxx.xx Stock COGS (Credit) xxxxx.xx The system uses the class code and the document type to find the AAI.
LILOTS: A user defined code (41/L) that indicates the status of the lot. If you leave this field blank, it indicates that the lot is approved. All other codes indicate that the lot is on hold. You can assign a different status code to each location in which a lot resides on Item/Location Information or Location Lot Status Change.
LILRCJ: The date that the last shipment of the item was received.
LIPQOH: The number of units that are physically in stock. The system displays the quantity on-hand in the primary unit of measure.
LIPBCK: The number of units backordered in primary units of measure.
LIPREQ: The number of units specified on the purchase order in primary units of measure.
LIQWBO: The number of units on work orders in primary units of measure.
LIOT1P: The first of two quantities that can be specified as additional offsets (subtractions from on-hand) in the determination of quantities available for sale. (Primary unit of measure)
LIOT2P: The second of two quantities that can be specified as additional offsets (subtractions from on-hand) in the determination of quantities available for sale. (Primary unit of measure)
LIOT1A: The quantity that appears on documents such as bid requests, which are not formal commitments to buy on the part of your organization.
LIHCOM: The number of units committed to a specific location and lot.
LIPCOM: The number of units soft committed to sales orders or work orders in the primary units of measure.
LIFCOM: A value that represents quantity on an order. This data item has two meanings: 1. This is the quantity on a sales order whose requested shipment date is beyond the standard commitment period specified in the Inventory Constants for that branch. As an example, if you normally ship most orders within 90 days, then an order for an item with a requested ship date a year from now would have its quantity reflected in this field. 2. The Allocation Process allocates all order quantity to this field regardless of future commitment.
LIFUN1: The number of units soft committed to Work Orders in the primary unit of measure.
LIQOWO: The number of units hard committed to work orders in the primary unit of measure.
LIQTTR: The quantity currently in transit from the supplier.
LIQTIN: The quantity currently being inspected. This quantity has been received, but is not considered on hand.
LIQTRI: A quantity in the primary unit of measure that you expect to add to the location detail after you confirm a putaway or replenishment suggestion.
LIQTRO: A quantity in the primary unit of measure that you expect to remove from the location after you confirm a picking or replenishment suggestion.
LINCDJ: The date the item is next scheduled to be cycle counted. This data is for information only but can be used to narrow the records selected for display on this screen.
LIQTY1: Quantity for future use in the Item Location file (F4102).
LIQTY2: Quantity for future use in the Item Location file (F4102).
LIURAB: This is a 8 position code that is reserved for the user. JDE does not currently use this field and will not utilize this field in the future.
LIURRF: A 15-position reference that is reserved for the user. J.D. Edwards does not currently use this field and does not plan to use it in the future.
LIURAT: This is a 15 position code that is reserved for the user. JDE does not currently use this field and will not utilize this field in the future.
LIURCD: This is a 2 position code that is reserved for the user. JDE does not currently use this field and will not utilize this field in the future.
LIJOBN: The code that identifies the work station ID that executed a particular job.
LIPID: The number that identifies the batch or interactive program (batch or interactive object). For example, the number of the Sales Order Entry interactive program is P4210, and the number of the Print Invoices batch process report is R42565. The program ID is a variable length value. It is assigned according to a structured syntax in the form TSSXXX, where: T The first character of the number is alphabetic and identifies the type, such as P for Program, R for Report, and so on. For example, the value P in the number P4210 indicates that the object is a program. SS The second and third characters of the number are numeric and identify the system code. For example, the value 42 in the number P4210 indicates that this program belongs to system 42, which is the Sales Order Processing system. XXX The remaining characters of the numer are numeric and identify a unique program or report. For example, the value 10 in the number P4210 indicates that this is the Sales Order Entry program.
LIUPMJ: The date that specifies the last update to the file record.
LIUSER: The code that identifies a user profile.
LITDAY: The computer clock in hours:minutes:seconds.
LIURDT: This is a 6 position code that is reserved for the user. JDE does not currently use this field and will not utilize this field in the future.
LIQTO1: The quantity which is currently at a user-defined operation within the dock-to-stock process. The quantity has been received, but may or may not be considered to be on hand.
LIQTO2: The quantity which is currently at a user-defined operation within the dock-to-stock process. The quantity has been received, but may or may not be considered to be on hand.
LIHCMS: The number of units (expressed in the secondary unit of measure) that are hard-committed to a specific location and lot.
LIPJCM: The number of units committed to a specified location and lot for a project.
LIPJDM: The number of units committed to a specified location and lot for a project.
LISCMS: The number of units (expressed in the secondary unit of measure) that are soft-committed to sales orders or work orders.
LISIBW: A quantity in the secondary unit of measure that you expect to add to the location detail after you confirm a putaway or replenishment suggestion.
LISOBW: The quantity (expressed in the secondary unit of measure) that you expect to remove from the location after you confirm a picking suggestion or replenishment suggestion.
LISQOH: The number of units on hand in secondary units of measure.
LISQWO: The number of units, expressed in the secondary unit of measure, that are specified on the work order.
LISREQ: The number of units, expressed in the secondary unit of measure, that are specified on the purchase order.
LISWHC: The number of units, expressed in the secondary unit of measure, that are hard-committed to work orders.
LISWSC: The number of units, expressed in the secondary unit of measure, that are soft-committed to work orders.
LICHDF: An option that indicates whether a critical hold exists.
LIWPDF: An option that indicates whether outstanding workflow entries exist for this transaction.
LICFGSID: An identifier that represents a unique configuration. It is generated from an encryption algorithm. Regardless of the number of segments or levels in the configured item, the system always converts the information into a 32-character digest. The digest is always a full 32 characters in length, consists of numbers and characters, and does not contain any blanks. You cannot determine the initial value from the digest, and it has no significant meaning.
