"""Consistency checks between site/data, site/img and results/ (acceptance criterion:
every lift number shown in the UI equals the one in results/)."""
from __future__ import annotations

import json
import sys

from brodilka.config import ROOT, Config, parse_args


def run(cfg: Config) -> None:
    site, art = cfg.path("site_data"), cfg.path("results")
    problems: list[str] = []
    for name in ("lift_department.json", "transitions_department.json"):
        a = json.load(open(art / name))
        s = json.load(open(site / name))
        if a != s:
            problems.append(f"{name} differs between results/ and site/data/")
    store = json.load(open(site / "store.json", encoding="utf-8"))
    i18n = json.load(open(site / "i18n.json", encoding="utf-8"))
    img = {p.name for p in cfg.path("site_img").glob("*.webp")}
    keys = [d["key"] for d in store["departments"]]
    if keys != json.load(open(art / "lift_department.json"))["departments"]:
        problems.append("department order in store.json differs from lift_department.json")
    grouped = {d for g in i18n["groups"] for d in g[2]}
    for d in store["departments"]:
        if d["icon"] not in img:
            problems.append(f"missing icon {d['icon']} for department {d['key']}")
        if d["key"] not in grouped:
            problems.append(f"department {d['key']} is not in any group")
        for a in d["aisles"]:
            if a["icon"] not in img:
                problems.append(f"missing icon {a['icon']} for aisle {a['key']}")
            if not a["ru"] or not a["products"]:
                problems.append(f"aisle {a['key']} lacks ru name or products")
    profiles = json.load(open(site / "profiles.json", encoding="utf-8"))["profiles"]
    if len(profiles) < 4:
        problems.append("fewer than 4 shopper profiles")
    for p in profiles:
        if set(p["hist"]) != set(keys):
            problems.append(f"profile {p['title']} hist keys mismatch")
    for f in ("index.html", "app.js", "styles.css"):
        if not (ROOT / "site" / f).exists():
            problems.append(f"site/{f} is missing")
    if problems:
        print("check_site: FAILED\n  " + "\n  ".join(problems))
        sys.exit(1)
    print(f"check_site: OK ({len(keys)} departments, {len(img)} icons, {len(profiles)} profiles)")


def main() -> None:
    run(parse_args(__doc__))


if __name__ == "__main__":
    main()
