"""Download the Instacart competition files via the Kaggle API and unpack them to data/raw.

Idempotent: skips the download when every expected CSV is already present.
Requires a Kaggle token (~/.kaggle/access_token, KAGGLE_API_TOKEN, or legacy kaggle.json).
Source is a dataset mirror: the original competition page no longer exists on Kaggle.
"""
from __future__ import annotations

import os
import sys
import zipfile
from pathlib import Path

from brodilka.config import Config, parse_args


def have_all(raw: Path, files: list[str]) -> bool:
    return all((raw / f).exists() and (raw / f).stat().st_size > 0 for f in files)


def token_present() -> bool:
    """Either a new-style API token (kaggle>=1.8) or legacy username/key credentials."""
    if os.environ.get("KAGGLE_API_TOKEN"):
        return True
    if os.environ.get("KAGGLE_USERNAME") and os.environ.get("KAGGLE_KEY"):
        return True
    cfg_dir = Path(os.environ.get("KAGGLE_CONFIG_DIR", Path.home() / ".kaggle"))
    return (cfg_dir / "access_token").exists() or (cfg_dir / "kaggle.json").exists()


def unpack_nested(zip_path: Path, dest: Path) -> None:
    """Flatten the archive (and any zip-per-CSV inside it) into dest."""
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(dest)
    zip_path.unlink()
    for inner in [p for p in dest.glob("*.zip") if p != zip_path]:
        with zipfile.ZipFile(inner) as z:
            z.extractall(dest)
        inner.unlink()


def download(cfg: Config) -> None:
    raw = cfg.path("raw")
    files: list[str] = cfg["kaggle"]["files"]
    if have_all(raw, files):
        print(f"data: all {len(files)} files present in {raw}, skipping download")
        return
    if not token_present():
        sys.exit(
            "data: Kaggle token not found. Save an API token to ~/.kaggle/access_token "
            "(https://www.kaggle.com/settings -> Generate New Token), or set KAGGLE_API_TOKEN, "
            "or put legacy kaggle.json into ~/.kaggle/."
        )
    # imported lazily: the kaggle package authenticates on import and raises without a token
    from kaggle.api.kaggle_api_extended import KaggleApi

    api = KaggleApi()
    api.authenticate()
    ds = cfg["kaggle"]["dataset"]
    print(f"data: downloading {ds} -> {raw}")
    api.dataset_download_files(ds, path=str(raw), quiet=False, unzip=False)
    for archive in list(raw.glob("*.zip")):
        unpack_nested(archive, raw)
    missing = [f for f in files if not (raw / f).exists()]
    if missing:
        sys.exit(f"data: download finished but files are missing: {missing}")
    sizes = {f: round((raw / f).stat().st_size / 2**20, 1) for f in files}
    print("data: OK, sizes in MB:", sizes)


def main() -> None:
    download(parse_args(__doc__))


if __name__ == "__main__":
    main()
