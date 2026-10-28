# Resale Manager — Architecture

## 1. Project Overview

Resale Manager is an **offline-first desktop application** for small and independent resellers.

The application manages the complete business lifecycle:

```text
Capital → Purchases → Orders → Inventory → Sales → Profit → Reinvestment
```

It supports:

- Products and variants
- Inventory and FIFO costing
- Purchases and order tracking
- Sales
- Customer returns and refunds
- Supplier returns and refunds
- Expenses
- Capital
- Accounts and wallets
- Multiple currencies
- Manual and automatic exchange rates
- Suppliers
- Customers
- Analytics
- Backup, restore and export

Internet connectivity enhances specific features but is **not required for core business operations**.

The architecture prioritizes:

- Maintainability
- Scalability
- Testability
- Offline-first operation
- Clear separation of responsibilities
- Replaceable infrastructure
- Business logic independent from the UI
- Business logic independent from external APIs
- Future migration to API/cloud architecture
- Future support for multiple frontends

---

## 2. Architecture Style

The project uses a **layered architecture inspired by Clean Architecture**.

```text
┌─────────────────────────────────────┐
│          Presentation Layer         │
│        Desktop UI / Views           │
├─────────────────────────────────────┤
│          Application Layer          │
│      Use Cases / Application        │
│             Services                │
├─────────────────────────────────────┤
│            Domain Layer             │
│ Entities / Business Rules / Values  │
├─────────────────────────────────────┤
│        Infrastructure Layer         │
│ DB / APIs / Repositories / Files    │
└─────────────────────────────────────┘
```

Dependency direction:

```text
Presentation
     │
     ▼
Application
     │
     ▼
Domain

Infrastructure
     │
     └────────► Domain / Application interfaces
```

The Domain must not depend on:

- UI frameworks
- SQLite
- PostgreSQL
- HTTP APIs
- elTOQUE
- Internet connectivity
- File formats
- Operating-system-specific functionality

---

## 3. Proposed Project Structure

```text
resale_manager/
│
├── app/
│   ├── domain/
│   │   ├── entities/
│   │   ├── value_objects/
│   │   ├── enums/
│   │   ├── exceptions/
│   │   └── repositories/
│   │
│   ├── application/
│   │   ├── products/
│   │   ├── purchases/
│   │   ├── sales/
│   │   ├── returns/
│   │   ├── inventory/
│   │   ├── finances/
│   │   ├── currencies/
│   │   ├── customers/
│   │   ├── suppliers/
│   │   └── analytics/
│   │
│   ├── infrastructure/
│   │   ├── database/
│   │   │   ├── models/
│   │   │   ├── repositories/
│   │   │   ├── migrations/
│   │   │   └── session.py
│   │   ├── exchange_rates/
│   │   ├── connectivity/
│   │   ├── backup/
│   │   ├── exports/
│   │   └── config/
│   │
│   ├── presentation/
│   │   └── desktop/
│   │       ├── views/
│   │       ├── components/
│   │       ├── dialogs/
│   │       └── navigation/
│   │
│   └── main.py
│
├── tests/
│   ├── unit/
│   ├── application/
│   └── integration/
│
├── data/
├── docs/
│   ├── ARCHITECTURE.md
│   ├── REQUIREMENTS.md
│   ├── DATABASE.md
│   ├── ERD.md
│   ├── TECH_STACK.md
│   └── ROADMAP.md
│
├── .ai/
│   ├── instructions.md
│   └── exercise_rules.md
│
├── .env.example
├── .gitignore
├── pyproject.toml
└── README.md
```

Create files only when needed. Do not generate empty modules merely to mirror this tree.

---

## 4. Domain Concepts

Primary concepts include:

- Product
- ProductVariant
- Purchase
- PurchaseItem
- PurchaseCost
- Sale
- SaleItem
- CustomerReturn
- CustomerReturnItem
- SupplierReturn
- SupplierReturnItem
- InventoryLot
- InventoryMovement
- Expense
- Account
- FinancialTransaction
- CapitalMovement
- Supplier
- Customer
- ExchangeRate
- Money
- Currency

Core rules include:

