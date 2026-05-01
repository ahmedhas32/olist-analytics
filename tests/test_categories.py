"""Tests for the category taxonomy mapping.

Pure-Python tests that don't require the Olist dataset — they exercise the
mapping logic with synthetic inputs. Useful as a sanity check that
refactoring the taxonomy doesn't break the assignment.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from olist_analytics.transforms.categories import (
    CATEGORY_GROUPS,
    OTHER_LABEL,
    assign_groups,
    to_group,
)


class TestToGroup:
    def test_known_category_maps_to_its_group(self):
        assert to_group("bed_bath_table") == "Home & Living"
        assert to_group("computers_accessories") == "Electronics & Tech"
        assert to_group("health_beauty") == "Fashion & Beauty"
        assert to_group("pet_shop") == "Baby, Kids & Pets"

    def test_unknown_category_maps_to_other(self):
        assert to_group("totally_made_up_category") == OTHER_LABEL

    def test_none_maps_to_other(self):
        assert to_group(None) == OTHER_LABEL

    def test_nan_maps_to_other(self):
        assert to_group(float("nan")) == OTHER_LABEL
        assert to_group(np.nan) == OTHER_LABEL

    def test_uncategorized_maps_to_other(self):
        assert to_group("uncategorized") == OTHER_LABEL

    def test_known_typo_categories_are_handled(self):
        # Olist's data contains these exact misspellings — taxonomy preserves them
        assert to_group("fashio_female_clothing") == "Fashion & Beauty"
        assert to_group("costruction_tools_garden") == "Home & Living"


class TestCategoryGroupsStructure:
    def test_no_category_appears_in_two_groups(self):
        seen: dict[str, str] = {}
        for group, cats in CATEGORY_GROUPS.items():
            for cat in cats:
                if cat in seen and seen[cat] != group:
                    pytest.fail(f"{cat!r} is in both {seen[cat]} and {group}")
                seen[cat] = group

    def test_all_seven_groups_present(self):
        expected = {
            "Home & Living",
            "Electronics & Tech",
            "Fashion & Beauty",
            "Leisure & Hobbies",
            "Auto & Tools",
            "Baby, Kids & Pets",
            "Food, Drinks & Office",
        }
        assert set(CATEGORY_GROUPS.keys()) == expected


class TestAssignGroups:
    def test_adds_category_and_group_columns(self):
        items = pd.DataFrame({
            "order_id": ["o1", "o2", "o3"],
            "product_category_name": ["cama_mesa_banho", "informatica_acessorios", None],
        })
        translation = pd.DataFrame({
            "product_category_name": ["cama_mesa_banho", "informatica_acessorios"],
            "product_category_name_english": ["bed_bath_table", "computers_accessories"],
        })
        out = assign_groups(items, translation)
        assert list(out["group"]) == ["Home & Living", "Electronics & Tech", OTHER_LABEL]
        # Original input not mutated
        assert "group" not in items.columns

    def test_idempotent_when_english_already_present(self):
        items = pd.DataFrame({
            "order_id": ["o1"],
            "product_category_name": ["bed_bath_table"],
            "product_category_name_english": ["bed_bath_table"],
        })
        translation = pd.DataFrame({
            "product_category_name": ["bed_bath_table"],
            "product_category_name_english": ["bed_bath_table"],
        })
        out = assign_groups(items, translation)
        assert out["group"].iloc[0] == "Home & Living"
