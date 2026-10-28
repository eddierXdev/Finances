"""Category entity tests."""

from __future__ import annotations

import pytest

from app.domain.entities.category import Category


def test_category_trims_name_and_description() -> None:
    category = Category(name="  Electronics  ", description="  Devices  ")

    assert category.name == "Electronics"
    assert category.description == "Devices"
    assert category.id is None


def test_blank_description_becomes_none() -> None:
    category = Category(name="Electronics", description="   ")

    assert category.description is None


def test_category_name_is_required() -> None:
    with pytest.raises(ValueError):
        Category(name="  ")
