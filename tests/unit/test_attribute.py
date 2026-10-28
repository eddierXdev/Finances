"""Attribute and attribute-value entity tests."""

from __future__ import annotations

import pytest

from app.domain.entities.attribute import Attribute, AttributeValue


def test_attribute_trims_name() -> None:
    attribute = Attribute(name="  Color  ")

    assert attribute.name == "Color"
    assert attribute.id is None


def test_attribute_name_is_required() -> None:
    with pytest.raises(ValueError):
        Attribute(name="   ")


def test_attribute_value_trims_value() -> None:
    attribute_value = AttributeValue(attribute_id=1, value="  Red  ")

    assert attribute_value.attribute_id == 1
    assert attribute_value.value == "Red"
    assert attribute_value.id is None


def test_attribute_value_requires_a_value() -> None:
    with pytest.raises(ValueError):
        AttributeValue(attribute_id=1, value="   ")


@pytest.mark.parametrize("attribute_id", [0, -1])
def test_attribute_value_attribute_id_must_be_positive(attribute_id: int) -> None:
    with pytest.raises(ValueError):
        AttributeValue(attribute_id=attribute_id, value="Red")
