# -*- coding: utf-8 -*-
"""配置读取工具

读取 `.sightconfig.json` 配置文件。

搜索顺序（从上到下，取第一个存在的）：
1. 当前工作目录
2. stocksight 技能目录
3. 用户主目录

配置文件格式示例：
```json
{
  "stock_sight": {
    "news_provider": "tavily",
    "tavily": {
      "api_key": "tvly-xxx"
    }
  }
}
```
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

_CONFIG_FILENAME = ".sightconfig.json"
_CONFIG_KEY = "stock_sight"

# 技能根目录（与 config.py 同级 → 上两级 = skills/stocksight）
_SKILL_DIR = Path(__file__).resolve().parent.parent


def _find_config_file() -> Optional[Path]:
    """按优先级搜索配置文件"""
    search_dirs = [
        Path.cwd(),
        _SKILL_DIR,
        Path.home(),
    ]
    for d in search_dirs:
        candidate = d / _CONFIG_FILENAME
        if candidate.exists():
            return candidate
    return None


def _load_config() -> dict:
    """加载配置（带缓存）"""
    path = _find_config_file()
    if path is None:
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            return cfg.get(_CONFIG_KEY, {})
    except (json.JSONDecodeError, OSError):
        return {}


def get_api_key(provider_name: str) -> Optional[str]:
    """获取指定 provider 的 API Key

    Args:
        provider_name: provider 名称，如 'tavily', 'serpapi'

    Returns:
        API Key 字符串，未配置返回 None
    """
    cfg = _load_config()
    provider_cfg = cfg.get(provider_name, {})
    key = provider_cfg.get("api_key")
    if key:
        return key
    # 兼容 DJ 列的几种 KEY 环境变量命名
    env_keys = {
        "tavily": "TAVILY_API_KEY",
        "serpapi": "SERPAPI_API_KEY",
        "brave": "BRAVE_API_KEY",
        "anaspire": "ANSPIRE_API_KEY",  # 带拼写差异的兼容
    }
    env_name = env_keys.get(provider_name)
    if env_name:
        return os.environ.get(env_name)
    return None


def get_active_provider() -> Optional[str]:
    """获取当前启用的 news provider 名称

    Returns:
        provider 名称，如 'tavily'，未配置返回 None
    """
    cfg = _load_config()
    return cfg.get("news_provider")
