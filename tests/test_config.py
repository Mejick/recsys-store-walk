from brodilka.config import load_config


def test_default_config_loads():
    cfg = load_config()
    assert cfg.seed == 42
    assert "missing" in cfg["data"]["exclude_departments"]
