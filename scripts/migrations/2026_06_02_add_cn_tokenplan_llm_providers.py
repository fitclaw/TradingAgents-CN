#!/usr/bin/env python3
"""Add CN TokenPlan LLM providers and refresh DeepSeek model entries.

Default mode is dry-run. Pass --apply to write MongoDB changes.
"""

from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pymongo import MongoClient

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import settings  # noqa: E402


OLD_DEEPSEEK_MODELS = {"deepseek-chat", "deepseek-reasoner", "deepseek-coder"}

PROVIDERS = [
    {
        "name": "deepseek",
        "display_name": "DeepSeek",
        "description": "DeepSeek V4 API provider.",
        "website": "https://www.deepseek.com",
        "api_doc_url": "https://platform.deepseek.com/api-docs",
        "default_base_url": "https://api.deepseek.com",
        "supported_features": ["chat", "completion", "function_calling", "streaming"],
        "is_active": True,
        "aliases": [],
        "extra_config": {"env_key": "DEEPSEEK_API_KEY"},
    },
    {
        "name": "minimax_tokenplan",
        "display_name": "MiniMax Token Plan",
        "description": "MiniMax Token Plan CN endpoint. Uses MINIMAX_TOKEN_PLAN_API_KEY.",
        "website": "https://platform.minimaxi.com",
        "api_doc_url": "https://platform.minimaxi.com/docs/api-reference/text-openai-api",
        "default_base_url": "https://api.minimaxi.com/v1",
        "supported_features": ["chat", "completion", "function_calling", "streaming"],
        "is_active": True,
        "aliases": [],
        "extra_config": {"env_key": "MINIMAX_TOKEN_PLAN_API_KEY"},
    },
    {
        "name": "kimi_code",
        "display_name": "Kimi Code Token Plan",
        "description": "Kimi Code Token Plan CN endpoint. Uses KIMI_CODE_API_KEY.",
        "website": "https://www.kimi.com",
        "api_doc_url": "https://www.kimi.com/code/docs",
        "default_base_url": "https://api.kimi.com/coding/v1",
        "supported_features": ["chat", "completion", "function_calling", "streaming"],
        "is_active": True,
        "aliases": [],
        "extra_config": {"env_key": "KIMI_CODE_API_KEY"},
    },
    {
        "name": "moonshot",
        "display_name": "Kimi / Moonshot API",
        "description": "Kimi CN open platform endpoint. Uses MOONSHOT_API_KEY.",
        "website": "https://platform.kimi.com",
        "api_doc_url": "https://platform.kimi.com/docs/api/overview",
        "default_base_url": "https://api.moonshot.cn/v1",
        "supported_features": ["chat", "completion", "function_calling", "streaming"],
        "is_active": True,
        "aliases": [],
        "extra_config": {"env_key": "MOONSHOT_API_KEY"},
    },
]

CATALOGS = [
    {
        "provider": "deepseek",
        "provider_name": "DeepSeek",
        "models": [
            {
                "name": "deepseek-v4-flash",
                "display_name": "DeepSeek V4 Flash - Fast analysis",
                "currency": "CNY",
                "capabilities": ["tool_calling", "long_context", "fast_response", "cost_effective"],
            },
            {
                "name": "deepseek-v4-pro",
                "display_name": "DeepSeek V4 Pro - Deep reasoning",
                "currency": "CNY",
                "capabilities": ["tool_calling", "long_context", "reasoning"],
            },
        ],
    },
    {
        "provider": "minimax_tokenplan",
        "provider_name": "MiniMax Token Plan",
        "models": [
            {"name": "MiniMax-M3", "display_name": "MiniMax M3 - Token Plan", "currency": "CNY"},
            {"name": "MiniMax-M2.7", "display_name": "MiniMax M2.7 - Token Plan", "currency": "CNY"},
            {
                "name": "MiniMax-M2.7-highspeed",
                "display_name": "MiniMax M2.7 Highspeed - Token Plan",
                "currency": "CNY",
            },
        ],
    },
    {
        "provider": "kimi_code",
        "provider_name": "Kimi Code Token Plan",
        "models": [
            {"name": "kimi-for-coding", "display_name": "Kimi for Coding - Token Plan", "currency": "CNY"},
        ],
    },
    {
        "provider": "moonshot",
        "provider_name": "Kimi / Moonshot API",
        "models": [
            {"name": "kimi-k2.6", "display_name": "Kimi K2.6", "currency": "CNY"},
            {"name": "kimi-k2.5", "display_name": "Kimi K2.5", "currency": "CNY"},
            {"name": "moonshot-v1-128k", "display_name": "Moonshot v1 128K", "currency": "CNY"},
        ],
    },
]

