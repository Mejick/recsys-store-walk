import numpy as np
import pandas as pd

from brodilka.baselines import mask_basket, score_heuristic
from brodilka.config import load_config
from brodilka.eda import basket_prefix_counts
from brodilka.features import split_orders, user_history
from brodilka.metrics import rank_of_target, summarize


def test_split_last_orders_go_to_test_then_val():
    orders = pd.DataFrame({"order_id": [10, 11, 12, 13, 20, 21, 22, 23],
                           "user_id": [1, 1, 1, 1, 2, 2, 2, 2],
                           "order_number": [1, 2, 3, 4, 3, 1, 4, 2]})
    s = split_orders(orders, load_config())
    assert s[13] == "test" and s[12] == "val" and s[10] == "train" and s[11] == "train"
    assert s[22] == "test" and s[20] == "val" and s[21] == "train"


def test_basket_prefix_counts_reset_per_order():
    dcat = np.array([0, 0, 1, 2, 2])
    starts, lengths = np.array([0, 3]), np.array([3, 2])
    c = basket_prefix_counts(dcat, starts, lengths, 3)
    assert c.tolist() == [[1, 0, 0], [2, 0, 0], [2, 1, 0], [0, 0, 1], [0, 0, 2]]


def test_user_history_is_strictly_prior():
    items = pd.DataFrame({
        "order_id": [1, 1, 2, 2, 3],
        "user_id": [7, 7, 7, 7, 7],
        "department_id": [3, 4, 3, 3, 4],
        "product_id": [1, 2, 1, 3, 2],
        "reordered": [0, 0, 1, 0, 1],
    })
    orders = pd.DataFrame({"order_id": [1, 2, 3], "user_id": [7, 7, 7], "order_number": [1, 2, 3],
                           "days_since_prior_order": [np.nan, 10.0, 20.0]})
    h = user_history(items, orders, {3: 0, 4: 1}).set_index("order_id")
    assert h.loc[1, "u_n_orders"] == 0 and np.isnan(h.loc[1, "u_reorder_rate"])
    assert h.loc[2, ["h_0", "h_1"]].tolist() == [1, 1]        # order 1 had both departments
    assert h.loc[3, ["h_0", "h_1"]].tolist() == [2, 1]        # order 2 had only dept 3
    assert h.loc[3, "u_reorder_rate"] == 0.25                 # 1 of 4 items before order 3
    assert h.loc[3, "u_avg_basket"] == 2.0
    assert h.loc[3, "u_days_mean"] == 5.0                     # (0 + 10) / 2


def test_metrics_and_masking():
    scores = np.array([[0.5, 0.3, 0.2], [0.1, 0.1, 0.8]])
    target = np.array([1, 2])
    assert rank_of_target(scores, target).tolist() == [2, 1]
    m = summarize(rank_of_target(scores, target))
    assert m["hit@1"] == 0.5 and m["hit@3"] == 1.0 and abs(m["mrr"] - 0.75) < 1e-9
    B = np.array([[1, 0, 0], [0, 0, 0]])
    masked = mask_basket(scores, B)
    assert np.isneginf(masked[0, 0]) and np.allclose(masked[1], [0.1, 0.1, 0.8])
    tied = np.array([[0.5, 0.5, 0.1]])
    assert rank_of_target(tied, np.array([1])).tolist() == [2]   # tie counts against the method


def test_heuristic_penalises_basket_departments():
    n = 19
    ex = pd.DataFrame({f"b_{j}": [0] * 2 for j in range(n)})
    ex["b_0"] = [2, 0]
    ex["b_1"] = [0, 1]
    for j in range(n):
        ex[f"h_{j}"] = 0
    ex["last_dept"] = [0, 1]
    ex["u_n_orders"] = 0
    tables = {"lift": np.ones((n, n)).tolist(), "pop_next": [1 / n] * n}
    s = score_heuristic(ex, tables)
    assert s[0, 0] == -1 and s[0, 5] == 0 and s[1, 1] == -1
