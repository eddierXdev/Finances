# Analytics Formulas

This document fixes the meaning of every Phase 11 analytics metric before the
implementation is exposed to a UI. All monetary arithmetic uses `Decimal` and
`Money`; SQLite `SUM` is never used for money because SQLite stores exact
decimal amounts as text.

## Principles

- Native amounts are preserved. A report never invents a currency, a rate or a
  historical cost.
- Implicit FX is forbidden. Native profit is only combined inside one currency.
  Cross-currency profit is available through the explicit base-currency
  consolidated report.
- Sales are filtered by `sale_date`; customer and supplier returns are filtered
  by `return_date`; expenses by `expense_date`.
- Period boundaries are inclusive. A UI date range must convert its end date to
  the end of that day before calling a use case.
- Cancelled sales are excluded from revenue, COGS and product/supplier
  analytics.
- Customer refunds and supplier refunds are reported separately and are never
  counted twice.
- Filters apply where the dimension exists. Product, category, supplier and
  customer filters apply to sales, returns and inventory. Operating expenses
  are only filtered by period, account and currency; they are business-wide
  costs and are not attributed to a product or supplier. Account balances are
  only filtered by account and currency.

## Revenue

For one sale:

```text
item line total = unit_price * quantity - item_discount
sale net revenue = sum(item line totals) - sale_discount
```

The sale-level discount is allocated across items in proportion to their line
totals. The last item receives any rounding residual so the allocated discounts
add exactly to the sale discount.

For one customer return line, the revenue reversal is based on the original
sale item, not on the refund cash amount:

```text
original item net revenue =
    item line total - proportional share of the sale-level discount

return value =
    original item net revenue * returned quantity / original item quantity
```

When a return line is split across several original FIFO allocations, each
return allocation reverses its proportional share. This preserves the link
between the returned unit and its original sale price.

```text
period revenue =
    sum(sale net revenue for sales in the period)
  - sum(return value for customer returns in the period)
```

A customer return without a refund still reduces revenue because the customer
returned merchandise. A refund amount is cash movement and is reported as
`customer_refunds`; it is **not** subtracted from revenue a second time.

The business summary also exposes:

```text
units_sold = sold allocation units - customer-return allocation units
```

Sale count counts distinct sales; return count counts distinct customer returns.

## COGS

Historical FIFO snapshots are the only source of sale COGS:

```text
sale COGS = sum(allocation quantity * allocation unit_cost_snapshot)
return COGS = sum(return allocation quantity * return unit_cost_snapshot)
period COGS = sum(sale COGS for sales in the period)
            - sum(return COGS for customer returns in the period)
```

Return COGS is reversed for both sellable and damaged returns. The condition
controls whether stock is restored; it does not change the historical cost that
must be reversed from the sale.

## Gross and Net Profit

Native gross profit is only calculated for a sale whose revenue currency equals
every allocation cost currency:

```text
gross profit = net revenue - COGS
```

A sale whose FIFO costs span another currency is counted in
`cross_currency_sale_count` and is excluded from native gross profit. Its
revenue and COGS remain visible in their native currencies. The consolidated
report converts both sides explicitly.

```text
net profit = gross profit - operating expenses
```

Expenses are period expenses in their account currency. A currency with
expenses but no same-currency gross profit produces a negative net profit in
that currency.

## Margins

```text
gross margin % = gross profit / revenue * 100
net margin %   = net profit / revenue * 100
```

A margin is undefined (`None`) when revenue is zero. Native margins use the
same-currency gross profit described above. Consolidated margins use the
base-currency values after explicit conversion.

## Customer and Supplier Returns

- Customer return value reduces revenue; return COGS reduces COGS.
- Customer refund cash is shown separately as `customer_refunds`.
- A supplier return removes stock at its historical lot cost. The returned cost
  is shown separately as `supplier_return_cost`.
- A supplier refund is cash recovery. It reduces the net cost of inventory and
  is shown as `supplier_refunds`. It is **not** recognized as profit until the
  related goods are sold.
- If a supplier refund differs from the returned historical cost, the
  difference remains visible as separate refund and returned-cost figures; it is
  not silently treated as profit.

## Inventory Value

```text
inventory value = sum(remaining_quantity * lot unit_cost)
```

Values are grouped by the lot's native cost currency. Inventory value is a
current snapshot; the application does not reconstruct historical remaining
quantities for a past date. The `as_of` timestamp is used for last-sale and
account-balance calculations.

