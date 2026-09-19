"""Icons for the site: Fluent Emoji 3D PNGs -> 120 px webp in site/img, plus prototype fallbacks.

  fetch_icons(cfg)      downloads every emoji named in site/data/aisle_icons.json (cached by slug)
  extract_prototype()   decodes the base64 webp images embedded in prototype/brodilka.html

Emoji folder names follow the fluentui-emoji repo: assets/<Name>/3D/<slug>_3d.png where
slug = name.lower() with spaces -> underscores (hyphens kept).
"""
from __future__ import annotations

import base64
import io
import json
import re
import time
from pathlib import Path

import requests
from PIL import Image

from brodilka.config import ROOT, Config

RAW = "https://raw.githubusercontent.com/microsoft/fluentui-emoji/main/assets/{name}/3D/{slug}_3d.png"


def slug_of(name: str) -> str:
    return re.sub(r"[^a-z0-9_-]", "", name.lower().replace(" ", "_"))


def fetch_icons(cfg: Config) -> dict[str, str]:
    """Return {emoji name: relative webp path}; missing ones are reported and left out."""
    mapping = json.load(open(ROOT / "site" / "data" / "aisle_icons.json", encoding="utf-8"))
    names = sorted(set(mapping["departments"].values()) | set(mapping["aisles"].values()))
    out_dir = cfg.path("site_img")
    size = int(cfg["export"]["icon_size"])
    done: dict[str, str] = {}
    missing: list[str] = []
    session = requests.Session()
    for name in names:
        slug = slug_of(name)
        target = out_dir / f"{slug}.webp"
        if target.exists():
            done[name] = target.name
            continue
        url = RAW.format(name=requests.utils.quote(name), slug=slug)
        try:
            r = session.get(url, timeout=30)
            if r.status_code != 200:
                missing.append(f"{name} ({r.status_code})")
                continue
            im = Image.open(io.BytesIO(r.content)).convert("RGBA")
            im.thumbnail((size, size), Image.LANCZOS)
            im.save(target, "WEBP", quality=88, method=6)
            done[name] = target.name
            time.sleep(0.1)
        except Exception as e:  # noqa: BLE001 - network hiccups are reported, not fatal
            missing.append(f"{name} ({e})")
    print(f"icons: {len(done)} ready in {out_dir}" + (f", missing: {missing}" if missing else ""))
    return done


def extract_prototype(dest: Path) -> int:
    """Decode the IMG object of the prototype into dest/<key>.webp (56 px originals)."""
    html = (ROOT / "prototype" / "brodilka.html").read_text(encoding="utf-8")
    m = re.search(r"var IMG=(\{.*?\});\n", html, re.DOTALL)
    if not m:
        return 0
    img = json.loads(m.group(1))
    dest.mkdir(parents=True, exist_ok=True)
    for key, data_url in img.items():
        b64 = data_url.split(",", 1)[1]
        (dest / f"{key}.webp").write_bytes(base64.b64decode(b64))
    return len(img)
