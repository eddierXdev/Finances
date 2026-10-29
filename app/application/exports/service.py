"""Application service for selected business-data exports."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, StrEnum

from app.application.exports.ports import (
    ExportArtifact,
    ExportGateway,
    ExportTable,
)
from app.application.finances.account_service import AccountService
from app.application.inventory.service import InventoryService
from app.application.purchases.service import PurchaseService
from app.application.returns.service import ReturnsService
from app.application.sales.service import SalesService
from app.domain.value_objects.money import Money


class ExportSection(StrEnum):
    """Business-information groups available to the export dialog."""

    ACCOUNTS = "accounts"
    INVENTORY = "inventory"
    PURCHASES = "purchases"
    SALES = "sales"
    RETURNS = "returns"


@dataclass(frozen=True, slots=True)
class ExportResult:
    """Summary of a completed business-data export."""

    path: str
    table_names: tuple[str, ...]
    row_count: int
    size_bytes: int
    generated_at: datetime


class ExportService:
    """Build read-model tables and delegate file writing to Infrastructure."""

    def __init__(
        self,
        accounts: AccountService,
        inventory: InventoryService,
        purchases: PurchaseService,
        sales: SalesService,
        returns: ReturnsService,
        gateway: ExportGateway,
    ) -> None:
        self._accounts = accounts
        self._inventory = inventory
        self._purchases = purchases
        self._sales = sales
        self._returns = returns
        self._gateway = gateway

    def export(
        self,
        destination: str,
        sections: Iterable[ExportSection] | None = None,
    ) -> ExportResult:
        """Write the selected sections to a ZIP archive."""
        tables = self.build_tables(sections)
        artifact: ExportArtifact = self._gateway.write_archive(
            destination, tables
        )
        return ExportResult(
            path=artifact.path,
            table_names=tuple(table.name for table in tables),
            row_count=sum(len(table.rows) for table in tables),
            size_bytes=artifact.size_bytes,
            generated_at=artifact.generated_at,
        )

    def build_tables(
        self,
        sections: Iterable[ExportSection] | None = None,
    ) -> tuple[ExportTable, ...]:
        """Build the selected CSV tables without touching the filesystem."""
        if sections is None:
            selected = tuple(ExportSection)
        else:
            selected = tuple(
                dict.fromkeys(
                    ExportSection(section) for section in sections
                )
            )
        if not selected:
            raise ValueError("Select at least one section to export.")

        tables: list[ExportTable] = []
        for section in selected:
            if section is ExportSection.ACCOUNTS:
                tables.append(self._accounts_table())
            elif section is ExportSection.INVENTORY:
                tables.append(self._inventory_table())
            elif section is ExportSection.PURCHASES:
                tables.append(self._purchases_table())
            elif section is ExportSection.SALES:
                tables.append(self._sales_table())
            elif section is ExportSection.RETURNS:
                tables.extend(self._returns_tables())
        return tuple(tables)

    def _accounts_table(self) -> ExportTable:
        rows = self._accounts.list_accounts(include_inactive=True)
        return ExportTable(
            name="accounts",
            headers=(
                "Account ID",
                "Name",
                "Type",
                "Currency",
                "Balance",
                "Active",
                "Notes",
            ),
            rows=tuple(
                (
                    str(row.account_id),
                    row.name,
                    _text(row.account_type),
                    row.currency_code,
                    str(row.balance),
                    _yes_no(row.is_active),
                    _text(row.notes),
                )
                for row in rows
            ),
        )

    def _inventory_table(self) -> ExportTable:
        rows = self._inventory.list_stock()
        return ExportTable(
            name="inventory",
            headers=(
                "Variant ID",
                "Product",
                "Variant",
                "SKU",
                "Active",
                "On hand",
                "Lots",
                "Acquisition value",
            ),
            rows=tuple(
                (
                    str(row.variant_id),
                    row.product_name,
                    _text(row.variant_name),
                    _text(row.sku),
                    _yes_no(row.is_active),
                    str(row.on_hand),
                    str(row.lot_count),
                    " + ".join(str(value) for value in row.value),
                )
                for row in rows
            ),
        )

    def _purchases_table(self) -> ExportTable:
        rows = self._purchases.list_purchases()
        return ExportTable(
            name="purchases",
            headers=(
                "Purchase ID",
                "Date",
                "Supplier",
                "Currency",
                "Items",
                "Total",
                "Status",
                "Account",
                "Order number",
                "Tracking number",
                "Notes",
            ),
            rows=tuple(
                (
                    str(row.purchase_id),
                    row.purchase_date.isoformat(),
                    _text(row.supplier_name),
                    row.currency_code,
                    str(row.item_count),
                    str(row.total),
                    str(row.status),
                    _text(row.account_name),
                    _text(row.order_number),
                    _text(row.tracking_number),
                    _text(row.notes),
                )
                for row in rows
            ),
        )

    def _sales_table(self) -> ExportTable:
        rows = self._sales.list_sales()
        return ExportTable(
            name="sales",
            headers=(
                "Sale ID",
                "Date",
                "Account",
                "Currency",
                "Items",
                "Total",
                "Status",
                "COGS",
                "Gross profit",
                "Notes",
            ),
            rows=tuple(
                (
                    str(row.sale_id),
                    row.sale_date.isoformat(),
                    row.account_name,
                    row.currency_code,
                    str(row.item_count),
                    str(row.total),
                    str(row.status),
                    _money_set(row.cogs),
                    _money_set(row.gross_profit),
                    _text(row.notes),
                )
                for row in rows
            ),
        )

    def _returns_tables(self) -> tuple[ExportTable, ExportTable]:
        customer_rows = self._returns.list_customer_returns()
        supplier_rows = self._returns.list_supplier_returns()
        customer = ExportTable(
            name="customer_returns",
            headers=(
                "Return ID",
                "Date",
                "Sale ID",
                "Items",
                "Refund",
                "Account",
                "Notes",
            ),
            rows=tuple(
                (
                    str(row.return_id),
                    row.return_date.isoformat(),
                    str(row.sale_id),
                    str(row.item_count),
                    _money(row.refund_amount),
                    _text(row.account_name),
                    _text(row.notes),
                )
                for row in customer_rows
            ),
        )
        supplier = ExportTable(
            name="supplier_returns",
            headers=(
                "Return ID",
                "Date",
                "Purchase ID",
                "Supplier",
                "Items",
                "Refund",
                "Account",
                "Notes",
            ),
            rows=tuple(
                (
                    str(row.return_id),
                    row.return_date.isoformat(),
                    str(row.purchase_id),
                    _text(row.supplier_name),
                    str(row.item_count),
                    _money(row.refund_amount),
                    _text(row.account_name),
                    _text(row.notes),
                )
                for row in supplier_rows
            ),
        )
        return customer, supplier


def _text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return _yes_no(value)
    if isinstance(value, Enum):
        return str(value.value)
    return str(value)


def _yes_no(value: bool) -> str:
    return "Yes" if value else "No"


def _money(value: Money | None) -> str:
    return str(value) if value is not None else ""


def _money_set(values: tuple[Money, ...]) -> str:
    return " + ".join(str(value) for value in values)