## Product Analytics

### Best sellers

```text
net quantity = sold quantity - returned quantity
```

Grouped by product, using FIFO allocation quantities so supplier filters can be
applied. Returned quantities are subtracted in the period in which the return
was recorded. The list is ordered by net quantity descending.

### Most profitable products

```text
product revenue = allocated sale revenue - allocated customer-return revenue
product COGS    = allocated FIFO COGS - allocated customer-return COGS
product profit  = product revenue - product COGS
```

Metrics are grouped by product and currency. Only same-currency flows
contribute to native profit; cross-currency flows are counted and excluded.
The consolidated report supplies the overall base-currency profitability view;
it does not invent a cross-currency product ranking when a required rate is
missing.

### Slow-moving stock

A product is slow-moving when it has remaining stock and its last non-cancelled
sale is older than the configured threshold:

```text
last_sale_date is None
or last_sale_date <= as_of - ANALYTICS_SLOW_MOVING_DAYS
```

The default threshold is 30 days. The report includes remaining quantity,
inventory value, last sale date and days since the last sale.

## Supplier Profitability

FIFO allocations connect each sold unit to its inventory lot, purchase item,
purchase and supplier. Sale item revenue is allocated to suppliers in proportion
to the allocation quantity:

```text
supplier revenue share =
    sale item net revenue * allocation quantity / sale item quantity

supplier COGS = allocation quantity * allocation unit_cost_snapshot
supplier profit = supplier revenue share - supplier COGS
```

Customer returns reverse the same revenue and cost shares against the original
supplier. Supplier refunds and supplier return costs are reported separately.
Volume is the net quantity sold after customer returns. Native profit is only
computed when the revenue and cost share use the same currency. Cross-currency
supplier flows are counted and excluded from native supplier profit; the
consolidated report provides the overall base-currency view without inventing a
per-supplier rate.

## Account Balances

An account balance is the sum of its signed ledger entries up to `as_of`:

```text
balance = sum(signed transaction amounts where transaction_date <= as_of)
```

Native balances are always returned. The consolidated report converts each
native balance to the configured base currency using an explicit stored rate as
of `as_of`.

## Base-Currency Consolidated Reporting

The configured `BASE_CURRENCY` is the reporting currency. Conversion uses a
direct stored rate whose base currency is the reporting currency and whose quote
currency is the native amount's currency:

```text
base amount = native amount / rate(BASE -> native)
```

The rate is the latest stored observation at or before the report's `as_of`
timestamp. The implementation does **not** invert a missing pair and does not
fall back to the network. If a required rate is missing, the native amount is
preserved, the amount is excluded from the consolidated total, and the missing
pair is listed in `missing_rates`.

```text
consolidated revenue   = sum(converted native revenue)
consolidated COGS      = sum(converted native COGS)
consolidated gross     = consolidated revenue - consolidated COGS
consolidated expenses  = sum(converted native expenses)
consolidated net       = consolidated gross - consolidated expenses
```

This is the authoritative cross-currency profitability view. It is marked
incomplete when any required rate is missing.

## Available and Invested Capital

The consolidated report exposes two dashboard capital figures in the reporting
currency:

```text
available capital = sum(converted native account balances)
invested capital  = current inventory value at historical cost
```

Available capital is net liquid capital across all selected accounts, including
negative account balances. Invested capital is the part of capital currently
held as stock. The two figures are informational and are not added together
implicitly by the analytics layer.

## ROI

ROI is documented before implementation. Phase 11 uses a cash-capital basis
because capital movements are append-only and can be reconstructed at both ends
of a period:

```text
net capital invested at date D =
    cumulative capital contributions up to D
  - cumulative capital withdrawals up to D

average net capital invested =
    (opening net capital invested + closing net capital invested) / 2

ROI % = net profit / average net capital invested * 100
```

Opening is the period start (or the earliest available date when no start is
given); closing is the period end. Values are converted to the configured base
currency with the same explicit-rate policy as the consolidated report. ROI is
undefined (`None`) when average net capital invested is zero or negative or when
a required rate is missing. ROI is a business-level metric; product, category,
supplier and customer filters do not isolate capital, while an account filter
does restrict the capital movements used.

A separate **inventory ROI** can be added later:

```text
inventory ROI % = gross profit / average inventory value at cost * 100
```

It requires historical inventory valuation snapshots and is therefore not part
of this increment.