LLM_CONFIGS = [
    {
        "provider": "deepseek",
        "model_name": "deepseek-v4-flash",
        "model_display_name": "DeepSeek V4 Flash",
        "max_tokens": 6000,
        "temperature": 0.7,
        "timeout": 120,
        "retry_times": 3,
        "enabled": True,
        "currency": "CNY",
        "capability_level": 4,
        "suitable_roles": ["both"],
        "features": ["tool_calling", "long_context", "fast_response", "cost_effective"],
        "recommended_depths": ["快速", "基础", "标准", "深度"],
    },
    {
        "provider": "deepseek",
        "model_name": "deepseek-v4-pro",
        "model_display_name": "DeepSeek V4 Pro",
        "max_tokens": 8000,
        "temperature": 0.7,
        "timeout": 180,
        "retry_times": 3,
        "enabled": True,
        "currency": "CNY",
        "capability_level": 5,
        "suitable_roles": ["deep_analysis"],
        "features": ["tool_calling", "long_context", "reasoning"],
        "recommended_depths": ["标准", "深度", "全面"],
    },
    {
        "provider": "minimax_tokenplan",
        "model_name": "MiniMax-M3",
        "model_display_name": "MiniMax M3 - Token Plan",
        "max_tokens": 8000,
        "temperature": 0.7,
        "timeout": 180,
        "retry_times": 3,
        "enabled": True,
        "currency": "CNY",
        "capability_level": 4,
        "suitable_roles": ["both"],
        "features": ["tool_calling", "long_context", "reasoning"],
        "recommended_depths": ["快速", "基础", "标准", "深度"],
    },
    {
        "provider": "minimax_tokenplan",
        "model_name": "MiniMax-M2.7",
        "model_display_name": "MiniMax M2.7 - Token Plan",
        "max_tokens": 8000,
        "temperature": 0.7,
        "timeout": 180,
        "retry_times": 3,
        "enabled": True,
        "currency": "CNY",
        "capability_level": 3,
        "suitable_roles": ["both"],
        "features": ["tool_calling", "long_context"],
        "recommended_depths": ["快速", "基础", "标准"],
    },
    {
        "provider": "minimax_tokenplan",
        "model_name": "MiniMax-M2.7-highspeed",
        "model_display_name": "MiniMax M2.7 Highspeed - Token Plan",
        "max_tokens": 6000,
        "temperature": 0.7,
        "timeout": 120,
        "retry_times": 3,
        "enabled": True,
        "currency": "CNY",
        "capability_level": 3,
        "suitable_roles": ["quick_analysis"],
        "features": ["tool_calling", "fast_response", "cost_effective"],
        "recommended_depths": ["快速", "基础", "标准"],
    },
    {
        "provider": "kimi_code",
        "model_name": "kimi-for-coding",
        "model_display_name": "Kimi for Coding - Token Plan",
        "max_tokens": 8000,
        "temperature": 0.7,
        "timeout": 180,
        "retry_times": 3,
        "enabled": True,
        "currency": "CNY",
        "capability_level": 4,
        "suitable_roles": ["both"],
        "features": ["tool_calling", "long_context", "reasoning"],
        "recommended_depths": ["快速", "基础", "标准", "深度"],
    },
    {
        "provider": "moonshot",
        "model_name": "kimi-k2.6",
        "model_display_name": "Kimi K2.6",
        "max_tokens": 8000,
        "temperature": 0.7,
        "timeout": 180,
        "retry_times": 3,
        "enabled": True,
        "currency": "CNY",
        "capability_level": 5,
        "suitable_roles": ["both"],
        "features": ["tool_calling", "long_context", "reasoning"],
        "recommended_depths": ["标准", "深度", "全面"],
    },
    {
        "provider": "moonshot",
        "model_name": "kimi-k2.5",
        "model_display_name": "Kimi K2.5",
        "max_tokens": 8000,
        "temperature": 0.7,
        "timeout": 180,
        "retry_times": 3,
        "enabled": True,
        "currency": "CNY",
        "capability_level": 4,
        "suitable_roles": ["both"],
        "features": ["tool_calling", "long_context", "reasoning"],
        "recommended_depths": ["基础", "标准", "深度"],
    },
    {
        "provider": "moonshot",
        "model_name": "moonshot-v1-128k",
        "model_display_name": "Moonshot v1 128K",
        "max_tokens": 8000,
        "temperature": 0.7,
        "timeout": 180,
        "retry_times": 3,
        "enabled": True,
        "currency": "CNY",
        "capability_level": 4,
        "suitable_roles": ["deep_analysis"],
        "features": ["tool_calling", "long_context", "reasoning"],
        "recommended_depths": ["标准", "深度", "全面"],
    },
]


