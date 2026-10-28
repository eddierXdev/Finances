# Resale Manager — V1 Requirements

## 1. Purpose

This document defines what Resale Manager V1 must do.

Identifiers:

```text
FR-*  Functional Requirement
NFR-* Non-Functional Requirement
```

Modules:

```text
PRO Products
INV Inventory
PUR Purchases
ORD Orders
SAL Sales
RET Returns
EXP Expenses
ACC Accounts
CAP Capital
CUR Currencies
EXR Exchange Rates
SUP Suppliers
CUS Customers
ANA Analytics
DAS Dashboard
BKP Backup
SET Settings
```

---

## 2. Field Classification

Every user input field is:

- REQUIRED
- OPTIONAL
- CONDITIONALLY_REQUIRED

Optional data must not require fake `0`, `"N/A"` or equivalent values.

---

## 3. Dashboard

### FR-DAS-001 — Business Summary

Display:

- Available capital
- Invested capital
- Inventory value
- Revenue
- Gross profit
- Net profit
- Expenses

Support period selection.

### FR-DAS-002 — Sales Summary

Display total sales, sale count, revenue and profit.

### FR-DAS-003 — Product Performance

Display best-selling, most profitable and slow-moving products.

### FR-DAS-004 — Base Currency Valuation

Provide consolidated reporting in configured base currency while preserving native account balances.

---

## 4. Products

### FR-PRO-001 — Create Product

Required: name.

Optional: category, description, brand, default selling price, selling currency.

### FR-PRO-002 — Edit Product

Editing must not modify historical transactions.

### FR-PRO-003 — Disable Product

Historically referenced products are not destructively deleted.

### FR-PRO-004 — Variants

Products may have flexible variants. Products without explicit variants receive an internal default variant.

### FR-PRO-005 — SKU

SKU is optional and unique when provided.

---

## 5. Inventory

### FR-INV-001 — Current Stock

Determine current stock per product variant.

### FR-INV-002 — Inventory Movements

Every stock change creates a traceable movement.

### FR-INV-003 — Negative Stock

Prevent invalid negative sellable stock.

### FR-INV-004 — Manual Adjustment

Required: product, quantity, reason, date.

Optional: notes.

### FR-INV-005 — History

Inventory movement history is viewable.

### FR-INV-006 — Low Stock

Products may define an optional low-stock threshold.

### FR-INV-007 — FIFO Costing

V1 uses FIFO.

### FR-INV-008 — Inventory Lots

Received inventory preserves originating purchase, variant, acquired quantity, remaining quantity, effective acquisition cost and receipt date.

### FR-INV-009 — FIFO Traceability

Preserve which lots were consumed by each sale item.

### FR-INV-010 — Inventory Movement Signs

Inventory entering sellable stock uses positive quantity. Inventory leaving uses negative quantity.

---

## 6. Purchases

### FR-PUR-001 — Register Purchase

Required:

- Purchase date
- At least one product
- Quantity
- Unit purchase price
- Currency

Optional:

- Supplier
- Order number
- Tracking number
- Notes

Account becomes required when financial payment is recorded.

### FR-PUR-002 — Multiple Items

A purchase may contain multiple variants.

### FR-PUR-003 — Additional Costs

A purchase may contain zero or more shipping, transportation, tax, commission, packaging, customs or other costs.

### FR-PUR-004 — Cost Allocation

Supported:

```text
BY_QUANTITY
BY_VALUE
BY_WEIGHT
MANUAL
```

Weight is conditionally required for `BY_WEIGHT`.

### FR-PUR-005 — Effective Acquisition Cost

Calculate effective acquisition cost including normalized allocated costs.

### FR-PUR-006 — Full Purchase Payment

V1 purchases are fully paid when payment is registered.

### FR-PUR-007 — No Purchase Credit

No supplier credit, partial purchase payments, accounts payable or installments.

### FR-PUR-008 — Purchase Account Currency

Paying account currency must equal purchase currency.

### FR-PUR-009 — Purchase Cost Currency

Additional costs may use other currencies. Preserve original amount/currency/rate and normalize allocated values into purchase currency.

---

## 7. Orders

