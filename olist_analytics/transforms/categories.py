"""Product-category taxonomy.

Olist exposes ~70 raw category labels. For decision-maker reporting we
collapse them into seven broad groups defined by consumer intent. The
mapping is hand-curated and intentionally small so it's auditable.
"""
from __future__ import annotations

import pandas as pd

# Group → list of raw Olist category slugs (Portuguese in some cases, English in
# others — Olist's taxonomy is itself inconsistent, including known typos like
# `fashio_female_clothing` and `costruction_tools_garden`).
CATEGORY_GROUPS: dict[str, list[str]] = {
    "Home & Living": [
        "bed_bath_table",
        "furniture_decor",
        "housewares",
        "home_confort",
        "home_comfort_2",
        "furniture_living_room",
        "furniture_bedroom",
        "furniture_mattress_and_upholstery",
        "kitchen_dining_laundry_garden_furniture",
        "home_appliances",
        "home_appliances_2",
        "small_appliances",
        "small_appliances_home_oven_and_coffee",
        "la_cuisine",
        "garden_tools",
        "flowers",
        "costruction_tools_garden",
    ],
    "Electronics & Tech": [
        "computers_accessories",
        "computers",
        "electronics",
        "telephony",
        "fixed_telephony",
        "tablets_printing_image",
        "pc_gamer",
        "consoles_games",
        "audio",
        "dvds_blu_ray",
        "cds_dvds_musicals",
        "cine_photo",
        "air_conditioning",
        "signaling_and_security",
    ],
    "Fashion & Beauty": [
        "health_beauty",
        "perfumery",
        "fashion_bags_accessories",
        "fashion_shoes",
        "fashion_male_clothing",
        "fashion_female_clothing",
        "fashion_underwear_beach",
        "fashion_sport",
        "fashio_female_clothing",
        "fashion_childrens_clothes",
        "luggage_accessories",
        "watches_gifts",
    ],
    "Leisure & Hobbies": [
        "sports_leisure",
        "toys",
        "cool_stuff",
        "party_supplies",
        "christmas_supplies",
        "art",
        "arts_and_craftmanship",
        "musical_instruments",
        "books_general_interest",
        "books_technical",
        "books_imported",
        "market_place",
    ],
    "Auto & Tools": [
        "auto",
        "construction_tools_construction",
        "construction_tools_lights",
        "construction_tools_safety",
        "costruction_tools_tools",
        "home_construction",
        "industry_commerce_and_business",
        "agro_industry_and_commerce",
    ],
    "Baby, Kids & Pets": [
        "baby",
        "diapers_and_hygiene",
        "pet_shop",
    ],
    "Food, Drinks & Office": [
        "food",
        "food_drink",
        "drinks",
        "office_furniture",
        "stationery",
        "security_and_services",
    ],
}

OTHER_LABEL = "Other / Unknown"


def _build_lookup() -> dict[str, str]:
    """Reverse-index: raw category → group. Earlier definitions win on conflict."""
    seen: set[str] = set()
    lookup: dict[str, str] = {}
    for group, categories in CATEGORY_GROUPS.items():
        for cat in categories:
            if cat in seen:
                continue
            lookup[cat] = group
            seen.add(cat)
    return lookup


_CAT_TO_GROUP = _build_lookup()


def to_group(category: str | float | None) -> str:
    """Map a raw category slug to its broad group label.

    Returns `OTHER_LABEL` for missing, NaN, or unmapped categories. Safe to
    use as the function passed to `Series.apply`.
    """
    if category is None or (isinstance(category, float) and pd.isna(category)):
        return OTHER_LABEL
    if category == "uncategorized":
        return OTHER_LABEL
    return _CAT_TO_GROUP.get(category, OTHER_LABEL)


def assign_groups(items: pd.DataFrame, translation: pd.DataFrame) -> pd.DataFrame:
    """Add `category` (English) and `group` columns to an order-items frame.

    Args:
        items: order-items dataframe — must contain `product_category_name`.
        translation: the category translation table from Olist.

    Returns:
        Copy of `items` with two new columns. Original columns are untouched.
    """
    out = items.copy()
    if "product_category_name_english" not in out.columns:
        out = out.merge(translation, on="product_category_name", how="left")
    out["category"] = out["product_category_name_english"].fillna("other")
    out["group"] = out["category"].apply(to_group)
    return out
