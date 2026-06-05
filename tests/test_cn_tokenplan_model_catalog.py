from app.services.config_service import ConfigService


def _catalog_by_provider():
    service = ConfigService()
    return {item["provider"]: item for item in service._get_default_model_catalog()}


def test_default_catalog_has_cn_tokenplan_providers():
    catalogs = _catalog_by_provider()

    assert catalogs["minimax_tokenplan"]["models"][0]["name"] == "MiniMax-M3"
    assert [model["name"] for model in catalogs["kimi_code"]["models"]] == ["kimi-for-coding"]
    assert "kimi-k2.6" in [model["name"] for model in catalogs["moonshot"]["models"]]


def test_default_deepseek_catalog_uses_v4_only():
    deepseek_models = [model["name"] for model in _catalog_by_provider()["deepseek"]["models"]]

    assert deepseek_models == ["deepseek-v4-flash", "deepseek-v4-pro"]


def test_default_dashscope_catalog_uses_latest_bailian_models():
    dashscope_models = [model["name"] for model in _catalog_by_provider()["dashscope"]["models"]]

    assert dashscope_models[:4] == [
        "qwen3.7-plus",
        "qwen3.7-max",
        "qwen3.6-plus",
        "qwen3.6-flash",
    ]
    assert "qwen3-vl-plus" in dashscope_models
    assert "qwen3-vl-flash" in dashscope_models
    assert "qwen-vl-ocr-latest" in dashscope_models
    assert "qwen3-omni-flash" in dashscope_models
