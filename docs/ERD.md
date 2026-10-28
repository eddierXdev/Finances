# Resale Manager — ERD

## 1. Core Diagram

```mermaid
erDiagram

    CURRENCIES ||--o{ EXCHANGE_RATES : base
    CURRENCIES ||--o{ EXCHANGE_RATES : quote
    CURRENCIES ||--o{ ACCOUNTS : native_currency

    CATEGORIES ||--o{ PRODUCTS : classifies
    PRODUCTS ||--|{ PRODUCT_VARIANTS : contains

    ATTRIBUTES ||--|{ ATTRIBUTE_VALUES : contains
    PRODUCT_VARIANTS ||--o{ VARIANT_ATTRIBUTE_VALUES : has
    ATTRIBUTE_VALUES ||--o{ VARIANT_ATTRIBUTE_VALUES : assigned

    SUPPLIERS ||--o{ PURCHASES : supplies
    PURCHASES ||--|{ PURCHASE_ITEMS : contains
    PRODUCT_VARIANTS ||--o{ PURCHASE_ITEMS : purchased

    PURCHASES ||--o{ PURCHASE_COSTS : has
    PURCHASE_COSTS ||--o{ PURCHASE_COST_ALLOCATIONS : allocates
    PURCHASE_ITEMS ||--o{ PURCHASE_COST_ALLOCATIONS : receives

    PURCHASE_ITEMS ||--o{ INVENTORY_LOTS : creates
    PRODUCT_VARIANTS ||--o{ INVENTORY_LOTS : stocked_as
    PRODUCT_VARIANTS ||--o{ INVENTORY_MOVEMENTS : moves
    INVENTORY_LOTS ||--o{ INVENTORY_MOVEMENTS : traced_by

    CUSTOMERS ||--o{ SALES : places
    SALES ||--|{ SALE_ITEMS : contains
    PRODUCT_VARIANTS ||--o{ SALE_ITEMS : sold

    SALE_ITEMS ||--|{ SALE_ITEM_LOT_ALLOCATIONS : consumes
    INVENTORY_LOTS ||--o{ SALE_ITEM_LOT_ALLOCATIONS : allocated_from

    SALES ||--o{ CUSTOMER_RETURNS : has
    CUSTOMER_RETURNS ||--|{ CUSTOMER_RETURN_ITEMS : contains
    SALE_ITEMS ||--o{ CUSTOMER_RETURN_ITEMS : returned_from

    CUSTOMER_RETURN_ITEMS ||--o{ RETURN_LOT_ALLOCATIONS : creates
    SALE_ITEM_LOT_ALLOCATIONS ||--o{ RETURN_LOT_ALLOCATIONS : reverses

    PURCHASES ||--o{ SUPPLIER_RETURNS : has
    SUPPLIER_RETURNS ||--|{ SUPPLIER_RETURN_ITEMS : contains
    PURCHASE_ITEMS ||--o{ SUPPLIER_RETURN_ITEMS : original_item
    INVENTORY_LOTS ||--o{ SUPPLIER_RETURN_ITEMS : returned_from

    ACCOUNTS ||--o{ EXPENSES : pays
    ACCOUNTS ||--o{ CAPITAL_MOVEMENTS : affects

    ACCOUNTS ||--o{ ACCOUNT_TRANSFERS : source
    ACCOUNTS ||--o{ ACCOUNT_TRANSFERS : destination

    ACCOUNTS ||--o{ FINANCIAL_TRANSACTIONS : contains
    PURCHASES ||--o{ FINANCIAL_TRANSACTIONS : source
    SALES ||--o{ FINANCIAL_TRANSACTIONS : source
    EXPENSES ||--o{ FINANCIAL_TRANSACTIONS : source
    CUSTOMER_RETURNS ||--o{ FINANCIAL_TRANSACTIONS : source
    SUPPLIER_RETURNS ||--o{ FINANCIAL_TRANSACTIONS : source
    CAPITAL_MOVEMENTS ||--o{ FINANCIAL_TRANSACTIONS : source
    ACCOUNT_TRANSFERS ||--o{ FINANCIAL_TRANSACTIONS : source
```

---

## 2. Purchase Flow

```text
Supplier
   ↓
Purchase
   ↓
PurchaseItem
   ↓
InventoryLot
```

A purchase item may create multiple lots because receipts may be partial.

```text
Ordered: 10
Receipt 1: 6
Receipt 2: 4
```

---

## 3. Purchase Cost Flow

```text
Purchase
   ↓
PurchaseCost
   ↓
PurchaseCostAllocation
   ↑
PurchaseItem
```

Foreign-currency costs preserve original values and normalized purchase-currency values.

---

## 4. FIFO Sale Flow

```text
Sale
 ↓
SaleItem
 ↓
SaleItemLotAllocation
 ↓
InventoryLot
```

One sale item may consume multiple lots.

---

## 5. Customer Return Flow

```text
Sale
 ↓
CustomerReturn
 ↓
CustomerReturnItem
 ↓
ReturnLotAllocation
 ↓
SaleItemLotAllocation
 ↓
InventoryLot
```

A sellable return restores the historically consumed lot.

---

## 6. Supplier Return Flow

```text
Purchase
 ↓
SupplierReturn
 ↓
SupplierReturnItem
 ↓
InventoryLot
```

Supplier returns remove stock from the exact historical lot.

---

## 7. Financial Flow

```text
Business Operation
      ↓
FinancialTransaction
      ↓
Account
```

Examples:

```text
Sale             → +SALE
Purchase         → -PURCHASE
Expense          → -EXPENSE
Customer Return  → -CUSTOMER_REFUND
Supplier Return  → +SUPPLIER_REFUND
Capital In       → +CAPITAL_CONTRIBUTION
Capital Out      → -CAPITAL_WITHDRAWAL
```

---

## 8. Closed V1 Decisions

```text
Architecture       → Offline-first layered architecture
Database           → SQLite initially
Money              → Decimal
Quantities         → Integer units
Inventory costing  → FIFO
Inventory origin   → Inventory lots
Sale cost source   → FIFO allocations
Payments           → Full payment only
Credit             → Out of scope
Partial payments   → Out of scope
Partial receipts   → Supported
Customer returns   → Supported
Supplier returns   → Supported
Manual FX          → Supported
Automatic FX       → Supported
Internet           → Optional
Direct account FX  → Not implicit
```

---

## 9. Schema Readiness

Logical design is ready for physical implementation.

Implementation sequence:

```text
Logical model
    ↓
SQLAlchemy base/config
    ↓
Enums/value constraints
    ↓
Core catalog tables
    ↓
Products/variants
    ↓
Purchases/costs
    ↓
Inventory lots/movements
    ↓
Sales/FIFO allocations
    ↓
Returns
    ↓
Accounts/ledger
    ↓
Migrations
    ↓
Application use cases
```

Do not introduce new major V1 features during schema implementation unless required for correctness.
