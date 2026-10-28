"""Supplier entity rules."""

from __future__ import annotations

import pytest

from app.domain.entities.supplier import Supplier


def test_supplier_normalizes_text_and_is_active_by_default() -> None:
    supplier = Supplier(
        name="  Acme Traders  ",
        supplier_type="  WHOLESALER ",
        website="  https://acme.example  ",
        contact="  sales@acme.example ",
        notes="  Preferred  ",
    )

    assert supplier.name == "Acme Traders"
    assert supplier.supplier_type == "WHOLESALER"
    assert supplier.website == "https://acme.example"
    assert supplier.contact == "sales@acme.example"
    assert supplier.notes == "Preferred"
    assert supplier.is_active is True
    assert supplier.id is None


def test_supplier_requires_a_name() -> None:
    with pytest.raises(ValueError):
        Supplier(name="   ")


def test_supplier_deactivation_is_non_destructive() -> None:
    supplier = Supplier(name="Acme", id=1)

    inactive = supplier.deactivate()

    assert inactive.is_active is False
    assert supplier.is_active is True
    assert inactive.activate() == supplier


def test_supplier_rejects_an_invalid_identifier() -> None:
    with pytest.raises(ValueError):
        Supplier(name="Acme", id=0)
