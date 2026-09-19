"""Build training examples: basket prefix -> next department not yet in the basket.

Steps
  1. sample `data.sample_users` users (seeded) among those with >= split.min_orders_per_user orders;
  2. per-user chronological split: last order -> test, previous -> val, the rest -> train;
  3. one example per (order, prefix length k <= task.max_prefix) whenever a "next new department"
     exists after position k (see eda.next_new_department);
  4. user-history features from orders strictly before the current one (cumulative, shifted);
  5. lift / transition / popularity tables recomputed on TRAIN orders only -> results/tables_train.json,
     so baselines and model features never see val/test orders.

Output: data/interim/examples.parquet
"""
from __future__ import annotations

import json
import time

import numpy as np
import pandas as pd

from brodilka.config import Config, parse_args
from brodilka.eda import cooccurrence, lift_from_cooc, next_new_department
from brodilka.loaders import load_dims, load_items, order_boundaries

USER_FEATS = ["u_n_orders", "u_reorder_rate", "u_avg_basket", "u_days_mean"]


def sample_users(items: pd.DataFrame, cfg: Config) -> np.ndarray:
    n_orders = items.groupby("user_id", sort=False)["order_id"].nunique()
    eligible = n_orders[n_orders >= int(cfg["split"]["min_orders_per_user"])].index.to_numpy()
    k = cfg["data"]["sample_users"]
    if k is None or k >= len(eligible):
        return np.sort(eligible)
    rng = np.random.default_rng(cfg.seed)
    return np.sort(rng.choice(eligible, size=int(k), replace=False))


def split_orders(orders: pd.DataFrame, cfg: Config) -> pd.Series:
    """'train' / 'val' / 'test' per order_id, by rank of order_number within user (desc)."""
    rank_desc = orders.groupby("user_id")["order_number"].rank(method="first", ascending=False)
    n_test, n_val = int(cfg["split"]["n_test"]), int(cfg["split"]["n_val"])
    split = np.where(rank_desc <= n_test, "test", np.where(rank_desc <= n_test + n_val, "val", "train"))
    return pd.Series(split, index=orders["order_id"].to_numpy(), name="split")


def basket_prefix_counts(dcat: np.ndarray, starts: np.ndarray, lengths: np.ndarray, n_dep: int) -> np.ndarray:
    """Row i -> counts of each department among items 1..i of the same order (inclusive)."""
    onehot = np.zeros((len(dcat), n_dep), dtype=np.int32)
    onehot[np.arange(len(dcat)), dcat] = 1
    cs = onehot.cumsum(axis=0)
    prev = cs[np.maximum(starts - 1, 0)]
    prev[starts == 0] = 0
    return cs - np.repeat(prev, lengths, axis=0)


def user_history(items: pd.DataFrame, orders: pd.DataFrame, dep_pos: dict) -> pd.DataFrame:
    """Per order: features from the same user's EARLIER orders only (cumulative, shifted by one)."""
    n_dep = len(dep_pos)
    od = items[["order_id", "department_id"]].drop_duplicates()
    od["d"] = od["department_id"].map(dep_pos)
    pres = pd.crosstab(od["order_id"], od["d"]).reindex(columns=range(n_dep), fill_value=0)
    per_order = orders[["order_id", "user_id", "order_number", "days_since_prior_order"]].copy()
    agg = items.groupby("order_id", sort=False).agg(n_items=("product_id", "size"), n_reord=("reordered", "sum"))
    per_order = per_order.merge(agg, on="order_id").merge(pres, left_on="order_id", right_index=True)
    per_order.sort_values(["user_id", "order_number"], inplace=True)
    g = per_order.groupby("user_id", sort=False)
    dep_cols = list(range(n_dep))
    hist = pd.DataFrame({"order_id": per_order["order_id"].to_numpy()})
    hist["u_n_orders"] = g.cumcount().to_numpy()
    cum_items = g["n_items"].cumsum() - per_order["n_items"]
    cum_reord = g["n_reord"].cumsum() - per_order["n_reord"]
    with np.errstate(divide="ignore", invalid="ignore"):
        hist["u_reorder_rate"] = np.where(cum_items > 0, cum_reord / cum_items, np.nan).astype("float32")
        hist["u_avg_basket"] = np.where(hist["u_n_orders"] > 0, cum_items / hist["u_n_orders"], np.nan).astype("float32")
    d = per_order["days_since_prior_order"].fillna(0)
    hist["u_days_mean"] = ((g["days_since_prior_order"].cumsum().fillna(0) - d) /
                           hist["u_n_orders"].replace(0, np.nan)).astype("float32").to_numpy()
    cum_dep = g[dep_cols].cumsum().to_numpy() - per_order[dep_cols].to_numpy()  # prior orders containing dept
    for j in dep_cols:
        hist[f"h_{j}"] = cum_dep[:, j].astype("int16")  # raw counts (heuristic uses them)
    return hist