### FR-ORD-001 — Status

```text
PENDING
PURCHASED
SHIPPED
IN_TRANSIT
PARTIALLY_RECEIVED
RECEIVED
CANCELLED
```

### FR-ORD-002 — Receive Order

Ordering does not create sellable inventory. Receiving does.

### FR-ORD-003 — Partial Receipt

Support multiple deliveries and determine ordered, received and remaining quantity.

### FR-ORD-004 — Receipt Validation

Received quantity cannot exceed ordered quantity in V1.

---

## 8. Sales

### FR-SAL-001 — Register Sale

Required:

- At least one product
- Quantity
- Selling price
- Currency
- Sale date
- Receiving account

Optional:

- Customer
- Discount
- Notes

### FR-SAL-002 — Inventory Reduction

Completed sales reduce inventory.

### FR-SAL-003 — Financial Movement

Completed sales create a financial movement.

### FR-SAL-004 — Profit

Profit uses historical FIFO cost.

### FR-SAL-005 — Custom Price

A sale may use a price different from default without modifying default price.

### FR-SAL-006 — Discounts

Discounts are optional.

### FR-SAL-007 — FIFO Allocation

Consume oldest available lots first and preserve exact allocations.

### FR-SAL-008 — Full Collection

A completed V1 sale is fully collected.

### FR-SAL-009 — No Credit Sales

No credit, partial customer payments, accounts receivable or installments.

### FR-SAL-010 — Sale Account Currency

Receiving account currency must equal sale currency.

### FR-SAL-011 — COGS Source

Exact historical COGS comes from FIFO lot allocations.

---

## 9. Returns and Refunds

### FR-RET-001 — Customer Return

Reference an original sale.

### FR-RET-002 — Return Items

Each returned item references an original sale item.

### FR-RET-003 — Partial Return

Partial returns are supported.

### FR-RET-004 — Return Quantity Validation

Returned quantity cannot exceed net quantity sold.

### FR-RET-005 — Condition

V1 supports `SELLABLE` and `DAMAGED`.

### FR-RET-006 — Sellable Return

Restore the appropriate historical inventory lot.

### FR-RET-007 — Damaged Return

Record it without increasing sellable stock.

### FR-RET-008 — Historical Cost

Use historical cost from original sale allocations.

### FR-RET-009 — Partial FIFO Reversal

Reverse the most recently consumed allocation of the original sale item first.

### FR-RET-010 — Customer Refund

Create a `CUSTOMER_REFUND` financial movement.

### FR-RET-011 — Partial Refund

Partial monetary refunds are supported.

### FR-RET-012 — Original Sale Preservation

Returns/refunds do not delete original sale or original financial movement.

### FR-RET-013 — Sale Status

Returns may lead to `PARTIALLY_REFUNDED` or `REFUNDED`.

### FR-RET-014 — Supplier Return

Reference original purchase and merchandise.

### FR-RET-015 — Partial Supplier Return

Allow partial supplier returns.

### FR-RET-016 — Supplier Return Inventory

Remove returned merchandise and preserve exact inventory lot.

### FR-RET-017 — Supplier Return Cost

Preserve historical acquisition cost.

### FR-RET-018 — Supplier Refund

Create a `SUPPLIER_REFUND` financial movement when money is returned.

### FR-RET-019 — Supplier Return History

Do not rewrite original purchase.

### FR-RET-020 — Customer Refund Currency

Customer refund currency equals original sale currency and refund account currency.

### FR-RET-021 — Supplier Refund Currency

Supplier refund currency equals original purchase currency and receiving account currency.

### FR-RET-022 — Supplier Refund Direction

Supplier refund is a positive financial movement.

### FR-RET-023 — Customer Refund Direction

Customer refund is a negative financial movement.

---

## 10. Expenses

### FR-EXP-001 — Register Expense

Required: amount, currency, account, date, type.

Optional: description, notes.

### FR-EXP-002 — Categories

Examples: advertising, transportation, packaging, internet, delivery, commission, other.

### FR-EXP-003 — Purchase Cost Separation

Acquisition costs belong to purchases. General operating costs belong to expenses.

