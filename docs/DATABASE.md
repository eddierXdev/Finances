# Resale Manager — Database Design

## 1. General Rules

- Relational database.
- SQLite for V1.
- Future PostgreSQL migration should remain feasible.
- PK convention: `id`.
- Foreign keys enforced.
- Money uses fixed-precision decimal values.
- Never use binary float for money.
- Quantities are integers in V1.
- Historical business records are not normally physically deleted.
- Multi-record business operations are atomic.
- Business dates are separate from persistence timestamps.

Common timestamps:

```text
created_at
updated_at
```

---

## 2. currencies

```text
id              PK
code            UNIQUE NOT NULL
name            NOT NULL
symbol          NULL
decimal_places  NOT NULL
is_enabled      NOT NULL
created_at      NOT NULL
```

Initial codes:

```text
CUP USD EUR GBP CAD MXN MLC
```

---

## 3. exchange_rates

```text
id                  PK
base_currency_id    FK → currencies NOT NULL
quote_currency_id   FK → currencies NOT NULL
rate                DECIMAL NOT NULL
source              NOT NULL
rate_timestamp      DATETIME NOT NULL
notes               NULL
created_at          NOT NULL
```

Sources:

```text
ELTOQUE
MANUAL
```

Constraints:

```text
rate > 0
base_currency_id != quote_currency_id
```

Historical rows are immutable.

Recommended index:

```text
(base_currency_id, quote_currency_id, rate_timestamp)
```

---

## 4. accounts

```text
id              PK
name            NOT NULL
currency_id     FK → currencies NOT NULL
account_type    NULL
is_active       NOT NULL
notes           NULL
created_at      NOT NULL
updated_at      NOT NULL
```

Each account has one native currency.

---

## 5. suppliers

```text
id              PK
name            NOT NULL
supplier_type   NULL
website         NULL
contact         NULL
notes           NULL
is_active       NOT NULL
created_at      NOT NULL
updated_at      NOT NULL
```

---

## 6. categories

```text
id              PK
name            NOT NULL
description     NULL
created_at      NOT NULL
```

---

## 7. products

```text
id                      PK
name                    NOT NULL
category_id             FK → categories NULL
description             NULL
brand                   NULL
default_selling_price   DECIMAL NULL
selling_currency_id     FK → currencies NULL
is_active               NOT NULL
created_at              NOT NULL
updated_at              NOT NULL
```

Stock is not stored here.

---

## 8. product_variants

```text
id              PK
product_id      FK → products NOT NULL
sku             UNIQUE NULL
variant_name    NULL
barcode         NULL
is_active       NOT NULL
created_at      NOT NULL
updated_at      NOT NULL
```

A product without explicit variants receives an internal default variant.

---

## 9. attributes

```text
id      PK
name    NOT NULL
```

## 10. attribute_values

```text
id              PK
attribute_id    FK → attributes NOT NULL
value           NOT NULL
```

## 11. variant_attribute_values

```text
variant_id          FK → product_variants NOT NULL
attribute_value_id  FK → attribute_values NOT NULL
```

Composite uniqueness:

```text
(variant_id, attribute_value_id)
```

---

## 12. purchases

```text
id                  PK
supplier_id         FK → suppliers NULL
account_id          FK → accounts NULL
status              NOT NULL
currency_id         FK → currencies NOT NULL
purchase_date       DATE/DATETIME NOT NULL
order_number        NULL
tracking_number     NULL
notes               NULL
created_at          NOT NULL
updated_at          NOT NULL
```

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

Rules:

- `account_id` may be NULL before payment is recorded.
- When financially completed, account is required.
- Account currency must match purchase currency.
- Create a negative `PURCHASE` financial transaction.
- `REFUNDED` is not a logistics status.

Indexes:

```text
purchase_date
status
supplier_id
```

---

## 13. purchase_items

```text
id              PK
purchase_id     FK → purchases NOT NULL
variant_id      FK → product_variants NOT NULL
quantity        INTEGER NOT NULL
unit_price      DECIMAL NOT NULL
weight          DECIMAL NULL
created_at      NOT NULL
```

Constraints:

```text
quantity > 0
unit_price >= 0
weight > 0 when present
```

`quantity` is ordered quantity.