- Stock cannot become negative.
- Quantities are positive integral units in V1.
- Monetary operations use decimal arithmetic.
- Direct financial operations must use an account with the same native currency as the operation.
- Currency conversion must be explicit.
- Received purchases create inventory.
- Sales reduce inventory.
- Inventory costing uses FIFO.
- Historical FIFO allocations are immutable.
- Historical exchange rates are immutable.
- Returned merchandise uses historical sale or purchase cost.
- Sellable customer returns restore stock.
- Damaged customer returns do not restore sellable stock.
- Supplier returns remove stock.
- Profit is calculated from historical transaction data.

---

## 5. Money and Currency

Money must never use binary floating-point arithmetic.

Conceptually:

```text
Money
├── amount
└── currency
```

Initial V1 currencies:

```text
CUP
USD
EUR
GBP
CAD
MLC
MXN
```

Additional currencies must be possible without architectural changes.

---

## 6. Accounts and Transaction Currency

Each account has one native currency.

Examples:

```text
Cash CUP
Cash USD
Zelle USD
Card
Bank Account
```

In V1:

```text
operation currency = account currency
```

Examples:

```text
Purchase: 20 USD
Account: Cash USD
→ valid
```

```text
Purchase: 20 USD
Account: Cash CUP
→ invalid
```

If funds are held in another currency:

```text
Cash CUP
   ↓
Currency Exchange
   ↓
Cash USD
   ↓
Purchase
```

Currency conversion is an explicit financial operation.

---

## 7. Financial Ledger

Financial movements are traceable.

Types:

```text
CAPITAL_CONTRIBUTION
CAPITAL_WITHDRAWAL
PURCHASE
SALE
EXPENSE
CUSTOMER_REFUND
SUPPLIER_REFUND
TRANSFER
CURRENCY_EXCHANGE
ADJUSTMENT
```

Sign convention:

```text
Money entering account → positive
Money leaving account  → negative
```

Examples:

```text
CAPITAL_CONTRIBUTION    +200
SALE                     +40
SUPPLIER_REFUND          +20

PURCHASE                 -80
EXPENSE                  -10
CUSTOMER_REFUND          -15
CAPITAL_WITHDRAWAL       -30
```

Account balance:

```text
SUM(financial_transactions.amount)
```

Financial transactions should reference their originating business records through explicit foreign keys.

---

## 8. V1 Payment Model

V1 uses **full payment only**.

Not supported:

- Credit sales
- Partial customer payments
- Supplier credit
- Partial purchase payments
- Accounts receivable
- Accounts payable
- Payment installments

A completed sale is fully collected.

A financially completed purchase is fully paid.

---

## 9. Exchange Rates

Exchange rates are historical financial data.

Each rate contains at minimum:

```text
base_currency
quote_currency
rate
source
timestamp
```

V1 sources:

```text
ELTOQUE
MANUAL
```

Manual rates are first-class records.

The application:

- Works without Internet.
- Stores automatic rates locally.
- Shows source and age.
- Allows stale stored rates when the user accepts them.
- Allows manual rates.
- Never invents a missing rate.
- Never overwrites historical transaction rates.

---

## 10. Offline-First Behavior

The local database is the primary operational source.

Core functionality must work offline:

- Product management
- Purchases
- Receiving orders
- Inventory
- Sales
- Customer returns
- Supplier returns
- Expenses
- Accounts
- Capital
- Reports
- Stored/manual exchange rates
- Backup and restore

External network requests must not block the desktop UI thread.

---

## 11. Purchases

A purchase may contain multiple items and optional acquisition costs.

Statuses:

```text
PENDING
PURCHASED
SHIPPED
IN_TRANSIT
PARTIALLY_RECEIVED
RECEIVED
CANCELLED
```

`REFUNDED` is not a logistics status.

Supplier returns/refunds are modeled separately.

A purchase may exist before `account_id` is known. When payment is recorded:

- `account_id` is required.
- Account currency must match purchase currency.
- A `PURCHASE` financial transaction is created.

---

## 12. Partial Purchase Receipt

A purchase item may arrive through multiple deliveries.