### FR-EXP-004 — Expense Account Currency

Expense currency must match paying account currency.

---

## 11. Accounts

### FR-ACC-001 — Create Account

Required: name, currency.

Optional: account type, notes.

### FR-ACC-002 — Balance

Balance derives from financial movements.

### FR-ACC-003 — Transfer

Support transfers between accounts.

### FR-ACC-004 — Same Currency Transfer

No FX rate required.

### FR-ACC-005 — Cross Currency Transfer

Applicable FX data is required.

### FR-ACC-006 — Account Currency Compatibility

Direct financial operations use an account whose currency matches operation currency.

### FR-ACC-007 — Explicit Currency Exchange

Cross-currency movement is represented explicitly and preserves source/destination amounts, currencies and exchange rate.

### FR-ACC-008 — Ledger Sign Convention

Money in is positive. Money out is negative.

---

## 12. Capital

### FR-CAP-001 — Contribution

Required: amount, currency, destination account, date.

Optional: notes.

### FR-CAP-002 — Withdrawal

Support capital withdrawals.

### FR-CAP-003 — Contributions

Contributions are not revenue or profit.

### FR-CAP-004 — Withdrawals

Withdrawals are not operating expenses.

### FR-CAP-005 — Capital Account Currency

Capital currency must match account currency.

---

## 13. Currencies

### FR-CUR-001 — Multiple Currencies

Initial:

```text
CUP USD EUR GBP CAD MXN MLC
```

Extensible without redesign.

### FR-CUR-002 — Base Currency

Configurable base currency.

### FR-CUR-003 — Original Currency

Preserve original transaction currency and amount.

### FR-CUR-004 — Converter

Provide conversion using suitable available rates.

---

## 14. Exchange Rates

### FR-EXR-001 — Automatic Rates

Configured providers may retrieve rates online. elTOQUE is an initial provider for applicable Cuban-market rates.

### FR-EXR-002 — Manual Rate

Required: base currency, quote currency, rate, date.

Optional: time, notes.

### FR-EXR-003 — Offline Rates

Manual rates work offline.

### FR-EXR-004 — Local Persistence

Automatic rates are stored locally.

### FR-EXR-005 — Offline Fallback

Offer suitable stored rate and show source/timestamp/age.

### FR-EXR-006 — Missing Rate

Request manual input. Never invent a rate.

### FR-EXR-007 — Stale Rate

Clearly identify stale rates.

### FR-EXR-008 — Historical Rate

Preserve the rate used by each historical operation.

### FR-EXR-009 — Manual Override

Allow a proposed rate to be replaced for an operation.

### FR-EXR-010 — Rate History

Rate history and sources are viewable.

---

## 15. Suppliers

### FR-SUP-001 — Create Supplier

Required: name.

Optional: type, website, contact, notes.

### FR-SUP-002 — Purchase History

View purchases by supplier.

### FR-SUP-003 — Analytics

Analyze volume and profitability by supplier/platform.

---

## 16. Customers

### FR-CUS-001 — Create Customer

Required: name.

Optional: phone, email, social contact, notes.

### FR-CUS-002 — Optional Customer

A customer is not required for a sale.

### FR-CUS-003 — History

Customer sales history is viewable.

---

## 17. Analytics

### FR-ANA-001 — Profit

Calculate gross and net profit.

### FR-ANA-002 — Margin

Calculate applicable margins.

### FR-ANA-003 — ROI

Calculate ROI using documented formulas.

### FR-ANA-004 — Product Analytics

Identify best-selling, most profitable and slow-moving products.

### FR-ANA-005 — Supplier Analytics

Analyze profitability by supplier/platform.

### FR-ANA-006 — Period Filters

Support date ranges.

### FR-ANA-007 — Additional Filters

Product, category, supplier, customer, currency and account where applicable.

### FR-ANA-008 — Returns

Analytics must correctly account for customer and supplier returns/refunds.

---

## 18. Backup and Restore

### FR-BKP-001 — Backup

Create local backups.

### FR-BKP-002 — Restore

Restore compatible backups.

### FR-BKP-003 — Offline

Backup/restore works without Internet.

