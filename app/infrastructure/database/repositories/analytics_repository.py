"""SQLAlchemy read-model repository for analytics."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.application.analytics.models import (
    AnalyticsFilters,
    AnalyticsPeriod,
    CustomerReturnAllocationRecord,
    ExpenseRecord,
    InventoryLotRecord,
    LastSaleRecord,
    SaleAllocationRecord,
    SupplierReturnItemRecord,
)
from app.domain.enums.expense_type import ExpenseType
from app.infrastructure.database.models import (
    CurrencyModel,
    CustomerReturnItemModel,
    CustomerReturnModel,
    ExpenseModel,
    InventoryLotModel,
    ProductModel,
    ProductVariantModel,
    PurchaseItemModel,
    PurchaseModel,
    ReturnLotAllocationModel,
    SaleItemLotAllocationModel,
    SaleItemModel,
    SaleModel,
    SupplierModel,
    SupplierReturnItemModel,
    SupplierReturnModel,
)
from app.infrastructure.database.repositories.mapping import (
    currency_to_domain,
)


class SqlAlchemyAnalyticsRepository:
    """Flat, read-only queries used by analytics use cases."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_sale_allocations(
        self,
        period: AnalyticsPeriod,
        filters: AnalyticsFilters,
    ) -> list[SaleAllocationRecord]:
        statement = (
            select(
                SaleItemLotAllocationModel,
                ProductVariantModel,
                ProductModel,
                SupplierModel,
            )
            .join(
                SaleItemModel,
                SaleItemLotAllocationModel.sale_item_id == SaleItemModel.id,
            )
            .join(SaleModel, SaleItemModel.sale_id == SaleModel.id)
            .join(CurrencyModel, SaleModel.currency_id == CurrencyModel.id)
            .join(
                InventoryLotModel,
                SaleItemLotAllocationModel.inventory_lot_id
                == InventoryLotModel.id,
            )
            .join(
                PurchaseItemModel,
                InventoryLotModel.purchase_item_id == PurchaseItemModel.id,
            )
            .join(
                PurchaseModel,
                PurchaseItemModel.purchase_id == PurchaseModel.id,
            )
            .outerjoin(
                SupplierModel, PurchaseModel.supplier_id == SupplierModel.id
            )
            .join(
                ProductVariantModel,
                SaleItemModel.variant_id == ProductVariantModel.id,
            )
            .join(
                ProductModel,
                ProductVariantModel.product_id == ProductModel.id,
            )
            .where(SaleModel.status != "CANCELLED")
        )
        statement = self._apply_sale_filters(statement, period, filters)
        statement = statement.order_by(
            SaleModel.sale_date.asc(),
            SaleItemModel.id.asc(),
            SaleItemLotAllocationModel.id.asc(),
        )

        rows = self._session.execute(statement).all()
        sale_ids = {row[0].sale_item.sale_id for row in rows}
        sale_totals = self._sale_total_line_totals(sale_ids)

        records: list[SaleAllocationRecord] = []
        for allocation, variant, product, supplier in rows:
            sale = allocation.sale_item.sale
            records.append(
                SaleAllocationRecord(
                    sale_id=sale.id,
                    sale_date=sale.sale_date,
                    sale_currency=currency_to_domain(sale.currency),
                    sale_account_id=sale.account_id,
                    customer_id=sale.customer_id,
                    sale_discount_amount=(
                        sale.discount_amount or Decimal("0")
                    ),
                    sale_total_line_total=sale_totals.get(
                        sale.id, Decimal("0")
                    ),
                    sale_item_id=allocation.sale_item.id,
                    variant_id=variant.id,
                    variant_name=variant.variant_name,
                    sku=variant.sku,
                    product_id=product.id,
                    product_name=product.name,
                    category_id=product.category_id,
                    item_quantity=allocation.sale_item.quantity,
                    item_unit_price=allocation.sale_item.unit_price,
                    item_discount_amount=(
                        allocation.sale_item.discount_amount or Decimal("0")
                    ),
                    allocation_id=allocation.id,
                    allocation_quantity=allocation.quantity,
                    allocation_unit_cost=allocation.unit_cost_snapshot,
                    cost_currency=currency_to_domain(
                        allocation.inventory_lot.currency
                    ),
                    inventory_lot_id=allocation.inventory_lot_id,
                    supplier_id=supplier.id if supplier is not None else None,
                    supplier_name=(
                        supplier.name if supplier is not None else None
                    ),
                )
            )
        return records

    def list_customer_return_allocations(
        self,
        period: AnalyticsPeriod,
        filters: AnalyticsFilters,
    ) -> list[CustomerReturnAllocationRecord]:
        statement = (
            select(
                ReturnLotAllocationModel,
                ProductVariantModel,
                ProductModel,
                SupplierModel,
            )
            .join(
                CustomerReturnItemModel,
                ReturnLotAllocationModel.customer_return_item_id
                == CustomerReturnItemModel.id,
            )
            .join(
                CustomerReturnModel,
                CustomerReturnItemModel.customer_return_id
                == CustomerReturnModel.id,
            )
            .join(
                SaleItemModel,
                CustomerReturnItemModel.sale_item_id == SaleItemModel.id,
            )
            .join(SaleModel, SaleItemModel.sale_id == SaleModel.id)
            .join(CurrencyModel, SaleModel.currency_id == CurrencyModel.id)
            .join(
                SaleItemLotAllocationModel,
                ReturnLotAllocationModel.sale_item_lot_allocation_id
                == SaleItemLotAllocationModel.id,
            )
            .join(
                InventoryLotModel,
                SaleItemLotAllocationModel.inventory_lot_id
                == InventoryLotModel.id,
            )
            .join(
                PurchaseItemModel,
                InventoryLotModel.purchase_item_id == PurchaseItemModel.id,
            )
            .join(
                PurchaseModel,
                PurchaseItemModel.purchase_id == PurchaseModel.id,
            )
            .outerjoin(
                SupplierModel, PurchaseModel.supplier_id == SupplierModel.id
            )
            .join(
                ProductVariantModel,
                SaleItemModel.variant_id == ProductVariantModel.id,
            )
            .join(
                ProductModel,
                ProductVariantModel.product_id == ProductModel.id,
            )
        )
        statement = self._apply_period(
            statement, CustomerReturnModel.return_date, period
        )
        statement = self._apply_return_filters(statement, filters)
        statement = statement.order_by(
            CustomerReturnModel.return_date.asc(),
            ReturnLotAllocationModel.id.asc(),
        )

        rows = self._session.execute(statement).all()
        sale_ids = {row[0].customer_return_item.sale_item.sale_id for row in rows}
        sale_totals = self._sale_total_line_totals(sale_ids)
        same_currency = self._sale_same_currency(sale_ids)

        records: list[CustomerReturnAllocationRecord] = []
        for allocation, variant, product, supplier in rows:
            return_item = allocation.customer_return_item
            customer_return = return_item.customer_return
            sale_item = return_item.sale_item
            sale = sale_item.sale
            records.append(
                CustomerReturnAllocationRecord(
                    customer_return_id=customer_return.id,
                    return_date=customer_return.return_date,
                    sale_id=sale.id,
                    sale_currency=currency_to_domain(sale.currency),
                    sale_account_id=sale.account_id,
                    refund_account_id=customer_return.account_id,
                    customer_id=sale.customer_id,
                    sale_discount_amount=(
                        sale.discount_amount or Decimal("0")
                    ),
                    sale_total_line_total=sale_totals.get(
                        sale.id, Decimal("0")
                    ),
                    sale_is_same_currency=same_currency.get(sale.id, False),
                    sale_item_id=sale_item.id,
                    variant_id=variant.id,
                    variant_name=variant.variant_name,
                    sku=variant.sku,
                    product_id=product.id,
                    product_name=product.name,
                    category_id=product.category_id,
                    item_quantity=sale_item.quantity,
                    item_unit_price=sale_item.unit_price,
                    item_discount_amount=(
                        sale_item.discount_amount or Decimal("0")
                    ),
                    return_item_id=return_item.id,
                    return_item_quantity=return_item.quantity,
                    return_condition=return_item.condition,
                    return_allocation_id=allocation.id,
                    return_allocation_quantity=allocation.quantity,
                    return_unit_cost=allocation.unit_cost_snapshot,
                    cost_currency=currency_to_domain(
                        allocation.sale_item_lot_allocation.inventory_lot.currency
                    ),
                    supplier_id=supplier.id if supplier is not None else None,
                    supplier_name=(
                        supplier.name if supplier is not None else None
                    ),
                    refund_amount=(
                        customer_return.refund_amount or Decimal("0")
                    ),
                    refund_currency=(
                        currency_to_domain(customer_return.refund_currency)
                        if customer_return.refund_currency is not None
                        else None
                    ),
                )
            )
        return records

    def list_supplier_return_items(
        self,
        period: AnalyticsPeriod,
        filters: AnalyticsFilters,
    ) -> list[SupplierReturnItemRecord]:
        statement = (
            select(
                SupplierReturnItemModel,
                ProductVariantModel,
                ProductModel,
                SupplierModel,
            )
            .join(
                SupplierReturnModel,
                SupplierReturnItemModel.supplier_return_id
                == SupplierReturnModel.id,
            )
            .join(
                PurchaseItemModel,
                SupplierReturnItemModel.purchase_item_id
                == PurchaseItemModel.id,
            )
            .join(
                PurchaseModel,
                PurchaseItemModel.purchase_id == PurchaseModel.id,
            )
            .join(
                InventoryLotModel,
                SupplierReturnItemModel.inventory_lot_id
                == InventoryLotModel.id,
            )
            .join(CurrencyModel, InventoryLotModel.currency_id == CurrencyModel.id)
            .outerjoin(
                SupplierModel, SupplierReturnModel.supplier_id == SupplierModel.id
            )
            .join(
                ProductVariantModel,
                PurchaseItemModel.variant_id == ProductVariantModel.id,
            )
            .join(
                ProductModel,
                ProductVariantModel.product_id == ProductModel.id,
            )
        )
        statement = self._apply_period(
            statement, SupplierReturnModel.return_date, period
        )
        statement = self._apply_supplier_return_filters(statement, filters)
        statement = statement.order_by(
            SupplierReturnModel.return_date.asc(),
            SupplierReturnItemModel.id.asc(),
        )

        records: list[SupplierReturnItemRecord] = []
        for item, variant, product, supplier in self._session.execute(
            statement
        ).all():
            supplier_return = item.supplier_return
            records.append(
                SupplierReturnItemRecord(
                    supplier_return_id=supplier_return.id,
                    return_date=supplier_return.return_date,
                    purchase_id=item.purchase_item.purchase_id,
                    supplier_id=supplier.id if supplier is not None else None,
                    supplier_name=(
                        supplier.name if supplier is not None else None
                    ),
                    purchase_item_id=item.purchase_item_id,
                    variant_id=variant.id,
                    variant_name=variant.variant_name,
                    sku=variant.sku,
                    product_id=product.id,
                    product_name=product.name,
                    category_id=product.category_id,
                    quantity=item.quantity,
                    unit_cost=item.unit_cost_snapshot,
                    cost_currency=currency_to_domain(item.inventory_lot.currency),
                    refund_amount=(
                        supplier_return.refund_amount or Decimal("0")
                    ),
                    refund_currency=(
                        currency_to_domain(supplier_return.refund_currency)
                        if supplier_return.refund_currency is not None
                        else None
                    ),
                    account_id=supplier_return.account_id,
                )
            )
        return records

    def list_expenses(
        self,
        period: AnalyticsPeriod,
        filters: AnalyticsFilters,
    ) -> list[ExpenseRecord]:
        statement = select(ExpenseModel).join(
            CurrencyModel, ExpenseModel.currency_id == CurrencyModel.id
        )
        statement = self._apply_period(
            statement, ExpenseModel.expense_date, period
        )
        if filters.account_id is not None:
            statement = statement.where(
                ExpenseModel.account_id == filters.account_id
            )
        if filters.currency_code is not None:
            statement = statement.where(
                CurrencyModel.code == filters.currency_code
            )
        statement = statement.order_by(
            ExpenseModel.expense_date.asc(), ExpenseModel.id.asc()
        )

        return [
            ExpenseRecord(
                expense_id=model.id,
                expense_date=model.expense_date,
                account_id=model.account_id,
                expense_type=ExpenseType(model.expense_type),
                amount=model.amount,
                currency=currency_to_domain(model.currency),
            )
            for model in self._session.scalars(statement)
        ]

    def list_inventory_lots(
        self,
        as_of: datetime,
        filters: AnalyticsFilters,
    ) -> list[InventoryLotRecord]:
        statement = (
            select(
                InventoryLotModel,
                ProductVariantModel,
                ProductModel,
                SupplierModel,
            )
            .join(
                ProductVariantModel,
                InventoryLotModel.variant_id == ProductVariantModel.id,
            )
            .join(
                ProductModel,
                ProductVariantModel.product_id == ProductModel.id,
            )
            .join(
                PurchaseItemModel,
                InventoryLotModel.purchase_item_id == PurchaseItemModel.id,
            )
            .join(
                PurchaseModel,
                PurchaseItemModel.purchase_id == PurchaseModel.id,
            )
            .outerjoin(
                SupplierModel, PurchaseModel.supplier_id == SupplierModel.id
            )
            .join(CurrencyModel, InventoryLotModel.currency_id == CurrencyModel.id)
            .where(
                InventoryLotModel.remaining_quantity > 0,
                InventoryLotModel.received_at <= as_of,
            )
        )
        if filters.product_id is not None:
            statement = statement.where(
                ProductModel.id == filters.product_id
            )
        if filters.category_id is not None:
            statement = statement.where(
                ProductModel.category_id == filters.category_id
            )
        if filters.supplier_id is not None:
            statement = statement.where(
                PurchaseModel.supplier_id == filters.supplier_id
            )
        if filters.currency_code is not None:
            statement = statement.where(
                CurrencyModel.code == filters.currency_code
            )
        statement = statement.order_by(
            ProductModel.name.asc(),
            InventoryLotModel.received_at.asc(),
            InventoryLotModel.id.asc(),
        )

        return [
            InventoryLotRecord(
                lot_id=lot.id,
                variant_id=variant.id,
                variant_name=variant.variant_name,
                sku=variant.sku,
                product_id=product.id,
                product_name=product.name,
                category_id=product.category_id,
                remaining_quantity=lot.remaining_quantity,
                unit_cost=lot.unit_cost,
                currency=currency_to_domain(lot.currency),
                received_at=lot.received_at,
                supplier_id=supplier.id if supplier is not None else None,
                supplier_name=(
                    supplier.name if supplier is not None else None
                ),
            )
            for lot, variant, product, supplier in self._session.execute(
                statement
            ).all()
        ]

    def list_last_sale_dates(
        self,
        as_of: datetime,
        filters: AnalyticsFilters,
    ) -> list[LastSaleRecord]:
        statement = (
            select(
                ProductModel.id,
                ProductVariantModel.id,
                func.max(SaleModel.sale_date),
            )
            .join(
                ProductVariantModel,
                ProductModel.id == ProductVariantModel.product_id,
            )
            .join(
                SaleItemModel,
                ProductVariantModel.id == SaleItemModel.variant_id,
            )
            .join(SaleModel, SaleItemModel.sale_id == SaleModel.id)
            .join(CurrencyModel, SaleModel.currency_id == CurrencyModel.id)
            .join(
                SaleItemLotAllocationModel,
                SaleItemModel.id == SaleItemLotAllocationModel.sale_item_id,
            )
            .join(
                InventoryLotModel,
                SaleItemLotAllocationModel.inventory_lot_id
                == InventoryLotModel.id,
            )
            .join(
                PurchaseItemModel,
                InventoryLotModel.purchase_item_id == PurchaseItemModel.id,
            )
            .join(
                PurchaseModel,
                PurchaseItemModel.purchase_id == PurchaseModel.id,
            )
            .where(
                SaleModel.status != "CANCELLED",
                SaleModel.sale_date <= as_of,
            )
        )
        if filters.currency_code is not None:
            statement = statement.where(
                CurrencyModel.code == filters.currency_code
            )
        if filters.account_id is not None:
            statement = statement.where(
                SaleModel.account_id == filters.account_id
            )
        if filters.customer_id is not None:
            statement = statement.where(
                SaleModel.customer_id == filters.customer_id
            )
        if filters.product_id is not None:
            statement = statement.where(
                ProductModel.id == filters.product_id
            )
        if filters.category_id is not None:
            statement = statement.where(
                ProductModel.category_id == filters.category_id
            )
        if filters.supplier_id is not None:
            statement = statement.where(
                PurchaseModel.supplier_id == filters.supplier_id
            )
        statement = statement.group_by(
            ProductModel.id, ProductVariantModel.id
        )

        return [
            LastSaleRecord(
                product_id=product_id,
                variant_id=variant_id,
                last_sale_date=last_sale_date,
            )
            for product_id, variant_id, last_sale_date in self._session.execute(
                statement
            ).all()
        ]

    def _apply_sale_filters(self, statement, period, filters):
        statement = self._apply_period(
            statement, SaleModel.sale_date, period
        )
        if filters.currency_code is not None:
            statement = statement.where(
                CurrencyModel.code == filters.currency_code
            )
        if filters.account_id is not None:
            statement = statement.where(
                SaleModel.account_id == filters.account_id
            )
        if filters.customer_id is not None:
            statement = statement.where(
                SaleModel.customer_id == filters.customer_id
            )
        if filters.product_id is not None:
            statement = statement.where(
                ProductModel.id == filters.product_id
            )
        if filters.category_id is not None:
            statement = statement.where(
                ProductModel.category_id == filters.category_id
            )
        if filters.supplier_id is not None:
            statement = statement.where(
                PurchaseModel.supplier_id == filters.supplier_id
            )
        return statement

    def _apply_return_filters(
        self, statement, filters: AnalyticsFilters
    ):
        if filters.currency_code is not None:
            statement = statement.where(
                CurrencyModel.code == filters.currency_code
            )
        if filters.account_id is not None:
            statement = statement.where(
                SaleModel.account_id == filters.account_id
            )
        if filters.customer_id is not None:
            statement = statement.where(
                SaleModel.customer_id == filters.customer_id
            )
        if filters.product_id is not None:
            statement = statement.where(
                ProductModel.id == filters.product_id
            )
        if filters.category_id is not None:
            statement = statement.where(
                ProductModel.category_id == filters.category_id
            )
        if filters.supplier_id is not None:
            statement = statement.where(
                PurchaseModel.supplier_id == filters.supplier_id
            )
        return statement

    def _apply_supplier_return_filters(self, statement, filters):
        if filters.currency_code is not None:
            statement = statement.where(
                CurrencyModel.code == filters.currency_code
            )
        if filters.account_id is not None:
            statement = statement.where(
                or_(
                    SupplierReturnModel.account_id == filters.account_id,
                    PurchaseModel.account_id == filters.account_id,
                )
            )
        if filters.supplier_id is not None:
            statement = statement.where(
                SupplierReturnModel.supplier_id == filters.supplier_id
            )
        if filters.product_id is not None:
            statement = statement.where(
                ProductModel.id == filters.product_id
            )
        if filters.category_id is not None:
            statement = statement.where(
                ProductModel.category_id == filters.category_id
            )
        return statement

    @staticmethod
    def _apply_period(statement, column, period: AnalyticsPeriod):
        if period.start is not None:
            statement = statement.where(column >= period.start)
        if period.end is not None:
            statement = statement.where(column <= period.end)
        return statement

    def _sale_total_line_totals(
        self, sale_ids: set[int]
    ) -> dict[int, Decimal]:
        if not sale_ids:
            return {}

        statement = select(SaleItemModel).where(
            SaleItemModel.sale_id.in_(sale_ids)
        )
        totals: dict[int, Decimal] = {}
        for item in self._session.scalars(statement):
            subtotal = item.unit_price * item.quantity
            discount = item.discount_amount or Decimal("0")
            totals[item.sale_id] = (
                totals.get(item.sale_id, Decimal("0"))
                + subtotal
                - discount
            )
        return totals

    def _sale_same_currency(self, sale_ids: set[int]) -> dict[int, bool]:
        if not sale_ids:
            return {}

        statement = (
            select(
                SaleModel.id,
                SaleModel.currency_id,
                InventoryLotModel.currency_id,
            )
            .join(SaleItemModel, SaleModel.id == SaleItemModel.sale_id)
            .join(
                SaleItemLotAllocationModel,
                SaleItemModel.id == SaleItemLotAllocationModel.sale_item_id,
            )
            .join(
                InventoryLotModel,
                SaleItemLotAllocationModel.inventory_lot_id
                == InventoryLotModel.id,
            )
            .where(SaleModel.id.in_(sale_ids))
        )
        sale_currencies: dict[int, int] = {}
        cost_currencies: dict[int, set[int]] = {}
        for sale_id, sale_currency_id, cost_currency_id in self._session.execute(
            statement
        ).all():
            sale_currencies[sale_id] = sale_currency_id
            cost_currencies.setdefault(sale_id, set()).add(cost_currency_id)

        return {
            sale_id: (
                sale_id in sale_currencies
                and cost_currencies.get(sale_id) == {sale_currencies[sale_id]}
            )
            for sale_id in sale_ids
        }
