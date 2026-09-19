"""Export everything the static demo needs into site/data + site/img.

  store.json                  departments (ru names, icons, groups, order share) and their aisles
                              (sorted by orders, ru names, icons, top products)
  lift_department.json        copy of results/lift_department.json (numbers shown in the UI)
  transitions_department.json copy of results/transitions_department.json
  profiles.json               shopper presets: KMeans clusters over user department shares
  meta.json                   dataset sizes for the footer / README
"""
from __future__ import annotations

import json
import shutil

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans

from brodilka.config import ROOT, Config, parse_args
from brodilka.icons import fetch_icons, slug_of
from brodilka.loaders import load_dims, load_items

PROFILE_ORDERS = 20  # presets are expressed as "orders out of 20 that contained the department"


def dump(obj, path) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))


def build_store(cfg: Config, items: pd.DataFrame) -> dict:
    dims = load_dims(cfg)
    i18n = json.load(open(ROOT / "site" / "data" / "i18n.json", encoding="utf-8"))
    icons = json.load(open(ROOT / "site" / "data" / "aisle_icons.json", encoding="utf-8"))
    lift_d = json.load(open(cfg.path("results") / "lift_department.json"))
    lift_a = json.load(open(cfg.path("results") / "lift_aisle.json"))
    n_orders = lift_d["n_orders"]
    dep_share = dict(zip(lift_d["departments"], np.array(lift_d["support"]) / n_orders))
    aisle_support = dict(zip(lift_a["aisles"], lift_a["support"]))

    # top products per aisle by number of orders containing them
    prod_orders = items.groupby("product_id", sort=False).size()
    prod = dims.products.set_index("product_id")
    prod["n_orders"] = prod_orders.reindex(prod.index).fillna(0).astype(int)
    top_n = int(cfg["data"]["top_products_per_aisle"])
    top_products = (prod.sort_values("n_orders", ascending=False).groupby("aisle_id").head(top_n)
                    .groupby("aisle_id")["product_name"].apply(list))

    group_of = {d: g[0] for g in i18n["groups"] for d in g[2]}
    departments = []
    for _, row in dims.departments.iterrows():
        name = row["department"]
        aisles = dims.aisles[dims.aisles["department_id"] == row["department_id"]].copy()
        aisles["n"] = aisles["aisle"].map(aisle_support)
        aisles = aisles.sort_values("n", ascending=False)
        departments.append({
            "id": int(row["department_id"]), "key": name, "ru": i18n["departments"][name],
            "group": group_of[name], "icon": slug_of(icons["departments"][name]) + ".webp",
            "share": round(float(dep_share[name]), 4),
            "norec": name in cfg["export"].get("no_recommend", []),
            "aisles": [{
                "id": int(a["aisle_id"]), "key": a["aisle"], "ru": i18n["aisles"][a["aisle"]],
                "short": i18n.get("aisles_short", {}).get(a["aisle"], i18n["aisles"][a["aisle"]]),
                "icon": slug_of(icons["aisles"][a["aisle"]]) + ".webp", "orders": int(a["n"]),
                "products": top_products.get(a["aisle_id"], []),
            } for _, a in aisles.iterrows()],
        })
    return {"groups": [{"key": g[0], "ru": g[1]} for g in i18n["groups"]],
            "top_aisles_shown": int(cfg["data"]["top_aisles_per_department"]),
            "departments": departments}


def build_profiles(cfg: Config, items: pd.DataFrame, dep_names: list[str], ru: dict[str, str]) -> dict:
    """KMeans over per-user shares of orders containing each department (all users)."""
    od = items[["user_id", "order_id", "department_id"]].drop_duplicates()
    user_orders = od.groupby("user_id")["order_id"].nunique()
    dep_ids = sorted(items["department_id"].unique())
    pres = pd.crosstab(od["user_id"], od["department_id"]).reindex(columns=dep_ids, fill_value=0)
    share = pres.div(user_orders.reindex(pres.index), axis=0)
    share = share[user_orders.reindex(share.index) >= 5]           # stable shares only
    km = KMeans(n_clusters=int(cfg["export"]["n_profiles"]), n_init=10, random_state=cfg.seed)
    labels = km.fit_predict(share.to_numpy())
    global_mean = share.mean().to_numpy()
    profiles = []
    for c in range(km.n_clusters):
        centre = km.cluster_centers_[c]
        size = float((labels == c).mean())
        # distinctive departments: largest positive deviation from the global mean
        dev = centre - global_mean
        top = [dep_names[j] for j in np.argsort(-dev)[:2] if dev[j] > 0.03]
        low = [dep_names[j] for j in np.argsort(dev)[:1] if dev[j] < -0.1]
        title = " + ".join(ru[d] for d in top) if top else "Средний покупатель"
        note = (f"{size:.0%} покупателей. Чаще среднего: " + ", ".join(ru[d].lower() for d in top)
                + (f". Реже среднего: {ru[low[0]].lower()}" if low else "") + ".")
        profiles.append({
            "title": title, "note": note, "share": round(size, 3), "orders": PROFILE_ORDERS,
            "hist": {dep_names[j]: int(round(centre[j] * PROFILE_ORDERS)) for j in range(len(dep_names))},
            "centre": {dep_names[j]: round(float(centre[j]), 4) for j in range(len(dep_names))},
        })
    profiles.sort(key=lambda p: -p["share"])
    profiles.insert(0, {"title": "Новый покупатель", "note": "Истории заказов нет, работают только корзина и текущий отдел.",
                        "share": None, "orders": 0, "hist": {d: 0 for d in dep_names}, "centre": None})
    return {"n_users_clustered": len(share), "min_orders": 5,
            "global_mean": {dep_names[j]: round(float(global_mean[j]), 4) for j in range(len(dep_names))},
            "profiles": profiles}


def run(cfg: Config) -> None:
    site = cfg.path("site_data")
    art = cfg.path("results")
    fetch_icons(cfg)
    items = load_items(cfg)
    store = build_store(cfg, items)
    dump(store, site / "store.json")
    for name in ("lift_department.json", "transitions_department.json"):
        shutil.copyfile(art / name, site / name)
    dep_names = [d["key"] for d in store["departments"]]
    ru = {d["key"]: d["ru"] for d in store["departments"]}
    profiles = build_profiles(cfg, items, dep_names, ru)
    dump(profiles, site / "profiles.json")
    stats = json.load(open(art / "eda_stats.json"))
    dump({"n_orders": stats["n_orders"], "n_users": stats["n_users"], "n_items": stats["n_items"],
          "source": "Instacart Market Basket Analysis (Kaggle), prior + train orders",
          "departments": len(dep_names), "aisles": sum(len(d["aisles"]) for d in store["departments"])},
         site / "meta.json")
    for p in profiles["profiles"]:
        print(f"export: profile {p['title']!r}: {p['note']}")
    print(f"export: {len(dep_names)} departments, {sum(len(d['aisles']) for d in store['departments'])} aisles -> {site}")


def main() -> None:
    run(parse_args(__doc__))


if __name__ == "__main__":
    main()
