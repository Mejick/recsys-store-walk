import numpy as np
import pandas as pd

from brodilka.eda import cooccurrence, lift_from_cooc, next_new_department


def test_next_new_department_targets():
    # order 1: depts A A B A C ; order 2: B B ; order 3: C A
    items = pd.DataFrame({
        "order_id": [1, 1, 1, 1, 1, 2, 2, 3, 3],
        "department_id": [1, 1, 2, 1, 3, 2, 2, 3, 1],
    })
    target, is_new = next_new_department(items)
    # after each row, the next department not yet seen in that order
    assert target.tolist() == [2, 2, 3, 3, -1, -1, -1, 1, -1]
    assert is_new.tolist() == [True, False, True, False, True, True, False, True, True]


def test_lift_symmetric_and_binary_cooccurrence():
    order_idx = np.array([0, 0, 0, 1, 1, 2])
    cat = np.array([0, 0, 1, 0, 1, 1])  # duplicates inside an order must count once
    co = cooccurrence(order_idx, cat, n_orders=3, n_cat=2)
    assert co.tolist() == [[2, 2], [2, 3]]
    lift, p = lift_from_cooc(co, 3)
    assert np.allclose(p, [2 / 3, 1.0])
    assert np.allclose(lift, [[1, 1], [1, 1]])
