# Resale Manager — V1 Roadmap

## Phase 0 — Repository Bootstrap

Goal: create a clean project foundation.

Tasks:

1. Initialize Git repository.
2. Create Python virtual environment.
3. Create `pyproject.toml`.
4. Add project package structure only as needed.
5. Configure pytest.
6. Configure SQLAlchemy base and SQLite connection.
7. Configure Alembic.
8. Add `.env.example`.
9. Make first migration runnable.

Exit criteria:

- App can start.
- Tests run.
- SQLite can be created.
- Alembic migration succeeds.

---

## Phase 1 — Core Money and Currency Domain

Implement:

- Currency
- Money
- ExchangeRate
- Decimal rules
- Manual rate storage
- Account-currency compatibility rules

Tests first for:

- Money arithmetic
- Currency mismatch rejection
- Exchange-rate validity
- Historical rate immutability assumptions

Exit criteria:

- Monetary primitives are stable.

---

## Phase 2 — Product Catalog

Implement:

- Category
- Product
- ProductVariant
- Attributes
- Attribute values
- SKU uniqueness
- Disable/inactivate behavior

Exit criteria:

- Products/variants can be created and queried.
- No inventory logic yet.

---

## Phase 3 — Accounts and Ledger Foundation

Implement:

- Account
- FinancialTransaction
- CapitalMovement
- Ledger sign convention
- Account balance calculation
- Same-currency transfer

Then:

- Cross-currency transfer
- Currency exchange

Exit criteria:

- Account balances are derived correctly.
- Currency compatibility rules are enforced.

---

## Phase 4 — Purchases

Implement:

- Supplier
- Purchase
- PurchaseItem
- PurchaseCost
- PurchaseCostAllocation
- Full-payment rule
- Purchase status transitions
- Purchase-cost currency normalization

Exit criteria:

- A purchase with optional costs can be persisted.
- Foreign-currency costs normalize correctly.

---

## Phase 5 — Receiving and Inventory Lots

Implement:

- Partial receipt
- InventoryLot
- InventoryMovement
- `PARTIALLY_RECEIVED`
- `RECEIVED`
- Inventory stock queries

Tests:

- Multiple receipts
- Over-receipt rejection
- Current stock
- Movement signs

Exit criteria:

- Received inventory is traceable to purchase lots.

---

## Phase 6 — FIFO Sales

Implement:

- Sale
- SaleItem
- FIFO lot selection
- SaleItemLotAllocation
- Inventory reduction
- SALE financial transaction
- Gross profit / COGS

Tests:

- One-lot sale
- Multi-lot sale
- Exact exhaustion
- Insufficient stock
- FIFO ordering
- Historical COGS

Exit criteria:

- A complete sale is atomic and financially correct.

---

## Phase 7 — Customer Returns

Implement:

- CustomerReturn
- CustomerReturnItem
- ReturnLotAllocation
- SELLABLE
- DAMAGED
- Partial returns
- Customer refund
- Sale status update

Tests:

- Sellable return restores lot
- Damaged return does not restore sellable stock
- Partial FIFO reversal
- Excess return rejected
- Customer refund sign

---

## Phase 8 — Supplier Returns

Implement:

- SupplierReturn
- SupplierReturnItem
- Inventory reduction
- Supplier refund
- Historical lot cost

Tests:

- Partial supplier return
- Wrong-lot return rejected
- Excess return rejected
- Supplier refund sign

---

## Phase 9 — Expenses and Capital

Implement:

- Expenses
- Expense categories
- Capital contributions
- Capital withdrawals
- Financial ledger integration

---

## Phase 10 — Exchange Rate Provider Integration

Implement Infrastructure only after manual FX works:

- `ExchangeRateProvider` interface
- `ManualRateProvider`
- `ElToqueProvider`
- Cache/local persistence
- Stale-rate behavior
- Connectivity failure handling

Never make online FX a prerequisite for business operations.

---

## Phase 11 — Analytics

Implement queries/use cases for:

- Revenue
- COGS
- Gross profit
- Net profit
- Expenses
- Refunds
- Inventory value
- Best sellers
- Most profitable products
- Slow-moving stock
- Supplier profitability
- Account balances
- Base-currency consolidated reporting

Document ROI formula before implementing ROI.

---

## Phase 12 — Desktop UI

Do not start with the full UI.

Build screens incrementally around completed use cases:

1. App shell/navigation
2. Products
3. Accounts
4. Purchases
5. Receiving
6. Inventory
7. Sales
8. Returns
9. Expenses/capital
10. Currency rates
11. Dashboard
12. Analytics
13. Settings

UI never calculates FIFO, profit or account balances itself.

---

## Phase 13 — Backup / Restore / Export

Implement:

- Local SQLite backup
- Restore validation
- Basic export
- Backup location setting

---

## Phase 14 - Hardening

Status: complete.

Before V1 release:

- Run full test suite
- Validate migrations from clean DB
- Test corrupted/invalid input paths
- Test offline mode
- Test stale FX
- Test backup restore
- Review indexes/query plans if needed
- Package desktop executable

---

## First Build Milestone

Do not attempt the whole project immediately.

The first coding milestone is:

```text
Project bootstrap
+
SQLite / SQLAlchemy / Alembic
+
Currency
+
ExchangeRate
+
Account
+
Product
+
ProductVariant
```

No FIFO implementation until these foundations are stable.
