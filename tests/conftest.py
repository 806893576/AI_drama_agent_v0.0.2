"""测试环境默认配置。

本地 `.env` 可能配置了真实 DeepSeek/OpenAI Key。测试默认强制使用 fake client，
避免集成测试误发真实 LLM 请求；需要验证真实配置解析的测试可用 monkeypatch 覆盖。
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

os.environ.setdefault("LLM_CLIENT", "fake")
os.environ.setdefault("DRAMA_STORAGE_DIR", "storage/pytest_tmp")

_pytest_storage = Path(os.environ["DRAMA_STORAGE_DIR"])
if _pytest_storage.exists():
    shutil.rmtree(_pytest_storage)
