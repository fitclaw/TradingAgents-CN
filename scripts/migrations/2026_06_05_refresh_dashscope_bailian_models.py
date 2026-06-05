"""Refresh Alibaba Cloud Model Studio (DashScope/Bailian) model entries.

Default mode is dry-run. Use --apply to update local MongoDB.
This migration does not write API keys and does not change default models.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from pymongo import MongoClient


MONGO_URI = "mongodb://localhost:27017/tradingagentscn"
DB_NAME = "tradingagentscn"

DASHSCOPE_PROVIDER = {
    "name": "dashscope",
    "display_name": "阿里云百炼",
    "description": "阿里云百炼大模型服务平台，提供 Qwen3.7、Qwen3.6、Qwen3-VL、OCR、Omni 等文本与多模态模型。",
    "website": "https://bailian.console.aliyun.com",
    "api_doc_url": "https://help.aliyun.com/zh/model-studio/",
    "default_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "aliases": ["dashscope", "alibaba", "阿里百炼", "百炼"],
    "supported_features": [
        "chat",
        "completion",
        "embedding",
        "function_calling",
        "streaming",
        "vision",
        "image",
        "video",
        "ocr",
    ],
    "is_active": True,
}

DASHSCOPE_MODELS = [
    {
        "name": "qwen3.7-plus",
        "display_name": "Qwen3.7 Plus - 推荐平衡模型",
        "input_price_per_1k": 0.002,
        "output_price_per_1k": 0.008,
        "context_length": 1_000_000,
        "max_tokens": 65_536,
        "currency": "CNY",
        "capabilities": ["chat", "function_calling", "reasoning", "long_context", "structured_output", "builtin_tools"],
        "description": "百炼推荐平衡模型，支持 1M 上下文、思考模式、函数调用、内置工具与结构化输出。",
    },
    {
        "name": "qwen3.7-max",
        "display_name": "Qwen3.7 Max - 最强推理",
        "input_price_per_1k": 0.012,
        "output_price_per_1k": 0.036,
        "context_length": 1_000_000,
        "max_tokens": 65_536,
        "currency": "CNY",
        "capabilities": ["chat", "function_calling", "reasoning", "long_context", "structured_output", "builtin_tools"],
        "description": "Qwen Max 系列新一代旗舰模型，适合复杂推理、编程与长周期任务。",
    },
    {
        "name": "qwen3.6-plus",
        "display_name": "Qwen3.6 Plus - 多模态平衡",
        "input_price_per_1k": 0.002,
        "output_price_per_1k": 0.012,
        "context_length": 1_000_000,
        "max_tokens": 65_536,
        "currency": "CNY",
        "capabilities": ["chat", "vision", "video", "function_calling", "reasoning", "long_context", "structured_output", "builtin_tools"],
        "description": "支持文本、图像、视频输入，适合多模态金融图表识别和通用分析。",
    },
    {
        "name": "qwen3.6-flash",
        "display_name": "Qwen3.6 Flash - 多模态快速",
        "context_length": 1_000_000,
        "max_tokens": 65_536,
        "currency": "CNY",
        "capabilities": ["chat", "vision", "video", "function_calling", "reasoning", "long_context", "structured_output", "builtin_tools", "cost_effective"],
        "description": "接近旗舰效果的低成本快速模型，支持图像、视频理解与工具调用。",
    },
    {
        "name": "qwen3-vl-plus",
        "display_name": "Qwen3-VL Plus - 视觉理解旗舰",
        "context_length": 262_144,
        "max_tokens": 32_768,
        "currency": "CNY",
        "capabilities": ["vision", "video", "ocr", "function_calling", "reasoning", "structured_output"],
        "description": "Qwen3-VL 稳定版视觉理解模型，适合图片、视频、图表和文档识别。",
    },
    {
        "name": "qwen3-vl-flash",
        "display_name": "Qwen3-VL Flash - 视觉理解快速",
        "context_length": 258_048,
        "max_tokens": 32_768,
        "currency": "CNY",
        "capabilities": ["vision", "video", "ocr", "function_calling", "reasoning", "structured_output", "cost_effective"],
        "description": "Qwen3-VL 快速视觉模型，适合低成本图像识别和视频理解。",
    },
    {
        "name": "qwen-vl-ocr-latest",
        "display_name": "Qwen VL OCR Latest - 文档识别",
        "currency": "CNY",
        "capabilities": ["vision", "ocr", "document_extraction"],
        "description": "面向文档、表格、试卷和手写内容的 OCR/文档提取模型。",
    },
    {
        "name": "qwen3-omni-flash",
        "display_name": "Qwen3 Omni Flash - 全模态快速",
        "currency": "CNY",
        "capabilities": ["vision", "audio", "video", "omni", "fast_response"],
        "description": "千问全模态快速模型，覆盖图像、音频和视频理解场景。",
    },
]


def now() -> datetime:
    return datetime.now(timezone.utc)


def summarize_models(models: list[dict[str, Any]]) -> list[str]:
    return [str(model.get("name")) for model in models]


def build_llm_config(model: dict[str, Any]) -> dict[str, Any]:
    capabilities = list(model.get("capabilities") or [])
    is_fast = "flash" in model["name"] or "ocr" in model["name"] or "omni" in model["name"]
    has_vision = any(item in capabilities for item in ("vision", "video", "ocr", "audio", "omni"))
    capability_level = 5 if model["name"] in {"qwen3.7-plus", "qwen3.7-max", "qwen3.6-plus"} else 4 if has_vision else 3
    role = ["quick_analysis"] if is_fast else ["both"]

    return {
        "provider": "dashscope",
        "model_name": model["name"],
        "model_display_name": model["display_name"],
        "api_key": "",
        "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "max_tokens": model.get("max_tokens") or 4000,
        "temperature": 0.7,
        "timeout": 180,
        "retry_times": 3,
        "enabled": True,
        "description": model.get("description"),
        "input_price_per_1k": model.get("input_price_per_1k"),
        "output_price_per_1k": model.get("output_price_per_1k"),
        "currency": model.get("currency", "CNY"),
        "capability_level": capability_level,
        "suitable_roles": role,
        "features": capabilities,
        "recommended_depths": ["快速", "基础", "标准", "深度"] if is_fast else ["基础", "标准", "深度", "全面"],
        "performance_metrics": {"speed": 5 if is_fast else 4, "cost": 4, "quality": 4 if is_fast else 5},
        "created_at": now(),
        "updated_at": now(),
    }


def active_config(db):
    return db.system_configs.find_one({"is_active": True}, sort=[("version", -1)])


def dry_run_summary(db) -> dict[str, Any]:
    provider = db.llm_providers.find_one({"name": "dashscope"}, {"api_key": 0})
    catalog = db.model_catalog.find_one({"provider": "dashscope"}, {"models.name": 1, "provider": 1})
    config = active_config(db) or {}
    llm_configs = config.get("llm_configs") or []
    dashscope_llm = [
        item.get("model_name")
        for item in llm_configs
        if item.get("provider") in {"dashscope", "qwen"} or str(item.get("model_name", "")).startswith("qwen")
    ]

    return {
        "provider_before": provider,
        "catalog_before": summarize_models(catalog.get("models", [])) if catalog else [],
        "llm_configs_before": dashscope_llm,
        "provider_after": {key: value for key, value in DASHSCOPE_PROVIDER.items() if key != "api_key"},
        "catalog_after": summarize_models(DASHSCOPE_MODELS),
        "llm_configs_to_add": summarize_models(DASHSCOPE_MODELS),
    }


def apply(db) -> dict[str, Any]:
    stamp = now()

    provider_update = deepcopy(DASHSCOPE_PROVIDER)
    provider_update["updated_at"] = stamp
    db.llm_providers.update_one(
        {"name": "dashscope"},
        {
            "$set": provider_update,
            "$setOnInsert": {"created_at": stamp, "api_key": ""},
        },
        upsert=True,
    )

    db.model_catalog.update_one(
        {"provider": "dashscope"},
        {
            "$set": {
                "provider": "dashscope",
                "provider_name": "阿里云百炼",
                "models": deepcopy(DASHSCOPE_MODELS),
                "updated_at": stamp,
            },
            "$setOnInsert": {"created_at": stamp},
        },
        upsert=True,
    )

    config = active_config(db)
    added = []
    if config:
        llm_configs = list(config.get("llm_configs") or [])
        existing = {
            (item.get("provider"), item.get("model_name"))
            for item in llm_configs
        }
        for model in DASHSCOPE_MODELS:
            key = ("dashscope", model["name"])
            if key not in existing:
                llm_configs.append(build_llm_config(model))
                added.append(model["name"])

        db.system_configs.update_one(
            {"_id": config["_id"]},
            {
                "$set": {
                    "llm_configs": llm_configs,
                    "updated_at": stamp,
                },
                "$inc": {"version": 1},
            },
        )

    return {
        "provider": "dashscope",
        "catalog_models": summarize_models(DASHSCOPE_MODELS),
        "llm_configs_added": added,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mongo-uri", default=MONGO_URI)
    parser.add_argument("--db", default=DB_NAME)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    client = MongoClient(args.mongo_uri)
    db = client[args.db]

    summary = dry_run_summary(db)
    print("=== DashScope/Bailian refresh plan ===")
    for key, value in summary.items():
        print(f"{key}: {value}")

    if not args.apply:
        print("\nDry-run only. Re-run with --apply to write changes.")
        return

    result = apply(db)
    print("\n=== Applied ===")
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
