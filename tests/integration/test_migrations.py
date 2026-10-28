"""Alembic migration tests."""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HEAD_REVISION = "0010_expenses"


def _alembic_config(database_url: str) -> Config:
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def test_migrations_apply_to_a_clean_database(tmp_path: Path) -> None:
    database_path = tmp_path / "migrated.db"
    database_url = f"sqlite:///{database_path.as_posix()}"

    config = _alembic_config(database_url)
    command.upgrade(config, "head")

    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            version = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
            currency_count = connection.execute(
                text("SELECT COUNT(*) FROM currencies")
            ).scalar_one()
    finally:
        engine.dispose()

    assert version == HEAD_REVISION
    assert ScriptDirectory.from_config(config).get_current_head() == HEAD_REVISION
    assert currency_count == 7
    assert database_path.is_file()


def test_purchase_migration_can_round_trip(tmp_path: Path) -> None:
    database_path = tmp_path / "round_trip.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    config = _alembic_config(database_url)

    command.upgrade(config, "head")
    engine = create_engine(database_url)
    try:
        assert {
            "suppliers",
            "purchases",
            "purchase_items",
            "purchase_costs",
            "purchase_cost_allocations",
        } <= set(inspect(engine).get_table_names())
        assert "purchase_id" in {
            column["name"]
            for column in inspect(engine).get_columns(
                "financial_transactions"
            )
        }

        command.downgrade(config, "0004_accounts_and_ledger")

        assert "purchases" not in inspect(engine).get_table_names()
        assert "purchase_id" not in {
            column["name"]
            for column in inspect(engine).get_columns(
                "financial_transactions"
            )
        }

        command.upgrade(config, "head")
        command.check(config)
    finally:
        engine.dispose()

    assert database_path.is_file()


def test_inventory_migration_can_round_trip(tmp_path: Path) -> None:
    database_path = tmp_path / "inventory_round_trip.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    config = _alembic_config(database_url)

    command.upgrade(config, "head")
    engine = create_engine(database_url)
    try:
        assert {
            "inventory_lots",
            "inventory_movements",
        } <= set(inspect(engine).get_table_names())
        assert {
            "acquired_quantity",
            "remaining_quantity",
            "unit_cost",
            "currency_id",
            "received_at",
        } <= {
            column["name"]
            for column in inspect(engine).get_columns("inventory_lots")
        }
        assert {
            "inventory_lot_id",
            "movement_type",
            "quantity",
            "reference_type",
            "reference_id",
        } <= {
            column["name"]
            for column in inspect(engine).get_columns(
                "inventory_movements"
            )
        }

        command.downgrade(config, "0005_purchases")

        assert "inventory_lots" not in inspect(engine).get_table_names()
        assert "inventory_movements" not in inspect(engine).get_table_names()

        command.upgrade(config, "head")
        command.check(config)
    finally:
        engine.dispose()

    assert database_path.is_file()


def test_sales_migration_can_round_trip(tmp_path: Path) -> None:
    database_path = tmp_path / "sales_round_trip.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    config = _alembic_config(database_url)

    command.upgrade(config, "head")
    engine = create_engine(database_url)
    try:
        assert {
            "customers",
            "sales",
            "sale_items",
            "sale_item_lot_allocations",
        } <= set(inspect(engine).get_table_names())
        assert {
            "customer_id",
            "account_id",
            "currency_id",
            "status",
            "sale_date",
            "discount_amount",
        } <= {
            column["name"]
            for column in inspect(engine).get_columns("sales")
        }
        assert {
            "sale_id",
            "variant_id",
            "quantity",
            "unit_price",
            "discount_amount",
        } <= {
            column["name"]
            for column in inspect(engine).get_columns("sale_items")
        }
        assert {
            "sale_item_id",
            "inventory_lot_id",
            "quantity",
            "unit_cost_snapshot",
        } <= {
            column["name"]
            for column in inspect(engine).get_columns(
                "sale_item_lot_allocations"
            )
        }
        assert "sale_id" in {
            column["name"]
            for column in inspect(engine).get_columns(
                "financial_transactions"
            )
        }

        command.downgrade(
            config, "0006_inventory_lots_and_movements"
        )

        assert "sales" not in inspect(engine).get_table_names()
        assert "sale_item_lot_allocations" not in (
            inspect(engine).get_table_names()
        )
        assert "sale_id" not in {
            column["name"]
            for column in inspect(engine).get_columns(
                "financial_transactions"
            )
        }

        command.upgrade(config, "head")
        command.check(config)
    finally:
        engine.dispose()

    assert database_path.is_file()


