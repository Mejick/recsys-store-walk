# Usage: make data && make train && make site   (needs ~/.kaggle/kaggle.json)
PY := uv run python
CFG ?= configs/default.yaml
# src on PYTHONPATH as a fallback: the editable .pth breaks on non-ASCII Windows paths
export PYTHONPATH := src
export PYTHONUTF8 := 1

.PHONY: all setup data eda features train eval export site clean test lint

all: data features train eval export site

setup:               ## create .venv and install everything
	uv sync --all-extras

data:                ## download + unzip Instacart via Kaggle API (skips if present)
	$(PY) -m brodilka.data --config $(CFG)

eda:                 ## lift / transition matrices -> results/*.json
	$(PY) -m brodilka.eda --config $(CFG)

features: eda        ## prefix examples + leak-free user history features -> data/interim
	$(PY) -m brodilka.features --config $(CFG)

train:               ## baselines + CatBoost -> results/model.cbm, results/metrics.json
	$(PY) -m brodilka.train --config $(CFG)

eval:                ## metrics table with slices -> results/metrics.md
	$(PY) -m brodilka.evaluate --config $(CFG)

export:              ## tables for the browser -> site/data/*.json, icons -> site/img
	$(PY) -m brodilka.export --config $(CFG)

site: export         ## sanity-check that site/data numbers match results/
	$(PY) -m brodilka.check_site --config $(CFG)

test:
	uv run pytest -q

lint:
	uv run ruff check src tests

clean:
	rm -rf data/interim results/*.json results/*.cbm catboost_info
