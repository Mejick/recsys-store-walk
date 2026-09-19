"""Ranking metrics over score matrices: hit@1, hit@3, MRR (+ boolean slices)."""
from __future__ import annotations

import numpy as np
import pandas as pd


def rank_of_target(scores: np.ndarray, target: np.ndarray) -> np.ndarray:
    """1-based rank of the target column within each row; ties count against the method."""
    t = scores[np.arange(len(target)), target]
    return (scores >= t[:, None]).sum(1)


def summarize(rank: np.ndarray) -> dict[str, float]:
    return {"hit@1": float((rank <= 1).mean()), "hit@3": float((rank <= 3).mean()),
            "mrr": float((1.0 / rank).mean()), "n": len(rank)}


def slices(ex: pd.DataFrame, top_pop: list[int], prefix_buckets: list[list[int]],
           new_user_max_orders: int = 4) -> dict[str, np.ndarray]:
    k = ex["k"].to_numpy()
    out: dict[str, np.ndarray] = {"all": np.ones(len(ex), dtype=bool)}
    for lo, hi in prefix_buckets:
        name = f"k={lo}" if lo == hi else (f"k={lo}-{hi}" if hi < 99 else f"k>={lo}")
        out[name] = (k >= lo) & (k <= hi)
    n = ex["u_n_orders"].to_numpy()
    out[f"new users (<={new_user_max_orders} prior orders)"] = n <= new_user_max_orders
    out[f"old users (>{new_user_max_orders} prior orders)"] = n > new_user_max_orders
    out["target not in global top-3"] = ~np.isin(ex["target"].to_numpy(), top_pop)
    return out


def evaluate(scores: np.ndarray, ex: pd.DataFrame, sl: dict[str, np.ndarray]) -> dict[str, dict]:
    rank = rank_of_target(scores, ex["target"].to_numpy())
    return {name: summarize(rank[m]) for name, m in sl.items()}