def train_tables(items_tr: pd.DataFrame, dep_pos: dict, cfg: Config) -> dict:
    """Lift, next-new-department transitions and next-department popularity on train orders."""
    n_dep = len(dep_pos)
    starts, lengths = order_boundaries(items_tr)
    order_idx = np.repeat(np.arange(len(starts)), lengths)
    dcat = items_tr["department_id"].map(dep_pos).to_numpy()
    co = cooccurrence(order_idx, dcat, len(starts), n_dep)
    lift, p_order = lift_from_cooc(co, len(starts))
    target, _ = next_new_department(items_tr)
    ok = target >= 0
    tcat = pd.Series(target[ok]).map(dep_pos).to_numpy()
    counts = np.zeros((n_dep, n_dep), dtype=np.int64)
    np.add.at(counts, (dcat[ok], tcat), 1)
    trans = counts / np.maximum(counts.sum(1, keepdims=True), 1)
    pop = counts.sum(0) / counts.sum()
    return {"n_orders": len(starts), "lift": lift.round(5).tolist(), "p_order": p_order.round(5).tolist(),
            "transitions": trans.round(5).tolist(), "pop_next": pop.round(5).tolist()}


def run(cfg: Config) -> None:
    t0 = time.time()
    dims = load_dims(cfg)
    dep_ids = dims.departments["department_id"].to_numpy()
    dep_pos = {d: i for i, d in enumerate(dep_ids)}
    n_dep = len(dep_ids)
    items = load_items(cfg)
    users = sample_users(items, cfg)
    items = items[items["user_id"].isin(users)].reset_index(drop=True)
    orders = items.drop_duplicates("order_id")[["order_id", "user_id", "order_number", "order_dow",
                                                 "order_hour_of_day", "days_since_prior_order"]]
    split = split_orders(orders, cfg)
    items["split"] = items["order_id"].map(split).astype("category")
    print(f"features: {len(users):,} users, {len(orders):,} orders, {len(items):,} items "
          f"(split by orders: {split.value_counts().to_dict()})")

    # ---- tables on train orders only ---------------------------------------------------
    tables = train_tables(items[items["split"] == "train"], dep_pos, cfg)
    tables["departments"] = dims.departments["department"].tolist()
    json.dump(tables, open(cfg.path("results") / "tables_train.json", "w"), indent=0)

    # ---- per-row example candidates -----------------------------------------------------
    starts, lengths = order_boundaries(items)
    dcat = items["department_id"].map(dep_pos).to_numpy()
    pos = (np.arange(len(items)) - np.repeat(starts, lengths) + 1).astype("int16")  # 1-based prefix len
    target, _ = next_new_department(items)
    counts = basket_prefix_counts(dcat, starts, lengths, n_dep)
    n_dep_basket = (counts > 0).sum(1).astype("int8")
    first_dept = np.repeat(dcat[starts], lengths)

    keep = (target >= 0) & (pos <= int(cfg["task"]["max_prefix"]))
    ex = pd.DataFrame({
        "order_id": items["order_id"].to_numpy()[keep],
        "user_id": items["user_id"].to_numpy()[keep],
        "split": items["split"].to_numpy()[keep],
        "order_number": items["order_number"].to_numpy()[keep],
        "order_dow": items["order_dow"].to_numpy()[keep],
        "order_hour_of_day": items["order_hour_of_day"].to_numpy()[keep],
        "days_since_prior_order": items["days_since_prior_order"].to_numpy()[keep],
        "k": pos[keep],
        "n_dep_basket": n_dep_basket[keep],
        "first_dept": first_dept[keep].astype("int8"),
        "last_dept": dcat[keep].astype("int8"),
        "last_aisle": items["aisle_id"].to_numpy()[keep].astype("int16"),
        "target": pd.Series(target[keep]).map(dep_pos).to_numpy().astype("int8"),
    })
    for j in range(n_dep):
        ex[f"b_{j}"] = counts[keep, j].astype("int8")

    # ---- leak-free user history ---------------------------------------------------------
    hist = user_history(items, orders, dep_pos)
    ex = ex.merge(hist, on="order_id", how="left")
    ex.sort_values(["user_id", "order_number", "k"], inplace=True, kind="stable")
    ex.reset_index(drop=True, inplace=True)
    out = cfg.path("interim") / "examples.parquet"
    ex.to_parquet(out, index=False)

    summary = {
        "n_users": len(users), "n_orders": len(orders),
        "examples_by_split": ex["split"].value_counts().to_dict(),
        "examples_per_order": float(len(ex) / len(orders)),
        "target_share_train": ex.loc[ex.split == "train", "target"].value_counts(normalize=True).round(4).to_dict(),
        "n_features": int(ex.shape[1]),
    }
    json.dump(summary, open(cfg.path("results") / "features_summary.json", "w"), indent=1)
    print(f"features: examples {summary['examples_by_split']}, {summary['examples_per_order']:.1f} per order, "
          f"{ex.shape[1]} columns -> {out} in {time.time() - t0:.0f}s")


def main() -> None:
    run(parse_args(__doc__))


if __name__ == "__main__":
    main()