```text
ordered_quantity = purchase_items.quantity
received_quantity = SUM(inventory_lots.acquired_quantity)
remaining_quantity = ordered_quantity - received_quantity
```

Rules:

- Received quantity cannot exceed ordered quantity.
- Some but not all received → `PARTIALLY_RECEIVED`.
- All expected received → `RECEIVED`.
- Each receipt may create one or more inventory lots.
- Receipt processing is atomic.

---

## 13. Purchase Cost Currency Normalization

Purchase items define the purchase/costing currency.

Additional acquisition costs may use other currencies.

Example:

```text
Purchase items: USD
Shipping: EUR
Customs: CUP
```

Each cost preserves:

- Original amount
- Original currency
- Historical exchange rate

Before inventory costing, allocated cost is normalized into the purchase currency.

Inventory lots always store effective cost in the purchase currency.

---

## 14. Inventory

Two separate concepts are used:

### InventoryLot

Answers:

> Where did the stock come from and what did it cost?

### InventoryMovement

Answers:

> What happened to stock?

Movement sign convention:

```text
Stock entering sellable inventory → positive
Stock leaving sellable inventory  → negative
```

Examples:

```text
PURCHASE_RECEIVED    +10
CUSTOMER_RETURN       +1

SALE                  -2
SUPPLIER_RETURN       -1
DAMAGED               -1
LOST                  -1
```

---

## 15. FIFO Costing

V1 uses FIFO.

Example:

```text
Lot A → 10 × 5 USD
Lot B → 10 × 7 USD
```

Sale of 12:

```text
Lot A → 10
Lot B → 2
```

COGS:

```text
(10 × 5) + (2 × 7) = 64 USD
```

Exact historical COGS comes from:

```text
SaleItem
   ↓
SaleItemLotAllocation[]
```

COGS:

```text
SUM(allocation.quantity × allocation.unit_cost_snapshot)
```

`SaleItem` must not maintain a competing averaged historical cost.

---

## 16. Sales

A completed sale may atomically create:

```text
Sale
+
SaleItems
+
FIFO Lot Allocations
+
Inventory Movements
+
Financial Transaction
```

Sales are fully collected into one account whose currency matches the sale currency.

---

## 17. Customer Returns

A customer return references an original sale.

Partial returns are supported.

Conditions:

```text
SELLABLE
DAMAGED
```

Sellable return:

- Restores the appropriate historical lot.
- Creates a positive `CUSTOMER_RETURN` inventory movement.

Damaged return:

- Is historically recorded.
- Does not increase sellable stock.

Returned quantities cannot exceed net quantities originally sold.

---

## 18. FIFO Return Reversal

Customer returns use historical sale allocations.

For partial returns, allocations are reversed from the most recently consumed allocation of that sale item first.

Example:

```text
Original:
Lot A → 2 × 5 USD
Lot B → 1 × 7 USD

Return 1:
Lot B ← 1 × 7 USD
```

This is only a reversal strategy for a specific sale. Normal inventory costing remains FIFO.

---

## 19. Customer Refunds

Customer refund currency equals original sale currency.

Refund account currency must match that currency.

A refund creates:

```text
CUSTOMER_REFUND
```

with a negative amount.

Original sales and original `SALE` financial transactions are never deleted.

---

## 20. Supplier Returns

Supplier returns are modeled independently from customer returns.

```text
Purchase
   ↓
SupplierReturn
   ↓
SupplierReturnItem
   ↓
InventoryLot
```

Rules:

- Reference original purchase.
- Reference original purchase item.
- Preserve exact inventory lot.
- Allow partial returns.
- Remove inventory.
- Create `SUPPLIER_RETURN` inventory movement.
- Preserve historical acquisition cost.
- Do not rewrite the original purchase.

---

## 21. Supplier Refunds

Supplier refund currency equals original purchase currency.

Receiving account must use that currency.

A supplier refund creates:

```text
SUPPLIER_REFUND
```

with a positive amount.

---

## 22. Expenses and Capital

Expense currency must match paying account currency.

Capital contribution/withdrawal currency must match affected account currency.

Contributions are not revenue.

Withdrawals are not operating expenses.

---

## 23. Application Layer

