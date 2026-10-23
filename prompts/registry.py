"""Prompt registry for mapping stable prompt ids to YAML files."""

from __future__ import annotations

from pathlib import Path

import yaml

from prompts.loader import PromptLoader, PromptTemplate


class PromptRegistry:
    """按 Prompt ID 读取模板，隐藏具体文件路径。

    prompts 目录中允许存在只有注释的占位 YAML 文件；这些文件用于保留后续模块位置，
    但不应该影响已经实现的 LLM 节点运行。
    """

    def __init__(self, root_dir: str | Path = "prompts") -> None:
        self.root_dir = Path(root_dir)
        self.loader = PromptLoader(root_dir=self.root_dir)
        self._index: dict[str, Path] = {}

    def scan(self) -> None:
        self._index.clear()

        for path in self.root_dir.rglob("*.yaml"):
            relative_path = path.relative_to(self.root_dir)
            if self._is_placeholder(path):
                continue

            template = self.loader.load(relative_path)
            self._index[template.id] = relative_path

    def get(self, prompt_id: str) -> PromptTemplate:
        if not self._index:
            self.scan()

        if prompt_id not in self._index:
            raise KeyError(f"Prompt not registered: {prompt_id}")

        return self.loader.load(self._index[prompt_id])

    def list_ids(self) -> list[str]:
        if not self._index:
            self.scan()

        return sorted(self._index.keys())

    @staticmethod
    def _is_placeholder(path: Path) -> bool:
        """判断是否为只有注释/空白的占位 Prompt 文件。"""

        return yaml.safe_load(path.read_text(encoding="utf-8")) is None