Received quantity is derived from inventory lots.

---

## 14. purchase_costs

```text
id                  PK
purchase_id         FK → purchases NOT NULL
cost_type           NOT NULL
amount              DECIMAL NOT NULL
currency_id         FK → currencies NOT NULL
exchange_rate_id    FK → exchange_rates NULL
allocation_method   NOT NULL
description         NULL
created_at          NOT NULL
```

Types:

```text
SHIPPING
TRANSPORTATION
TAX
COMMISSION
PACKAGING
CUSTOMS
OTHER
```

Allocation methods:

```text
BY_QUANTITY
BY_VALUE
BY_WEIGHT
MANUAL
```

Rules:

- `amount > 0`
- If cost currency differs from purchase currency, a historical rate is conditionally required.
- Original cost amount/currency is preserved.

---

## 15. purchase_cost_allocations

```text
id                                  PK
purchase_cost_id                    FK → purchase_costs NOT NULL
purchase_item_id                    FK → purchase_items NOT NULL
allocated_original_amount           DECIMAL NOT NULL
allocated_purchase_currency_amount  DECIMAL NOT NULL
```

Constraints:

```text
allocated_original_amount >= 0
allocated_purchase_currency_amount >= 0
```

Inventory costing uses `allocated_purchase_currency_amount`.

---

## 16. inventory_lots

```text
id                    PK
purchase_item_id      FK → purchase_items NOT NULL
variant_id            FK → product_variants NOT NULL
acquired_quantity     INTEGER NOT NULL
remaining_quantity    INTEGER NOT NULL
unit_cost             DECIMAL NOT NULL
currency_id           FK → currencies NOT NULL
received_at           DATETIME NOT NULL
created_at            NOT NULL
```

Rules:

```text
acquired_quantity > 0
remaining_quantity >= 0
remaining_quantity <= acquired_quantity
unit_cost >= 0
currency_id = original purchase currency
```

FIFO index:

```text
(variant_id, received_at)
```

FIFO query additionally filters `remaining_quantity > 0`.

---

## 17. inventory_movements

```text
id                  PK
variant_id          FK → product_variants NOT NULL
inventory_lot_id    FK → inventory_lots NULL
movement_type       NOT NULL
quantity            INTEGER NOT NULL
unit_cost           DECIMAL NULL
currency_id         FK → currencies NULL
reference_type      NULL
reference_id        NULL
movement_date       DATETIME NOT NULL
notes               NULL
created_at          NOT NULL
```

Types:

```text
PURCHASE_RECEIVED
SALE
CUSTOMER_RETURN
SUPPLIER_RETURN
ADJUSTMENT_IN
ADJUSTMENT_OUT
DAMAGED
LOST
```

Sign convention:

```text
PURCHASE_RECEIVED  positive
CUSTOMER_RETURN    positive
ADJUSTMENT_IN      positive

SALE               negative
SUPPLIER_RETURN    negative
ADJUSTMENT_OUT     negative
DAMAGED            negative
LOST               negative
```

Indexes:

```text
variant_id
movement_date
```

---

## 18. customers

```text
id              PK
name            NOT NULL
phone           NULL
email           NULL
social_contact  NULL
notes           NULL
created_at      NOT NULL
updated_at      NOT NULL
```

---

## 19. sales

```text
id                  PK
customer_id         FK → customers NULL
account_id          FK → accounts NOT NULL
currency_id         FK → currencies NOT NULL
status              NOT NULL
sale_date           DATETIME NOT NULL
discount_amount     DECIMAL NULL
notes               NULL
created_at          NOT NULL
updated_at          NOT NULL
```

Statuses:

```text
COMPLETED
PARTIALLY_REFUNDED
REFUNDED
CANCELLED
```

Rules:

```text
account currency = sale currency
discount_amount >= 0 when present
```

Indexes:

```text
sale_date
customer_id
status
```

---

## 20. sale_items

```text
id              PK
sale_id         FK → sales NOT NULL
variant_id      FK → product_variants NOT NULL
quantity        INTEGER NOT NULL
unit_price      DECIMAL NOT NULL
discount_amount DECIMAL NULL
created_at      NOT NULL
```

Constraints:

