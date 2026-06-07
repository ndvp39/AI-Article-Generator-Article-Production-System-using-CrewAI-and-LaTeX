from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from article_generator.constants import (
    CONFIG_DIR,
    MODEL_PRICING_CONFIG_FILE,
    MODEL_PRICING_CONFIG_VERSION,
    RATE_LIMITS_CONFIG_FILE,
    RATE_LIMITS_CONFIG_VERSION,
    SETUP_CONFIG_FILE,
    SETUP_CONFIG_VERSION,
)


class ConfigVersionError(Exception):
    pass


class ConfigKeyError(KeyError):
    pass


@dataclass
class ServiceLimits:
    requests_per_minute: int
    requests_per_hour: int
    concurrent_max: int
    retry_after_seconds: int
    max_retries: int
    max_queue_depth: int


@dataclass
class ModelPricing:
    display_name: str
    provider: str
    input_price_per_mtok: float
    output_price_per_mtok: float


class ConfigManager:
    def __init__(self, config_dir: Path | str = CONFIG_DIR) -> None:
        self._dir = Path(config_dir)

    def load_setup(self) -> dict:
        data = self._load(SETUP_CONFIG_FILE)
        root = self._require(data, "setup", SETUP_CONFIG_FILE)
        self._validate_version(root, SETUP_CONFIG_FILE, SETUP_CONFIG_VERSION)
        self._require(root, "article", SETUP_CONFIG_FILE)
        self._require(root, "agents", SETUP_CONFIG_FILE)
        return root

    def load_rate_limits(self) -> dict[str, ServiceLimits]:
        data = self._load(RATE_LIMITS_CONFIG_FILE)
        root = self._require(data, "rate_limits", RATE_LIMITS_CONFIG_FILE)
        self._validate_version(root, RATE_LIMITS_CONFIG_FILE, RATE_LIMITS_CONFIG_VERSION)
        services_raw = self._require(root, "services", RATE_LIMITS_CONFIG_FILE)
        return {name: ServiceLimits(**svc) for name, svc in services_raw.items()}

    def load_pricing(self) -> dict[str, ModelPricing]:
        data = self._load(MODEL_PRICING_CONFIG_FILE)
        root = self._require(data, "model_pricing", MODEL_PRICING_CONFIG_FILE)
        self._validate_version(root, MODEL_PRICING_CONFIG_FILE, MODEL_PRICING_CONFIG_VERSION)
        models_raw = self._require(root, "models", MODEL_PRICING_CONFIG_FILE)
        return {model_id: ModelPricing(**pricing) for model_id, pricing in models_raw.items()}

    def _load(self, filename: str) -> dict:
        path = self._dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        return json.loads(path.read_text(encoding="utf-8"))

    def _require(self, data: dict, key: str, filename: str) -> dict:
        if key not in data:
            raise ConfigKeyError(f"Required key '{key}' missing in {filename}")
        return data[key]

    def _validate_version(self, config: dict, filename: str, expected: str) -> None:
        version = config.get("version")
        if version != expected:
            raise ConfigVersionError(
                f"{filename}: expected version '{expected}', got '{version}'"
            )
