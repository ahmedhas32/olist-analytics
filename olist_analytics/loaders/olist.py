"""Olist dataset loaders.

A single entry point (`load_all`) reads every CSV the project needs and
returns a typed container. Date columns are parsed up front so downstream
code never has to think about it.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

# Filenames used by the Olist Kaggle distribution. Kept centralised so an
# upstream rename (or local data subset) is a one-line change.
FILES = {
    "orders": "olist_orders_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "order_payments": "olist_order_payments_dataset.csv",
    "order_reviews": "olist_order_reviews_dataset.csv",
    "customers": "olist_customers_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "products": "olist_products_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
}

ORDER_DATE_COLS = [
    "order_purchase_timestamp",
    "order_approved_at",
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "order_estimated_delivery_date",
]


@dataclass
class OlistData:
    """Typed container for the loaded Olist tables.

    Each attribute is a `pd.DataFrame`; the names match the CSVs minus the
    `olist_` prefix and `_dataset` suffix.
    """

    orders: pd.DataFrame
    order_items: pd.DataFrame
    order_payments: pd.DataFrame
    order_reviews: pd.DataFrame
    customers: pd.DataFrame
    sellers: pd.DataFrame
    products: pd.DataFrame
    category_translation: pd.DataFrame


def load_all(data_dir: str | Path) -> OlistData:
    """Read every CSV in `data_dir` and return an `OlistData` container.

    Raises:
        FileNotFoundError: if any expected CSV is missing.
    """
    data_dir = Path(data_dir)
    if not data_dir.exists():
        raise FileNotFoundError(f"Data directory not found: {data_dir}")

    frames = {key: _read_csv(data_dir / fname) for key, fname in FILES.items()}

    # Parse order-related dates once, here — every downstream module relies on
    # these being datetimes.
    for col in ORDER_DATE_COLS:
        if col in frames["orders"].columns:
            frames["orders"][col] = pd.to_datetime(
                frames["orders"][col], errors="coerce"
            )

    return OlistData(**frames)


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Expected Olist CSV not found: {path}")
    return pd.read_csv(path)
