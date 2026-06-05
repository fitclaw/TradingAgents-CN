"""Shared model catalog used by CLI prompts and lightweight validation."""

from __future__ import annotations

from typing import Dict, List, Tuple

ModelOption = Tuple[str, str]
ProviderModeOptions = Dict[str, Dict[str, List[ModelOption]]]


MODEL_OPTIONS: ProviderModeOptions = {
    "openai": {
        "quick": [
            ("GPT-4o Mini - Fast and cost-effective", "gpt-4o-mini"),
            ("GPT-4.1 Mini - Compact, capable", "gpt-4.1-mini"),
            ("GPT-4.1 Nano - Lightweight", "gpt-4.1-nano"),
            ("Custom model ID", "custom"),
        ],
        "deep": [
            ("o4-mini - Reasoning focused", "o4-mini"),
            ("o3-mini - Advanced reasoning", "o3-mini"),
            ("GPT-4o - Balanced general model", "gpt-4o"),
            ("Custom model ID", "custom"),
        ],
    },
    "anthropic": {
        "quick": [
            ("Claude Haiku 3.5 - Fast responses", "claude-3-5-haiku-latest"),
            ("Claude Sonnet 3.5 - Balanced", "claude-3-5-sonnet-latest"),
            ("Claude Sonnet 3.7 - Strong reasoning", "claude-3-7-sonnet-latest"),
            ("Custom model ID", "custom"),
        ],
        "deep": [
            ("Claude Sonnet 3.7 - Strong reasoning", "claude-3-7-sonnet-latest"),
            ("Claude Sonnet 4 - High performance", "claude-sonnet-4-0"),
            ("Claude Opus 4 - Max capability", "claude-opus-4-0"),
            ("Custom model ID", "custom"),
        ],
    },
    "google": {
        "quick": [
            ("Gemini 2.5 Flash - Fast", "gemini-2.5-flash"),
            ("Gemini 2.5 Flash Lite - Low cost", "gemini-2.5-flash-lite"),
            ("Gemini 2.0 Flash - Stable", "gemini-2.0-flash"),
            ("Custom model ID", "custom"),
        ],
        "deep": [
            ("Gemini 2.5 Pro - Strong reasoning", "gemini-2.5-pro"),
            ("Gemini 2.5 Pro-002 - Updated", "gemini-2.5-pro-002"),
            ("Gemini 1.5 Pro - Compatibility fallback", "gemini-1.5-pro"),
            ("Custom model ID", "custom"),
        ],
    },
    "deepseek": {
        "quick": [
            ("DeepSeek V4 Flash - Fast", "deepseek-v4-flash"),
            ("Custom model ID", "custom"),
        ],
        "deep": [
            ("DeepSeek V4 Pro - Strong reasoning", "deepseek-v4-pro"),
            ("Custom model ID", "custom"),
        ],
    },
    "minimax_tokenplan": {
        "quick": [
            ("MiniMax M3 - Token Plan", "MiniMax-M3"),
            ("MiniMax M2.7 Highspeed - Token Plan", "MiniMax-M2.7-highspeed"),
            ("Custom model ID", "custom"),
        ],
        "deep": [
            ("MiniMax M3 - Token Plan", "MiniMax-M3"),
            ("MiniMax M2.7 - Token Plan", "MiniMax-M2.7"),
            ("Custom model ID", "custom"),
        ],
    },
    "kimi_code": {
        "quick": [
            ("Kimi for Coding - Token Plan", "kimi-for-coding"),
            ("Custom model ID", "custom"),
        ],
        "deep": [
            ("Kimi for Coding - Token Plan", "kimi-for-coding"),
            ("Custom model ID", "custom"),
        ],
    },
    "moonshot": {
        "quick": [
            ("Kimi K2.6", "kimi-k2.6"),
            ("Kimi K2.5", "kimi-k2.5"),
            ("Custom model ID", "custom"),
        ],
        "deep": [
            ("Kimi K2.6", "kimi-k2.6"),
            ("Moonshot v1 128K", "moonshot-v1-128k"),
            ("Custom model ID", "custom"),
        ],
    },
    "qwen": {
        "quick": [
            ("Qwen3.7 Plus - Balanced latest", "qwen3.7-plus"),
            ("Qwen3.6 Flash - Fast multimodal", "qwen3.6-flash"),
            ("Qwen3-VL Flash - Fast vision", "qwen3-vl-flash"),
            ("Custom model ID", "custom"),
        ],
        "deep": [
            ("Qwen3.7 Max - Strongest reasoning", "qwen3.7-max"),
            ("Qwen3.7 Plus - Balanced latest", "qwen3.7-plus"),
            ("Qwen3.6 Plus - Multimodal long context", "qwen3.6-plus"),
            ("Qwen3-VL Plus - Vision flagship", "qwen3-vl-plus"),
            ("Qwen VL OCR Latest - Document OCR", "qwen-vl-ocr-latest"),
            ("Qwen3 Omni Flash - Omni fast", "qwen3-omni-flash"),
            ("Custom model ID", "custom"),
        ],
    },
    "openrouter": {
        "quick": [
            ("Custom model ID", "custom"),
        ],
        "deep": [
            ("Custom model ID", "custom"),
        ],
    },
    "aihubmix": {
        "quick": [
            ("GPT-4o Mini", "gpt-4o-mini"),
            ("Custom model ID", "custom"),
        ],
        "deep": [
            ("GPT-4o", "gpt-4o"),
            ("Custom model ID", "custom"),
        ],
    },
    "ollama": {
        "quick": [
            ("llama3.1", "llama3.1"),
            ("qwen3", "qwen3"),
            ("Custom model ID", "custom"),
        ],
        "deep": [
            ("qwen3", "qwen3"),
            ("llama3.1", "llama3.1"),
            ("Custom model ID", "custom"),
        ],
    },
    "glm": {
        "quick": [
            ("GLM-4-Flash", "glm-4-flash"),
            ("GLM-4-Air", "glm-4-air"),
            ("Custom model ID", "custom"),
        ],
        "deep": [
            ("GLM-4-Plus", "glm-4-plus"),
            ("GLM-4-Long", "glm-4-long"),
            ("Custom model ID", "custom"),
        ],
    },
    "custom_openai": {
        "quick": [
            ("GPT-4o Mini", "gpt-4o-mini"),
            ("GPT-4o", "gpt-4o"),
            ("Custom model ID", "custom"),
        ],
        "deep": [
            ("GPT-4o", "gpt-4o"),
            ("o1", "o1"),
            ("Custom model ID", "custom"),
        ],
    },
}


def get_model_options(provider: str, mode: str) -> List[ModelOption]:
    return MODEL_OPTIONS[provider.lower()][mode]


def get_known_models() -> Dict[str, List[str]]:
    return {
        provider: sorted(
            {
                value
                for options in mode_options.values()
                for _, value in options
                if value != "custom"
            }
        )
        for provider, mode_options in MODEL_OPTIONS.items()
    }