```text
quantity > 0
unit_price >= 0
discount_amount >= 0 when present
```

No `unit_cost_snapshot` here.

Exact historical COGS comes from FIFO allocations.

---

## 21. sale_item_lot_allocations

```text
id                  PK
sale_item_id        FK → sale_items NOT NULL
inventory_lot_id    FK → inventory_lots NOT NULL
quantity            INTEGER NOT NULL
unit_cost_snapshot  DECIMAL NOT NULL
created_at          NOT NULL
```

Constraints:

```text
quantity > 0
unit_cost_snapshot >= 0
```

COGS:

```text
SUM(quantity × unit_cost_snapshot)
```

---

## 22. customer_returns

```text
id                  PK
sale_id             FK → sales NOT NULL
account_id          FK → accounts NULL
refund_amount       DECIMAL NULL
refund_currency_id  FK → currencies NULL
return_date         DATETIME NOT NULL
notes               NULL
created_at          NOT NULL
```

When refund exists:

```text
refund_amount > 0
refund_currency_id = original sale currency
account currency = refund currency
```

Refund creates a negative `CUSTOMER_REFUND` financial transaction.

---

## 23. customer_return_items

```text
id                  PK
customer_return_id  FK → customer_returns NOT NULL
sale_item_id        FK → sale_items NOT NULL
quantity            INTEGER NOT NULL
condition           NOT NULL
created_at          NOT NULL
```

Conditions:

```text
SELLABLE
DAMAGED
```

Constraint:

```text
quantity > 0
```

Application rule:

```text
sum(returned quantity for sale_item) <= original sold quantity
```

---

## 24. return_lot_allocations

```text
id                          PK
customer_return_item_id     FK → customer_return_items NOT NULL
sale_item_lot_allocation_id FK → sale_item_lot_allocations NOT NULL
quantity                    INTEGER NOT NULL
unit_cost_snapshot          DECIMAL NOT NULL
created_at                  NOT NULL
```

Constraints:

```text
quantity > 0
unit_cost_snapshot >= 0
```

Do not duplicate `inventory_lot_id`; it is derivable through the original sale allocation.

---

## 25. supplier_returns

```text
id                  PK
purchase_id         FK → purchases NOT NULL
supplier_id         FK → suppliers NULL
account_id          FK → accounts NULL
refund_amount       DECIMAL NULL
refund_currency_id  FK → currencies NULL
return_date         DATETIME NOT NULL
notes               NULL
created_at          NOT NULL
```

When refund exists:

```text
refund_amount > 0
refund_currency_id = original purchase currency
account currency = refund currency
```

Refund creates a positive `SUPPLIER_REFUND` financial transaction.

---

## 26. supplier_return_items

```text
id                  PK
supplier_return_id  FK → supplier_returns NOT NULL
purchase_item_id    FK → purchase_items NOT NULL
inventory_lot_id    FK → inventory_lots NOT NULL
quantity            INTEGER NOT NULL
unit_cost_snapshot  DECIMAL NOT NULL
created_at          NOT NULL
```

Constraints:

```text
quantity > 0
unit_cost_snapshot >= 0
```

Returned quantity cannot exceed eligible remaining inventory.

Supplier return creates negative `SUPPLIER_RETURN` inventory movements.

---

## 27. expenses

```text
id                  PK
account_id          FK → accounts NOT NULL
expense_type        NOT NULL
amount              DECIMAL NOT NULL
currency_id         FK → currencies NOT NULL
expense_date        DATETIME NOT NULL
description         NULL
notes               NULL
created_at          NOT NULL
```

Rules:

```text
amount > 0
currency_id = account currency
```

Financial ledger entry is negative `EXPENSE`.

---

## 28. capital_movements

```text
id                  PK
account_id          FK → accounts NOT NULL
movement_type       NOT NULL
amount              DECIMAL NOT NULL
currency_id         FK → currencies NOT NULL
movement_date       DATETIME NOT NULL
notes               NULL
created_at          NOT NULL
```

Types:

```text
CONTRIBUTION
WITHDRAWAL
```

Rules:

```text
amount > 0
currency_id = account currency
```

Ledger sign:

```text
CONTRIBUTION positive
WITHDRAWAL   negative
```

---

## 29. account_transfers

