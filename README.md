# Resale Manager

Offline-first desktop application for independent resellers.

## Business Flow

```text
Capital → Purchases → Orders → Inventory → Sales → Profit → Reinvestment
```

## V1 Highlights

- Products and flexible variants
- FIFO inventory costing
- Inventory lots and movement history
- Purchase/order tracking
- Partial order receipt
- Optional acquisition costs
- Full-payment sales and purchases
- Customer returns/refunds
- Supplier returns/refunds
- Accounts, capital and operating expenses
- Multi-currency
- Manual and automatic exchange rates
- Offline-first operation
- Analytics
- Backup and restore

## Documentation

Read in this order:

1. `docs/REQUIREMENTS.md`
2. `docs/ARCHITECTURE.md`
3. `docs/DATABASE.md`
4. `docs/ERD.md`
5. `docs/TECH_STACK.md`
6. `docs/ROADMAP.md`
7. `docs/ANALYTICS.md`

## Current State

Phases 0-11 completed (bootstrap, money/currency, product catalog, accounts and
ledger, purchases, receiving, inventory lots, FIFO sales, customer returns,
supplier returns, expenses, capital, exchange-rate providers and analytics).
Phase 12 (Desktop UI) is in progress with the application shell and navigation:

- Python virtual environment support
- `pyproject.toml` with SQLAlchemy, Alembic, pydantic-settings, httpx and
  PySide6
- SQLite engine/session with foreign-key enforcement
- Exact `Decimal` storage on SQLite (no binary float)
- `Currency`, `Money` and `ExchangeRate` domain objects
- Manual rate storage with append-only history
- Account/operation currency compatibility rules
- Categories, products and product variants
- Flexible attributes and variant attribute values
- Unique SKUs and non-destructive product/variant deactivation
- `CreateProduct` use case with automatic default variant
- Accounts with one native currency and non-destructive deactivation
- Signed financial ledger with fixed inflow/outflow rules
- Capital contributions and withdrawals linked to their ledger entries
- Exact balance derivation from signed ledger amounts
- Same-currency transfers and explicit cross-currency exchange
- Historical exchange rates preserved by every currency exchange
- Suppliers with non-destructive deactivation
- Purchases, purchase items, additional costs and cost allocations
- Full-payment purchases linked to `PURCHASE` ledger entries
- Purchase status transitions with protected receipt states
- Exact allocation by quantity, value, weight or manual amounts
- Foreign-currency cost normalization using historical exchange rates
- Inventory lots with FIFO ordering and immutable acquisition data
- Traceable inventory movements with fixed inflow/outflow signs
- Partial and multiple purchase receipts with over-receipt rejection
- Received quantity and purchase status derived from inventory lots
- Lot unit cost including allocated purchase costs
- Current stock queries per product variant
- Fully collected sales with account/sale currency compatibility
- FIFO lot selection across multiple lots with exact exhaustion
- Immutable `SaleItemLotAllocation` cost snapshots for historical COGS
- Atomic inventory reduction, `SALE` movements and `SALE` ledger entries
- Revenue, COGS and gross-profit calculation without implicit FX
- Customer returns against an original sale with partial-return support
- `SELLABLE` returns restore the historical lot with `CUSTOMER_RETURN`
  movements
- `DAMAGED` returns are recorded without increasing sellable stock
- Partial FIFO reversal from the most recently consumed sale allocation
- Customer refunds with `CUSTOMER_REFUND` ledger entries and sale status
  updates
- Supplier returns against the original purchase item and exact inventory lot
- Partial supplier returns with negative `SUPPLIER_RETURN` inventory movements
- Historical lot unit cost snapshotted without rewriting the original purchase
- Supplier refunds with positive `SUPPLIER_REFUND` ledger entries and purchase
  currency checks
- Operating expenses with documented categories, optional descriptions and notes
- Expenses paid from an active account in its native currency
- Negative `EXPENSE` ledger entries linked to their originating expense
- Expenses kept separate from purchase acquisition costs
- Capital contributions and withdrawals kept separate from operating expenses
- Replaceable `ExchangeRateProvider` port for exchange-rate observations
- `ManualRateProvider` backed by locally stored manual rates
- `ElToqueProvider` isolated in Infrastructure and configured by token, URL and
  timeout
- `SetManualExchangeRate` use case for first-class manual rate records
- `UpdateExchangeRates` persists successful automatic observations locally
- `ResolveExchangeRate` provides offline lookup with source, timestamp and age
- Stale rates are explicitly identified and can be rejected by callers
- Provider failures fall back to stored rates instead of blocking the app
- Manual-only operation remains the default; online FX is optional
- Historical exchange-rate lookup at or before a reporting cutoff
- Period analytics with product, category, supplier, customer, currency and
  account filters
- Revenue net of item/sale discounts and customer-return value
- FIFO historical COGS net of returned FIFO cost
- Gross profit, operating expenses, net profit and margins in native currencies
- Cross-currency sales excluded from native profit instead of using implicit FX
- Customer refunds and supplier refunds reported separately without double
  counting
- Current inventory value, best sellers, most profitable products and
  slow-moving stock
- Supplier profitability with revenue/COGS attribution, volume and refunds
- Native account balances at a reporting cutoff
- Base-currency consolidated reporting with direct stored rates, explicit
  missing-rate reporting and cash-capital ROI
- `BASE_CURRENCY` and `ANALYTICS_SLOW_MOVING_DAYS` configuration
- PySide6 desktop shell with sidebar navigation and one screen per section
- Placeholder screens isolated from business logic, ready to be replaced
  incrementally by use-case-driven views
- Products screen with catalog search, inactive-product toggle and refresh
- Create/edit product dialogs with category, brand, default price, currency and
  an optional initial variant
- Product activation/deactivation without deleting catalog history
- Variant management with SKU, barcode, activation and attribute values
- Attribute management with reusable attributes and values
- Create-category dialog from the product catalog screen
- Read-only product and variant table models; the UI formats values but never
  calculates prices, stock or profit
- Accounts screen with native-currency balances, search and inactive filter
- Create-account dialog with native currency, type and notes
- Account activation/deactivation without deleting ledger history
- Purchases screen with supplier, order, item count, total, payment state and
  logistics status, plus search and status filtering
- Create-purchase dialog with supplier creation, optional immediate full
  payment, multiple items and automatic additional-cost allocation
- Read-only purchase detail with item lines, normalized costs and totals
- Full-payment and logistics-status dialogs driven by the existing purchase use
  cases, without duplicating financial rules in the UI
- Application-level `UnitOfWork` boundary with a SQLAlchemy implementation, so
  screens never open sessions or commit transactions
- Alembic migrations with the initial currencies seeded
- pytest test suite (domain, application, integration and presentation)

Next milestone (in progress):

```text
Phase 12 — Desktop UI
✔ App shell and navigation
✔ Products screen (list, search, create/edit/deactivate, variants, attributes)
✔ Accounts screen (native balances, create and deactivate)
✔ Purchases screen (list, search, create, costs, payments, status, suppliers)
→ Receiving screen
```

FIFO allocations are immutable and remain the source of truth for historical
sale COGS. Supplier return items reference their exact inventory lot and
snapshot its historical unit cost; the original purchase is never rewritten.
Expenses never modify historical purchase costs. Exchange-rate providers never
invent missing rates or overwrite historical observations.

## Getting Started

```text
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"

copy .env.example .env

alembic upgrade head
python -m app.main
python -m app.main --check   # database diagnostics without opening the UI
pytest
```

On POSIX systems, replace the activation and copy commands with:

```text
source .venv/bin/activate
cp .env.example .env
```
