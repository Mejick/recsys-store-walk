"""Metrics table (baselines vs CatBoost) with slices, feature importance and worked examples.

Reads data/interim/scores_{val,test}.npz + examples.parquet, writes
  results/metrics.json   nested {split: {method: {slice: {hit@1, hit@3, mrr, n}}}}
  results/metrics.md     human-readable tables + 5 worked test examples
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from brodilka.baselines import BASELINES, N_DEP, basket_counts, mask_basket
from brodilka.config import Config, parse_args
from brodilka.metrics import evaluate, rank_of_target, slices

METHOD_LABEL = {
    "popularity": "1. Global popularity",
    "personal": "2. Personal popularity",
    "markov": "3. Markov chain (order 1)",
    "heuristic": "4. Prototype heuristic",
    "heuristic_v2": "4b. Heuristic with directed lift",
    "catboost_multiclass": "CatBoost MultiClass",
    "catboost_yetirank": "CatBoost YetiRank (subsample)",
}


PREFIX = {"b": "basket", "s": "share", "m": "markov", "e": "heur"}


def feature_label(name: str, deps: list[str]) -> str:
    """b_14 -> basket[dairy eggs] etc.; other names unchanged."""
    head, _, idx = name.partition("_")
    if head in PREFIX and idx.isdigit():
        return f"{PREFIX[head]}[{deps[int(idx)]}]"
    return name


def md_table(rows: list[list], header: list[str]) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "|".join(["---"] * len(header)) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def worked_examples(ex: pd.DataFrame, S: dict[str, np.ndarray], deps: list[str], n: int = 5,
                    seed: int = 0) -> str:
    """A few test examples where the model and the popularity baseline disagree."""
    rng = np.random.default_rng(seed)
    y = ex["target"].to_numpy()
    r_model = rank_of_target(S["catboost_multiclass"], y)
    r_pop = rank_of_target(S["popularity"], y)
    pool = np.flatnonzero((r_model == 1) & (r_pop > 3))
    pool2 = np.flatnonzero((r_model > 3) & (r_pop == 1))
    picks = list(rng.choice(pool, min(n - 1, len(pool)), replace=False)) + list(rng.choice(pool2, 1))
    parts = []
    for i in picks:
        row = ex.iloc[i]
        basket = ", ".join(f"{deps[j]}×{int(row[f'b_{j}'])}" for j in range(N_DEP) if row[f"b_{j}"] > 0)
        hist_top = sorted(((int(row[f"h_{j}"]), deps[j]) for j in range(N_DEP)), reverse=True)[:3]
        hist = ", ".join(f"{d} ({c}/{int(row['u_n_orders'])})" for c, d in hist_top if c > 0) or "нет истории"
        lines = [f"**Пример {len(parts) + 1}.** Корзина после {int(row['k'])} позиций: {basket}. "
                 f"Последний отдел: {deps[int(row['last_dept'])]}. "
                 f"История ({int(row['u_n_orders'])} заказов), чаще всего: {hist}. "
                 f"Реально следующий: **{deps[int(y[i])]}**."]
        for m in ("popularity", "personal", "markov", "heuristic", "heuristic_v2", "catboost_multiclass"):
            top = np.argsort(-S[m][i])[:3]
            lines.append(f"- {METHOD_LABEL[m]}: " + ", ".join(deps[j] for j in top))
        parts.append("\n".join(lines))
    return "\n\n".join(parts)


def run(cfg: Config) -> None:
    art = cfg.path("results")
    tables = json.load(open(art / "tables_train.json"))
    deps = tables["departments"]
    pop = np.asarray(tables["pop_next"])
    top_pop = np.argsort(-pop)[:3].tolist()
    ex_all = pd.read_parquet(cfg.path("interim") / "examples.parquet")
    result: dict = {"top_pop_departments": [deps[j] for j in top_pop]}
    md = ["# Метрики: следующий отдел, которого ещё нет в корзине", "",
          f"Топ-3 популярных таргета (исключаются в срезе «не из топ-3»): {', '.join(deps[j] for j in top_pop)}.",
          "Все методы ранжируют только отделы, которых ещё нет в корзине. Ничьи в счёте засчитываются против метода.", ""]
    S_test = None
    for split in ("val", "test"):
        ex = ex_all[ex_all["split"] == split].reset_index(drop=True)
        z = np.load(cfg.path("interim") / f"scores_{split}.npz")
        assert (z["target"] == ex["target"].to_numpy()).all()
        B = basket_counts(ex)
        S = {name: mask_basket(fn(ex, tables), B) for name, fn in BASELINES.items()}  # cheap, recomputed
        S.update({k: z[k] for k in z.files if k.startswith("catboost")})
        sl = slices(ex, top_pop, cfg["task"]["prefix_buckets"])
        result[split] = {m: evaluate(S[m], ex, sl) for m in S}
        md.append(f"## {split} ({len(ex):,} примеров, {ex['order_id'].nunique():,} заказов)\n")
        rows = [[METHOD_LABEL.get(m, m)] + [f"{result[split][m]['all'][k]:.4f}" for k in ("hit@1", "hit@3", "mrr")]
                for m in S]
        md.append(md_table(rows, ["Метод", "hit@1", "hit@3", "MRR"]) + "\n")
        md.append(f"### Срезы, hit@3 ({split})\n")
        names = [s for s in sl if s != "all"]
        rows = [[METHOD_LABEL.get(m, m)] + [f"{result[split][m][s]['hit@3']:.4f}" for s in names] for m in S]
        md.append(md_table(rows, ["Метод"] + [f"{s} (n={sl[s].sum():,})" for s in names]) + "\n")
        if split == "test":
            S_test = (ex, S)

    imp = json.load(open(art / "feature_importance.json"))[:20]
    md.append("## Важность признаков (CatBoost, PredictionValuesChange, топ-20)\n")
    md.append(md_table([[feature_label(i["feature"], deps), i["importance"]] for i in imp],
                       ["Признак", "Важность"]) + "\n")
    md.append("Обозначения: `basket[d]` число позиций отдела d в корзине, `share[d]` доля прошлых заказов "
              "с отделом d, `markov[d]` P(следующий = d | последний отдел), `heur[d]` скор эвристики прототипа.\n")
    md.append("## Разобранные примеры (test)\n")
    md.append(worked_examples(*S_test, deps, seed=cfg.seed))
    json.dump(result, open(art / "metrics.json", "w"), indent=1)
    (art / "metrics.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    best_base = max((m for m in result["test"] if not m.startswith("catboost")),
                    key=lambda m: result["test"][m]["all"]["hit@3"])
    print(f"eval: test hit@3 best baseline {best_base}={result['test'][best_base]['all']['hit@3']:.4f}, "
          f"catboost_multiclass={result['test']['catboost_multiclass']['all']['hit@3']:.4f} -> {art / 'metrics.md'}")


def main() -> None:
    run(parse_args(__doc__))


if __name__ == "__main__":
    main()
