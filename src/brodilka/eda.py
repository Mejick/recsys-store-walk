"""EDA: basket statistics, department/aisle lift, directed transitions by add_to_cart_order.

Outputs (all on ALL orders, prior + train):
  results/lift_department.json     symmetric lift matrix over 19 departments
  results/lift_aisle.json          lift over 134 aisles, pairs below min support set to null
  results/transitions_department.json  P(next NEW department | current department)
  results/eda_stats.json           distributions + directed-vs-symmetric divergence table
"""
from __future__ import annotations

import json
import time

import numpy as np
import pandas as pd
import scipy.sparse as sp

from brodilka.config import Config, parse_args
from brodilka.loaders import load_dims, load_items, order_boundaries


def cooccurrence(order_idx: np.ndarray, cat: np.ndarray, n_orders: int, n_cat: int) -> np.ndarray:
    """Binary order x category matrix -> category x category co-occurrence counts (orders)."""
    m = sp.csr_matrix((np.ones(len(cat), dtype=np.float32), (order_idx, cat)), shape=(n_orders, n_cat))
    m.data[:] = 1.0  # duplicates summed above; make it binary
    return (m.T @ m).toarray()


def lift_from_cooc(co: np.ndarray, n_orders: int) -> tuple[np.ndarray, np.ndarray]:
    p = np.diag(co) / n_orders
    with np.errstate(divide="ignore", invalid="ignore"):
        lift = (co / n_orders) / np.outer(p, p)
    np.fill_diagonal(lift, 1.0)
    return lift, p


