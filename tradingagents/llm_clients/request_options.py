"""Provider-specific request option normalization."""

from __future__ import annotations

from typing import Any, Mapping


def requires_temperature_one(provider: str, model: str) -> bool:
    """Return whether the provider/model only accepts temperature=1."""
    provider_key = (provider or "").lower().replace("-", "_")
    model_key = (model or "").lower()

    return provider_key == "moonshot" and model_key.startswith("kimi-k2")


def normalize_request_options(provider: str, model: str, options: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize request options for provider/model-specific API constraints."""
    normalized = dict(options)

    if requires_temperature_one(provider, model):
        normalized["temperature"] = 1

    return normalized