```text
id                      PK
source_account_id       FK → accounts NOT NULL
destination_account_id  FK → accounts NOT NULL
source_amount           DECIMAL NOT NULL
destination_amount      DECIMAL NOT NULL
exchange_rate_id        FK → exchange_rates NULL
transfer_date           DATETIME NOT NULL
notes                   NULL
created_at              NOT NULL
```

Constraints:

```text
source_account_id != destination_account_id
source_amount > 0
destination_amount > 0
```

Same currency:

- Exchange rate not required.

Different currencies:

- Historical FX data required.

Transfers generate ledger movements atomically.

---

## 30. financial_transactions

```text
id                      PK
transaction_type        NOT NULL
account_id              FK → accounts NOT NULL
amount                  DECIMAL NOT NULL
currency_id             FK → currencies NOT NULL

purchase_id             FK → purchases NULL
sale_id                 FK → sales NULL
expense_id              FK → expenses NULL
customer_return_id      FK → customer_returns NULL
supplier_return_id      FK → supplier_returns NULL
capital_movement_id     FK → capital_movements NULL
account_transfer_id     FK → account_transfers NULL

exchange_rate_id        FK → exchange_rates NULL
description             NULL
transaction_date        DATETIME NOT NULL
created_at              NOT NULL
```

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

Rules:

```text
currency_id = account currency
```

Sign convention:

```text
Money in  → positive
Money out → negative
```

Exactly one applicable business-source FK should normally be populated for business-generated rows.

Balance:

```text
SUM(amount)
```

Indexes:

```text
account_id
transaction_date
(account_id, transaction_date)
```

---

## 31. settings

```text
key         PK/UNIQUE
value       NOT NULL
updated_at  NOT NULL
```

API secrets/tokens are not ordinary plaintext settings.

---

## 32. Derived Values

Do not create competing sources of truth for:

- Current stock
- Account balance
- Revenue
- COGS
- Gross profit
- Net profit
- Inventory value
- Total refunds

Historical snapshots are allowed only where required for financial integrity:

- FIFO `unit_cost_snapshot`
- Return cost snapshot
- Historical FX
- Original purchase price
- Original sale price

---

## 33. Source of Truth

```text
Products              → products
Variants              → product_variants
Purchases             → purchases + purchase_items
Purchase costs        → purchase_costs
Normalized allocations→ purchase_cost_allocations
Inventory provenance  → inventory_lots
Stock history         → inventory_movements
Sales                 → sales + sale_items
Historical COGS       → sale_item_lot_allocations
Customer returns      → customer_returns + customer_return_items
Return reversals      → return_lot_allocations
Supplier returns      → supplier_returns + supplier_return_items
Financial ledger      → financial_transactions
Exchange rates        → exchange_rates
Accounts              → accounts
Capital history       → capital_movements
```

---

## 34. Recommended Indexes

```text
purchases(purchase_date)
purchases(status)
purchases(supplier_id)

inventory_lots(variant_id, received_at)

inventory_movements(variant_id)
inventory_movements(movement_date)

sales(sale_date)
sales(customer_id)
sales(status)

sale_items(variant_id)

customer_returns(sale_id)
customer_returns(return_date)

supplier_returns(purchase_id)
supplier_returns(return_date)

financial_transactions(account_id, transaction_date)

exchange_rates(base_currency_id, quote_currency_id, rate_timestamp)
```

---

## 35. Database Design Rules

1. Never use float for money.
2. Direct account operations use account native currency.
3. Currency conversion is explicit.
4. Financial inflows are positive.
5. Financial outflows are negative.
6. Inventory inflows are positive.
7. Inventory outflows are negative.
8. Historical exchange rates are immutable.
9. Purchase costs preserve original and normalized values.
10. Inventory lots use purchase currency.
11. FIFO allocations are source of truth for sale COGS.
12. Customer returns preserve original FIFO provenance.
13. Supplier returns preserve original purchase/lot provenance.
14. Historical records are not destructively rewritten.
15. Multi-table operations are atomic.
16. V1 quantities are integral units.
17. Referential integrity is enforced wherever practical.
18. V1 does not implement credit or partial payments.
19. Schema should remain compatible with future PostgreSQL migration.
