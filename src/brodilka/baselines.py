"""Score matrices (n_examples x n_departments) for the four baselines + shared masking.

All scorers take the examples frame and the train-only tables; departments already in the
basket are masked to -inf by `mask_basket` before ranking (the target can never be one of them).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

N_DEP = 19


def basket_counts(ex: pd.DataFrame) -> np.ndarray:
    return ex[[f"b_{j}" for j in range(N_DEP)]].to_numpy(dtype=np.float32)


def hist_counts(ex: pd.DataFrame) -> np.ndarray:
    return ex[[f"h_{j}" for j in range(N_DEP)]].to_numpy(dtype=np.float32)


def mask_basket(scores: np.ndarray, B: np.ndarray) -> np.ndarray:
    out = scores.astype(np.float32, copy=True)
    out[B > 0] = -np.inf
    return out


def score_popularity(ex: pd.DataFrame, tables: dict) -> np.ndarray:
    pop = np.asarray(tables["pop_next"], dtype=np.float32)
    return np.broadcast_to(pop, (len(ex), N_DEP)).copy()


def score_personal(ex: pd.DataFrame, tables: dict) -> np.ndarray:
    """User's share of prior orders containing each department; popularity breaks ties / cold start."""
    H = hist_counts(ex)
    n = ex["u_n_orders"].to_numpy(dtype=np.float32)[:, None]
    share = np.divide(H, n, out=np.zeros_like(H), where=n > 0)
    return share + 1e-3 * score_popularity(ex, tables)


def score_markov(ex: pd.DataFrame, tables: dict) -> np.ndarray:
    """First-order chain: P(next new department | department of the last added item)."""
    T = np.asarray(tables["transitions"], dtype=np.float32)
    return T[ex["last_dept"].to_numpy()]


def score_heuristic(ex: pd.DataFrame, tables: dict) -> np.ndarray:
    """The prototype's ranked(): basket-share-weighted ln lift + 0.5 ln lift(current room)
    + 0.6 normalised log history - 1 for departments already in the basket."""
    lift = np.asarray(tables["lift"], dtype=np.float32)
    loglift = np.log(np.maximum(lift, 0.05))
    np.fill_diagonal(loglift, 0.0)                     # prototype skips c == L
    B = basket_counts(ex)
    tot = B.sum(1, keepdims=True)
    sc = (B / tot) @ loglift                           # sum_c share_c * ln lift[c][L]
    sr = 0.5 * loglift[ex["last_dept"].to_numpy()]     # lift to the current room
    H = hist_counts(ex)
    hmax = np.maximum(1.0, H.max(1, keepdims=True))
    sh = 0.6 * np.log1p(H) / np.log1p(hmax)
    return sc + sr + sh - (B > 0)


def score_heuristic_v2(ex: pd.DataFrame, tables: dict) -> np.ndarray:
    """Same as the prototype heuristic, but the "current room" term uses the DIRECTED lift
    P(next=L | last=room) / P(next=L) from add_to_cart_order instead of the symmetric lift."""
    lift = np.asarray(tables["lift"], dtype=np.float32)
    loglift = np.log(np.maximum(lift, 0.05))
    np.fill_diagonal(loglift, 0.0)
    T = np.asarray(tables["transitions"], dtype=np.float32)
    pop = np.asarray(tables["pop_next"], dtype=np.float32)
    dlift = np.log(np.maximum(T / np.maximum(pop, 1e-6), 0.05))
    B = basket_counts(ex)
    tot = B.sum(1, keepdims=True)
    sc = (B / tot) @ loglift
    sr = 0.5 * dlift[ex["last_dept"].to_numpy()]
    H = hist_counts(ex)
    hmax = np.maximum(1.0, H.max(1, keepdims=True))
    sh = 0.6 * np.log1p(H) / np.log1p(hmax)
    return sc + sr + sh - (B > 0)


# weights of the demo formula, picked on val (see results/metrics.md)
DEMO_W_BASKET, DEMO_W_ROOM, DEMO_W_HIST = 2.0, 1.0, 4.0


def score_heuristic_v3(ex: pd.DataFrame, tables: dict) -> np.ndarray:
    """The formula the demo runs in the browser. Naive-Bayes style on hazard tables:
    ln P(L | L absent) + 2 * sum_c share_c * ln basket_lift[c][L] + 1.0 * ln markov_lift[last][L]
    + 4 * (share of the user's past orders containing L); basket departments are masked later."""
    pop_h = np.asarray(tables["pop_hazard"], dtype=np.float32)
    blift = np.log(np.maximum(np.asarray(tables["basket_lift"], dtype=np.float32), 0.05))
    np.fill_diagonal(blift, 0.0)
    mlift = np.log(np.maximum(np.asarray(tables["markov_lift"], dtype=np.float32), 0.05))
    B = basket_counts(ex)
    tot = B.sum(1, keepdims=True)
    H = hist_counts(ex)
    n = ex["u_n_orders"].to_numpy(dtype=np.float32)[:, None]
    share = np.divide(H, n, out=np.zeros_like(H), where=n > 0)
    return (np.log(np.maximum(pop_h, 1e-6)) + DEMO_W_BASKET * ((B / tot) @ blift)
            + DEMO_W_ROOM * mlift[ex["last_dept"].to_numpy()] + DEMO_W_HIST * share)


BASELINES = {
    "popularity": score_popularity,
    "personal": score_personal,
    "markov": score_markov,
    "heuristic": score_heuristic,
    "heuristic_v2": score_heuristic_v2,
    "heuristic_v3": score_heuristic_v3,
}
