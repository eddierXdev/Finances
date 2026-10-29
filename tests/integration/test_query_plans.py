"""SQLite query-plan regression tests for frequently ordered queries."""

from __future__ import annotations

from sqlalchemy import text


def _plan(connection, statement: str) -> str:
    rows = connection.execute(
        text(f"EXPLAIN QUERY PLAN {statement}")
    ).fetchall()
    return "\n".join(str(row[-1]) for row in rows)


def test_inventory_lot_purchase_item_query_uses_its_index(
    migrated_engine,
) -> None:
    with migrated_engine.connect() as connection:
        plan = _plan(
            connection,
            "SELECT id FROM inventory_lots "
            "WHERE purchase_item_id = 1 ORDER BY received_at, id",
        )

    assert "ix_inventory_lots_purchase_item_id_received_at" in plan
    assert "TEMP B-TREE" not in plan


def test_inventory_movement_history_uses_variant_date_index(
    migrated_engine,
) -> None:
    with migrated_engine.connect() as connection:
        plan = _plan(
            connection,
            "SELECT id FROM inventory_movements "
            "WHERE variant_id = 1 ORDER BY movement_date, id",
        )

    assert "ix_inventory_movements_variant_id_movement_date" in plan
    assert "TEMP B-TREE" not in plan


def test_inventory_movement_lot_history_uses_lot_date_index(
    migrated_engine,
) -> None:
    with migrated_engine.connect() as connection:
        plan = _plan(
            connection,
            "SELECT id FROM inventory_movements "
            "WHERE inventory_lot_id = 1 ORDER BY movement_date, id",
        )

    assert (
        "ix_inventory_movements_inventory_lot_id_movement_date" in plan
    )
    assert "TEMP B-TREE" not in plan