def now() -> datetime:
    return datetime.now(timezone.utc)


def compact_list(items: list[dict[str, Any]], key: str) -> list[str]:
    return [str(item.get(key)) for item in items if item.get(key)]


def clean_llm_config(config: dict[str, Any]) -> dict[str, Any]:
    item = {
        "api_key": "",
        "api_base": "",
        "description": "",
        "model_category": "",
        "custom_endpoint": None,
        "enable_memory": False,
        "enable_debug": False,
        "priority": 0,
        "input_price_per_1k": None,
        "output_price_per_1k": None,
        "performance_metrics": {"speed": 3, "cost": 3, "quality": 3},
        "created_at": now(),
        "updated_at": now(),
    }
    item.update(config)
    return item


def build_updated_llm_configs(existing: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    kept = [cfg for cfg in existing if cfg.get("model_name") not in OLD_DEEPSEEK_MODELS]
    existing_names = {cfg.get("model_name") for cfg in kept}
    additions = [clean_llm_config(cfg) for cfg in LLM_CONFIGS if cfg["model_name"] not in existing_names]
    return kept + additions, {
        "removed_old_deepseek": len(existing) - len(kept),
        "added_models": compact_list(additions, "model_name"),
    }


def summarize(db) -> dict[str, Any]:
    providers = list(
        db.llm_providers.find(
            {"name": {"$in": [provider["name"] for provider in PROVIDERS]}},
            {"_id": 0, "name": 1, "default_base_url": 1},
        )
    )
    catalogs = list(
        db.model_catalog.find(
            {"provider": {"$in": [catalog["provider"] for catalog in CATALOGS]}},
            {"_id": 0, "provider": 1, "models.name": 1},
        )
    )
    config = db.system_configs.find_one({"is_active": True}, sort=[("version", -1)])
    llm_models = []
    if config:
        llm_models = [
            item.get("model_name")
            for item in config.get("llm_configs", [])
            if item.get("provider") in {"deepseek", "minimax_tokenplan", "kimi_code", "moonshot"}
        ]
    return {"providers": providers, "catalogs": catalogs, "llm_models": llm_models}


def print_json(title: str, data: Any) -> None:
    print(f"\n{title}")
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str))


def run(apply: bool) -> int:
    client = MongoClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB]
    timestamp = now()

    before = summarize(db)
    print_json("Before", before)

    active_config = db.system_configs.find_one({"is_active": True}, sort=[("version", -1)])
    if not active_config:
        print("ERROR: No active system config found.")
        return 1

    default_llm = active_config.get("default_llm")
    if default_llm in OLD_DEEPSEEK_MODELS:
        print(f"ERROR: default_llm is old DeepSeek model {default_llm}. Please choose a new default manually.")
        return 2

    updated_llm_configs, llm_change = build_updated_llm_configs(active_config.get("llm_configs", []))

    planned = {
        "providers_upsert": compact_list(PROVIDERS, "name"),
        "catalogs_upsert": compact_list(CATALOGS, "provider"),
        "llm_config_change": llm_change,
        "mode": "apply" if apply else "dry-run",
    }
    print_json("Planned changes", planned)

    if not apply:
        print("\nDry-run only. Re-run with --apply to write changes.")
        return 0

    for provider in PROVIDERS:
        doc = deepcopy(provider)
        doc["updated_at"] = timestamp
        db.llm_providers.update_one(
            {"name": doc["name"]},
            {
                "$set": doc,
                "$setOnInsert": {"created_at": timestamp, "api_key": None, "api_secret": None},
            },
            upsert=True,
        )

    for catalog in CATALOGS:
        doc = deepcopy(catalog)
        doc["updated_at"] = timestamp
        db.model_catalog.update_one(
            {"provider": doc["provider"]},
            {
                "$set": doc,
                "$setOnInsert": {"created_at": timestamp},
            },
            upsert=True,
        )

    db.system_configs.update_one(
        {"_id": active_config["_id"]},
        {
            "$set": {
                "llm_configs": updated_llm_configs,
                "updated_at": timestamp,
                "version": int(active_config.get("version", 0)) + 1,
            }
        },
    )

    after = summarize(db)
    print_json("After", after)
    print("\nMigration applied.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Write changes to MongoDB")
    args = parser.parse_args()
    return run(apply=args.apply)


if __name__ == "__main__":
    raise SystemExit(main())
