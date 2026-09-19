"""Fit CatBoost on the prefix examples and dump scores of every method on val/test.

Outputs
  results/model.cbm                 CatBoost model (gitignored; JSON export lives in export.py)
  results/feature_importance.json   PredictionValuesChange importances
  results/train_log.json            chosen loss, best iteration, timings, YetiRank comparison
  data/interim/scores_{val,test}.npz  masked score matrices of the CatBoost models + targets
                                      (baseline scores are cheap and recomputed in evaluate.py)
"""
from __future__ import annotations

import json
import time

import numpy as np
import pandas as pd
from catboost import CatBoostClassifier, CatBoostRanker, Pool

from brodilka.baselines import BASELINES, N_DEP, basket_counts, hist_counts, mask_basket
from brodilka.config import Config, parse_args
from brodilka.metrics import rank_of_target, summarize

CAT_FEATURES = ["first_dept", "last_dept", "last_aisle"]
# one-hot instead of CTR statistics for the 3 low-cardinality categoricals + coarser borders
# + Bernoulli subsampling: 4-5x faster per iteration at the same validation loss (measured)
SPEED = {"one_hot_max_size": 255, "max_ctr_complexity": 1, "border_count": 32,
         "bootstrap_type": "Bernoulli", "subsample": 0.5}
BASE_FEATURES = ["k", "n_dep_basket", "order_dow", "order_hour_of_day", "days_since_prior_order",
                 "order_number", "u_n_orders", "u_reorder_rate", "u_avg_basket", "u_days_mean"]


def build_matrix(ex: pd.DataFrame, tables: dict) -> pd.DataFrame:
    """Model features: raw columns + user department shares + Markov and heuristic score vectors."""
    X = ex[CAT_FEATURES + BASE_FEATURES].copy()
    for j in range(N_DEP):
        X[f"b_{j}"] = ex[f"b_{j}"]
    H = hist_counts(ex)
    n = ex["u_n_orders"].to_numpy(dtype=np.float32)[:, None]
    share = np.divide(H, n, out=np.full_like(H, np.nan), where=n > 0)
    mk = BASELINES["markov"](ex, tables)
    he = BASELINES["heuristic"](ex, tables)
    for j in range(N_DEP):
        X[f"s_{j}"] = share[:, j]
        X[f"m_{j}"] = mk[:, j]
        X[f"e_{j}"] = he[:, j]
    return X


def save_model(model, path) -> None:
    """CatBoost decodes the path in the locale encoding and chokes on non-ASCII directories
    (Cyrillic user name on Windows); write to an ASCII temp file and move it into place."""
    import os
    import shutil
    import tempfile

    fd, tmp = tempfile.mkstemp(suffix=".cbm", dir=None if os.path.abspath(tempfile.gettempdir()).isascii() else "C:/Temp")
    os.close(fd)
    model.save_model(tmp)
    shutil.move(tmp, str(path))


def fit_multiclass(cfg: Config, Xtr, ytr, Xva, yva) -> CatBoostClassifier:
    m = cfg["model"]
    model = CatBoostClassifier(
        loss_function="MultiClass", iterations=int(m["iterations"]), learning_rate=float(m["learning_rate"]),
        depth=int(m["depth"]), random_seed=cfg.seed, thread_count=-1, verbose=100,
        early_stopping_rounds=int(m["early_stopping_rounds"]), cat_features=CAT_FEATURES,
        eval_metric="MultiClass", **SPEED,
    )
    model.fit(Xtr, ytr, eval_set=(Xva, yva))
    return model


def expand_for_ranking(X: pd.DataFrame, ex: pd.DataFrame) -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    """One row per (example, candidate department not in basket) for YetiRank."""
    B = basket_counts(ex)
    cand = B == 0
    rows, cols = np.nonzero(cand)
    Xc = X.iloc[rows].reset_index(drop=True)
    Xc["cand"] = cols.astype("int8")
    # candidate-specific values of the score vectors
    Xc["cand_share"] = X[[f"s_{j}" for j in range(N_DEP)]].to_numpy()[rows, cols]
    Xc["cand_markov"] = X[[f"m_{j}" for j in range(N_DEP)]].to_numpy()[rows, cols]
    Xc["cand_heur"] = X[[f"e_{j}" for j in range(N_DEP)]].to_numpy()[rows, cols]
    y = (cols == ex["target"].to_numpy()[rows]).astype("int8")
    return Xc, y, rows


def fit_yetirank(cfg: Config, X: pd.DataFrame, ex: pd.DataFrame, Xva: pd.DataFrame, exva: pd.DataFrame,
                 n_train: int) -> tuple[CatBoostRanker, np.ndarray]:
    rng = np.random.default_rng(cfg.seed)
    idx = np.sort(rng.choice(len(X), size=min(n_train, len(X)), replace=False))
    Xc, y, g = expand_for_ranking(X.iloc[idx].reset_index(drop=True), ex.iloc[idx].reset_index(drop=True))
    Xvc, yv, gv = expand_for_ranking(Xva, exva)
    cat = CAT_FEATURES + ["cand"]
    m = cfg["model"]
    model = CatBoostRanker(loss_function="YetiRank", iterations=int(m["iterations"]),
                           learning_rate=float(m["learning_rate"]), depth=int(m["depth"]),
                           random_seed=cfg.seed, thread_count=-1, verbose=100,
                           early_stopping_rounds=int(m["early_stopping_rounds"]), cat_features=cat, **SPEED)
    model.fit(Pool(Xc, y, group_id=g, cat_features=cat), eval_set=Pool(Xvc, yv, group_id=gv, cat_features=cat))
    return model, gv