### FR-BKP-004 — Export

Selected business information can be exported.

---

## 19. Settings

### FR-SET-001 — Configuration

Include base currency, enabled currencies, FX provider, automatic updates, freshness threshold, default account, date format and backup location.

### FR-SET-002 — Manual-Only Rates

Automatic FX retrieval may be disabled.

---

## 20. Non-Functional Requirements

### NFR-OFF-001 — Offline First

Core functionality works without Internet.

### NFR-OFF-002 — External Failure Isolation

External provider failure must not make the app unavailable.

### NFR-FIN-001 — Precision

Money uses decimal arithmetic.

### NFR-FIN-002 — Historical Integrity

Historical financial values remain stable when current values change.

### NFR-FIN-003 — Explicit Financial Sources

Ledger records preserve traceable relationships to originating business operations.

### NFR-FIN-004 — No Implicit FX

Direct operations never silently convert currencies.

### NFR-DATA-001 — Referential Integrity

Enforce relationships.

### NFR-DATA-002 — Atomicity

Multi-record business operations are atomic.

### NFR-DATA-003 — Traceability

Inventory and financial changes are traceable.

### NFR-DATA-004 — Non-Destructive History

Use cancellation, refund, reversal or adjustment instead of destructive rewrites.

### NFR-DATA-005 — Quantity Integrity

V1 merchandise quantities use positive integral units where applicable.

### NFR-UX-001 — Field Requirements

Forms distinguish required, optional and conditional fields.

### NFR-UX-002 — Optional Information

Do not force irrelevant information.

### NFR-UX-003 — Validation

Validation explains what is invalid and why.

### NFR-ARCH-001 — Separation

Business logic remains independent of UI, DB engine and external APIs.

### NFR-ARCH-002 — Replaceable Infrastructure

Infrastructure implementations are replaceable.

### NFR-SEC-001 — Secrets

API tokens and credentials are not ordinary plaintext settings.

### NFR-TST-001 — Testability

Core business logic is testable without UI, Internet or live APIs.

### NFR-PER-001 — Responsiveness

Network/I/O operations do not freeze desktop UI.

---

## 21. V1 Scope

Included:

- Dashboard
- Products
- Variants
- FIFO inventory
- Inventory lots
- Inventory movements
- Purchases
- Partial order receipt
- Purchase costs
- Sales
- Full payment
- Customer returns
- Supplier returns
- Refunds
- Expenses
- Accounts
- Capital
- Multiple currencies
- Automatic/manual FX
- Offline operation
- Converter
- Suppliers
- Customers
- Analytics
- Reports
- Backup
- Restore
- Export
- Settings

---

## 22. Out of Scope

- Cloud synchronization
- Multiple users
- Authentication
- Mobile app
- Web app
- Online store
- Automatic marketplace imports
- Barcode hardware
- Electronic invoicing
- Employees
- AI features
- Remote DB
- Credit
- Partial payments
- Accounts receivable/payable

---

## 23. Definition of V1 Complete

V1 is complete when:

1. Products and variants work.
2. Purchases support optional acquisition costs.
3. Purchase costs support foreign currencies and normalization.
4. Purchases use full payment.
5. Partial receipt works.
6. Received merchandise creates inventory lots.
7. FIFO works.
8. FIFO allocations are traceable.
9. Sales reduce inventory.
10. Sales use full collection.
11. Sales calculate COGS from FIFO allocations.
12. Customer returns may be partial/full.
13. Returned quantities cannot exceed net quantities sold.
14. Sellable returns restore historical lots.
15. Damaged returns do not increase sellable stock.
16. Supplier returns remove exact historical lots.
17. Customer/supplier refunds create financial movements.
18. Original operations remain preserved.
19. Expenses work.
20. Capital remains separate from profit/expenses.
21. Accounts/currencies coexist.
22. Account-currency compatibility is enforced.
23. Cross-currency movement is explicit.
24. Automatic/manual FX work offline.
25. Historical rates are preserved.
26. Analytics correctly account for returns/refunds.
27. Optional/conditional fields behave correctly.
28. Backup/restore works.
29. Critical business rules have automated tests.
