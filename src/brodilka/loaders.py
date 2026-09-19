"""Loading Instacart CSVs with compact dtypes and a parquet cache of the long item table.

The long table `items` has one row per (order, product) from prior+train, sorted by
(order_id, add_to_cart_order), joined with aisle/department ids, with `missing`/`other`
departments dropped. Everything downstream (EDA, features) starts from it.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from brodilka.config import Config

ITEM_COLS = ["order_id", "user_id", "order_number", "add_to_cart_order", "product_id",
             "aisle_id", "department_id", "reordered", "order_dow", "order_hour_of_day",
             "days_since_prior_order", "eval_set"]


@dataclass
class Dims:
    departments: pd.DataFrame  # department_id, department (filtered, sorted by id)
    aisles: pd.DataFrame       # aisle_id, aisle, department_id (dominant department)
    products: pd.DataFrame     # product_id, product_name, aisle_id, department_id


def load_dims(cfg: Config) -> Dims:
    raw = cfg.path("raw")
    dep = pd.read_csv(raw / "departments.csv")
    dep = dep[~dep["department"].isin(cfg["data"]["exclude_departments"])].sort_values("department_id")
    prod = pd.read_csv(raw / "products.csv")
    prod = prod[prod["department_id"].isin(dep["department_id"])]
    aisles = pd.read_csv(raw / "aisles.csv")
    # each aisle belongs to exactly one department in Instacart, but derive it defensively
    a2d = prod.groupby("aisle_id")["department_id"].agg(lambda s: s.value_counts().index[0])
    aisles = aisles[aisles["aisle_id"].isin(a2d.index)].copy()
    aisles["department_id"] = aisles["aisle_id"].map(a2d).astype(int)
    return Dims(dep.reset_index(drop=True), aisles.reset_index(drop=True), prod.reset_index(drop=True))


def load_orders(cfg: Config) -> pd.DataFrame:
    raw = cfg.path("raw")
    return pd.read_csv(
        raw / "orders.csv",
        dtype={"order_id": "int32", "user_id": "int32", "order_number": "int16",
               "order_dow": "int8", "order_hour_of_day": "int8", "days_since_prior_order": "float32",
               "eval_set": "category"},
    )


def load_items(cfg: Config, rebuild: bool = False) -> pd.DataFrame:
    """Long item table (prior + train), cached as parquet in data/interim."""
    cache = cfg.path("interim") / "items.parquet"
    if cache.exists() and not rebuild:
        return pd.read_parquet(cache)
    raw = cfg.path("raw")
    dims = load_dims(cfg)
    dt = {"order_id": "int32", "product_id": "int32", "add_to_cart_order": "int16", "reordered": "int8"}
    parts = [pd.read_csv(raw / f, dtype=dt, engine="pyarrow")
             for f in ("order_products__prior.csv", "order_products__train.csv")]
    op = pd.concat(parts, ignore_index=True)
    del parts
    prod = dims.products[["product_id", "aisle_id", "department_id"]].astype(
        {"product_id": "int32", "aisle_id": "int16", "department_id": "int8"})
    op = op.merge(prod, on="product_id", how="inner")  # inner join drops missing/other departments
    orders = load_orders(cfg)
    op = op.merge(orders, on="order_id", how="inner")
    op.sort_values(["order_id", "add_to_cart_order"], inplace=True, kind="stable")
    op = op[ITEM_COLS].reset_index(drop=True)
    op.to_parquet(cache, index=False)
    return op


def order_boundaries(items: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Start indices and lengths of each order in the (sorted) long table."""
    oid = items["order_id"].to_numpy()
    starts = np.flatnonzero(np.r_[True, oid[1:] != oid[:-1]])
    lengths = np.diff(np.r_[starts, len(oid)])
    return starts, lengths