def test_customer_returns_migration_can_round_trip(tmp_path: Path) -> None:
    database_path = tmp_path / "returns_round_trip.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    config = _alembic_config(database_url)

    command.upgrade(config, "head")
    engine = create_engine(database_url)
    try:
        assert {
            "customer_returns",
            "customer_return_items",
            "return_lot_allocations",
        } <= set(inspect(engine).get_table_names())
        assert {
            "sale_id",
            "account_id",
            "refund_amount",
            "refund_currency_id",
            "return_date",
            "notes",
        } <= {
            column["name"]
            for column in inspect(engine).get_columns("customer_returns")
        }
        assert {
            "customer_return_id",
            "sale_item_id",
            "quantity",
            "condition",
        } <= {
            column["name"]
            for column in inspect(engine).get_columns(
                "customer_return_items"
            )
        }
        assert {
            "customer_return_item_id",
            "sale_item_lot_allocation_id",
            "quantity",
            "unit_cost_snapshot",
        } <= {
            column["name"]
            for column in inspect(engine).get_columns(
                "return_lot_allocations"
            )
        }
        assert "customer_return_id" in {
            column["name"]
            for column in inspect(engine).get_columns(
                "financial_transactions"
            )
        }

        command.downgrade(config, "0007_sales_and_fifo_allocations")

        assert "customer_returns" not in inspect(engine).get_table_names()
        assert "customer_return_items" not in (
            inspect(engine).get_table_names()
        )
        assert "return_lot_allocations" not in (
            inspect(engine).get_table_names()
        )
        assert "customer_return_id" not in {
            column["name"]
            for column in inspect(engine).get_columns(
                "financial_transactions"
            )
        }

        command.upgrade(config, "head")
        command.check(config)
    finally:
        engine.dispose()

    assert database_path.is_file()


def test_supplier_returns_migration_can_round_trip(tmp_path: Path) -> None:
    database_path = tmp_path / "supplier_returns_round_trip.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    config = _alembic_config(database_url)

    command.upgrade(config, "head")
    engine = create_engine(database_url)
    try:
        assert {
            "supplier_returns",
            "supplier_return_items",
        } <= set(inspect(engine).get_table_names())
        assert {
            "purchase_id",
            "supplier_id",
            "account_id",
            "refund_amount",
            "refund_currency_id",
            "return_date",
            "notes",
        } <= {
            column["name"]
            for column in inspect(engine).get_columns("supplier_returns")
        }
        assert {
            "supplier_return_id",
            "purchase_item_id",
            "inventory_lot_id",
            "quantity",
            "unit_cost_snapshot",
        } <= {
            column["name"]
            for column in inspect(engine).get_columns(
                "supplier_return_items"
            )
        }
        assert "supplier_return_id" in {
            column["name"]
            for column in inspect(engine).get_columns(
                "financial_transactions"
            )
        }

        command.downgrade(config, "0008_customer_returns")

        assert "supplier_returns" not in inspect(engine).get_table_names()
        assert "supplier_return_items" not in (
            inspect(engine).get_table_names()
        )
        assert "supplier_return_id" not in {
            column["name"]
            for column in inspect(engine).get_columns(
                "financial_transactions"
            )
        }

        command.upgrade(config, "head")
        command.check(config)
    finally:
        engine.dispose()

    assert database_path.is_file()


def test_expenses_migration_can_round_trip(tmp_path: Path) -> None:
    database_path = tmp_path / "expenses_round_trip.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    config = _alembic_config(database_url)

    command.upgrade(config, "head")
    engine = create_engine(database_url)
    try:
        assert "expenses" in inspect(engine).get_table_names()
        assert {
            "account_id",
            "expense_type",
            "amount",
            "currency_id",
            "expense_date",
            "description",
            "notes",
        } <= {
            column["name"]
            for column in inspect(engine).get_columns("expenses")
        }
        assert "expense_id" in {
            column["name"]
            for column in inspect(engine).get_columns(
                "financial_transactions"
            )
        }

        command.downgrade(config, "0009_supplier_returns")

        assert "expenses" not in inspect(engine).get_table_names()
        assert "expense_id" not in {
            column["name"]
            for column in inspect(engine).get_columns(
                "financial_transactions"
            )
        }

        command.upgrade(config, "head")
        command.check(config)
    finally:
        engine.dispose()

    assert database_path.is_file()


def test_migrations_can_run_offline(tmp_path: Path, capsys) -> None:
    config = _alembic_config(f"sqlite:///{(tmp_path / 'offline.db').as_posix()}")

    command.upgrade(config, "head", sql=True)

    output = capsys.readouterr().out
    assert "CREATE TABLE alembic_version" in output
    assert "CREATE TABLE currencies" in output
    assert "CREATE TABLE exchange_rates" in output

    command.downgrade(
        config,
        f"{HEAD_REVISION}:0004_accounts_and_ledger",
        sql=True,
    )
    downgrade_output = capsys.readouterr().out
    assert "_alembic_tmp_financial_transactions" in downgrade_output
    assert "DROP TABLE purchases" in downgrade_output