Representative use cases:

```text
CreateProduct
RegisterPurchase
ReceivePurchase
RegisterSale
CancelSale
RegisterCustomerReturn
RegisterSupplierReturn
RegisterExpense
AddCapital
WithdrawCapital
TransferMoney
ExchangeCurrency
UpdateExchangeRates
SetManualExchangeRate
CalculateDashboard
GenerateProfitReport
```

The UI calls use cases, never the database directly.

Application services own transaction boundaries. A `UnitOfWork` exposes the
repositories needed by one operation and an explicit `commit`; Infrastructure
implements it with one SQLAlchemy session. Screens receive application services,
never sessions, and therefore cannot commit or query persistence directly.

---

## 24. Infrastructure Layer

Infrastructure contains:

- SQLite
- Future PostgreSQL
- elTOQUE provider
- Filesystem
- Backup/restore
- Export implementations
- Connectivity services

Application services must not contain raw SQL.

---

## 25. Atomicity

Multi-step business operations are atomic.

Example sale:

```text
BEGIN
Create sale
Create sale items
Allocate FIFO lots
Reduce lot quantities
Create inventory movements
Create SALE financial transaction
COMMIT
```

Example customer return:

```text
BEGIN
Create return
Create return items
Resolve historical allocations
Restore sellable lots when applicable
Create inventory movements
Create CUSTOMER_REFUND when applicable
Update sale status
COMMIT
```

Failure of a required step causes rollback.

---

## 26. Testing Strategy

High-priority tests:

- Money calculations
- Currency conversion
- Manual FX
- Offline fallback
- Purchase cost allocation
- Foreign-currency purchase costs
- FIFO allocation
- FIFO across multiple lots
- Partial receipts
- COGS
- Customer returns
- Damaged returns
- Supplier returns
- Refunds
- Account currency compatibility
- Ledger sign conventions
- Capital
- Historical exchange-rate integrity

Core tests must not require UI, Internet, or live APIs.

---

## 27. Future Scalability

V1:

```text
Desktop
   ↓
Application
   ↓
SQLite
```

Possible future architecture:

```text
Desktop ──┐
Web ──────┼──► FastAPI ──► Application ──► PostgreSQL
Mobile ───┘
```

Future features may include cloud sync, multiple users, authentication, credit, partial payments, and multiple payments per transaction.

---

## 28. Core Development Rules

1. Business logic does not belong in UI.
2. UI does not access the database directly.
3. Domain does not depend on Infrastructure.
4. Domain does not depend on Internet connectivity.
5. Money uses decimal arithmetic.
6. Historical exchange rates are preserved.
7. Inventory changes are traceable.
8. Financial movements are traceable.
9. Required/optional/conditional fields are explicit.
10. Optional costs remain optional.
11. Multi-step operations are atomic.
12. Derived data is not duplicated unnecessarily.
13. External services are replaceable.
14. elTOQUE is a provider, not a dependency.
15. Core operations work offline.
16. Manual exchange rates are first-class records.
17. Missing rates are never invented.
18. Inventory costing uses FIFO.
19. FIFO uses traceable inventory lots.
20. Historical FIFO allocations are immutable.
21. Customer returns reference original sales.
22. Supplier returns reference original purchases.
23. Partial returns are supported.
24. Sellable customer returns restore inventory.
25. Damaged customer returns do not restore sellable inventory.
26. Refunds create financial movements.
27. Original operations are never deleted to represent returns.
28. Purchases and sales use full payment in V1.
29. Credit and partial payments are outside V1.
30. Direct financial operations use account currency equal to operation currency.
31. Currency conversion is explicit.
32. Financial inflows are positive.
33. Financial outflows are negative.
34. Inventory inflows are positive.
35. Inventory outflows are negative.
36. Purchase costs preserve original and normalized currency values.
37. Inventory-lot cost uses purchase currency.
38. Customer refunds use original sale currency.
39. Supplier refunds use original purchase currency.
40. Exact sale COGS comes from FIFO allocations.
41. `PARTIALLY_RECEIVED` represents incomplete purchase receipt.
42. Code-facing names, identifiers, documentation and comments use English.