def next_new_department(items: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """For every item row: the department of the next item in the same order whose
    department is not yet in the basket at that point (-1 if there is none)."""
    oid = items["order_id"].to_numpy()
    dept = items["department_id"].to_numpy()
    is_new = ~items.duplicated(["order_id", "department_id"]).to_numpy()
    n = len(oid)
    idx = np.arange(n)
    # for each row, the nearest later row flagged as "new" (globally, then checked for same order)
    cand = np.where(is_new, idx, n)
    nxt = np.minimum.accumulate(cand[::-1])[::-1]              # nearest new at position >= i
    nxt = np.r_[nxt[1:], n]                                     # strictly > i
    ok = (nxt < n)
    ok[ok] &= oid[nxt[ok]] == oid[ok]
    target = np.full(n, -1, dtype=np.int16)
    target[ok] = dept[nxt[ok]]
    return target, is_new


def run(cfg: Config) -> None:
    t0 = time.time()
    dims = load_dims(cfg)
    items = load_items(cfg)
    print(f"eda: items table {len(items):,} rows, loaded in {time.time() - t0:.0f}s")
    art = cfg.path("results")

    dep_ids = dims.departments["department_id"].to_numpy()
    dep_names = dims.departments["department"].tolist()
    dep_pos = {d: i for i, d in enumerate(dep_ids)}
    aisle_ids = dims.aisles["aisle_id"].to_numpy()
    aisle_names = dims.aisles["aisle"].tolist()
    aisle_pos = {a: i for i, a in enumerate(aisle_ids)}

    starts, lengths = order_boundaries(items)
    n_orders = len(starts)
    order_idx = np.repeat(np.arange(n_orders), lengths)
    dcat = items["department_id"].map(dep_pos).to_numpy()
    acat = items["aisle_id"].map(aisle_pos).to_numpy()

    # ---- distributions ----------------------------------------------------------------
    n_dept_per_order = items.groupby("order_id", sort=False)["department_id"].nunique().to_numpy()
    stats = {
        "n_orders": int(n_orders),
        "n_users": int(items["user_id"].nunique()),
        "n_items": len(items),
        "basket_size": {"mean": float(lengths.mean()), "median": float(np.median(lengths)),
                        "p90": float(np.percentile(lengths, 90)),
                        "hist": {str(k): int(v) for k, v in zip(*np.unique(np.minimum(lengths, 30), return_counts=True))}},
        "departments_per_order": {"mean": float(n_dept_per_order.mean()),
                                  "hist": {str(k): int(v) for k, v in zip(*np.unique(n_dept_per_order, return_counts=True))}},
        "share_single_department_orders": float((n_dept_per_order == 1).mean()),
    }

    # ---- lift: department ------------------------------------------------------------
    co_d = cooccurrence(order_idx, dcat, n_orders, len(dep_ids))
    lift_d, p_d = lift_from_cooc(co_d, n_orders)
    stats["department_share_of_orders"] = dict(zip(dep_names, map(float, p_d)))
    json.dump({"departments": dep_names, "department_ids": dep_ids.tolist(),
               "n_orders": int(n_orders), "support": np.diag(co_d).astype(int).tolist(),
               "lift": np.round(lift_d, 4).tolist()},
              open(art / "lift_department.json", "w"), indent=0)

    # ---- lift: aisle (with min support) ----------------------------------------------
    co_a = cooccurrence(order_idx, acat, n_orders, len(aisle_ids))
    lift_a, p_a = lift_from_cooc(co_a, n_orders)
    min_sup = int(cfg["data"]["aisle_min_support"])
    lift_a_out = np.where(co_a >= min_sup, np.round(lift_a, 4), np.nan)
    np.fill_diagonal(lift_a_out, 1.0)
    stats["aisle_pairs_kept_share"] = float((co_a >= min_sup).sum() / co_a.size)
    json.dump({"aisles": aisle_names, "aisle_ids": aisle_ids.tolist(),
               "aisle_department_ids": dims.aisles["department_id"].tolist(),
               "min_support": min_sup, "support": np.diag(co_a).astype(int).tolist(),
               "lift": [[None if np.isnan(x) else float(x) for x in row] for row in lift_a_out]},
              open(art / "lift_aisle.json", "w"), indent=0)

    # ---- directed transitions by add_to_cart_order ------------------------------------
    target, is_new = next_new_department(items)
    has_t = target >= 0
    cur = dcat[has_t]
    nxt = np.array([dep_pos[d] for d in dep_ids])[np.searchsorted(dep_ids, target[has_t])]
    trans_counts = np.zeros((len(dep_ids), len(dep_ids)), dtype=np.int64)
    np.add.at(trans_counts, (cur, nxt), 1)
    row_sum = trans_counts.sum(1, keepdims=True)
    trans = np.divide(trans_counts, row_sum, out=np.zeros_like(trans_counts, dtype=float), where=row_sum > 0)
    # "directed lift": P(next=B | cur=A) / P(next=B) — comparable in scale to symmetric lift
    p_next = trans_counts.sum(0) / trans_counts.sum()
    dlift = trans / p_next
    stats["share_items_with_next_new_department"] = float(has_t.mean())
    json.dump({"departments": dep_names, "department_ids": dep_ids.tolist(),
               "counts": trans_counts.tolist(), "p_next_given_current": np.round(trans, 5).tolist(),
               "p_next_marginal": np.round(p_next, 5).tolist(),
               "directed_lift": np.round(dlift, 4).tolist()},
              open(art / "transitions_department.json", "w"), indent=0)

    # ---- where directed and symmetric disagree ---------------------------------------
    rows = []
    for i in range(len(dep_ids)):
        for j in range(len(dep_ids)):
            if i != j:
                rows.append((dep_names[i], dep_names[j], lift_d[i, j], dlift[i, j], dlift[j, i], trans[i, j]))
    df = pd.DataFrame(rows, columns=["a", "b", "lift_sym", "dlift_a_to_b", "dlift_b_to_a", "p_next_b_given_a"])
    df["asym"] = np.log(df["dlift_a_to_b"] / df["dlift_b_to_a"])
    df["gap_vs_sym"] = np.log(df["dlift_a_to_b"] / df["lift_sym"])
    stats["top_asymmetric_pairs"] = (df.sort_values("asym", ascending=False).head(12)
                                     .round(3).to_dict("records"))
    stats["top_directed_over_symmetric"] = (df.sort_values("gap_vs_sym", ascending=False).head(10)
                                            .round(3).to_dict("records"))
    stats["top_lift_pairs_department"] = (df[df.a < df.b].sort_values("lift_sym", ascending=False)
                                          .head(10)[["a", "b", "lift_sym"]].round(3).to_dict("records"))
    top_a = []
    iu = np.triu_indices(len(aisle_ids), 1)
    order = np.argsort(-np.nan_to_num(lift_a_out[iu], nan=-1))[:15]
    for k in order:
        i, j = iu[0][k], iu[1][k]
        top_a.append({"a": aisle_names[i], "b": aisle_names[j], "lift": float(lift_a_out[i, j]),
                      "support": int(co_a[i, j])})
    stats["top_lift_pairs_aisle"] = top_a
    json.dump(stats, open(art / "eda_stats.json", "w"), indent=1)

    print(f"eda: orders={n_orders:,} users={stats['n_users']:,} "
          f"basket mean={stats['basket_size']['mean']:.1f} median={stats['basket_size']['median']:.0f} "
          f"depts/order={stats['departments_per_order']['mean']:.2f} "
          f"single-dept share={stats['share_single_department_orders']:.3f}")
    print(f"eda: aisle pairs kept at support>={min_sup}: {stats['aisle_pairs_kept_share']:.1%}")
    print(f"eda: done in {time.time() - t0:.0f}s -> {art}")


def main() -> None:
    run(parse_args(__doc__))


if __name__ == "__main__":
    main()
