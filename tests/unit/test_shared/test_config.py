import json
from pathlib import Path

import pytest

from article_generator.shared.config import (
    ConfigKeyError,
    ConfigManager,
    ConfigVersionError,
    ModelPricing,
    ServiceLimits,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VALID_SETUP = {
    "setup": {
        "version": "1.00",
        "article": {"target_pages": 15, "language": "english"},
        "agents": {"model": "claude-sonnet-4-5", "temperature": 0.7},
    }
}

VALID_RATE_LIMITS = {
    "rate_limits": {
        "version": "1.01",
        "providers": {
            "claude": {
                "free": {
                    "requests_per_minute": 5,
                    "tokens_per_minute": 20000,
                    "requests_per_hour": 50,
                    "concurrent_max": 2,
                    "retry_after_seconds": 60,
                    "max_retries": 3,
                    "max_queue_depth": 10,
                }
            }
        },
        "services": {
            "serper": {
                "requests_per_minute": 10,
                "tokens_per_minute": 0,
                "requests_per_hour": 100,
                "concurrent_max": 2,
                "retry_after_seconds": 10,
                "max_retries": 2,
                "max_queue_depth": 20,
            }
        },
    }
}

VALID_PRICING = {
    "model_pricing": {
        "version": "1.00",
        "currency": "USD",
        "unit": "per_million_tokens",
        "models": {
            "claude-sonnet-4-5": {
                "display_name": "Claude Sonnet 4.5",
                "provider": "Anthropic",
                "input_price_per_mtok": 3.00,
                "output_price_per_mtok": 15.00,
            }
        },
    }
}


@pytest.fixture()
def config_dir(tmp_path: Path) -> Path:
    (tmp_path / "setup.json").write_text(json.dumps(VALID_SETUP), encoding="utf-8")
    (tmp_path / "rate_limits.json").write_text(json.dumps(VALID_RATE_LIMITS), encoding="utf-8")
    (tmp_path / "model_pricing.json").write_text(json.dumps(VALID_PRICING), encoding="utf-8")
    return tmp_path


# ---------------------------------------------------------------------------
# load_setup
# ---------------------------------------------------------------------------

def test_load_setup_returns_setup_section(config_dir: Path) -> None:
    result = ConfigManager(config_dir).load_setup()
    assert result["version"] == "1.00"
    assert result["article"]["target_pages"] == 15
    assert result["agents"]["model"] == "claude-sonnet-4-5"


def test_load_setup_version_mismatch_raises(tmp_path: Path) -> None:
    bad = {"setup": {"version": "9.99", "article": {}, "agents": {}}}
    (tmp_path / "setup.json").write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(ConfigVersionError, match="9.99"):
        ConfigManager(tmp_path).load_setup()


def test_load_setup_missing_root_key_raises(tmp_path: Path) -> None:
    (tmp_path / "setup.json").write_text(json.dumps({"wrong": {}}), encoding="utf-8")
    with pytest.raises(ConfigKeyError, match="setup"):
        ConfigManager(tmp_path).load_setup()


def test_load_setup_missing_article_key_raises(tmp_path: Path) -> None:
    bad = {"setup": {"version": "1.00", "agents": {}}}
    (tmp_path / "setup.json").write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(ConfigKeyError, match="article"):
        ConfigManager(tmp_path).load_setup()


def test_load_setup_missing_agents_key_raises(tmp_path: Path) -> None:
    bad = {"setup": {"version": "1.00", "article": {}}}
    (tmp_path / "setup.json").write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(ConfigKeyError, match="agents"):
        ConfigManager(tmp_path).load_setup()


# ---------------------------------------------------------------------------
# load_rate_limits
# ---------------------------------------------------------------------------

def test_load_rate_limits_returns_service_limits(config_dir: Path) -> None:
    result = ConfigManager(config_dir).load_rate_limits()
    assert "serper" in result
    limits = result["serper"]
    assert isinstance(limits, ServiceLimits)
    assert limits.requests_per_minute == 10
    assert limits.max_queue_depth == 20


def test_load_rate_limits_version_mismatch_raises(tmp_path: Path) -> None:
    bad = {"rate_limits": {"version": "0.00", "services": {}}}
    (tmp_path / "rate_limits.json").write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(ConfigVersionError, match="0.00"):
        ConfigManager(tmp_path).load_rate_limits()


def test_load_rate_limits_missing_services_raises(tmp_path: Path) -> None:
    bad = {"rate_limits": {"version": "1.01", "providers": {}}}
    (tmp_path / "rate_limits.json").write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(ConfigKeyError, match="services"):
        ConfigManager(tmp_path).load_rate_limits()


def test_load_rate_limits_tokens_per_minute_loaded(config_dir: Path) -> None:
    result = ConfigManager(config_dir).load_rate_limits()
    assert result["serper"].tokens_per_minute == 0


# ---------------------------------------------------------------------------
# load_provider_limits
# ---------------------------------------------------------------------------

def test_load_provider_limits_returns_service_limits(config_dir: Path) -> None:
    limits = ConfigManager(config_dir).load_provider_limits("claude", "free")
    assert isinstance(limits, ServiceLimits)
    assert limits.requests_per_minute == 5
    assert limits.tokens_per_minute == 20000
    assert limits.retry_after_seconds == 60


def test_load_provider_limits_unknown_provider_raises(config_dir: Path) -> None:
    with pytest.raises(ConfigKeyError, match="gemini"):
        ConfigManager(config_dir).load_provider_limits("gemini", "free")


def test_load_provider_limits_unknown_tier_raises(config_dir: Path) -> None:
    with pytest.raises(ConfigKeyError, match="pro"):
        ConfigManager(config_dir).load_provider_limits("claude", "pro")


def test_load_provider_limits_missing_providers_raises(tmp_path: Path) -> None:
    bad = {"rate_limits": {"version": "1.01", "services": {}}}
    (tmp_path / "rate_limits.json").write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(ConfigKeyError, match="providers"):
        ConfigManager(tmp_path).load_provider_limits("claude", "free")


# ---------------------------------------------------------------------------
# load_pricing
# ---------------------------------------------------------------------------

def test_load_pricing_returns_model_pricing(config_dir: Path) -> None:
    result = ConfigManager(config_dir).load_pricing()
    assert "claude-sonnet-4-5" in result
    pricing = result["claude-sonnet-4-5"]
    assert isinstance(pricing, ModelPricing)
    assert pricing.input_price_per_mtok == 3.00
    assert pricing.provider == "Anthropic"


def test_load_pricing_version_mismatch_raises(tmp_path: Path) -> None:
    bad = {"model_pricing": {"version": "2.00", "models": {}}}
    (tmp_path / "model_pricing.json").write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(ConfigVersionError, match="2.00"):
        ConfigManager(tmp_path).load_pricing()


def test_load_pricing_missing_models_raises(tmp_path: Path) -> None:
    bad = {"model_pricing": {"version": "1.00"}}
    (tmp_path / "model_pricing.json").write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(ConfigKeyError, match="models"):
        ConfigManager(tmp_path).load_pricing()


# ---------------------------------------------------------------------------
# File not found
# ---------------------------------------------------------------------------

def test_missing_file_raises_file_not_found(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="setup.json"):
        ConfigManager(tmp_path).load_setup()


def test_custom_config_dir_is_used(config_dir: Path) -> None:
    mgr = ConfigManager(config_dir)
    assert mgr._dir == config_dir


def test_default_config_dir_is_project_config(tmp_path: Path) -> None:
    from article_generator.constants import CONFIG_DIR
    mgr = ConfigManager()
    assert mgr._dir == CONFIG_DIR