def scores_yetirank(model: CatBoostRanker, X: pd.DataFrame, ex: pd.DataFrame) -> np.ndarray:
    Xc, _, rows = expand_for_ranking(X, ex)
    cols = Xc["cand"].to_numpy()
    pred = model.predict(Pool(Xc, cat_features=CAT_FEATURES + ["cand"]))
    S = np.full((len(ex), N_DEP), -np.inf, dtype=np.float32)
    S[rows, cols] = pred
    return S


def run(cfg: Config) -> None:
    t0 = time.time()
    art = cfg.path("results")
    tables = json.load(open(art / "tables_train.json"))
    ex = pd.read_parquet(cfg.path("interim") / "examples.parquet")
    parts = {s: ex[ex["split"] == s].reset_index(drop=True) for s in ("train", "val", "test")}
    log: dict = {"n_examples": {s: len(p) for s, p in parts.items()}}

    # ---- baselines: score everything, masked ---------------------------------------------
    scores = {s: {} for s in ("val", "test")}
    for s in ("val", "test"):
        B = basket_counts(parts[s])
        for name, fn in BASELINES.items():
            scores[s][name] = mask_basket(fn(parts[s], tables), B)
    print("train: baselines scored in %.0fs" % (time.time() - t0))

    # ---- feature matrices --------------------------------------------------------------
    X = {s: build_matrix(parts[s], tables) for s in parts}
    y = {s: parts[s]["target"].to_numpy() for s in parts}
    cap = cfg["model"].get("max_train_examples")
    if cap and len(X["train"]) > cap:
        rng = np.random.default_rng(cfg.seed)
        idx = np.sort(rng.choice(len(X["train"]), size=int(cap), replace=False))
        X["train"], y["train"] = X["train"].iloc[idx].reset_index(drop=True), y["train"][idx]
    log["n_train_used"] = len(X["train"])
    log["n_features"] = int(X["train"].shape[1])
    print(f"train: fitting MultiClass on {len(X['train']):,} x {X['train'].shape[1]} features")

    # ---- CatBoost MultiClass -----------------------------------------------------------
    t1 = time.time()
    model = fit_multiclass(cfg, X["train"], y["train"], X["val"], y["val"])
    log["multiclass"] = {"best_iteration": int(model.get_best_iteration()), "fit_seconds": round(time.time() - t1)}
    classes = np.asarray(model.classes_, dtype=int)
    for s in ("val", "test"):
        P = np.zeros((len(parts[s]), N_DEP), dtype=np.float32)
        P[:, classes] = model.predict_proba(X[s])
        scores[s]["catboost_multiclass"] = mask_basket(P, basket_counts(parts[s]))
        np.savez_compressed(cfg.path("interim") / f"scores_{s}.npz", target=y[s], **scores[s])
    save_model(model, art / "model.cbm")
    imp = sorted(zip(X["train"].columns, model.get_feature_importance()), key=lambda t: -t[1])
    json.dump([{"feature": f, "importance": round(float(v), 4)} for f, v in imp],
              open(art / "feature_importance.json", "w"), indent=1)

    # ---- optional YetiRank comparison on a subsample -----------------------------------
    if cfg["model"].get("compare_yetirank"):
        t1 = time.time()
        n = int(cfg["model"].get("yetirank_train_examples", 200_000))
        print(f"train: fitting YetiRank on {n:,} examples expanded to candidates")
        ranker, _ = fit_yetirank(cfg, X["train"], parts["train"].iloc[:len(X["train"])], X["val"], parts["val"], n)
        for s in ("val", "test"):
            scores[s]["catboost_yetirank"] = scores_yetirank(ranker, X[s], parts[s])
        log["yetirank"] = {"best_iteration": int(ranker.get_best_iteration()), "n_train_examples": n,
                           "fit_seconds": round(time.time() - t1)}

    # ---- quick val summary + dump ------------------------------------------------------
    for s in ("val", "test"):
        np.savez_compressed(cfg.path("interim") / f"scores_{s}.npz", target=y[s], **scores[s])
    log["val_summary"] = {name: summarize(rank_of_target(S, y["val"])) for name, S in scores["val"].items()}
    log["total_seconds"] = round(time.time() - t0)
    json.dump(log, open(art / "train_log.json", "w"), indent=1)
    for name, m in log["val_summary"].items():
        print(f"train: val {name:22s} hit@1={m['hit@1']:.4f} hit@3={m['hit@3']:.4f} mrr={m['mrr']:.4f}")
    print(f"train: done in {log['total_seconds']}s")


def main() -> None:
    run(parse_args(__doc__))


if __name__ == "__main__":
    main()
